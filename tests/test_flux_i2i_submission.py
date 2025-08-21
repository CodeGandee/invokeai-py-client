#!/usr/bin/env python
"""End-to-end FLUX image-to-image workflow test using index-centric APIs.

Previously exercised deprecated convenience APIs (set_input_value_simple, set_many);
these have been removed/disabled. This test now performs:
    1. Board creation
    2. Test image generation & upload
    3. Workflow load
    4. Input configuration via explicit loop
    5. Submission & monitoring
    6. Cleanup

Run (assuming InvokeAI running @ 127.0.0.1:9090):
  pixi run -e dev python tests/test_flux_i2i_submission_new_api.py
"""
from __future__ import annotations

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from io import BytesIO
from typing import Any, Callable

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient  # noqa: E402
from invokeai_py_client.workflow import WorkflowRepository  # noqa: E402
# BoardRepository import not needed directly
from invokeai_py_client.dnn_model import (  # noqa: E402
    DnnModelRepository,
    DnnModelType,
    BaseDnnModelType,
)
from invokeai_py_client.models import IvkImage  # noqa: E402

try:
    import PIL  # noqa: F401
    HAS_PIL = True
except Exception:  # pragma: no cover
    HAS_PIL = False

BOARD_PREFIX = "test_flux_i2i_newapi_"
IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 1024
TEST_PROMPT = (
    "A surreal digital art painting, vibrant colors, dreamlike atmosphere, "
    "abstract elements blending with realistic details, masterpiece quality, "
    "8k resolution, trending on artstation"
)

# Field name constants (still stable, but no node UUIDs)
PROMPT_FIELD = "prompt"
FLUX_MODEL_FIELD = "model"
T5_MODEL_FIELD = "t5_encoder_model"
CLIP_MODEL_FIELD = "clip_embed_model"
VAE_MODEL_FIELD = "vae_model"
NUM_STEPS_FIELD = "num_steps"
DENOISE_STRENGTH_FIELD = "denoising_strength"
DENOISE_START_FIELD = "denoising_start"
BOARD_FIELD = "board"


def generate_test_image(width: int = IMAGE_WIDTH, height: int = IMAGE_HEIGHT) -> bytes:
    if not HAS_PIL:  # runtime guard
        raise RuntimeError("PIL not available")
    # Localize imports for type checkers (they may be unavailable)
    from PIL import Image as _Image  # type: ignore
    from PIL import ImageDraw as _ImageDraw  # type: ignore
    from PIL import ImageFont as _ImageFont  # type: ignore
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
        print(f"[ERROR] Missing models: {', '.join(missing)}")
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
    base = model.base.value if hasattr(model.base, 'value') else str(model.base)
    mtype = model.type.value if hasattr(model.type, 'value') else str(model.type)
    return {
        "key": model.key,
        "hash": model.hash,
        "name": model.name,
        "base": base,
        "type": mtype,
    }


def configure_inputs(workflow, models: dict[str, Any], image: IvkImage, board_id: str):
    """Configure inputs without hard-coded node UUIDs (replaces removed set_many)."""
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
    pos_idx = first_index(lambda i: i.field_name == PROMPT_FIELD and isinstance(getattr(i.field, 'value', ''), (str, type(None))) and 'positive prompt' in (i.label or '').lower())
    neg_idx = first_index(lambda i: i.field_name == PROMPT_FIELD and isinstance(getattr(i.field, 'value', ''), (str, type(None))) and 'negative prompt' in (i.label or '').lower())
    if pos_idx is not None:
        updates[pos_idx] = TEST_PROMPT
    if neg_idx is not None:
        updates[neg_idx] = "Low quality, distorted, blurry"  # basic negative prompt

    # Image input
    img_idx = first_index(lambda i: i.field_name == 'image' and node_type_map.get(i.node_id) == 'image')
    if img_idx is not None:
        updates[img_idx] = image.image_name

    # Model loader fields
    model_field_map = {
        FLUX_MODEL_FIELD: models.get('flux_main'),
        T5_MODEL_FIELD: models.get('t5_encoder'),
        CLIP_MODEL_FIELD: models.get('clip_embed'),
        VAE_MODEL_FIELD: models.get('flux_vae'),
    }
    for field_name, model_obj in model_field_map.items():
        if not model_obj:
            continue
        idx = first_index(lambda i, fn=field_name: i.field_name == fn and node_type_map.get(i.node_id) == 'flux_model_loader')
        if idx is not None:
            updates[idx] = model_dict(model_obj)

    # Sampler (flux_denoise_meta)
    steps_idx = first_index(lambda i: i.field_name == NUM_STEPS_FIELD and node_type_map.get(i.node_id) == 'flux_denoise_meta')
    if steps_idx is not None:
        updates[steps_idx] = 12
    denoise_strength_idx = first_index(lambda i: i.field_name == DENOISE_STRENGTH_FIELD and node_type_map.get(i.node_id) == 'flux_denoise_meta')
    denoise_start_idx = first_index(lambda i: i.field_name == DENOISE_START_FIELD and node_type_map.get(i.node_id) == 'flux_denoise_meta')
    if denoise_strength_idx is not None:
        updates[denoise_strength_idx] = 0.7
    elif denoise_start_idx is not None:
        updates[denoise_start_idx] = 0.4

    # Board field on decode
    board_idx = first_index(lambda i: i.field_name == BOARD_FIELD and node_type_map.get(i.node_id) == 'flux_vae_decode')
    if board_idx is not None:
        updates[board_idx] = board_id

    print(f"[INFO] Applying {len(updates)} input updates (explicit loop; set_many removed)")
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
    print("[DEBUG] Input preview after updates:")
    for row in workflow.preview():
        print(f"  [{row['index']:02d}] {row['label']} ({row['type']}): {row['value']}")


def submit_and_wait(client: InvokeAIClient, workflow, board_id: str) -> bool:
    print("\n[SUBMIT]")
    errs = workflow.validate_inputs()
    if errs:
        print("[ERROR] Validation errors:")
        for idx, msgs in errs.items():
            print(f"  {idx}: {msgs}")
        return False
    try:
        # board_id now must be set via form input; call without board override
        result = workflow.submit_sync()
    except Exception as e:
        print(f"[ERROR] submit failed: {e}")
        return False
    item_id = (result.get("item_ids") or [None])[0]
    if not item_id:
        print("[ERROR] No item id returned")
        return False
    print(f"[OK] Submitted batch={result.get('batch_id')} item={item_id} session={result.get('session_id')}")
    # Poll
    url = f"{client.base_url}/queue/default/i/{item_id}"
    start = time.time()
    last = None
    timeout = int(os.environ.get("WF_TIMEOUT", "180"))
    while time.time() - start < timeout:
        try:
            resp = client.session.get(url)
            resp.raise_for_status()
            qi = resp.json()
            status = qi.get("status")
            if status != last:
                print(f"  [{int(time.time()-start):3d}s] status={status}")
                last = status
            if status in {"completed", "failed", "canceled"}:
                print(f"[DONE] status={status}")
                if status == "completed":
                    outputs = qi.get("outputs") or []
                    print(f"[OK] Completed with {len(outputs)} outputs")
                    return True
                else:
                    print(f"[ERROR] {qi.get('error') or qi.get('error_message')}")
                    return False
        except Exception as e:
            print(f"  [WARN] poll error: {e}")
        time.sleep(3)
    print(f"[ERROR] Timeout after {timeout}s")
    return False


def cleanup_board(client: InvokeAIClient, board_id: str):
    if board_id == "none":
        print("[INFO] Skipping cleanup (uncategorized board)")
        return
    try:
        client.board_repo.delete_board(board_id, delete_images=True)
        print(f"[OK] Deleted board {board_id}")
    except Exception as e:
        print(f"[WARN] Board cleanup failed: {e}")


def main() -> int:
    print("\n" + "="*70)
    print(" FLUX I2I WORKFLOW TEST (NEW API)")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    base_url = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090")
    try:
        client = InvokeAIClient(base_url=base_url)
        print(f"[OK] Client @ {base_url}")
    except Exception as e:
        print(f"[ERROR] client init failed: {e}")
        return 1
    models = list_required_models(client.dnn_model_repo)
    if not all(models.values()):
        return 1
    board_name = f"{BOARD_PREFIX}{int(time.time())}"
    board = ensure_board(client, board_name)
    # Normalize board id to plain str (never None)
    board_id_val: str = getattr(getattr(board, 'board', None), 'board_id', None) or getattr(board, 'board_id', None) or 'none'
    # Generate/upload image
    try:
        img_bytes = generate_test_image()
        uploaded = board.upload_image_data(image_data=img_bytes, filename="flux_new_api_input.png")
        print(f"[OK] Uploaded image {uploaded.image_name}")
    except Exception as e:
        print(f"[ERROR] image prep failed: {e}")
        cleanup_board(client, board_id_val)
        return 1
    # Load workflow
    wf_path = Path(__file__).parent.parent / "data" / "workflows" / "flux-image-to-image.json"
    if not wf_path.exists():
        print(f"[ERROR] workflow file missing: {wf_path}")
        cleanup_board(client, board_id_val)
        return 1
    wf_repo = WorkflowRepository(client)
    try:
        workflow = wf_repo.create_workflow_from_file(str(wf_path))
        print(f"[OK] Loaded workflow '{workflow.definition.name}' with {len(workflow.inputs)} inputs")
    except Exception as e:
        print(f"[ERROR] workflow load failed: {e}")
        cleanup_board(client, board_id_val)
        return 1
    # Configure via new API
    configure_inputs(workflow, models, uploaded, board_id_val)
    # Save API graph for debug
    try:
        api_graph = workflow._convert_to_api_format()
        Path('tmp').mkdir(exist_ok=True)
        with open('tmp/flux_i2i_api_graph_new_api.json', 'w') as f:
            json.dump(api_graph, f, indent=2)
        print("[DEBUG] Saved API graph to tmp/flux_i2i_api_graph_new_api.json")
    except Exception as e:
        print(f"[WARN] Could not save API graph: {e}")
    # Submit
    success = submit_and_wait(client, workflow, board_id_val)
    # Cleanup
    if os.environ.get("KEEP_TEST_BOARD") != "1":
        cleanup_board(client, board_id_val)
    else:
        print(f"[INFO] Keeping board {board_id_val}")
    print("\n" + "="*70)
    print(" RESULT")
    print("="*70)
    if success:
        print("[PASS] New API workflow run succeeded")
        return 0
    print("[FAIL] New API workflow run failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
