#!/usr/bin/env python
"""End-to-end test for SDXL-FLUX-Refine workflow submission."""

from __future__ import annotations

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional, Any, Dict
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowRepository
from invokeai_py_client.board import BoardRepository
from invokeai_py_client.dnn_model import DnnModelRepository, DnnModel, DnnModelType, BaseDnnModelType
from invokeai_py_client.ivk_fields.model_conversion import to_ivk_model_field


# Configuration
TEST_PROMPT = "A majestic mountain landscape at sunset, golden hour lighting, photorealistic, 8k quality"
TEST_NEGATIVE = "blurry, low quality, distorted"
OUTPUT_WIDTH = 1024
OUTPUT_HEIGHT = 1024
SDXL_STEPS = 20
FLUX_STEPS = 12
NOISE_RATIO = 0.3


def check_models(repo: DnnModelRepository) -> Dict[str, Optional[DnnModel]]:
    """Check available models for the workflow."""
    print("\n[MODEL CHECK]")
    all_models = repo.list_models()
    
    models = {
        "sdxl": next((m for m in all_models if m.type == DnnModelType.Main and m.base == BaseDnnModelType.StableDiffusionXL), None),
        "flux": next((m for m in all_models if m.type == DnnModelType.Main and m.base == BaseDnnModelType.Flux), None),
        "sdxl_vae": next((m for m in all_models if m.type == DnnModelType.VAE and m.base == BaseDnnModelType.StableDiffusionXL), None),
        "flux_vae": next((m for m in all_models if m.type == DnnModelType.VAE and m.base == BaseDnnModelType.Flux), None),
        "t5_encoder": next((m for m in all_models if m.type == DnnModelType.T5Encoder), None),
        "clip_embed": next((m for m in all_models if m.type == DnnModelType.CLIPEmbed), None),
    }
    
    for key, model in models.items():
        status = "OK" if model else "MISSING"
        name = getattr(model, "name", "N/A")
        print(f"[{status}] {key}: {name}")
    
    return models


def configure_workflow(workflow: Any, models: Dict[str, Optional[DnnModel]]) -> None:
    """Configure all workflow inputs."""
    print("\n[CONFIGURE INPUTS]")
    
    # Build input lookup
    input_lookup = {
        (inp.node_id, inp.field_name): inp.input_index 
        for inp in workflow.list_inputs()
    }
    
    # Set prompts
    prompt_configs = [
        ("cdb3e45f-a9da-4b4f-b1ef-1cb6b691997f", "value", TEST_PROMPT, "positive prompt"),
        ("31346633-f8e8-415a-ae34-66771d62e44f", "value", TEST_NEGATIVE, "negative prompt"),
    ]
    
    for node_id, field_name, value, label in prompt_configs:
        key = (node_id, field_name)
        if key in input_lookup:
            field = workflow.get_input_value(input_lookup[key])
            if hasattr(field, 'value'):
                field.value = value
                print(f"[OK] Set {label}: {value[:50]}...")
    
    # Set dimensions
    dimension_configs = [
        ("fc1c13c9-ccba-4f70-8793-0f5b26c9450f", "value", OUTPUT_WIDTH, "width"),
        ("7f14f907-5659-4f82-9bbe-c4e88517e002", "value", OUTPUT_HEIGHT, "height"),
    ]
    
    for node_id, field_name, value, label in dimension_configs:
        key = (node_id, field_name)
        if key in input_lookup:
            field = workflow.get_input_value(input_lookup[key])
            if hasattr(field, 'value'):
                field.value = value
                print(f"[OK] Set {label}: {value}")
    
    # Set models
    model_configs = [
        ("90f25dcd-e0e0-420f-8e09-56402678ad08", "model", models.get("sdxl"), "SDXL model"),
        ("8e36a01e-d8fc-4b25-ae96-32a74a087ca7", "model", models.get("flux"), "FLUX model"),
        ("8e36a01e-d8fc-4b25-ae96-32a74a087ca7", "t5_encoder_model", models.get("t5_encoder"), "T5 encoder"),
        ("8e36a01e-d8fc-4b25-ae96-32a74a087ca7", "clip_embed_model", models.get("clip_embed"), "CLIP embed"),
        ("8e36a01e-d8fc-4b25-ae96-32a74a087ca7", "vae_model", models.get("flux_vae"), "FLUX VAE"),
        ("90f25dcd-e0e0-420f-8e09-56402678ad08", "vae", models.get("sdxl_vae"), "SDXL VAE"),
    ]
    
    for node_id, field_name, model, label in model_configs:
        if model:
            key = (node_id, field_name)
            if key in input_lookup:
                try:
                    field = to_ivk_model_field(model)
                    workflow.set_input_value(input_lookup[key], field)
                    print(f"[OK] Set {label}: {model.name}")
                except Exception as e:
                    print(f"[WARN] Failed to set {label}: {e}")
    
    # Set other parameters
    param_configs = [
        ("c8a8a0b6-b2d5-4bed-a08e-8c2c6d455731", "b", NOISE_RATIO, "noise ratio"),
        ("0e659086-1212-4b21-97e8-88e1e1a93e33", "num_steps", FLUX_STEPS, "FLUX steps"),
        ("ffe7d637-e383-4b97-85ae-adcaee9c3343", "num_steps", SDXL_STEPS, "SDXL steps"),
    ]
    
    for node_id, field_name, value, label in param_configs:
        key = (node_id, field_name)
        if key in input_lookup:
            field = workflow.get_input_value(input_lookup[key])
            if hasattr(field, 'value'):
                field.value = value
                print(f"[OK] Set {label}: {value}")
    
    # Set output board to uncategorized
    board_configs = [
        ("6fa8cc65-9968-403d-8ddb-14cbeb913edc", "board"),
        ("ed8e2b08-39f8-4a95-92e1-c4d6c3e95529", "board"),
        ("5efc13f3-b58a-42e7-8ef1-4a54dd056dc4", "board"),
    ]
    
    for node_id, field_name in board_configs:
        key = (node_id, field_name)
        if key in input_lookup:
            field = workflow.get_input_value(input_lookup[key])
            if hasattr(field, 'value'):
                field.value = "none"


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
    timeout = int(os.environ.get("WF_TIMEOUT", "300"))  # 5 minutes for this complex workflow
    
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
    print(" SDXL-FLUX-REFINE WORKFLOW TEST")
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
    models = check_models(client.dnn_model_repo)
    required = ["sdxl", "flux", "t5_encoder", "clip_embed"]
    if not all(models.get(k) for k in required):
        print("[ERROR] Required models not available")
        return 1
    
    # Load workflow
    workflow_path = Path(__file__).parent.parent / "data" / "workflows" / "sdxl-flux-refine.json"
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
    
    # Configure workflow inputs
    configure_workflow(workflow, models)
    
    # Debug: Save the API graph
    api_graph = workflow._convert_to_api_format("none")
    debug_path = Path("tmp/sdxl_flux_refine_api_graph.json")
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
        print("[PASS] SDXL-FLUX-Refine workflow completed successfully")
        return 0
    else:
        print("[FAIL] SDXL-FLUX-Refine workflow failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())