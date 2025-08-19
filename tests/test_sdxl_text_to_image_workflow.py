#!/usr/bin/env python
"""End-to-end test for SDXL Text-to-Image workflow submission."""

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
from invokeai_py_client.dnn_model import DnnModelRepository, DnnModel, DnnModelType, BaseDnnModelType
from invokeai_py_client.ivk_fields.model_conversion import to_ivk_model_field


# Configuration
TEST_PROMPT = "A futuristic city skyline with flying cars, cyberpunk aesthetic, neon lights, detailed architecture"
TEST_NEGATIVE = "blurry, low quality, distorted, ugly"
OUTPUT_WIDTH = 1024
OUTPUT_HEIGHT = 1024
NUM_STEPS = 30
CFG_SCALE = 7.5
SCHEDULER = "euler"


def check_models(repo: DnnModelRepository) -> Dict[str, Optional[DnnModel]]:
    """Check available models for the workflow."""
    print("\n[MODEL CHECK]")
    all_models = repo.list_models()
    
    models = {
        "sdxl": next((m for m in all_models if m.type == DnnModelType.Main and m.base == BaseDnnModelType.StableDiffusionXL), None),
        "sdxl_vae": next((m for m in all_models if m.type == DnnModelType.VAE and m.base == BaseDnnModelType.StableDiffusionXL), None),
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
    
    # Set model - using the actual node IDs from the workflow
    if models.get("sdxl"):
        key = ("sdxl_model_loader:PwBr7RXRsy", "model")
        if key in input_lookup:
            try:
                field = to_ivk_model_field(models["sdxl"])
                workflow.set_input_value(input_lookup[key], field)
                print(f"[OK] Set SDXL model: {models['sdxl'].name}")
            except Exception as e:
                print(f"[WARN] Failed to set SDXL model: {e}")
    
    # Set VAE if available and exposed
    if models.get("sdxl_vae"):
        key = ("sdxl_model_loader:PwBr7RXRsy", "vae")
        if key in input_lookup:
            try:
                field = to_ivk_model_field(models["sdxl_vae"])
                workflow.set_input_value(input_lookup[key], field)
                print(f"[OK] Set SDXL VAE: {models['sdxl_vae'].name}")
            except Exception as e:
                print(f"[WARN] Failed to set VAE: {e}")
    
    # Set prompts - using the actual node IDs from the workflow
    prompt_configs = [
        ("positive_prompt:kjUMdcg0zO", "value", TEST_PROMPT, "positive prompt"),
        ("484ecc77-b7a0-4e19-b793-cc313f20fbe6", "value", TEST_NEGATIVE, "negative prompt"),
    ]
    
    for node_id, field_name, value, label in prompt_configs:
        key = (node_id, field_name)
        if key in input_lookup:
            field = workflow.get_input_value(input_lookup[key])
            if hasattr(field, 'value'):
                field.value = value
                print(f"[OK] Set {label}: {value[:50]}...")
    
    # Set dimensions - using the actual node IDs from the workflow
    dimension_configs = [
        ("noise:f4Bv4UWa22", "width", OUTPUT_WIDTH, "width"),
        ("noise:f4Bv4UWa22", "height", OUTPUT_HEIGHT, "height"),
    ]
    
    for node_id, field_name, value, label in dimension_configs:
        key = (node_id, field_name)
        if key in input_lookup:
            field = workflow.get_input_value(input_lookup[key])
            if hasattr(field, 'value'):
                field.value = value
                print(f"[OK] Set {label}: {value}")
    
    # Set generation parameters - using the actual node IDs from the workflow
    param_configs = [
        ("denoise_latents:TRC0Y88EWe", "steps", NUM_STEPS, "steps"),
        ("denoise_latents:TRC0Y88EWe", "cfg_scale", CFG_SCALE, "CFG scale"),
    ]
    
    for node_id, field_name, value, label in param_configs:
        key = (node_id, field_name)
        if key in input_lookup:
            field = workflow.get_input_value(input_lookup[key])
            if hasattr(field, 'value'):
                field.value = value
                print(f"[OK] Set {label}: {value}")
    
    # Set scheduler - using the actual node ID from the workflow
    key = ("denoise_latents:TRC0Y88EWe", "scheduler")
    if key in input_lookup:
        field = workflow.get_input_value(input_lookup[key])
        if hasattr(field, 'value'):
            field.value = SCHEDULER
            print(f"[OK] Set scheduler: {SCHEDULER}")


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
    models = check_models(client.dnn_model_repo)
    if not models.get("sdxl"):
        print("[ERROR] SDXL model not available")
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
    configure_workflow(workflow, models)
    
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