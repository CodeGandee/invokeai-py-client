#!/usr/bin/env python
"""End-to-end test for SDXL Text-to-Image workflow submission."""

from __future__ import annotations

import os
import sys
import json
import time
from pathlib import Path
from typing import Any
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowRepository
from invokeai_py_client.dnn_model import DnnModelRepository, DnnModelType, BaseDnnModelType


# Configuration
TEST_PROMPT = "A futuristic city skyline with flying cars, cyberpunk aesthetic, neon lights, detailed architecture"
TEST_NEGATIVE = "blurry, low quality, distorted, ugly"
OUTPUT_WIDTH = 1024
OUTPUT_HEIGHT = 1024
NUM_STEPS = 24  # reduced for faster test runtime
CFG_SCALE = 7.0
SCHEDULER = "euler"


def select_sdxl_models(repo: DnnModelRepository) -> dict[str, Any]:
    """Select SDXL main (and optional VAE) models by name preference then fallback.

    Preference order for main model names (substring match, case-insensitive):
      1. "juggernaut"
      2. "cyberrealistic"
      3. first SDXL main model
    """
    print("\n[MODEL DISCOVERY]")
    all_models = repo.list_models()
    mains = [m for m in all_models if m.type == DnnModelType.Main and m.base == BaseDnnModelType.StableDiffusionXL]
    vaes = [m for m in all_models if m.type == DnnModelType.VAE and m.base == BaseDnnModelType.StableDiffusionXL]

    def pick_main() -> Any | None:
        priorities = ["juggernaut", "cyberrealistic"]
        for p in priorities:
            for m in mains:
                if p in m.name.lower():
                    return m
        return mains[0] if mains else None

    chosen_main = pick_main()
    chosen_vae = vaes[0] if vaes else None
    for label, mdl in [("main", chosen_main), ("vae", chosen_vae)]:
        print(f"[{ 'OK' if mdl else 'MISSING'}] {label}: {getattr(mdl,'name','<none>')}")
    return {"main": chosen_main, "vae": chosen_vae}


def configure_workflow_via_new_api(workflow: Any, models: dict[str, Any]) -> None:
    """Configure workflow inputs without hard-coded node IDs.

    Strategy:
      - Build a node_id -> node_type map from workflow.definition
      - Iterate exposed inputs; select by field_name + (label heuristics or node_type)
      - Apply updates atomically using set_many()
    """
    print("\n[CONFIGURE INPUTS - NEW API]")

    # Map node id -> type for disambiguation (avoids hard-coded ids)
    node_type_map: dict[str, str] = {}
    try:
        for n in workflow.definition.nodes:
            nid = n.get("id")
            ntype = n.get("data", {}).get("type")
            if nid and ntype:
                node_type_map[nid] = ntype
    except Exception:
        pass

    inputs = workflow.list_inputs()

    # Helper to locate first input matching predicate
    def find_input(pred) -> int | None:
        for inp in inputs:
            try:
                if pred(inp):
                    return inp.input_index
            except Exception:
                continue
        return None

    updates: dict[int, Any] = {}

    main_model = models.get("main")
    if main_model:
        model_idx = find_input(lambda inp: inp.field_name == "model" and node_type_map.get(inp.node_id, "").startswith("sdxl_model_loader"))
        if model_idx is not None:
            updates[model_idx] = {
                "key": main_model.key,
                "hash": main_model.hash,
                "name": main_model.name,
                "base": getattr(main_model.base, 'value', str(main_model.base)),
                "type": getattr(main_model.type, 'value', str(main_model.type)),
            }

    # Positive & negative prompts (labels carry hints)
    pos_idx = find_input(lambda inp: inp.field_name == "value" and "positive" in (inp.label or "").lower())
    if pos_idx is not None:
        updates[pos_idx] = TEST_PROMPT
    neg_idx = find_input(lambda inp: inp.field_name == "value" and "negative" in (inp.label or "").lower())
    if neg_idx is not None:
        updates[neg_idx] = TEST_NEGATIVE

    # Width / Height
    width_idx = find_input(lambda inp: inp.field_name == "width")
    if width_idx is not None:
        updates[width_idx] = OUTPUT_WIDTH
    height_idx = find_input(lambda inp: inp.field_name == "height")
    if height_idx is not None:
        updates[height_idx] = OUTPUT_HEIGHT

    # Steps / cfg_scale / scheduler (under denoise_latents node type)
    steps_idx = find_input(lambda inp: inp.field_name == "steps" and node_type_map.get(inp.node_id, "") == "denoise_latents")
    if steps_idx is not None:
        updates[steps_idx] = NUM_STEPS
    cfg_idx = find_input(lambda inp: inp.field_name == "cfg_scale" and node_type_map.get(inp.node_id, "") == "denoise_latents")
    if cfg_idx is not None:
        updates[cfg_idx] = CFG_SCALE
    sched_idx = find_input(lambda inp: inp.field_name == "scheduler" and node_type_map.get(inp.node_id, "") == "denoise_latents")
    if sched_idx is not None:
        updates[sched_idx] = SCHEDULER

    # Apply
    print(f"[INFO] Applying {len(updates)} updates via set_many() (dynamic discovery)")
    workflow.set_many(updates)
    # Compact single-line header to avoid syntax issues from multiline string
    print("[DEBUG] Input preview (index label type value):")
    for row in workflow.preview():
        print(f"  [{row['index']:02d}] {row['label']} ({row['type']}): {row['value']}")


def submit_and_monitor(client: InvokeAIClient, workflow: Any) -> bool:
    """Submit workflow and monitor execution."""
    print("\n[SUBMIT]")
    
    # Validate inputs
    errors = workflow.validate_inputs()
    if errors:
        print("[ERROR] Input validation failed:")
        for idx, errs in errors.items():
            print(f"  - [{idx}] {', '.join(errs)}")
        return False
    
    try:
        # Submit the workflow
        result = workflow.submit_sync(board_id="none")
    except Exception as e:
        print(f"[ERROR] Submission failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    batch_id = result.get("batch_id")
    item_ids = result.get("item_ids", [])
    item_id = item_ids[0] if item_ids else None
    session_id = result.get("session_id")
    
    print(f"[OK] Submitted batch={batch_id} item={item_id} session={session_id}")
    
    if not item_id:
        print("[ERROR] No item ID returned")
        return False
    
    # Monitor execution
    item_url = f"{client.base_url}/queue/default/i/{item_id}"
    start_time = time.time()
    last_status = None
    timeout = int(os.environ.get("WF_TIMEOUT", "180"))
    
    while time.time() - start_time < timeout:
        try:
            response = client.session.get(item_url)
            response.raise_for_status()
            queue_item = response.json()
            status = queue_item.get("status")
            
            if status != last_status:
                elapsed = int(time.time() - start_time)
                print(f"  [{elapsed:3d}s] status={status}")
                last_status = status
            
            if status in {"completed", "failed", "canceled"}:
                print(f"[DONE] Final status={status}")
                if status == "completed":
                    outputs = queue_item.get("outputs") or []
                    print(f"[OK] Workflow completed with {len(outputs)} outputs")
                    for output in outputs[:3]:  # Show first 3 outputs
                        output_type = output.get("type", "unknown")
                        if output_type == "image_output":
                            image = output.get("image", {})
                            print(f"  - Image: {image.get('image_name', 'unknown')}")
                    return True
                else:
                    error_type = queue_item.get("error_type")
                    error_message = queue_item.get("error_message")
                    if error_type or error_message:
                        print(f"[ERROR] Type: {error_type}, Message: {error_message}")
                    return False
                    
        except Exception as e:
            print(f"  [WARN] Poll error: {e}")
        
        time.sleep(3)
    
    print(f"[ERROR] Timeout after {timeout}s")
    return False


def main() -> int:
    """Main test function."""
    print("\n" + "=" * 70)
    print(" SDXL TEXT-TO-IMAGE WORKFLOW TEST")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize client
    base_url = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090")
    try:
        client = InvokeAIClient(base_url=base_url)
        print(f"[OK] Client ready @ {base_url}")
    except Exception as e:
        print(f"[ERROR] Cannot initialize client: {e}")
        return 1
    
    # Check available models
    models = select_sdxl_models(client.dnn_model_repo)
    if not models.get("main"):
        print("[ERROR] No SDXL main model available")
        return 1
    
    # Load workflow
    workflow_path = Path(__file__).parent.parent / "data" / "workflows" / "sdxl-text-to-image.json"
    if not workflow_path.exists():
        print(f"[ERROR] Workflow file not found: {workflow_path}")
        return 1
    
    workflow_repo = WorkflowRepository(client)
    try:
        workflow = workflow_repo.create_workflow_from_file(str(workflow_path))
        print(f"\n[OK] Loaded workflow '{workflow.definition.name}' with {len(workflow.inputs)} inputs")
    except Exception as e:
        print(f"[ERROR] Failed to load workflow: {e}")
        return 1
    
    # Debug: List all inputs
    print("\n[DEBUG] Available workflow inputs:")
    for inp in workflow.list_inputs():
        field_type = type(inp.field).__name__
        print(f"  [{inp.input_index}] {inp.node_id}.{inp.field_name} ({field_type}) - {inp.label}")
    
    # Configure workflow inputs
    configure_workflow_via_new_api(workflow, models)
    
    # Debug: Save the API graph
    api_graph = workflow._convert_to_api_format("none")
    debug_path = Path("tmp/sdxl_text_to_image_api_graph.json")
    debug_path.parent.mkdir(exist_ok=True)
    with open(debug_path, "w") as f:
        json.dump(api_graph, f, indent=2)
    print(f"\n[DEBUG] Saved API graph to {debug_path}")
    
    # Submit and monitor
    success = submit_and_monitor(client, workflow)
    
    # Summary
    print("\n" + "=" * 70)
    print(" RESULT SUMMARY")
    print("=" * 70)
    if success:
        print("[PASS] SDXL Text-to-Image workflow completed successfully")
        return 0
    else:
        print("[FAIL] SDXL Text-to-Image workflow failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())