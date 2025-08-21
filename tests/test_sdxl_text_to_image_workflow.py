#!/usr/bin/env python
"""SDXL Text-to-Image workflow demo (sync + async) using InvokeAI Python client.

Two execution styles shown:
  1. Sync: submit + HTTP polling loop.
  2. Async: submit + Socket.IO events (progress + completion callbacks).

Design goals:
  * No dependence on node UUIDs (heuristic discovery of exposed inputs).
  * Zero environment-variable config; all constants below in one place.
  * Clear separation of concerns (model select, configure, submit/monitor).
  * Concise comments (kept practical—trim further for production if desired).
"""
from __future__ import annotations

import sys
import time
import asyncio
import socket
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Make local src/ importable when executing file directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient  # type: ignore
from invokeai_py_client.workflow import WorkflowRepository  # type: ignore
from invokeai_py_client.dnn_model import (  # type: ignore
    DnnModelRepository,
    DnnModelType,
    BaseDnnModelType,
)

# ----------------------------- CONSTANTS ----------------------------------
TEST_PROMPT = (
    "A futuristic city skyline with flying cars, cyberpunk aesthetic, neon lights, "
    "detailed architecture"
)
TEST_NEGATIVE = "blurry, low quality, distorted, ugly"
OUTPUT_WIDTH = 1024
OUTPUT_HEIGHT = 1024
NUM_STEPS_SYNC = 24
NUM_STEPS_ASYNC = 16
CFG_SCALE = 7.0
SCHEDULER = "euler"
BASE_URL = "http://127.0.0.1:9090"
WORKFLOW_FILE = Path(__file__).parent.parent / "data" / "workflows" / "sdxl-text-to-image.json"
BOARD_ID = "none"
QUEUE_ID = "default"
SOCKET_CONNECT_TIMEOUT = 0.5
PRIORITY_MODEL_HINTS = ["juggernaut", "cyberrealistic"]
TIMEOUT_SYNC = 180
TIMEOUT_ASYNC = 30
DEBUG_GRAPH_SYNC = Path("tmp/sdxl_text_to_image_api_graph.json")
DEBUG_GRAPH_ASYNC = Path("tmp/sdxl_text_to_image_api_graph_async.json")
RUN_SYNC = True
RUN_ASYNC = True


def select_sdxl_models(repo: DnnModelRepository, label: str) -> dict[str, Any]:
    """Pick SDXL main (and optional VAE) using substring priority order."""
    print(f"\n[MODEL DISCOVERY - {label}]")
    all_models = repo.list_models()
    mains = [m for m in all_models if m.type == DnnModelType.Main and m.base == BaseDnnModelType.StableDiffusionXL]
    vaes = [m for m in all_models if m.type == DnnModelType.VAE and m.base == BaseDnnModelType.StableDiffusionXL]
    chosen_main = None
    for hint in PRIORITY_MODEL_HINTS:
        chosen_main = next((m for m in mains if hint in m.name.lower()), None)
        if chosen_main:
            break
    if not chosen_main and mains:
        chosen_main = mains[0]
    chosen_vae = vaes[0] if vaes else None
    for tag, mdl in [("main", chosen_main), ("vae", chosen_vae)]:
        print(f"[{ 'OK' if mdl else 'MISSING'}] {tag}: {getattr(mdl,'name','<none>')}")
    return {"main": chosen_main, "vae": chosen_vae}


def configure_workflow(workflow: Any, models: dict[str, Any], *, steps: int) -> None:
    """Configure exposed inputs heuristically (labels / field names / node types)."""
    print("\n[CONFIGURE INPUTS]")
    node_type_map: dict[str, str] = {}
    try:
        for n in workflow.definition.nodes:  # type: ignore[attr-defined]
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
        midx = find_input(lambda i: i.field_name == "model" and node_type_map.get(i.node_id, "").startswith("sdxl_model_loader"))
        if midx is not None:
            updates[midx] = {
                "key": main_model.key,
                "hash": main_model.hash,
                "name": main_model.name,
                "base": getattr(main_model.base, 'value', str(main_model.base)),
                "type": getattr(main_model.type, 'value', str(main_model.type)),
            }
    pos_idx = find_input(lambda i: i.field_name == "value" and "positive" in (i.label or "").lower())
    if pos_idx is not None:
        updates[pos_idx] = TEST_PROMPT
    neg_idx = find_input(lambda i: i.field_name == "value" and "negative" in (i.label or "").lower())
    if neg_idx is not None:
        updates[neg_idx] = TEST_NEGATIVE
    w_idx = find_input(lambda i: i.field_name == "width")
    if w_idx is not None:
        updates[w_idx] = OUTPUT_WIDTH
    h_idx = find_input(lambda i: i.field_name == "height")
    if h_idx is not None:
        updates[h_idx] = OUTPUT_HEIGHT
    steps_idx = find_input(lambda i: i.field_name == "steps" and node_type_map.get(i.node_id, "") == "denoise_latents")
    if steps_idx is not None:
        updates[steps_idx] = steps
    cfg_idx = find_input(lambda i: i.field_name == "cfg_scale" and node_type_map.get(i.node_id, "") == "denoise_latents")
    if cfg_idx is not None:
        updates[cfg_idx] = CFG_SCALE
    sched_idx = find_input(lambda i: i.field_name == "scheduler" and node_type_map.get(i.node_id, "") == "denoise_latents")
    if sched_idx is not None:
        updates[sched_idx] = SCHEDULER
    # set_many removed: apply explicitly
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
    print(f"[INFO] Applied {len(updates)} updates (explicit loop; set_many removed)")
    for row in workflow.preview():
        print(f"  [{row['index']:02d}] {row['label']} ({row['type']}): {row['value']}")


def submit_and_monitor_sync(client: InvokeAIClient, workflow: Any) -> bool:
    """Submit synchronously then poll until terminal status."""
    print("\n[SYNC][SUBMIT]")
    errors = workflow.validate_inputs()
    if errors:
        for idx, errs in errors.items():
            print(f"[SYNC][ERROR] input {idx}: {', '.join(errs)}")
        return False
    try:
        result = workflow.submit_sync()
    except Exception as e:
        print(f"[SYNC][ERROR] submission failed: {e}")
        return False
    item_ids = result.get("item_ids", [])
    item_id = item_ids[0] if item_ids else None
    print(f"[SYNC][OK] batch={result.get('batch_id')} item={item_id}")
    if not item_id:
        return False
    url = f"{client.base_url}/queue/{QUEUE_ID}/i/{item_id}"
    start = time.time()
    last = None
    while time.time() - start < TIMEOUT_SYNC:
        try:
            r = client.session.get(url)
            r.raise_for_status()
            qi = r.json()
            st = qi.get("status")
            if st != last:
                print(f"  [SYNC] status={st}")
                last = st
            if st in {"completed", "failed", "canceled"}:
                print(f"[SYNC][DONE] {st}")
                if st == "completed":
                    outs = qi.get("outputs") or []
                    print(f"[SYNC][OK] outputs={len(outs)}")
                    for o in outs[:3]:
                        if o.get("type") == "image_output":
                            print(f"    - {o.get('image', {}).get('image_name','<no-name>')}")
                    return True
                return False
        except Exception as e:
            print(f"  [SYNC][WARN] {e}")
        time.sleep(3)
    print(f"[SYNC][ERROR] timeout after {TIMEOUT_SYNC}s")
    return False


async def run_async_workflow(client: InvokeAIClient) -> bool:
    """Submit asynchronously and stream progress via Socket.IO."""
    # Fast TCP preflight
    try:
        parsed = urlparse(BASE_URL)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        with socket.create_connection((host, port), timeout=SOCKET_CONNECT_TIMEOUT):
            pass
    except Exception:
        print(f"[ASYNC][SKIP] unreachable {BASE_URL}")
        return False
    models = select_sdxl_models(client.dnn_model_repo, "ASYNC")
    if not models.get("main"):
        return False
    if not WORKFLOW_FILE.exists():
        print(f"[ASYNC][ERROR] missing workflow file {WORKFLOW_FILE}")
        return False
    repo = WorkflowRepository(client)
    try:
        workflow = repo.create_workflow_from_file(str(WORKFLOW_FILE))
    except Exception as e:
        print(f"[ASYNC][ERROR] load failed: {e}")
        return False
    print(f"[ASYNC][OK] workflow '{workflow.definition.name}' inputs={len(workflow.inputs)}")
    configure_workflow(workflow, models, steps=NUM_STEPS_ASYNC)
    # Debug API graph generation removed (private method usage deprecated)

    synth = {"denoise_steps": 0, "printed_keys": False}
    def on_started(evt: dict[str, Any]):
        if evt.get("session_id") == workflow.session_id:
            print(f"  [ASYNC] ▶ {evt.get('node_type')} started")
    def on_progress(evt: dict[str, Any]):
        if evt.get("session_id") != workflow.session_id:
            return
        msg = (evt.get("message") or "").lower()
        pct = None
        if isinstance(evt.get("progress"), (int, float)):
            try:
                val = float(evt["progress"])
                if 0 <= val <= 1.05:
                    pct = min(1.0, max(0.0, val)) * 100
            except Exception:
                pass
        if pct is None and "denois" in msg:
            synth["denoise_steps"] += 1
            pct = (synth["denoise_steps"] / NUM_STEPS_ASYNC) * 100
        if pct is not None:
            print(f"  [ASYNC] ⏳ {pct:5.1f}% {evt.get('message','')}")
        else:
            if not synth["printed_keys"]:
                print("  [ASYNC] progress keys: " + ", ".join(k for k in evt.keys() if k != "session_id"))
                synth["printed_keys"] = True
            print(f"  [ASYNC] ⏳ {evt.get('message','')}")
    def on_complete(evt: dict[str, Any]):
        if evt.get("session_id") == workflow.session_id:
            print(f"  [ASYNC] ✅ {evt.get('node_type')} complete")
    def on_error(evt: dict[str, Any]):
        if evt.get("session_id") == workflow.session_id:
            print(f"  [ASYNC] ❌ {evt.get('node_type')} -> {evt.get('error')}")

    print("\n[ASYNC][SUBMIT]")
    try:
        submission = await workflow.submit(
            subscribe_events=True,
            on_invocation_started=on_started,
            on_invocation_progress=on_progress,
            on_invocation_complete=on_complete,
            on_invocation_error=on_error,
        )
    except Exception as e:
        print(f"[ASYNC][ERROR] submission failed: {e}")
        return False
    print(f"[ASYNC][OK] batch={submission['batch_id']} session={submission['session_id']}")
    try:
        res = await workflow.wait_for_completion(timeout=TIMEOUT_ASYNC)
        queue_item = res[0] if isinstance(res, tuple) else res
    except asyncio.TimeoutError:
        print(f"[ASYNC][ERROR] timeout after {TIMEOUT_ASYNC}s")
        return False
    except Exception as e:
        print(f"[ASYNC][ERROR] wait failed: {e}")
        return False
    status = queue_item.get("status")
    print(f"[ASYNC][DONE] status={status}")
    if status != "completed":
        return False
    try:
        for m in workflow.map_outputs_to_images(queue_item):
            print(f"  [ASYNC] Output idx={m.get('input_index')} images={m.get('image_names')}")
    except Exception:
        pass
    try:
        await client.disconnect_socketio()
    except Exception:
        pass
    print("[ASYNC][PASS] completed")
    return True


def run_sync_workflow(client: InvokeAIClient) -> bool:
    models = select_sdxl_models(client.dnn_model_repo, "SYNC")
    if not models.get("main"):
        print("[SYNC][ERROR] no main model")
        return False
    if not WORKFLOW_FILE.exists():
        print(f"[SYNC][ERROR] missing workflow file {WORKFLOW_FILE}")
        return False
    repo = WorkflowRepository(client)
    try:
        workflow = repo.create_workflow_from_file(str(WORKFLOW_FILE))
    except Exception as e:
        print(f"[SYNC][ERROR] load failed: {e}")
        return False
    print(f"[SYNC][OK] workflow '{workflow.definition.name}' inputs={len(workflow.inputs)}")
    configure_workflow(workflow, models, steps=NUM_STEPS_SYNC)
    # Debug API graph generation removed (private method usage deprecated)
    return submit_and_monitor_sync(client, workflow)


def main() -> int:
    print("\n" + "=" * 70)
    print(" SDXL TEXT-TO-IMAGE WORKFLOW (SYNC + ASYNC)")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        client = InvokeAIClient(base_url=BASE_URL)
        print(f"[OK] Client ready @ {BASE_URL}")
    except Exception as e:
        print(f"[ERROR] init failed: {e}")
        return 1
    sync_result = True
    async_result = True
    if RUN_SYNC:
        print("\n--- RUN SYNC MODE ---")
        sync_result = run_sync_workflow(client)
    else:
        print("[INFO] sync disabled")
    if RUN_ASYNC:
        print("\n--- RUN ASYNC MODE ---")
        async_result = asyncio.run(run_async_workflow(client))
    else:
        print("[INFO] async disabled")
    print("\n" + "=" * 70)
    print(" RESULT SUMMARY")
    print("=" * 70)
    print(f"Sync:  {'PASS' if sync_result else 'FAIL'} (enabled={RUN_SYNC})")
    print(f"Async: {'PASS' if async_result else 'FAIL'} (enabled={RUN_ASYNC})")
    return 0 if ((not RUN_SYNC or sync_result) and (not RUN_ASYNC or async_result)) else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
