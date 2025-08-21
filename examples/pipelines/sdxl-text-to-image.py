#!/usr/bin/env python
"""Minimal SDXL Text-to-Image example (sync).

This mirrors the style of `flux-image-to-image.py`: explicit indexed input mapping,
inline assignment, rich console tables, and an in-memory `final_image` variable
for notebook users.

ASCII representation of the current GUI form (depth‑first / pre-order):

    +------------------------------------------------------------------+
    |                      SDXL Text-to-Image                          |
    +------------------------------------------------------------------+
    | Model (Main SDXL)                                                |
    | +--------------------------------------------------------------+ |
    | | <model dropdown>                                             | |
    | +--------------------------------------------------------------+ |
    |                                                                  |
    | positive prompt (String)                                        |
    | +--------------------------------------------------------------+ |
    | | deep space, high quality, colorful                           | |
    | +--------------------------------------------------------------+ |
    |                                                                  |
    | negative prompt (String)                                        |
    | +--------------------------------------------------------------+ |
    | | earth, star war, blurry                                      | |
    | +--------------------------------------------------------------+ |
    |                                                                  |
    | Width (Number)                                                   |
    | +--------------------------------------------------------------+ |
    | | 768                                                          | |
    | +--------------------------------------------------------------+ |
    |                                                                  |
    | Height (Number)                                                  |
    | +--------------------------------------------------------------+ |
    | | 1024                                                         | |
    | +--------------------------------------------------------------+ |
    |                                                                  |
    | Steps (Number)                                                   |
    | +--------------------------------------------------------------+ |
    | | 30                                                           | |
    | +--------------------------------------------------------------+ |
    |                                                                  |
    | CFG Scale (Number/Float)                                        |
    | +--------------------------------------------------------------+ |
    | | 7.5                                                          | |
    | +--------------------------------------------------------------+ |
    |                                                                  |
    | Scheduler (String)                                               |
    | +--------------------------------------------------------------+ |
    | | dpmpp_3m_k                                                   | |
    | +--------------------------------------------------------------+ |
    |                                                                  |
    | Board (Dropdown)                                                |
    | +--------------------------------------------------------------+ |
    | | Auto (GUI shows board name; id differs)                      | |
    | +--------------------------------------------------------------+ |
    +------------------------------------------------------------------+

Steps:
  1. Load workflow JSON (`sdxl-text-to-image.json`)
  2. Sync model identifier field (ensures server-known model metadata)
  3. Retrieve inputs deterministically by index (pre-order form traversal)
  4. Assign positive/negative prompts + dims + sampling params
  5. Submit synchronously, wait, map outputs, optionally save first image

Run (InvokeAI at default URL):
  pixi run -e dev python examples/pipelines/sdxl-text-to-image.py
"""
from __future__ import annotations

from pathlib import Path
import os
import tempfile
from typing import Any

from rich.console import Console
from rich.table import Table
from rich import box

from invokeai_py_client import InvokeAIClient  # type: ignore
from invokeai_py_client.workflow import WorkflowDefinition  # type: ignore
from invokeai_py_client.workflow.workflow_handle import OutputMapping  # type: ignore
from invokeai_py_client.ivk_fields import (  # type: ignore
    IvkStringField,
    IvkIntegerField,
    IvkFloatField,
    IvkSchedulerField,
    SchedulerName,
)
from invokeai_py_client.ivk_fields.models import IvkModelIdentifierField  # type: ignore
from invokeai_py_client.board.board_handle import BoardHandle  # type: ignore

# ============================================================================
# NOTE FOR INTERACTIVE (e.g. Jupyter) USERS
# ----------------------------------------------------------------------------
# We expose a placeholder variable `final_image` populated with a Pillow Image
# instance (first generated image) after successful completion. Access it via:
#   display(final_image)
# If generation fails or yields no images, it remains None.
# ============================================================================
final_image = None  # Will hold a PIL.Image.Image at end of script if available

# ------------------------------- CONFIG -------------------------------------
INVOKEAI_BASE_URL = "http://127.0.0.1:9090"
WORKFLOW_PATH = Path("data/workflows/sdxl-text-to-image.json")
BOARD_NAME: str | None = None  # GUI-visible board name to target; None => uncategorized ('none')
# NOTE: Board names are NOT guaranteed unique in InvokeAI; only board_id is
# authoritative. This example allows specifying BOARD_NAME for convenience.
# If multiple boards share the same (case-insensitive) name we will pick the
# FIRST match returned by list_boards(). For production, persist and use
# board_id directly.
SAVE_IMAGES = True            # Toggle saving to OUTPUT_DIR
OUTPUT_DIR = Path(os.getenv("INVOKEAI_EXAMPLE_OUTPUT_DIR") or tempfile.gettempdir())
POLL_INTERVAL_SEC = 2.0
TIMEOUT_SEC = 240.0

# Generation parameters (override workflow defaults)
POSITIVE_PROMPT = (
    "A futuristic city skyline with flying cars, cyberpunk aesthetic, neon lights, detailed architecture"
)
NEGATIVE_PROMPT = "blurry, low quality, distorted, ugly"
OUTPUT_WIDTH = 1024
OUTPUT_HEIGHT = 1024
NUM_STEPS = 30
CFG_SCALE = 7.5
SCHEDULER: SchedulerName = SchedulerName.DPMPP_3M_K

console = Console()
client: InvokeAIClient = InvokeAIClient.from_url(INVOKEAI_BASE_URL)

# 1. Load workflow
workflow_definition: WorkflowDefinition = WorkflowDefinition.from_file(str(WORKFLOW_PATH))
workflow_handle = client.workflow_repo.create_workflow(workflow_definition)

# 2. Sync model identifiers (if model name/hash differs on server)
synced = workflow_handle.sync_dnn_model(by_name=True, by_base=True)
if synced:
    console.rule("Model Synchronization")
    for orig, resolved in synced:
        console.print(f"[green]Resolved[/green] {getattr(orig,'name','?')} -> {getattr(resolved,'name','?')}")

# 3. Discover inputs (stable pre-order traversal of form tree)
inputs = workflow_handle.list_inputs()
console.rule("Discovered Workflow Inputs")
inputs_table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
inputs_table.add_column("Idx", justify="right")
inputs_table.add_column("Label")
inputs_table.add_column("Field")
inputs_table.add_column("Node")
inputs_table.add_column("Required")
for inp in inputs:
    inputs_table.add_row(
        f"{inp.input_index:02d}",
        (inp.label or inp.field_name) or '-',
        inp.field_name,
        inp.node_name,
        "Y" if inp.required else "",
    )
console.print(inputs_table)

# Dynamically discover board input index (field name == 'board') now that the
# workflow form includes it. Falls back to None if absent (older workflow JSON).
BOARD_INPUT_INDEX: int | None = next((i.input_index for i in inputs if i.field_name == 'board'), None)
if BOARD_INPUT_INDEX is not None:
    console.print(f"[green]Detected board input at index {BOARD_INPUT_INDEX}.\n[/green]")
else:
    console.print("[yellow]No 'board' input detected in form; will use uncategorized output.\n[/yellow]")

# Enumerate available boards (IDs vs names) for user clarity. Board IDs are
# used by the API; board names are what the GUI displays. We still use 'none'
# (uncategorized) for submission here, but display alternatives.
try:
    boards = client.board_repo.list_boards(include_uncategorized=True)
except Exception as _e:  # pragma: no cover
    boards = []
    console.print(f"[yellow]Warning: could not list boards: {_e}[/yellow]")
else:
    console.rule("Available Boards (API id vs GUI name)")
    bt = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
    bt.add_column("API Board ID", overflow="fold")
    bt.add_column("Board Name (GUI)")
    bt.add_column("Images", justify="right")
    bt.add_column("Uncategorized", justify="center")
    for b in boards:
        bid = getattr(b, 'board_id', '?')
        bname = getattr(b, 'board_name', '') or ''
        count = str(getattr(b, 'image_count', ''))
        is_uncat = 'Y' if getattr(b, 'is_uncategorized', lambda: False)() else ''
        bt.add_row(bid, bname, count, is_uncat)
    console.print(bt)

# --------------------------------- BOARD SELECTION ---------------------------------
# BOARD SELECTION (as normal workflow input)
DEFAULT_UNCATEGORIZED_ID = 'none'
resolved_board_id = DEFAULT_UNCATEGORIZED_ID
if BOARD_NAME and boards:
    target_lower = BOARD_NAME.lower()
    match = next((b for b in boards if getattr(b, 'board_name', '').lower() == target_lower), None)
    if match:
        resolved_board_id = getattr(match, 'board_id', DEFAULT_UNCATEGORIZED_ID)
        console.print(f"[green]Using board by name[/green]: '{BOARD_NAME}' (id={resolved_board_id})")
    else:
        console.print(f"[yellow]Requested board name '{BOARD_NAME}' not found; using {resolved_board_id} (uncategorized fallback).[/yellow]")
else:
    console.print(f"[cyan]Using uncategorized board id[/cyan]: {resolved_board_id}")


# Depth-first indices (static for current workflow version except board which we now detect)
IDX_MODEL = 0
IDX_POS_PROMPT = 1
IDX_NEG_PROMPT = 2
IDX_WIDTH = 3
IDX_HEIGHT = 4
IDX_STEPS = 5
IDX_CFG_SCALE = 6
IDX_SCHEDULER = 7
# Board index is dynamic (BOARD_INPUT_INDEX) — do NOT rely on hard-coded value.

# 4. Retrieve + assign inline ------------------------------------------------
# Model
field_model: IvkModelIdentifierField = workflow_handle.get_input_value(IDX_MODEL)  # type: ignore[assignment]
assert isinstance(field_model, IvkModelIdentifierField), f"IDX_MODEL expected IvkModelIdentifierField, got {type(field_model)}"
# Positive prompt
field_pos: IvkStringField = workflow_handle.get_input_value(IDX_POS_PROMPT)  # type: ignore[assignment]
assert isinstance(field_pos, IvkStringField)
field_pos.value = POSITIVE_PROMPT
# Negative prompt
field_neg: IvkStringField = workflow_handle.get_input_value(IDX_NEG_PROMPT)  # type: ignore[assignment]
assert isinstance(field_neg, IvkStringField)
field_neg.value = NEGATIVE_PROMPT
# Width
field_width: IvkIntegerField = workflow_handle.get_input_value(IDX_WIDTH)  # type: ignore[assignment]
assert isinstance(field_width, IvkIntegerField)
field_width.value = OUTPUT_WIDTH  # type: ignore[assignment]
# Height
field_height: IvkIntegerField = workflow_handle.get_input_value(IDX_HEIGHT)  # type: ignore[assignment]
assert isinstance(field_height, IvkIntegerField)
field_height.value = OUTPUT_HEIGHT  # type: ignore[assignment]
# Steps
field_steps: IvkIntegerField = workflow_handle.get_input_value(IDX_STEPS)  # type: ignore[assignment]
assert isinstance(field_steps, IvkIntegerField)
field_steps.value = NUM_STEPS  # type: ignore[assignment]
# CFG Scale
field_cfg: IvkFloatField = workflow_handle.get_input_value(IDX_CFG_SCALE)  # type: ignore[assignment]
assert isinstance(field_cfg, IvkFloatField)
field_cfg.value = CFG_SCALE  # type: ignore[assignment]
# Scheduler field (enum-backed)
field_sched = workflow_handle.get_input_value(IDX_SCHEDULER)  # type: ignore[assignment]
if not hasattr(field_sched, 'value'):
    raise TypeError(f"IDX_SCHEDULER field object lacks 'value' attribute (type={type(field_sched)})")
try:
    # Normalize any alias if server still uses legacy naming
    canonical = IvkSchedulerField.normalize_alias(SCHEDULER.value)
    field_sched.value = canonical  # type: ignore[attr-defined]
except Exception as _e:  # pragma: no cover
    console.print(f"[yellow]Warning: could not set scheduler value: {_e}[/yellow]")

# Board field (optional; only if present in this workflow)
if BOARD_INPUT_INDEX is not None:
    try:
        field_board = workflow_handle.get_input_value(BOARD_INPUT_INDEX)  # type: ignore[assignment]
        if hasattr(field_board, 'value'):
            try:
                field_board.value = resolved_board_id  # type: ignore[attr-defined]
            except Exception as _e:  # pragma: no cover
                console.print(f"[yellow]Warning: could not set board field: {_e}[/yellow]")
        else:
            field_board = None  # type: ignore
    except Exception:
        field_board = None  # type: ignore
else:
    field_board = None  # type: ignore

# Helper for logging values

def log_field(idx: int, fld: object) -> None:
    meta = workflow_handle.get_input(idx)
    val = getattr(fld, 'value', None)
    console.print(f"[blue]Configured[/blue] input[{idx}] {(meta.label or meta.field_name)!r} -> {val!r} (type={type(fld).__name__})")

console.rule("Configured Inputs")
_log_items = [
    (IDX_POS_PROMPT, field_pos),
    (IDX_NEG_PROMPT, field_neg),
    (IDX_WIDTH, field_width),
    (IDX_HEIGHT, field_height),
    (IDX_STEPS, field_steps),
    (IDX_CFG_SCALE, field_cfg),
    (IDX_SCHEDULER, field_sched),
]
if field_board is not None and BOARD_INPUT_INDEX is not None:
    _log_items.append((BOARD_INPUT_INDEX, field_board))
for idx, fld in _log_items:
    log_field(idx, fld)

config_tbl = Table(show_header=False, box=box.MINIMAL_DOUBLE_HEAD)
config_tbl.add_row("POSITIVE_PROMPT", POSITIVE_PROMPT)
config_tbl.add_row("NEGATIVE_PROMPT", NEGATIVE_PROMPT)
config_tbl.add_row("WIDTH", str(OUTPUT_WIDTH))
config_tbl.add_row("HEIGHT", str(OUTPUT_HEIGHT))
config_tbl.add_row("STEPS", str(NUM_STEPS))
config_tbl.add_row("CFG_SCALE", str(CFG_SCALE))
config_tbl.add_row("SCHEDULER", SCHEDULER.value)
config_tbl.add_row("BOARD_ID (input)", resolved_board_id if BOARD_INPUT_INDEX is not None else f"(no board field) {resolved_board_id}")
console.print(config_tbl)

# 5. Submit & wait -----------------------------------------------------------
console.rule("Submission")
submission: dict[str, Any] = workflow_handle.submit_sync()  # board chosen via input field

try:
    queue_item: dict[str, Any] = workflow_handle.wait_for_completion_sync(
        poll_interval=POLL_INTERVAL_SEC,
        timeout=TIMEOUT_SEC,
        progress_callback=lambda qi: console.print(f"Status: {qi.get('status')}") if qi.get('status') else None,
    )
except RuntimeError as e:
    if "canceled" in str(e).lower():
        console.print("[red]Workflow canceled.[/red]")
        queue_item = {"status": "canceled", "error": str(e)}
    else:
        raise

console.rule("Completion")
status = queue_item.get("status")
console.print(f"Final status: [bold]{status}[/bold]")
if status == "completed":
    mappings: list[OutputMapping] = workflow_handle.map_outputs_to_images(queue_item)
    console.print(f"Outputs (form-exposed): {len(mappings)}")
    for m in mappings:
        console.print(f"  Node {m['node_id'][:8]} -> {len(m['image_names'])} image(s) (tier={m['tier']})")

    if SAVE_IMAGES and mappings:
        from io import BytesIO
        try:
            from PIL import Image  # type: ignore
        except Exception:
            console.print("[yellow]Pillow not installed; skipping save.[/yellow]")
        else:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            saved = 0
            for m in mappings:
                image_names = m.get('image_names') or []
                if not image_names:
                    continue
                name = image_names[0]  # Current decode emits a single image
                bh: BoardHandle = client.board_repo.get_board_handle(m.get('board_id') or 'none')
                try:
                    data: bytes = bh.download_image(name, full_resolution=True)
                    img = Image.open(BytesIO(data))
                    if final_image is None:
                        try:
                            # Store a copy for notebook usage
                            final_image = img.copy()
                        except Exception:
                            final_image = img
                    dest = OUTPUT_DIR / name
                    try:
                        img.save(dest)
                    except Exception:
                        dest = dest.with_suffix('.png')
                        img.save(dest, format='PNG')
                    saved += 1
                    console.print(f"[green]Saved[/green] {dest}")
                except Exception as e:  # pragma: no cover
                    console.print(f"[red]Failed {name}: {e}[/red]")
            console.print(f"Saved {saved} file(s).")
            if final_image is not None:
                console.print("[bold cyan]In-memory PIL Image available as 'final_image'.[/bold cyan]")
else:
    console.print("[red]Workflow did not complete successfully.[/red]")
