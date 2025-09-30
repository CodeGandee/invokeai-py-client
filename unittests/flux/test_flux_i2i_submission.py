"""
Pytest-compatible FLUX image-to-image workflow test using index-centric APIs.

This test performs:
  1. Board creation
  2. Test image generation & upload
  3. Workflow load
  4. Input configuration via explicit loop
  5. Submission & monitoring
  6. Cleanup

Requires a running InvokeAI service with endpoint provided via
environment variable `INVOKE_AI_ENDPOINT`.
"""
from __future__ import annotations

import os
import time
import json
from pathlib import Path
from io import BytesIO
from typing import Any, Callable, Optional

import pytest

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowRepository
from invokeai_py_client.dnn_model import (
    DnnModelRepository,
    DnnModelType,
    BaseDnnModelType,
)
from invokeai_py_client.models import IvkImage

try:
    from PIL import Image as _Image  # type: ignore
    from PIL import ImageDraw as _ImageDraw  # type: ignore
    from PIL import ImageFont as _ImageFont  # type: ignore
    HAS_PIL = True
except Exception:  # pragma: no cover
    HAS_PIL = False


BOARD_PREFIX = "test_flux_i2i_newapi_"
IMAGE_WIDTH = 512
IMAGE_HEIGHT = 512
TEST_PROMPT = (
    "A surreal digital art painting, vibrant colors, dreamlike atmosphere, "
    "abstract elements blending with realistic details, masterpiece quality"
)

# Field name constants
PROMPT_FIELD = "prompt"
FLUX_MODEL_FIELD = "model"
T5_MODEL_FIELD = "t5_encoder_model"
CLIP_MODEL_FIELD = "clip_embed_model"
VAE_MODEL_FIELD = "vae_model"
NUM_STEPS_FIELD = "num_steps"
DENOISE_STRENGTH_FIELD = "denoising_strength"
DENOISE_START_FIELD = "denoising_start"
BOARD_FIELD = "board"


def _require_endpoint() -> str:
    ep = os.environ.get("INVOKE_AI_ENDPOINT")
    if not ep:
        pytest.skip("INVOKE_AI_ENDPOINT not set; integration test requires a running server")
    return ep


def generate_test_image(width: int = IMAGE_WIDTH, height: int = IMAGE_HEIGHT) -> bytes:
    if not HAS_PIL:  # runtime guard
        pytest.skip("Pillow not installed")
    img = _Image.new("RGB", (width, height), color="white")
    draw = _ImageDraw.Draw(img)
    for y in range(height):
        r = int(100 + (155 * y / height))
        g = int(50 + (50 * y / height))
        b = int(200 - (100 * y / height))
        draw.rectangle([0, y, width, y + 1], fill=(r, g, b))
    text = "FLUX NEW API"
    try:
        font = _ImageFont.load_default()
    except Exception:
        font = None
    tw, _ = draw.textbbox((0, 0), text, font=font)[2:]
    draw.text(((width - tw) // 2, height - 90), text, fill="white", font=font)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def ensure_board(client: InvokeAIClient, name: str):
    repo = client.board_repo
    for b in repo.list_boards():
        if b.board_name == name:
            return repo.get_board_handle(b.board_id)
    try:
        return repo.create_board(name)
    except Exception:
        return repo.get_board_handle("none")


def list_required_models(repo: DnnModelRepository) -> dict[str, Any]:
    all_models = repo.list_models()

    def find(pred: Callable[[Any], bool]):
        for m in all_models:
            if pred(m):
                return m
        return None

    models = {
        "flux_main": find(lambda m: m.type == DnnModelType.Main and m.base == BaseDnnModelType.Flux),
        "t5_encoder": find(lambda m: m.type == DnnModelType.T5Encoder),
        "clip_embed": find(lambda m: m.type == DnnModelType.CLIPEmbed),
        "flux_vae": find(lambda m: m.type == DnnModelType.VAE and m.base == BaseDnnModelType.Flux),
    }
    missing = [k for k, v in models.items() if v is None]
    if missing:
        pytest.skip(f"Missing models: {', '.join(missing)}")
    return models


def _build_node_type_map(workflow) -> dict[str, str]:
    node_type_map: dict[str, str] = {}
    try:
        for n in workflow.definition.nodes:  # raw node dicts
            nid = n.get("id")
            ntype = n.get("data", {}).get("type")
            if nid and ntype:
                node_type_map[nid] = ntype
    except Exception:
        pass
    return node_type_map


def model_dict(model) -> dict:
    if model is None:
        return {}
    base = model.base.value if hasattr(model.base, "value") else str(model.base)
    mtype = model.type.value if hasattr(model.type, "value") else str(model.type)
    return {"key": model.key, "hash": model.hash, "name": model.name, "base": base, "type": mtype}


def configure_inputs(workflow, models: dict[str, Any], image: IvkImage, board_id: str, steps: int = 10) -> None:
    node_type_map = _build_node_type_map(workflow)
    inputs = list(workflow.list_inputs())

    def first_index(predicate) -> int | None:
        for inp in inputs:
            try:
                if predicate(inp):
                    return inp.input_index
            except Exception:
                continue
        return None

    updates: dict[int, Any] = {}

    # Prompts
    pos_idx = first_index(
        lambda i: i.field_name == PROMPT_FIELD
        and isinstance(getattr(i.field, "value", ""), (str, type(None)))
        and "positive prompt" in (i.label or "").lower()
    )
    neg_idx = first_index(
        lambda i: i.field_name == PROMPT_FIELD
        and isinstance(getattr(i.field, "value", ""), (str, type(None)))
        and "negative prompt" in (i.label or "").lower()
    )
    if pos_idx is not None:
        updates[pos_idx] = TEST_PROMPT
    if neg_idx is not None:
        updates[neg_idx] = "Low quality, distorted, blurry"

    # Image input
    img_idx = first_index(lambda i: i.field_name == "image" and node_type_map.get(i.node_id) == "image")
    if img_idx is not None:
        updates[img_idx] = image.image_name

    # Model loader fields
    model_field_map = {
        FLUX_MODEL_FIELD: models.get("flux_main"),
        T5_MODEL_FIELD: models.get("t5_encoder"),
        CLIP_MODEL_FIELD: models.get("clip_embed"),
        VAE_MODEL_FIELD: models.get("flux_vae"),
    }
    for field_name, model_obj in model_field_map.items():
        if not model_obj:
            continue
        idx = first_index(
            lambda i, fn=field_name: i.field_name == fn and node_type_map.get(i.node_id) == "flux_model_loader"
        )
        if idx is not None:
            updates[idx] = model_dict(model_obj)

    # Sampler (flux_denoise_meta)
    steps_idx = first_index(lambda i: i.field_name == NUM_STEPS_FIELD and node_type_map.get(i.node_id) == "flux_denoise_meta")
    if steps_idx is not None:
        updates[steps_idx] = steps
    denoise_strength_idx = first_index(
        lambda i: i.field_name == DENOISE_STRENGTH_FIELD and node_type_map.get(i.node_id) == "flux_denoise_meta"
    )
    denoise_start_idx = first_index(
        lambda i: i.field_name == DENOISE_START_FIELD and node_type_map.get(i.node_id) == "flux_denoise_meta"
    )
    if denoise_strength_idx is not None:
        updates[denoise_strength_idx] = 0.7
    elif denoise_start_idx is not None:
        updates[denoise_start_idx] = 0.4

    # Board field on decode
    board_idx = first_index(lambda i: i.field_name == BOARD_FIELD and node_type_map.get(i.node_id) == "flux_vae_decode")
    if board_idx is not None:
        updates[board_idx] = board_id

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
        except Exception as e:  # pragma: no cover - best-effort
            print(f"[WARN] could not set input {idx}: {e}")


def submit_and_wait(client: InvokeAIClient, workflow, timeout: int = 180) -> bool:
    errs = workflow.validate_inputs()
    if errs:
        for idx, msgs in errs.items():
            print(f"  [VALIDATION] {idx}: {msgs}")
        return False
    result = workflow.submit_sync()
    item_id = (result.get("item_ids") or [None])[0]
    if not item_id:
        print("[ERROR] No item id returned")
        return False
    url = f"{client.base_url}/queue/default/i/{item_id}"
    start = time.time()
    last = None
    while time.time() - start < timeout:
        try:
            resp = client.session.get(url)
            resp.raise_for_status()
            qi = resp.json()
            status = qi.get("status")
            if status != last:
                print(f"  [poll {int(time.time()-start):3d}s] status={status}")
                last = status
            if status in {"completed", "failed", "canceled"}:
                return status == "completed"
        except Exception as e:
            print(f"  [WARN] poll error: {e}")
        time.sleep(2)
    print(f"[ERROR] Timeout after {timeout}s")
    return False


@pytest.mark.integration
@pytest.mark.slow
def test_flux_i2i_submission_integration() -> None:
    base_url = _require_endpoint()
    client = InvokeAIClient.from_url(base_url)
    models = list_required_models(client.dnn_model_repo)
    board_name = f"{BOARD_PREFIX}{int(time.time())}"
    board = ensure_board(client, board_name)
    board_id_val: str = (
        getattr(getattr(board, "board", None), "board_id", None)
        or getattr(board, "board_id", None)
        or "none"
    )

    try:
        img_bytes = generate_test_image()
        uploaded = board.upload_image_data(image_data=img_bytes, filename="flux_new_api_input.png")
    except Exception as e:
        pytest.skip(f"image prep failed: {e}")

    wf_path = Path("data/workflows/flux-image-to-image.json")
    if not wf_path.exists():
        pytest.skip(f"workflow file missing: {wf_path}")

    wf_repo = WorkflowRepository(client)
    workflow = wf_repo.create_workflow_from_file(str(wf_path))

    configure_inputs(workflow, models, uploaded, board_id_val, steps=10)

    # Optionally save API graph for debug
    try:
        api_graph = workflow._convert_to_api_format()
        Path("tmp").mkdir(exist_ok=True)
        with open("tmp/flux_i2i_api_graph_new_api.json", "w") as f:
            json.dump(api_graph, f, indent=2)
    except Exception:
        pass

    success = submit_and_wait(client, workflow, timeout=180)

    # Cleanup (best-effort)
    try:
        if os.environ.get("KEEP_TEST_BOARD") != "1" and board_id_val != "none":
            client.board_repo.delete_board(board_id_val, delete_images=True)
    except Exception:
        pass

    assert success is True

