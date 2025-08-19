#!/usr/bin/env python
"""End-to-end crafting & submission test for the SDXL→FLUX refine workflow.

Goals:
 1. Load the source workflow JSON (kept pristine in repo).
 2. Map form-driven inputs (no hard-coded fragile indices).
 3. Mutate a copy with new prompt/board/model selections.
 4. Submit via InvokeAI API (127.0.0.1:9090) using workflow.submit_sync().
 5. Monitor queue item until terminal state.
 6. Dump the exact API graph we sent for diffing vs GUI reference.

Produces: tmp/last_flux_refine_submission_graph.json (API graph only)
          tmp/last_flux_refine_submission_batch.json (full batch envelope if DEBUG_WORKFLOW set)
"""

from __future__ import annotations

import os
import sys
import json
import time
import traceback
from pathlib import Path
from typing import Optional, Any
from datetime import datetime

# Ensure src/ on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient  # noqa: E402
from invokeai_py_client.workflow import WorkflowRepository  # noqa: E402
from invokeai_py_client.dnn_model import (  # noqa: E402
    DnnModelRepository,
    DnnModel,
    DnnModelType,
    BaseDnnModelType,
)
from invokeai_py_client.ivk_fields.model_conversion import to_ivk_model_field  # noqa: E402


# --- Utility / configuration -------------------------------------------------

POSITIVE_NODE = "0a167316-ba62-4218-9fcf-b3cff7963df8"  # string node (value)
NEGATIVE_NODE = "1711c26d-2b53-473c-aaf8-f600443d3c34"  # string node (value)
SDXL_STEPS_NODE = "f7a96570-59e0-400d-8fc9-889a438534c0"  # steps (generation)
FLUX_DOMAIN_STEPS_NODE = "9c773392-5647-4f2b-958e-9da1707b6e6a"  # num_steps
FLUX_REFINEMENT_STEPS_NODE = "56fb09f9-0fdc-499e-9933-de31c3aa6e61"  # num_steps

SAVE_IMG_STAGE1 = "4414d4b5-82c3-4513-8c3f-86d88c24aadc"
SAVE_IMG_STAGE2 = "67e997b2-2d56-43f4-8d2e-886c04e18d9f"
SAVE_IMG_FINAL = "abc466fe-12eb-48a5-87d8-488c8bda180f"


def generate_prompts() -> dict[str, str]:
    return {
        "positive": (
            "A mystical forest with bioluminescent trees, ethereal lights, ancient stone ruins, "
            "glowing moss, moonbeams through canopy, cinematic, ultra detailed, 8k"
        ),
        "negative": (
            "blurry, low quality, distortion, watermark, signature, jpeg artifacts, cropped, text, nsfw"
        ),
    }


def check_models(repo: DnnModelRepository) -> dict[str, Optional[DnnModel]]:
    print("\n[MODEL CHECK]")
    all_models = repo.list_models()

    def find(pred) -> Optional[DnnModel]:
        for m in all_models:
            if pred(m):
                return m
        return None

    out = {
        "sdxl_main": find(lambda m: m.type == DnnModelType.Main and m.base == BaseDnnModelType.StableDiffusionXL),
        "flux_main": find(lambda m: m.type == DnnModelType.Main and m.base == BaseDnnModelType.Flux),
        "t5_encoder": find(lambda m: m.type == DnnModelType.T5Encoder),
        "clip_embed": find(lambda m: m.type == DnnModelType.CLIPEmbed),
        "flux_vae": find(lambda m: m.type == DnnModelType.VAE and m.base == BaseDnnModelType.Flux),
    }
    for k, v in out.items():
        print(f"[{'OK' if v else '??'}] {k}: {getattr(v,'name', 'MISSING')}")
    return out


def build_input_lookup(workflow) -> dict[tuple[str, str], int]:
    """Map (node_id, field_name) -> input index for robust addressing."""
    lookup: dict[tuple[str, str], int] = {}
    for inp in workflow.list_inputs():
        lookup[(inp.node_id, inp.field_name)] = inp.input_index
    return lookup


def set_simple_value(workflow, lookup, node_id: str, field_name: str, value: Any) -> bool:
    key = (node_id, field_name)
    if key not in lookup:
        print(f"[WARN] Input not found in form: {node_id}.{field_name}")
        return False
    field = workflow.get_input_value(lookup[key])
    if hasattr(field, "value"):
        field.value = value
        print(f"[OK] Set {field_name} ({node_id[:8]}..) -> {value}")
        return True
    print(f"[WARN] Field {field_name} has no 'value' attribute")
    return False


def configure_inputs(workflow, models, prompts, board_id: Optional[str]) -> None:
    print("\n[CONFIGURE INPUTS]")
    lookup = build_input_lookup(workflow)
    if board_id is None:
        board_id = "none"
    # Prompts
    set_simple_value(workflow, lookup, POSITIVE_NODE, "value", prompts["positive"])
    set_simple_value(workflow, lookup, NEGATIVE_NODE, "value", prompts["negative"])

    # Steps adjustments (shorter for test speed if present)
    set_simple_value(workflow, lookup, SDXL_STEPS_NODE, "steps", 15)
    set_simple_value(workflow, lookup, FLUX_DOMAIN_STEPS_NODE, "num_steps", 8)
    set_simple_value(workflow, lookup, FLUX_REFINEMENT_STEPS_NODE, "num_steps", 12)

    # Ensure required FLUX meta params exist even if edges would supply them at runtime
    # (server schema may expect explicit presence)
    for node in [FLUX_DOMAIN_STEPS_NODE, FLUX_REFINEMENT_STEPS_NODE]:
        set_simple_value(workflow, lookup, node, "width", 1024)
        set_simple_value(workflow, lookup, node, "height", 1024)
        # Some schemas expect denoising_start explicitly (default 0)
        set_simple_value(workflow, lookup, node, "denoising_start", 0)
        # Provide cfg_scale if not already set (leave domain at 1 for now, refinement scaled)
    set_simple_value(workflow, lookup, FLUX_DOMAIN_STEPS_NODE, "cfg_scale", 1)
    set_simple_value(workflow, lookup, FLUX_REFINEMENT_STEPS_NODE, "cfg_scale", 1)

    # Boards (three save_image nodes) — if they are part of the form
    for node in [SAVE_IMG_STAGE1, SAVE_IMG_STAGE2, SAVE_IMG_FINAL]:
        set_simple_value(workflow, lookup, node, "board", board_id)

    # Node type lookup for targeted model assignment
    node_types: dict[str, str] = {}
    try:
        raw_nodes = workflow.definition.workflow.get("nodes", [])  # type: ignore[attr-defined]
        for n in raw_nodes:
            node_types[n.get("id")] = n.get("type")
    except Exception:  # noqa: BLE001
        pass

    sdxl_main = models.get("sdxl_main")
    flux_main = models.get("flux_main")
    t5_model = models.get("t5_encoder")
    clip_model = models.get("clip_embed")
    vae_model = models.get("flux_vae")

    for inp in workflow.list_inputs():
        nt = node_types.get(inp.node_id, "")
        field_name = inp.field_name
        target_model: Optional[Any] = None
        if field_name == "model":
            if nt == "sdxl_model_loader" and sdxl_main:
                target_model = sdxl_main
            elif nt == "flux_model_loader" and flux_main:
                target_model = flux_main
            else:
                continue  # skip other 'model' fields (e.g., model_identifier)
        elif field_name == "t5_encoder_model" and t5_model:
            target_model = t5_model
        elif field_name == "clip_embed_model" and clip_model:
            target_model = clip_model
        elif field_name == "vae_model" and vae_model:
            target_model = vae_model
        else:
            continue

        try:
            if target_model is None:
                continue
            field = to_ivk_model_field(target_model)
            workflow.set_input_value(inp.input_index, field)
            print(f"[OK] Bound {getattr(target_model,'name','?')} -> input {inp.input_index} ({field_name})")
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] Model bind failed for {field_name}: {e}")


def dump_api_graph(workflow, path: Path) -> None:
    try:
        graph = workflow._convert_to_api_format()  # pylint: disable=protected-access
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2)
        print(f"[DEBUG] Wrote API graph to {path}")
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] Failed to dump api graph: {e}")


def submit_and_monitor(client: InvokeAIClient, workflow, board_id: Optional[str]) -> bool:
    print("\n[SUBMIT]")
    errors = workflow.validate_inputs()
    if errors:
        print("[X] Input validation errors:")
        for idx, errs in errors.items():
            print(f"  - [{idx}] {', '.join(errs)}")
        return False
    try:
        result = workflow.submit_sync(board_id=board_id)
    except Exception as e:  # noqa: BLE001
        print(f"[X] submit_sync failed: {e}")
        traceback.print_exc()
        return False

    batch_id = result.get("batch_id")
    item_ids = result.get("item_ids", [])
    item_id = item_ids[0] if item_ids else None
    session_id = result.get("session_id")
    print(f"[OK] Enqueued batch={batch_id} item={item_id} session={session_id}")
    if not item_id:
        print("[X] No item id returned")
        return False

    item_url = f"{client.base_url}/queue/default/i/{item_id}"
    start = time.time()
    last_status = None
    timeout = int(os.environ.get("WF_TIMEOUT", "180"))
    while time.time() - start < timeout:
        try:
            r = client.session.get(item_url)
            r.raise_for_status()
            qi = r.json()
            status = qi.get("status")
            if status != last_status:
                print(f"  [{int(time.time()-start):3d}s] status={status}")
                last_status = status
            if status in {"completed", "failed", "canceled"}:
                print(f"[DONE] Final status={status}")
                if status == "completed":
                    outputs = qi.get("outputs") or []
                    print(f"[OK] Outputs: {len(outputs)} (if server populates)")
                    return True
                else:
                    err = qi.get("error") or {}
                    if err:
                        print(f"[ERR] {err}")
                    return False
        except Exception as e:  # noqa: BLE001
            print(f"  [WARN] poll error: {e}")
        time.sleep(3)
    print(f"[X] Timeout after {timeout}s")
    return False


def main() -> int:
    print("\n" + "=" * 70)
    print(" SDXL→FLUX REFINE WORKFLOW SUBMISSION TEST")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    base_url = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090")
    try:
        client = InvokeAIClient(base_url=base_url)
        print(f"[OK] Client ready @ {base_url}")
    except Exception as e:  # noqa: BLE001
        print(f"[X] Cannot init client: {e}")
        return 1

    models = check_models(client.dnn_model_repo)
    workflow_path = Path(__file__).parent.parent / "data" / "workflows" / "sdxl-flux-refine.json"
    if not workflow_path.exists():
        print(f"[X] Workflow file missing: {workflow_path}")
        return 1
    repo = WorkflowRepository(client)
    try:
        wf = repo.create_workflow_from_file(str(workflow_path))
        print(f"[OK] Loaded workflow '{wf.definition.name}' with {len(wf.inputs)} form inputs")
    except Exception as e:  # noqa: BLE001
        print(f"[X] Failed to load workflow: {e}")
        traceback.print_exc()
        return 1

    prompts = generate_prompts()
    board_id = client.board_repo.get_uncategorized_board().board_id
    print(f"[OK] Uncategorized board id={board_id}")

    configure_inputs(wf, models, prompts, board_id)
    dump_api_graph(wf, Path("tmp/last_flux_refine_submission_graph.json"))

    success = submit_and_monitor(client, wf, board_id)
    print("\n" + "=" * 70)
    print(" RESULT SUMMARY")
    print("=" * 70)
    if success:
        print("[PASS] Workflow completed")
        return 0
    print("[FAIL] Workflow did not complete successfully")
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
