#!/usr/bin/env python
"""Async SDXL Text-to-Image workflow demo using InvokeAI Python client + Socket.IO events.

This script demonstrates an end-to-end flow:
    1. Resolve configuration (base URL, workflow file, etc.).
    2. Lightweight TCP preflight to fail fast if backend is unreachable.
    3. Instantiate `InvokeAIClient`.
    4. Heuristically select an SDXL Main (and optional VAE) model.
    5. Load the exported GUI workflow JSON (no hard‑coded node UUIDs).
    6. Auto-configure exposed inputs via label/field heuristics.
    7. Submit the workflow with event subscriptions (`invocation_*`).
    8. Stream progress (deriving percentage when backend omits explicit progress).
    9. Await graph completion (`wait_for_completion`).
 10. Map output nodes to generated images (no re-wait / hang risk).
 11. Cleanly disconnect Socket.IO.

Exit codes (non-exhaustive):
    0 success; 1 generic failure / missing model / timeout; 2 backend not reachable;
    3 workflow file missing; other codes reserved for future granular states.

Run with:
        pixi run -e dev python tests/test_sdxl_text_to_image_workflow_async.py

Override behavior via environment variables (all optional):
        INVOKEAI_BASE_URL         Base URL of InvokeAI server.
        WF_TIMEOUT                Seconds to wait for completion (default: 30).
        WF_FILE                   Path to workflow JSON file.
        WF_DEBUG_API_GRAPH        Path to write converted API graph JSON.
        WF_BOARD_ID               Board ID to tag outputs (default: "none").
        WF_QUEUE_ID               Queue ID (default: "default").
        WF_SOCKET_TIMEOUT         Seconds for TCP preflight timeout (default: 0.5).
        WF_MODEL_HINTS            Comma list of model name substrings to prefer.

All external resources (paths, hostnames, IDs) are centralized below as variables
so nothing is hard-coded deep in the execution logic.
"""
from __future__ import annotations

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Any
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient  # type: ignore  # noqa: E402
from invokeai_py_client.workflow import WorkflowRepository  # type: ignore  # noqa: E402
from invokeai_py_client.dnn_model import (  # type: ignore  # noqa: E402
    DnnModelRepository,
    DnnModelType,
    BaseDnnModelType,
)

# Configuration (kept modest for CI speed)
TEST_PROMPT = "A futuristic city skyline with flying cars, cyberpunk aesthetic, neon lights, detailed architecture"
TEST_NEGATIVE = "blurry, low quality, distorted, ugly"
OUTPUT_WIDTH = 1024
OUTPUT_HEIGHT = 1024
NUM_STEPS = 16  # fewer steps for faster async test
CFG_SCALE = 7.0
SCHEDULER = "euler"
TIMEOUT = int(os.environ.get("WF_TIMEOUT", "30"))

# ---------------------------------------------------------------------------
# Centralized external resource + runtime configuration
# ---------------------------------------------------------------------------
BASE_URL = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090")
WORKFLOW_FILE = Path(os.environ.get(
    "WF_FILE",
    Path(__file__).parent.parent / "data" / "workflows" / "sdxl-text-to-image.json"
))
DEBUG_API_GRAPH_PATH = Path(os.environ.get(
    "WF_DEBUG_API_GRAPH",
    "tmp/sdxl_text_to_image_api_graph_async.json"
))
BOARD_ID = os.environ.get("WF_BOARD_ID", "none")
QUEUE_ID = os.environ.get("WF_QUEUE_ID", "default")
SOCKET_CONNECT_TIMEOUT = float(os.environ.get("WF_SOCKET_TIMEOUT", "0.5"))
PRIORITY_MODEL_HINTS = [h.strip() for h in os.environ.get("WF_MODEL_HINTS", "juggernaut,cyberrealistic").split(",") if h.strip()]


def select_sdxl_models(repo: DnnModelRepository) -> dict[str, Any]:
    """Select SDXL main model (heuristic) and optionally VAE."""
    print("\n[MODEL DISCOVERY - ASYNC TEST]")
    all_models = repo.list_models()
    mains = [m for m in all_models if m.type == DnnModelType.Main and m.base == BaseDnnModelType.StableDiffusionXL]
    vaes = [m for m in all_models if m.type == DnnModelType.VAE and m.base == BaseDnnModelType.StableDiffusionXL]

    chosen_main = None
    for p in PRIORITY_MODEL_HINTS:
        chosen_main = next((m for m in mains if p in m.name.lower()), None)
        if chosen_main:
            break
    if not chosen_main and mains:
        chosen_main = mains[0]
    chosen_vae = vaes[0] if vaes else None

    for label, mdl in [("main", chosen_main), ("vae", chosen_vae)]:
        print(f"[{ 'OK' if mdl else 'MISSING'}] {label}: {getattr(mdl,'name','<none>')}")
    return {"main": chosen_main, "vae": chosen_vae}


def configure_workflow(workflow: Any, models: dict[str, Any]) -> None:
    """Configure workflow inputs via index/heuristics; no hard-coded node UUIDs."""
    print("\n[CONFIGURE INPUTS - ASYNC]")

    # Build map node_id -> type for heuristics
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

    pos_idx = find_input(lambda inp: inp.field_name == "value" and "positive" in (inp.label or "").lower())
    if pos_idx is not None:
        updates[pos_idx] = TEST_PROMPT
    neg_idx = find_input(lambda inp: inp.field_name == "value" and "negative" in (inp.label or "").lower())
    if neg_idx is not None:
        updates[neg_idx] = TEST_NEGATIVE

    width_idx = find_input(lambda inp: inp.field_name == "width")
    if width_idx is not None:
        updates[width_idx] = OUTPUT_WIDTH
    height_idx = find_input(lambda inp: inp.field_name == "height")
    if height_idx is not None:
        updates[height_idx] = OUTPUT_HEIGHT

    steps_idx = find_input(lambda inp: inp.field_name == "steps" and node_type_map.get(inp.node_id, "") == "denoise_latents")
    if steps_idx is not None:
        updates[steps_idx] = NUM_STEPS
    cfg_idx = find_input(lambda inp: inp.field_name == "cfg_scale" and node_type_map.get(inp.node_id, "") == "denoise_latents")
    if cfg_idx is not None:
        updates[cfg_idx] = CFG_SCALE
    sched_idx = find_input(lambda inp: inp.field_name == "scheduler" and node_type_map.get(inp.node_id, "") == "denoise_latents")
    if sched_idx is not None:
        updates[sched_idx] = SCHEDULER

    print(f"[INFO] Applying {len(updates)} updates (explicit loop; set_many removed)")
    for idx, val in updates.items():
        try:
            workflow._set_input_value_simple_impl(idx, val)  # type: ignore[attr-defined]
        except AttributeError:
            # Fallback: direct field mutation when possible
            fld = workflow.get_input_value(idx)
            if hasattr(fld, 'value') and not isinstance(val, dict):
                try:
                    fld.value = val  # type: ignore[attr-defined]
                except Exception:
                    pass
            elif isinstance(val, dict):
                for k, v in val.items():
                    if hasattr(fld, k):
                        setattr(fld, k, v)
        except Exception as e:
            print(f"[WARN] could not set input {idx}: {e}")
    print("[DEBUG] Input preview (index label type value):")
    for row in workflow.preview():
        print(f"  [{row['index']:02d}] {row['label']} ({row['type']}): {row['value']}")

async def run_async_test() -> int:
    """Orchestrate async submission + event monitoring."""
    print("\n" + "=" * 70)
    print(" SDXL TEXT-TO-IMAGE WORKFLOW ASYNC TEST")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Fast preflight: attempt TCP connect to host:port with short timeout to avoid long hangs when backend absent
    try:
        from urllib.parse import urlparse
        import socket
        parsed = urlparse(BASE_URL)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        with socket.create_connection((host, port), timeout=SOCKET_CONNECT_TIMEOUT):
            pass
    except Exception:
        print(f"[SKIP] Backend not reachable at {BASE_URL}")
        return 1

    try:
        client = InvokeAIClient(base_url=BASE_URL)
        print(f"[OK] Client ready @ {BASE_URL}")
    except Exception as e:
        print(f"[ERROR] Cannot initialize client: {e}")
        return 1

    models = select_sdxl_models(client.dnn_model_repo)
    if not models.get("main"):
        print("[ERROR] No SDXL main model available")
        return 1

    workflow_path = WORKFLOW_FILE
    if not workflow_path.exists():
        print(f"[ERROR] Workflow file not found: {workflow_path}")
        return 1

    repo = WorkflowRepository(client)
    try:
        workflow = repo.create_workflow_from_file(str(workflow_path))
        print(f"\n[OK] Loaded workflow '{workflow.definition.name}' with {len(workflow.inputs)} inputs")
    except Exception as e:
        print(f"[ERROR] Failed to load workflow: {e}")
        return 1

    configure_workflow(workflow, models)

    # Save API graph for debugging parity with sync test
    api_graph = workflow._convert_to_api_format("none")
    debug_path = DEBUG_API_GRAPH_PATH
    debug_path.parent.mkdir(exist_ok=True)
    with open(debug_path, "w") as f:
        json.dump(api_graph, f, indent=2)
    print(f"[DEBUG] Saved API graph to {debug_path}")

    # Event callbacks
    def on_started(evt: dict[str, Any]):
        if evt.get("session_id") == workflow.session_id:
            print(f"  ▶ {evt.get('node_type')} started")

    # Local state for synthetic progress
    synthetic_state = {"denoise_steps": 0, "printed_schema": False}

    def on_progress(evt: dict[str, Any]):
        if evt.get("session_id") != workflow.session_id:
            return

        msg = (evt.get("message") or "").lower()
        pct: float | None = None

        # 1. Direct numeric 'progress' (0..1)
        if isinstance(evt.get("progress"), (int, float)):
            try:
                val = float(evt["progress"])
                if 0 <= val <= 1.05:
                    pct = max(0.0, min(1.0, val)) * 100
            except Exception:
                pct = None

        # 2. Alternate key pairs (current/total, step/steps, iteration/iterations, etc.)
        if pct is None:
            current_keys = ["current", "step", "steps_done", "iteration", "iter", "i", "denoise_step", "current_step"]
            total_keys = ["total", "total_steps", "max_steps", "steps", "iterations", "num_steps"]
            cur_val = None
            total_val = None
            for ck in current_keys:
                if ck in evt and isinstance(evt[ck], (int, float)):
                    cur_val = float(evt[ck])
                    break
            for tk in total_keys:
                if tk in evt and isinstance(evt[tk], (int, float)):
                    total_val = float(evt[tk])
                    break
            if cur_val is not None and total_val and total_val > 0:
                pct = (cur_val / total_val) * 100

        # 3. Synthetic: count denoising passes if message contains 'denois'
        if pct is None and "denois" in msg:
            synthetic_state["denoise_steps"] += 1
            pct = (synthetic_state["denoise_steps"] / NUM_STEPS) * 100

        # Clamp and print
        if pct is not None:
            print(f"  ⏳ {pct:5.1f}% {evt.get('message','')}")
        else:
            if not synthetic_state["printed_schema"]:
                # Print available keys once to aid debugging missing progress
                keys_preview = ", ".join(sorted(k for k in evt.keys() if k not in {"session_id"}))
                print(f"  ⏳ progress keys: {keys_preview}")
                synthetic_state["printed_schema"] = True
            print(f"  ⏳ progress event: {evt.get('message','')}")

    def on_complete(evt: dict[str, Any]):
        if evt.get("session_id") == workflow.session_id:
            print(f"  ✅ {evt.get('node_type')} complete")

    def on_error(evt: dict[str, Any]):
        if evt.get("session_id") == workflow.session_id:
            print(f"  ❌ Error in {evt.get('node_type')}: {evt.get('error')}")

    print("\n[SUBMIT - ASYNC]")
    try:
        submission = await workflow.submit(
            board_id=BOARD_ID,
            subscribe_events=True,
            on_invocation_started=on_started,
            on_invocation_progress=on_progress,
            on_invocation_complete=on_complete,
            on_invocation_error=on_error,
        )
    except Exception as e:
        print(f"[ERROR] Submission failed: {e}")
        return 1

    print(f"[OK] Submitted batch={submission['batch_id']} session={submission['session_id']}")

    try:
        raw_result = await workflow.wait_for_completion(timeout=TIMEOUT)
        if isinstance(raw_result, tuple):  # defensive typing
            queue_item = raw_result[0]
        else:
            queue_item = raw_result
    except asyncio.TimeoutError:
        print(f"[ERROR] Timeout after {TIMEOUT}s")
        return 1
    except Exception as e:
        print(f"[ERROR] Execution failed: {e}")
        return 1

    status = queue_item.get("status")  # type: ignore[union-attr]
    print(f"[DONE] Final status={status}")
    if status != "completed":
        return 1

    # Optional: map outputs to images (direct mapping; avoid re-waiting which could hang)
    try:
        mappings = workflow.map_outputs_to_images(queue_item)
        for m in mappings:
            print(f"  Output idx={m.get('input_index')} images={m.get('image_names')}")
    except Exception as e:
        print(f"[WARN] Output mapping failed: {e}")

    # Clean up socket connection to ensure loop can exit
    try:
        await client.disconnect_socketio()
    except Exception:
        pass

    print("\n[PASS] Async SDXL Text-to-Image workflow completed successfully")
    return 0


def main() -> int:
    return asyncio.run(run_async_test())


if __name__ == "__main__":
    raise SystemExit(main())
