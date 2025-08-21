#!/usr/bin/env python
"""SDXL + FLUX Refine Workflow Example (sync)

This end-to-end example runs the composite SDXL -> Flux Domain Transfer -> Flux Refinement
workflow (`sdxl-flux-refine.json`) using the same style as the simpler examples:
  * Explicit, index-centric workflow input mapping (pre-order GUI form traversal)
  * Inline assignment of field values (no helper DSL / deprecated convenience funcs)
    * Rich console tables (requires `rich`) and an in-memory `images_by_node` map
  * Board selection by GUI name (optional) applied to ALL board input fields

GUI FORM (concatenated from two screenshots, pre-order / depth-first indices shown)
================================================================================
  (0) Positive Prompt                (1) Negative Prompt
  +-----------------------------+    +-----------------------------+
  | beautiful girl, relax,...  |    | naked, bad quality          |
  +-----------------------------+    +-----------------------------+

  (2) Output Width               (3) Output Height
  +-----------+                  +-----------+
  |   600     |                  |   800     |
  +-----------+                  +-----------+

  --------------------- Generation Stage ----------------------
  (4) SDXL Model                          (5) Output Board
  +-------------------------------+       +-------------------+
  | sdxlUnstableDiffusers_...     |       | None (Uncategorized)
  +-------------------------------+       +-------------------+
  (6) Scheduler   (7) Steps   (8) CFG Scale
  +-----------+   +------+    +----------+
  | Euler ... |   | 20   |    | 7.5      |
  +-----------+   +------+    +----------+

  (9)  Positive Append (string right)     (10) Negative Append (string right)
  +-----------------------------+         +-----------------------------+
  | real photography, ...       |         | unrealistic, painting, ...  |
  +-----------------------------+         +-----------------------------+

  (11) Flux Model (loader)
  (12) T5 Encoder   (13) CLIP Embed   (14) VAE   (15) Model (Control/Union)
  (16) Output Board
  (17) Noise Ratio (Domain Transfer)   (18) Num Steps   (19) Control Weight

  --------------------- Flux Refinement -----------------------
  (20) Flux Model (Refine)    (21) Output Board
  (22) Num Steps              (23) Control Weight    (24) Noise Ratio
================================================================================
NOTE
----
Indices above are a SNAPSHOT for the current exported workflow revision. If the
workflow form structure changes (added/removed/reordered containers or fields),
these indices will shift. To re-inspect after a workflow export change, just
run this script again; it always prints a full enumerated table of current
input indices before applying any values. Update the IDX_* constants below if
the ordering changes.

Run (InvokeAI default URL):
  pixi run -e dev python examples/pipelines/sdxl-flux-refine.py
"""
from __future__ import annotations

from pathlib import Path
import os
import tempfile
from typing import Any, Union

from rich.console import Console
from rich.table import Table
from rich import box

from invokeai_py_client import InvokeAIClient  # type: ignore
from invokeai_py_client.workflow import WorkflowDefinition  # type: ignore
from invokeai_py_client.workflow.workflow_handle import OutputMapping  # type: ignore
from invokeai_py_client.board.board_handle import BoardHandle  # type: ignore
from invokeai_py_client.ivk_fields import (  # type: ignore
    IvkStringField,
    IvkIntegerField,
    IvkFloatField,
    IvkBoardField,
)
from invokeai_py_client.ivk_fields.models import IvkModelIdentifierField  # type: ignore

# In-memory images dict: node_id -> (input_index, image_name, PIL Image)
images_by_node: dict[str, tuple[int, str, Any]] = {}

# --------------------------- CONFIG -----------------------------------------
INVOKEAI_BASE_URL = os.getenv("INVOKEAI_BASE_URL", "http://127.0.0.1:9090")
WORKFLOW_PATH = Path("data/workflows/sdxl-flux-refine.json")
BOARD_NAME: str | None = None   # Optional GUI board name to apply to all board inputs (None => 'none')
SAVE_IMAGES = True
OUTPUT_DIR = Path(os.getenv("INVOKEAI_EXAMPLE_OUTPUT_DIR") or tempfile.gettempdir())
POLL_INTERVAL_SEC = 2.0
TIMEOUT_SEC = 360.0

# User-tunable prompt / sampler params
POS_PROMPT = "A majestic mountain landscape at sunset, golden hour lighting, photorealistic, 8k quality"
NEG_PROMPT = "blurry, low quality, distorted"
WIDTH = 768
HEIGHT = 1024
SDXL_STEPS = 20
SDXL_CFG_SCALE = 7.5
SDXL_SCHEDULER = "euler_a"  # Valid scheduler (formerly often called 'euler_ancestral')
FLUX_DOMAIN_STEPS = 10
FLUX_DOMAIN_NOISE_RATIO = 0.85  # (field 'b')
FLUX_DOMAIN_CONTROL_WEIGHT = 0.3
FLUX_REFINEMENT_STEPS = 12
FLUX_REFINEMENT_NOISE_RATIO = 0.8
FLUX_REFINEMENT_CONTROL_WEIGHT = 0.05
POS_APPEND = "real photography, high quality"
NEG_APPEND = "unrealistic, cartoon"

console = Console()
client = InvokeAIClient.from_url(INVOKEAI_BASE_URL)

# --------------------------- LOAD WORKFLOW ----------------------------------
workflow_definition: WorkflowDefinition = WorkflowDefinition.from_file(str(WORKFLOW_PATH))
workflow_handle = client.workflow_repo.create_workflow(workflow_definition)

# --------------------------- MODEL SYNC -------------------------------------
synced = workflow_handle.sync_dnn_model(by_name=True, by_base=True)
if synced:
    console.rule("Model Synchronization")
    for o, r in synced:
        console.print(f"[green]Resolved[/green] {getattr(o,'name','?')} -> {getattr(r,'name','?')}")

# --------------------------- ENUMERATE INPUTS -------------------------------
inputs = workflow_handle.list_inputs()
console.rule("Discovered Workflow Inputs")
inputs_tbl = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
inputs_tbl.add_column("Idx", justify="right")
inputs_tbl.add_column("Label")
inputs_tbl.add_column("Field")
inputs_tbl.add_column("Node")
inputs_tbl.add_column("Req")
for inp in inputs:
    inputs_tbl.add_row(str(inp.input_index), (inp.label or inp.field_name) or '-', inp.field_name, inp.node_name, 'Y' if inp.required else '')
console.print(inputs_tbl)

# --------------------------- OUTPUTS ENUMERATION ---------------------------
exposed_outputs = workflow_handle.list_outputs()
output_index_by_node_id = {out.node_id: out.input_index for out in exposed_outputs}
console.rule("Discovered Workflow Outputs")
outputs_tbl = Table(show_header=True, header_style="bold green", box=box.SIMPLE)
outputs_tbl.add_column("Idx", justify="right")
outputs_tbl.add_column("Node Name")
outputs_tbl.add_column("Node ID")
outputs_tbl.add_column("Label")
outputs_tbl.add_column("Field")
for out in exposed_outputs:
    outputs_tbl.add_row(str(out.input_index), out.node_name, out.node_id[:8], (out.label or out.field_name) or '-', out.field_name)
if not exposed_outputs:
    outputs_tbl.caption = "(No output nodes with exposed board fields)"
console.print(outputs_tbl)
# --------------------------- BOARD SELECTION --------------------------------
try:
    boards = client.board_repo.list_boards(include_uncategorized=True)
except Exception as _e:  # pragma: no cover
    boards = []
    console.print(f"[yellow]Warning: could not list boards: {_e}[/yellow]")

bt = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
bt.add_column("Board ID")
bt.add_column("Name")
bt.add_column("Images", justify="right")
bt.add_column("Uncat?", justify="center")
for b in boards:
    bid = getattr(b, 'board_id', '?')
    name = getattr(b, 'board_name', '') or ''
    count = str(getattr(b, 'image_count', ''))
    is_uncat = 'Y' if getattr(b, 'is_uncategorized', lambda: False)() else ''
    bt.add_row(bid, name, count, is_uncat)
console.rule("Available Boards")
console.print(bt)

BOARD_ID = 'none'
if BOARD_NAME and boards:
    match = next((b for b in boards if getattr(b,'board_name','').lower() == BOARD_NAME.lower()), None)
    if match:
        BOARD_ID = getattr(match, 'board_id', 'none')
        console.print(f"[green]Using board by name[/green]: '{BOARD_NAME}' (id={BOARD_ID})")
    else:
        console.print(f"[yellow]Board name '{BOARD_NAME}' not found; using 'none'.[/yellow]")
else:
    console.print(f"[cyan]Using uncategorized board id[/cyan]: {BOARD_ID}")

# --------------------------- INDEX CONSTANTS --------------------------------
# SNAPSHOT indices (see ASCII layout). If workflow form changes, re-inspect.
IDX_POS_PROMPT = 0
IDX_NEG_PROMPT = 1
IDX_WIDTH = 2
IDX_HEIGHT = 3
IDX_SDXL_MODEL = 4
IDX_SDXL_BOARD = 5
IDX_SDXL_SCHEDULER = 6
IDX_SDXL_STEPS = 7
IDX_SDXL_CFG_SCALE = 8
IDX_FLUX_POS_APPEND = 9
IDX_FLUX_NEG_APPEND = 10
IDX_FLUX_MODEL = 11
IDX_T5_ENCODER = 12
IDX_CLIP_EMBED = 13
IDX_FLUX_VAE = 14
IDX_FLUX_CONTROL_MODEL = 15
IDX_DOMAIN_BOARD = 16
IDX_DOMAIN_NOISE_RATIO = 17
IDX_DOMAIN_STEPS = 18
IDX_DOMAIN_CONTROL_WEIGHT = 19
IDX_REFINEMENT_MODEL = 20
IDX_REFINEMENT_BOARD = 21
IDX_REFINEMENT_STEPS = 22
IDX_REFINEMENT_CONTROL_WEIGHT = 23
IDX_REFINEMENT_NOISE_RATIO = 24

# --------------------------- FIELD RETRIEVAL --------------------------------
# Helper to fetch and assert type quickly

def _get(idx: int) -> Any:
    return workflow_handle.get_input_value(idx)

# Prompts
pos_field: IvkStringField = _get(IDX_POS_PROMPT)  # type: ignore[assignment]
neg_field: IvkStringField = _get(IDX_NEG_PROMPT)  # type: ignore[assignment]
if hasattr(pos_field, 'value'):
    pos_field.value = POS_PROMPT  # type: ignore[attr-defined]
if hasattr(neg_field, 'value'):
    neg_field.value = NEG_PROMPT  # type: ignore[attr-defined]

# Dimensions
width_field: IvkIntegerField = _get(IDX_WIDTH)  # type: ignore[assignment]
height_field: IvkIntegerField = _get(IDX_HEIGHT)  # type: ignore[assignment]
if hasattr(width_field, 'value'):
    width_field.value = WIDTH  # type: ignore[attr-defined]
if hasattr(height_field, 'value'):
    height_field.value = HEIGHT  # type: ignore[attr-defined]

# SDXL Stage
sdxl_model: IvkModelIdentifierField = _get(IDX_SDXL_MODEL)  # type: ignore[assignment]
board_stage: Union[IvkStringField, IvkBoardField] = _get(IDX_SDXL_BOARD)  # type: ignore[assignment]
scheduler_field = _get(IDX_SDXL_SCHEDULER)
steps_field: IvkIntegerField = _get(IDX_SDXL_STEPS)  # type: ignore[assignment]
cfg_field: IvkFloatField = _get(IDX_SDXL_CFG_SCALE)  # type: ignore[assignment]
if hasattr(steps_field, 'value'):
    steps_field.value = SDXL_STEPS  # type: ignore[attr-defined]
if hasattr(cfg_field, 'value'):
    cfg_field.value = SDXL_CFG_SCALE  # type: ignore[attr-defined]
if hasattr(scheduler_field, 'value'):
    # Normalize a few common alias spellings to valid literal values
    _sched_aliases = {
        "euler_ancestral": "euler_a",
        "euler-ancestral": "euler_a",
        "euler ancestral": "euler_a",
    }
    desired = _sched_aliases.get(SDXL_SCHEDULER.lower(), SDXL_SCHEDULER)
    try:
        scheduler_field.value = desired  # type: ignore[attr-defined]
    except Exception:
        pass

# Flux Domain Transfer Inputs
pos_append_field: IvkStringField = _get(IDX_FLUX_POS_APPEND)  # type: ignore[assignment]
neg_append_field: IvkStringField = _get(IDX_FLUX_NEG_APPEND)  # type: ignore[assignment]
if hasattr(pos_append_field, 'value'):
    pos_append_field.value = POS_APPEND  # type: ignore[attr-defined]
if hasattr(neg_append_field, 'value'):
    neg_append_field.value = NEG_APPEND  # type: ignore[attr-defined]
flux_model_field: IvkModelIdentifierField = _get(IDX_FLUX_MODEL)  # type: ignore[assignment]
t5_field: IvkModelIdentifierField = _get(IDX_T5_ENCODER)  # type: ignore[assignment]
clip_field: IvkModelIdentifierField = _get(IDX_CLIP_EMBED)  # type: ignore[assignment]
vae_field: IvkModelIdentifierField = _get(IDX_FLUX_VAE)  # type: ignore[assignment]
control_union_field = _get(IDX_FLUX_CONTROL_MODEL)

domain_board_field: Union[IvkStringField, IvkBoardField] = _get(IDX_DOMAIN_BOARD)  # type: ignore[assignment]
noise_ratio_field: IvkFloatField = _get(IDX_DOMAIN_NOISE_RATIO)  # type: ignore[assignment]
domain_steps_field: IvkIntegerField = _get(IDX_DOMAIN_STEPS)  # type: ignore[assignment]
control_weight_field: IvkFloatField = _get(IDX_DOMAIN_CONTROL_WEIGHT)  # type: ignore[assignment]
if hasattr(noise_ratio_field, 'value'):
    noise_ratio_field.value = FLUX_DOMAIN_NOISE_RATIO  # type: ignore[attr-defined]
if hasattr(domain_steps_field, 'value'):
    domain_steps_field.value = FLUX_DOMAIN_STEPS  # type: ignore[attr-defined]
if hasattr(control_weight_field, 'value'):
    control_weight_field.value = FLUX_DOMAIN_CONTROL_WEIGHT  # type: ignore[attr-defined]

# Flux Refinement
refine_model_field = _get(IDX_REFINEMENT_MODEL)
refine_board_field: Union[IvkStringField, IvkBoardField] = _get(IDX_REFINEMENT_BOARD)  # type: ignore[assignment]
refine_steps_field: IvkIntegerField = _get(IDX_REFINEMENT_STEPS)  # type: ignore[assignment]
refine_control_weight_field: IvkFloatField = _get(IDX_REFINEMENT_CONTROL_WEIGHT)  # type: ignore[assignment]
refine_noise_ratio_field: IvkFloatField = _get(IDX_REFINEMENT_NOISE_RATIO)  # type: ignore[assignment]
if hasattr(refine_steps_field, 'value'):
    refine_steps_field.value = FLUX_REFINEMENT_STEPS  # type: ignore[attr-defined]
if hasattr(refine_control_weight_field, 'value'):
    refine_control_weight_field.value = FLUX_REFINEMENT_CONTROL_WEIGHT  # type: ignore[attr-defined]
if hasattr(refine_noise_ratio_field, 'value'):
    refine_noise_ratio_field.value = FLUX_REFINEMENT_NOISE_RATIO  # type: ignore[attr-defined]

# Apply selected board id to all board-capable fields
for fld in (board_stage, domain_board_field, refine_board_field):
    if hasattr(fld, 'value'):
        try:
            fld.value = BOARD_ID  # type: ignore[attr-defined]
        except Exception:
            pass

# --------------------------- LOG CONFIG -------------------------------------
console.rule("Configured Inputs (subset)")
log_tbl = Table(show_header=True, header_style="bold blue", box=box.SIMPLE)
log_tbl.add_column("Idx", justify="right")
log_tbl.add_column("Name")
log_tbl.add_column("Value")
sel_indices = [
    (IDX_POS_PROMPT, pos_field),
    (IDX_NEG_PROMPT, neg_field),
    (IDX_WIDTH, width_field),
    (IDX_HEIGHT, height_field),
    (IDX_SDXL_STEPS, steps_field),
    (IDX_SDXL_CFG_SCALE, cfg_field),
    (IDX_FLUX_POS_APPEND, pos_append_field),
    (IDX_FLUX_NEG_APPEND, neg_append_field),
    (IDX_DOMAIN_NOISE_RATIO, noise_ratio_field),
    (IDX_DOMAIN_STEPS, domain_steps_field),
    (IDX_REFINEMENT_STEPS, refine_steps_field),
    (IDX_REFINEMENT_NOISE_RATIO, refine_noise_ratio_field),
]
for idx, fld in sel_indices:
    meta = workflow_handle.get_input(idx)
    log_tbl.add_row(str(idx), (meta.label or meta.field_name) or '-', repr(getattr(fld,'value', None)))
console.print(log_tbl)

# --------------------------- SUBMIT -----------------------------------------
console.rule("Submission")
submission: dict[str, Any] = workflow_handle.submit_sync()

# Wait for completion
try:
    queue_item: dict[str, Any] = workflow_handle.wait_for_completion_sync(
        poll_interval=POLL_INTERVAL_SEC,
        timeout=TIMEOUT_SEC,
        progress_callback=lambda qi: console.print(f"Status: {qi.get('status')}") if qi.get('status') else None,
    )
except RuntimeError as e:
    if 'canceled' in str(e).lower():
        console.print("[red]Workflow canceled.[/red]")
        queue_item = {"status": "canceled", "error": str(e)}
    else:
        raise

console.rule("Completion")
status = queue_item.get('status')
console.print(f"Final status: [bold]{status}[/bold]")
if status == 'completed':
    mappings: list[OutputMapping] = workflow_handle.map_outputs_to_images(queue_item)
    # Table of mapped outputs
    results_tbl = Table(show_header=True, header_style="bold green", box=box.SIMPLE)
    results_tbl.add_column("Node ID")
    results_tbl.add_column("Tier")
    results_tbl.add_column("# Images", justify="right")
    results_tbl.add_column("First Image Name")
    for m in mappings:
        img_names = m.get('image_names') or []
        results_tbl.add_row(m['node_id'][:8], str(m.get('tier')), str(len(img_names)), img_names[0] if img_names else '')
    console.print(results_tbl)
    if SAVE_IMAGES and mappings:
        try:
            from io import BytesIO
            from PIL import Image  # type: ignore
        except Exception:
            console.print('[yellow]Pillow not installed; skipping image save.[/yellow]')
        else:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            saved = 0
            for m in mappings:
                image_names = m.get('image_names') or []
                if not image_names:
                    continue
                name = image_names[0]
                bh: BoardHandle = client.board_repo.get_board_handle(m.get('board_id') or 'none')
                try:
                    data: bytes = bh.download_image(name, full_resolution=True)
                    img = Image.open(BytesIO(data))
                    # store tuple: (input_index, image_name, PIL image)
                    images_by_node[m['node_id']] = (
                        output_index_by_node_id.get(m['node_id'], -1),
                        name,
                        img.copy() if hasattr(img, 'copy') else img,
                    )
                    dest = OUTPUT_DIR / name
                    try:
                        img.save(dest)
                    except Exception:
                        dest = dest.with_suffix('.png')
                        img.save(dest, format='PNG')
                    saved += 1
                    console.print(f"[green]Saved[/green] {dest}")
                except Exception as ex:  # pragma: no cover
                    console.print(f"[red]Failed {name}: {ex}[/red]")
            console.print(f"Saved {saved} file(s).")
            if images_by_node:
                console.print("[bold cyan]In-memory images stored in 'images_by_node' dict (node_id -> (input_index, image_name, PIL image)).[/bold cyan]")
else:
    console.print('[red]Workflow did not complete successfully.[/red]')

