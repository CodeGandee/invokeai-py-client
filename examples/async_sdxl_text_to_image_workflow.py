#!/usr/bin/env python
"""Async SDXL Text-to-Image workflow demo using event streaming.

Run with:
    pixi run -e dev python examples/async_sdxl_text_to_image_workflow.py

Environment variables:
    INVOKEAI_BASE_URL   (default: http://127.0.0.1:9090)
    WF_TIMEOUT          (default: 30 seconds)

Exits 0 on success, non-zero otherwise.
"""
from __future__ import annotations

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Any
from datetime import datetime

# Add src to path (repo root = parent of this file's parent)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from invokeai_py_client import InvokeAIClient  # type: ignore  # noqa: E402
from invokeai_py_client.workflow import WorkflowRepository  # type: ignore  # noqa: E402
from invokeai_py_client.dnn_model import (  # type: ignore  # noqa: E402
    DnnModelRepository,
    DnnModelType,
    BaseDnnModelType,
)

# ---------------------------------------------------------------------------
# Configuration (kept modest for faster demo)
# ---------------------------------------------------------------------------
TEST_PROMPT = "A futuristic city skyline with flying cars, cyberpunk aesthetic, neon lights, detailed architecture"
TEST_NEGATIVE = "blurry, low quality, distorted, ugly"
OUTPUT_WIDTH = 1024
OUTPUT_HEIGHT = 1024
NUM_STEPS = 16
CFG_SCALE = 7.0
SCHEDULER = "euler"
TIMEOUT = int(os.environ.get("WF_TIMEOUT", "30"))


def select_sdxl_models(repo: DnnModelRepository) -> dict[str, Any]:
    """Select SDXL main + optional VAE model heuristically."""
    print("\n[MODEL DISCOVERY - ASYNC DEMO]")
    all_models = repo.list_models()
    mains = [m for m in all_models if m.type == DnnModelType.Main and m.base == BaseDnnModelType.StableDiffusionXL]
    vaes = [m for m in all_models if m.type == DnnModelType.VAE and m.base == BaseDnnModelType.StableDiffusionXL]

    priorities = ["juggernaut", "cyberrealistic"]
    chosen_main = None
    for p in priorities:
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
    """Configure workflow inputs via index/heuristics (no hard-coded UUIDs)."""
    print("\n[CONFIGURE INPUTS - ASYNC]")

    # Build node id -> type map
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

    print(f"[INFO] Applying {len(updates)} updates via set_many()")
    workflow.set_many(updates)
    print("[DEBUG] Input preview (index label type value):")
    for row in workflow.preview():
        print(f"  [{row['index']:02d}] {row['label']} ({row['type']}): {row['value']}")


+async def run_async_demo() -> int:
+    print("\n" + "=" * 70)
+    print(" SDXL TEXT-TO-IMAGE WORKFLOW ASYNC DEMO")
+    print("=" * 70)
+    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
+
+    base_url = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090")
+
+    # Fast preflight: attempt TCP connect to host:port quickly
+    try:
+        from urllib.parse import urlparse
+        import socket
+        parsed = urlparse(base_url)
+        host = parsed.hostname or "127.0.0.1"
+        port = parsed.port or 80
+        with socket.create_connection((host, port), timeout=0.5):
+            pass
+    except Exception:
+        print(f"[ERROR] Backend not reachable at {base_url}")
+        return 2
+
+    try:
+        client = InvokeAIClient(base_url=base_url)
+        print(f"[OK] Client ready @ {base_url}")
+    except Exception as e:
+        print(f"[ERROR] Cannot initialize client: {e}")
+        return 1
+
+    models = select_sdxl_models(client.dnn_model_repo)
+    if not models.get("main"):
+        print("[ERROR] No SDXL main model available")
+        return 3
+
+    workflow_path = ROOT / "data" / "workflows" / "sdxl-text-to-image.json"
+    if not workflow_path.exists():
+        print(f"[ERROR] Workflow file not found: {workflow_path}")
+        return 4
+
+    repo = WorkflowRepository(client)
+    try:
+        workflow = repo.create_workflow_from_file(str(workflow_path))
+        print(f"\n[OK] Loaded workflow '{workflow.definition.name}' with {len(workflow.inputs)} inputs")
+    except Exception as e:
+        print(f"[ERROR] Failed to load workflow: {e}")
+        return 5
+
+    configure_workflow(workflow, models)
+
+    # Save API graph for debugging
+    try:
+        api_graph = workflow._convert_to_api_format("none")  # noqa: SLF001
+        debug_path = ROOT / "tmp" / "sdxl_text_to_image_api_graph_async.json"
+        debug_path.parent.mkdir(exist_ok=True)
+        with open(debug_path, "w") as f:
+            json.dump(api_graph, f, indent=2)
+        print(f"[DEBUG] Saved API graph to {debug_path}")
+    except Exception as e:
+        print(f"[WARN] Could not save API graph: {e}")
+
+    # Event callbacks
+    def on_started(evt: dict[str, Any]):
+        if evt.get("session_id") == workflow.session_id:
+            print(f"  ▶ {evt.get('node_type')} started")
+
+    def on_progress(evt: dict[str, Any]):
+        if evt.get("session_id") == workflow.session_id and evt.get("progress") is not None:
+            pct = evt["progress"] * 100
+            print(f"  ⏳ {pct:.0f}% {evt.get('message','')}")
+
+    def on_complete(evt: dict[str, Any]):
+        if evt.get("session_id") == workflow.session_id:
+            print(f"  ✅ {evt.get('node_type')} complete")
+
+    def on_error(evt: dict[str, Any]):
+        if evt.get("session_id") == workflow.session_id:
+            print(f"  ❌ Error in {evt.get('node_type')}: {evt.get('error')}")
+
+    print("\n[SUBMIT - ASYNC]")
+    try:
+        submission = await workflow.submit(
+            board_id="none",
+            subscribe_events=True,
+            on_invocation_started=on_started,
+            on_invocation_progress=on_progress,
+            on_invocation_complete=on_complete,
+            on_invocation_error=on_error,
+        )
+    except Exception as e:
+        print(f"[ERROR] Submission failed: {e}")
+        return 6
+
+    print(f"[OK] Submitted batch={submission['batch_id']} session={submission['session_id']}")
+
+    try:
+        raw_result = await workflow.wait_for_completion(timeout=TIMEOUT)
+        queue_item = raw_result[0] if isinstance(raw_result, tuple) else raw_result
+    except asyncio.TimeoutError:
+        print(f"[ERROR] Timeout after {TIMEOUT}s")
+        return 7
+    except Exception as e:
+        print(f"[ERROR] Execution failed: {e}")
+        return 8
+
+    status = queue_item.get("status")  # type: ignore[union-attr]
+    print(f"[DONE] Final status={status}")
+    if status != "completed":
+        return 9
+
+    # Optional output mapping
+    try:
+        _, mappings = await workflow.wait_for_completion(map_outputs=True)
+        for m in mappings:
+            if isinstance(m, dict):
+                print(f"  Output idx={m.get('input_index')} images={m.get('image_names')}")
+    except Exception:
+        pass
+
+    print("\n[SUCCESS] Async SDXL Text-to-Image workflow completed")
+    return 0
+
+
+def main() -> int:
+    return asyncio.run(run_async_demo())
+
+
+if __name__ == "__main__":  # pragma: no cover
+    raise SystemExit(main())
