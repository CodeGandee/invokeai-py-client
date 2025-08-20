#!/usr/bin/env python
"""Demonstration / executable test: Map workflow output nodes to final (board_id, image filenames).

Purpose:
  Runs the `sdxl-flux-refine` workflow end-to-end against a locally running InvokeAI instance
  (default http://127.0.0.1:9090) and produces a table mapping each declared output node
  to the board it targeted and the image filenames it produced. This formalizes the
  approach described in `context/hints/howto-map-workflow-image-nodes-to-boards.md`.

Evidence tiers (in priority order) used to collect image names per original output node:
  1. session.results + prepared_source_mapping (authoritative modern source)
  2. Legacy queue_item['outputs'] list (if present)
  3. Descendant traversal through execution graph to find inline image blobs (heuristic fallback)

Board attribution comes from the *original* submission graph node's `board.board_id` when present;
otherwise 'none'. No external board/image endpoint calls or timestamp heuristics are used.

Exit code:
  0 = success (at least one image mapped) / or gracefully skipped (no server)
  1 = failure (workflow ran but produced zero images)
  2 = cannot reach server / setup issue

NOTE: This script mirrors logic in `tmp/task3_2_run_workflow_outputs.py` but is placed under tests/
so it can be treated as an official demonstration. It is safe to invoke manually:

  python tests/test_node_to_image_output_mapping.py
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

# Add src path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
except ImportError:  # pragma: no cover
    print("rich required: pip install rich", file=sys.stderr)
    sys.exit(2)

from invokeai_py_client import InvokeAIClient  # type: ignore
from invokeai_py_client.workflow import WorkflowRepository  # type: ignore

WORKFLOW_FILE = Path("data/workflows/sdxl-flux-refine.json")
BASE_URL = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090")
TIMEOUT_SECONDS = int(os.environ.get("WF_TIMEOUT", "900"))  # allow longer for heavier runs


def _random_prompt(prefix: str) -> str:
    return f"{prefix} {uuid.uuid4()} cinematic, detailed, high quality"


def _configure_prompts(workflow) -> None:
    for inp in workflow.list_inputs():
        label_l = inp.label.lower()
        if inp.field_name == 'prompt' or 'prompt' in label_l:
            if hasattr(inp.field, 'value'):
                prefix = 'Positive' if 'negative' not in label_l else 'Negative'
                inp.field.value = _random_prompt(prefix)


def _submit_and_wait(workflow, console: Console) -> dict[str, Any]:
    start = time.time()
    result = workflow.submit_sync()
    console.print(f"[green]Submitted batch_id={result.get('batch_id')} item_id={workflow.item_id} session_id={result.get('session_id')}[/green]")
    queue_item = workflow.wait_for_completion_sync(timeout=TIMEOUT_SECONDS, poll_interval=2.0)
    elapsed = time.time() - start
    console.print(f"[bold green]Completed in {elapsed:.1f}s status={queue_item.get('status')}[/bold green]")
    return queue_item


def _map_outputs(queue_item: dict[str, Any], workflow) -> list[dict[str, Any]]:
    session_graph = queue_item.get('session', {}).get('graph', {})
    graph_nodes: dict[str, Any] = session_graph.get('nodes', {}) or {}
    exec_graph = queue_item.get('session', {}).get('execution_graph', {})
    exec_nodes: dict[str, Any] = (exec_graph.get('nodes') or {})
    exec_edges = exec_graph.get('edges', []) or []
    session_data = queue_item.get('session', {}) or {}
    session_results: dict[str, Any] = session_data.get('results', {}) or {}
    prepared_source_mapping: dict[str, str] = session_data.get('prepared_source_mapping', {}) or {}

    # Build adjacency for fallback traversal
    forward: dict[str, list[str]] = {}
    for e in exec_edges:
        try:
            src = e.get('source', {}).get('node_id')
            dst = e.get('destination', {}).get('node_id')
            if src and dst:
                forward.setdefault(src, []).append(dst)
        except Exception:
            continue

    # Tier 1: results -> original mapping
    results_images: dict[str, list[str]] = {}
    for prepared_id, payload in session_results.items():
        original_id = prepared_source_mapping.get(prepared_id, prepared_id)
        img_obj = (payload or {}).get('image') or {}
        name = img_obj.get('image_name')
        if name:
            results_images.setdefault(original_id, [])
            if name not in results_images[original_id]:
                results_images[original_id].append(name)

    # Tier 2: legacy outputs array
    legacy_images: dict[str, list[str]] = {}
    for out in queue_item.get('outputs', []) or []:
        node_id = out.get('node_id') or out.get('id')
        img_obj = out.get('image') or {}
        name = img_obj.get('image_name')
        if node_id and name:
            legacy_images.setdefault(node_id, []).append(name)

    # Tier 3: descendant traversal
    def descend_collect(start: str) -> list[str]:
        seen, stack, found = set(), [start], []
        while stack:
            nid = stack.pop()
            if nid in seen:
                continue
            seen.add(nid)
            node_data = exec_nodes.get(nid, {})
            img_obj = node_data.get('image') or {}
            name = img_obj.get('image_name')
            if name and name not in found:
                found.append(name)
            for nxt in forward.get(nid, []):
                if nxt not in seen:
                    stack.append(nxt)
        return found

    outputs_meta: list[dict[str, Any]] = []
    for out_inp in workflow.list_outputs():
        node_id = out_inp.node_id
        node_graph = graph_nodes.get(node_id, {})
        board_entry = node_graph.get('board', {}) if isinstance(node_graph.get('board'), dict) else {}
        board_id = board_entry.get('board_id') or 'none'

        images = list(results_images.get(node_id, []))
        tier = 'results' if images else ''
        if not images:
            images = list(legacy_images.get(node_id, []))
            tier = 'legacy' if images else tier
        if not images:
            images = descend_collect(node_id)
            tier = 'traversal' if images else tier or 'none'

        outputs_meta.append({
            'node_id': node_id,
            'board_id': board_id,
            'image_names': images,
            'tier': tier,
            'node_type': node_graph.get('type', 'unknown'),
            'input_index': out_inp.input_index,
            'label': out_inp.label,
        })
    return outputs_meta


def _render(console: Console, outputs_meta: list[dict[str, Any]], queue_item: dict[str, Any]) -> None:
    table = Table(title="Output Node → Board/Image Mapping", box=box.SIMPLE_HEAVY)
    table.add_column("#", style="cyan")
    table.add_column("Idx", style="magenta")
    table.add_column("Node ID", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Board", style="blue")
    table.add_column("Tier", style="cyan")
    table.add_column("Images", style="white")
    for i, meta in enumerate(outputs_meta, start=1):
        imgs = "\n".join(meta['image_names']) if meta['image_names'] else "(none)"
        table.add_row(str(i), str(meta['input_index']), meta['node_id'][:12] + '…', meta['node_type'], meta['board_id'], meta['tier'], imgs)
    console.print(table)

    total_images = sum(len(m['image_names']) for m in outputs_meta)
    panel = Panel(f"Total images: {total_images}\nSession: {queue_item.get('session_id')}\nItem: {queue_item.get('item_id')}\nStatus: {queue_item.get('status')}", title="Summary", box=box.ROUNDED)
    console.print(panel)


def main() -> int:
    console = Console()
    console.print("[bold cyan]\nNode→Image Mapping Demonstration (sdxl-flux-refine)\n[/bold cyan]")

    if not WORKFLOW_FILE.exists():
        console.print(f"[red]Workflow file not found: {WORKFLOW_FILE}[/red]")
        return 2

    # Quick server reachability check
    import requests  # type: ignore
    try:
        r = requests.get(f"{BASE_URL}/api/v1/app/version", timeout=5)
        r.raise_for_status()
    except Exception as e:
        console.print(f"[yellow]Skipping: cannot reach InvokeAI server at {BASE_URL}: {e}[/yellow]")
        return 0  # treat as graceful skip

    client = InvokeAIClient(base_url=BASE_URL)
    repo = WorkflowRepository(client)
    workflow = repo.create_workflow_from_file(str(WORKFLOW_FILE))

    _configure_prompts(workflow)
    outputs = workflow.list_outputs()
    if not outputs:
        console.print("[red]No output nodes detected; aborting.[/red]")
        return 1

    try:
        queue_item = _submit_and_wait(workflow, console)
    except Exception as e:  # pragma: no cover - runtime
        console.print(f"[red]Workflow execution failed: {e}[/red]")
        return 1

    outputs_meta = _map_outputs(queue_item, workflow)
    _render(console, outputs_meta, queue_item)

    images_total = sum(len(m['image_names']) for m in outputs_meta)
    if images_total == 0:
        console.print("[red]No images discovered via mapping tiers (results/legacy/traversal).[/red]")
        return 1

    console.print("[green]Mapping successful.[/green]")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
