#!/usr/bin/env python
"""End-to-end test for SDXL-FLUX-Refine workflow submission."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional, Any
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowRepository
from invokeai_py_client.dnn_model import (
    DnnModelRepository,
    DnnModel,
    DnnModelType,
    BaseDnnModelType,
)


# Configuration
TEST_PROMPT = "A majestic mountain landscape at sunset, golden hour lighting, photorealistic, 8k quality"
TEST_NEGATIVE = "blurry, low quality, distorted"
OUTPUT_WIDTH = 1024
OUTPUT_HEIGHT = 1024
SDXL_STEPS = 20
FLUX_STEPS = 12
NOISE_RATIO = 0.3


def check_models(repo: DnnModelRepository) -> dict[str, Optional[DnnModel]]:
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


def configure_workflow(workflow: Any, models: dict[str, Optional[DnnModel]]) -> None:
    """Configure workflow using dynamic discovery + index-centric API.

    Rules (heuristics relying only on labels & field names):
      - Positive Prompt: first string input whose label contains 'positive prompt'
      - Negative Prompt: first string input whose label contains 'negative prompt'
      - Width/Height: first integer inputs with field_name 'width'/'height'
      - SDXL stage model fields: node_type contains 'sdxl_model_loader'
      - FLUX stage model fields: node_type contains 'flux_model_loader'
      - Sampler steps: inputs named 'num_steps'; first associated with SDXL stage gets SDXL_STEPS; second gets FLUX_STEPS
      - Noise ratio / blend param: field_name 'b' (common for mix/blend) set to NOISE_RATIO if found
      - Any 'board' field: set to 'none'
    """
    print("\n[CONFIGURE INPUTS - NEW API]")

    # Build node_type map
    node_type_map: dict[str, str] = {}
    try:
        for n in workflow.definition.nodes:
            nid = n.get('id')
            ntype = n.get('data', {}).get('type')
            if nid and ntype:
                node_type_map[nid] = ntype
    except Exception:
        pass

    inputs = workflow.list_inputs()

    def first_index(pred) -> int | None:
        for inp in inputs:
            try:
                if pred(inp):
                    return inp.input_index
            except Exception:
                continue
        return None

    updates: dict[int, Any] = {}

    # Prompts
    pos_idx = first_index(lambda i: i.field_name == 'value' and 'positive prompt' in (i.label or '').lower())
    neg_idx = first_index(lambda i: i.field_name == 'value' and 'negative prompt' in (i.label or '').lower())
    if pos_idx is not None:
        updates[pos_idx] = TEST_PROMPT
    if neg_idx is not None:
        updates[neg_idx] = TEST_NEGATIVE

    # Dimensions
    width_idx = first_index(lambda i: i.field_name == 'value' and (i.label or '').strip().lower() == 'width')
    height_idx = first_index(lambda i: i.field_name == 'value' and (i.label or '').strip().lower() == 'height')
    # Fallback: look for field_name width/height directly if label missing
    if width_idx is None:
        width_idx = first_index(lambda i: i.field_name == 'width')
    if height_idx is None:
        height_idx = first_index(lambda i: i.field_name == 'height')
    if width_idx is not None:
        updates[width_idx] = OUTPUT_WIDTH
    if height_idx is not None:
        updates[height_idx] = OUTPUT_HEIGHT

    # Model fields (SDXL and FLUX phases)
    # (Model field name hints are implicit in conditional below; no separate map kept.)
    # Map phase -> available model objects
    model_objs = {
        'sdxl_model': models.get('sdxl'),
        'flux_model': models.get('flux'),
        't5_encoder_model': models.get('t5_encoder'),
        'clip_embed_model': models.get('clip_embed'),
        'flux_vae_model': models.get('flux_vae'),
        'sdxl_vae_model': models.get('sdxl_vae'),
    }

    def to_model_dict(m: DnnModel | None) -> dict[str, Any] | None:
        if not m:
            return None
        base = m.base.value if hasattr(m.base, 'value') else str(m.base)
        mtype = m.type.value if hasattr(m.type, 'value') else str(m.type)
        return {
            'key': m.key,
            'hash': m.hash,
            'name': m.name,
            'base': base,
            'type': mtype,
        }

    # Iterate inputs; assign when matches type & field
    for inp in inputs:
        ntype = node_type_map.get(inp.node_id, '')
        fn = inp.field_name
        if fn == 'model':
            if 'sdxl' in ntype and (md := to_model_dict(model_objs['sdxl_model'])):
                updates[inp.input_index] = md
            elif 'flux' in ntype and (md := to_model_dict(model_objs['flux_model'])):
                updates[inp.input_index] = md
        elif fn == 't5_encoder_model' and 'flux' in ntype and (md := to_model_dict(model_objs['t5_encoder_model'])):
            updates[inp.input_index] = md
        elif fn == 'clip_embed_model' and 'flux' in ntype and (md := to_model_dict(model_objs['clip_embed_model'])):
            updates[inp.input_index] = md
        elif fn == 'vae_model' and 'flux' in ntype and (md := to_model_dict(model_objs['flux_vae_model'])):
            updates[inp.input_index] = md
        elif fn == 'vae' and 'sdxl' in ntype and (md := to_model_dict(model_objs['sdxl_vae_model'])):
            updates[inp.input_index] = md

    # Steps: collect indices then assign SDXL_STEPS to first, FLUX_STEPS to second (order of discovery)
    step_indices = [inp.input_index for inp in inputs if inp.field_name == 'num_steps']
    if step_indices:
        updates[step_indices[0]] = SDXL_STEPS
    if len(step_indices) > 1:
        updates[step_indices[1]] = FLUX_STEPS

    # Noise ratio (field 'b')
    noise_idx = first_index(lambda i: i.field_name == 'b')
    if noise_idx is not None:
        updates[noise_idx] = NOISE_RATIO

    # Board fields
    for inp in inputs:
        if inp.field_name == 'board':
            updates[inp.input_index] = 'none'

    print(f"[INFO] Applying {len(updates)} updates (explicit loop; set_many removed)")
    for idx, val in updates.items():
        try:
            workflow._set_input_value_simple_impl(idx, val)  # type: ignore[attr-defined]
        except AttributeError:
            fld = workflow.get_input_value(idx)
            if hasattr(fld, 'value') and not isinstance(val, dict):
                try:
                    fld.value = val  # type: ignore[attr-defined]
                except Exception:
                    pass
            elif isinstance(val, dict):
                for k, v in val.items():
                    if hasattr(fld, k):
                        try:
                            setattr(fld, k, v)
                        except Exception:
                            pass
        except Exception as e:
            print(f"[WARN] could not set input {idx}: {e}")
    print('[DEBUG] Input preview:')
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
        result = workflow.submit_sync()
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

    # Synchronize embedded DNN model identifiers with local installation
    try:
        replaced = workflow.sync_dnn_model(by_name=True, by_base=True)
        print(f"[OK] Synchronized {len(replaced)} model reference(s) with local system")
    except Exception as e:
        print(f"[ERROR] Model synchronization failed: {e}")
        return 1
    
    # Configure workflow inputs
    configure_workflow(workflow, models)
    
    # Debug API graph generation removed; no file output
    
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