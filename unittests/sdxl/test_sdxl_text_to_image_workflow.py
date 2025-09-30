"""
Integration test: SDXL Text-to-Image workflow (sync).

Requires a running InvokeAI server with endpoint provided via
environment variable `INVOKE_AI_ENDPOINT`.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pytest

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowRepository
from invokeai_py_client.dnn_model import DnnModelRepository, DnnModelType, BaseDnnModelType


TEST_PROMPT = "A city skyline at dusk, detailed, vibrant, cinematic lighting"
TEST_NEGATIVE = "blurry, low quality, distorted, ugly"
OUTPUT_WIDTH = 512
OUTPUT_HEIGHT = 512
NUM_STEPS = 10
QUEUE_ID = "default"


def _require_endpoint() -> str:
    ep = os.environ.get("INVOKE_AI_ENDPOINT")
    if not ep:
        pytest.skip("INVOKE_AI_ENDPOINT not set; integration test requires a running server")
    return ep


def _select_sdxl_models(repo: DnnModelRepository) -> dict[str, Any]:
    all_models = repo.list_models()
    mains = [m for m in all_models if m.type == DnnModelType.Main and m.base == BaseDnnModelType.StableDiffusionXL]
    vaes = [m for m in all_models if m.type == DnnModelType.VAE and m.base == BaseDnnModelType.StableDiffusionXL]
    if not mains:
        pytest.skip("No SDXL main models installed")
    return {"main": mains[0], "vae": vaes[0] if vaes else None}


def _configure_t2i(workflow: Any, models: dict[str, Any]) -> None:
    node_type_map: dict[str, str] = {}
    try:
        for n in workflow.definition.nodes:  # raw node dicts
            nid = n.get("id")
            ntype = n.get("data", {}).get("type")
            if nid and ntype:
                node_type_map[nid] = ntype
    except Exception:
        pass
    inputs = workflow.list_inputs()

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
        midx = find_input(
            lambda i: i.field_name == "model" and node_type_map.get(i.node_id, "").startswith("sdxl_model_loader")
        )
        if midx is not None:
            updates[midx] = {
                "key": main_model.key,
                "hash": main_model.hash,
                "name": main_model.name,
                "base": getattr(main_model.base, "value", str(main_model.base)),
                "type": getattr(main_model.type, "value", str(main_model.type)),
            }

    # Prompts
    pos_idx = find_input(lambda i: i.field_name == "value" and "positive" in (i.label or "").lower())
    if pos_idx is not None:
        updates[pos_idx] = TEST_PROMPT
    neg_idx = find_input(lambda i: i.field_name == "value" and "negative" in (i.label or "").lower())
    if neg_idx is not None:
        updates[neg_idx] = TEST_NEGATIVE

    # Dimensions and steps
    w_idx = find_input(lambda i: i.field_name == "width")
    if w_idx is not None:
        updates[w_idx] = OUTPUT_WIDTH
    h_idx = find_input(lambda i: i.field_name == "height")
    if h_idx is not None:
        updates[h_idx] = OUTPUT_HEIGHT
    steps_idx = find_input(lambda i: i.field_name == "steps" and node_type_map.get(i.node_id, "") == "denoise_latents")
    if steps_idx is not None:
        updates[steps_idx] = NUM_STEPS

    # Apply updates via field.value fallbacks
    for idx, val in updates.items():
        try:
            fld = workflow.get_input_value(idx)
            if hasattr(fld, "value") and not isinstance(val, dict):
                setattr(fld, "value", val)  # type: ignore[assignment]
            elif isinstance(val, dict):
                for k, v in val.items():
                    if hasattr(fld, k):
                        setattr(fld, k, v)
        except Exception:
            pass


@pytest.mark.integration
@pytest.mark.slow
def test_sdxl_text_to_image_workflow_sync() -> None:
    base_url = _require_endpoint()
    client = InvokeAIClient.from_url(base_url)

    models = _select_sdxl_models(client.dnn_model_repo)
    wf_path = Path("data/workflows/sdxl-text-to-image.json")
    if not wf_path.exists():
        pytest.skip(f"workflow file missing: {wf_path}")

    repo = WorkflowRepository(client)
    workflow = repo.create_workflow_from_file(str(wf_path))
    _configure_t2i(workflow, models)

    # Submit and poll status until terminal
    result = workflow.submit_sync()
    item_ids = result.get("item_ids", [])
    item_id = item_ids[0] if item_ids else None
    assert item_id is not None

    url = f"{client.base_url}/queue/{QUEUE_ID}/i/{item_id}"
    start = time.time()
    last = None
    timeout = 180
    while time.time() - start < timeout:
        try:
            r = client.session.get(url)
            r.raise_for_status()
            qi = r.json()
            st = qi.get("status")
            if st != last:
                last = st
            if st in {"completed", "failed", "canceled"}:
                assert st == "completed"
                return
        except Exception:
            pass
        time.sleep(2)
    pytest.fail(f"timeout after {timeout}s")

