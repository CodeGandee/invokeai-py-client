#!/usr/bin/env python
"""Minimal FLUX image-to-image example.

This script executes a FLUX image-to-image workflow. Below is a map of the
settable inputs discovered from the workflow's form layout.

  +--------------------------------------------------+
  |               FLUX Image-to-Image                |
  +--------------------------------------------------+
  |                                                  |
  |  Model (Dropdown)                                |
  |  +--------------------------------------------+  |
  |  | flux1-schnell                              |  |
  |  +--------------------------------------------+  |
  |                                                  |
  |  Image (Upload)                                  |
  |  +--------------------------------------------+  |
  |  | [  Image Preview (1024x1024)             ] |  |
  |  +--------------------------------------------+  |
  |                                                  |
  |  T5 Encoder (Dropdown)                           |
  |  +--------------------------------------------+  |
  |  | t5_bnb_int8_quantized_encoder              |  |
  |  +--------------------------------------------+  |
  |                                                  |
  |  CLIP Embed (Dropdown)                           |
  |  +--------------------------------------------+  |
  |  | clip-vit-large-patch14                     |  |
  |  +--------------------------------------------+  |
  |                                                  |
  |  VAE (Dropdown)                                  |
  |  +--------------------------------------------+  |
  |  | FLUX.1-schnell_ae                          |  |
  |  +--------------------------------------------+  |
  |                                                  |
  |  Positive Prompt (Text)                          |
  |  +--------------------------------------------+  |
  |  | good looking girl                          |  |
  |  +--------------------------------------------+  |
  |                                                  |
  |  Negative Prompt (Text)                          |
  |  +--------------------------------------------+  |
  |  | naked, adult                               |  |
  |  +--------------------------------------------+  |
  |                                                  |
  |  Num Steps (Number)                              |
  |  +--------------------------------------------+  |
  |  | 10                                         |  |
  |  +--------------------------------------------+  |
  |                                                  |
  |  Denoising Start (Number)                        |
  |  +--------------------------------------------+  |
  |  | 0.4                                        |  |
  |  +--------------------------------------------+  |
  |                                                  |
  +--------------------------------------------------+

Intentionally tiny: no defensive error handling, no model lookup heuristics.
Steps:
    1. Pick a sample PNG from data/images
    2. Upload to the uncategorized board ('none')
    3. Load the exported workflow JSON
    4. Assign a random positive / fixed negative prompt + image input
    5. Submit synchronously and wait for completion

Run (InvokeAI at default URL):
  pixi run -e dev python examples/pipelines/flux-image-to-image.py
"""
from __future__ import annotations

from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box

# Assumes execution from repository root (pixi run ...). Paths are relative.

from invokeai_py_client import InvokeAIClient  # noqa: E402
from invokeai_py_client.workflow import WorkflowDefinition  # noqa: E402

#############################################
# SERVER / PATH CONFIG
#############################################
INVOKEAI_BASE_URL = "http://127.0.0.1:9090"  # Running InvokeAI server
IMAGE_DIR = Path("data/images")              # Input images folder
WORKFLOW_PATH = Path("data/workflows/flux-image-to-image.json")  # Exported workflow JSON
BOARD_ID = "none"                            # 'none' => uncategorized board
SAMPLE_IMAGE_FILENAME = "8079126e-6cb0-4d47-956a-0eec6b71c600.png"

#############################################
# EXECUTION / POLL PARAMETERS
#############################################
POLL_INTERVAL_SEC = 2.0       # Queue polling interval
TIMEOUT_SEC = 300.0           # Overall wait timeout

#############################################
# GENERATION PARAMETERS
#############################################
STEPS = 15                    # num_steps
NOISE_RATIO = 0.7             # 0..1, used to derive denoising_start = 1 - NOISE_RATIO
NEGATIVE_PROMPT_DEFAULT = "blurry, low quality, distorted"

#############################################
# PROMPTS (FIXED CONTENT-FOLLOWING)
#############################################
POSITIVE_PROMPT = (
    "A beautiful woman with long, flowing dark brown hair and warm, expressive eyes, enjoying a peaceful moment "
    "on a sun-drenched balcony overlooking the sea. She wears an elegant, off-white sundress with delicate lace details. "
    "The scene is filled with the golden light of a late afternoon sun, casting soft shadows. "
    "In the background, vibrant bougainvillea flowers cascade down a rustic stone wall. "
    "The atmosphere is serene and joyful. Cinematic, high detail, soft fabric texture, warm, glowing sunlight."
)


console = Console()
client = InvokeAIClient.from_url(INVOKEAI_BASE_URL)

# 1. Pick sample & upload image to 'none' board
chosen_image_path = IMAGE_DIR / SAMPLE_IMAGE_FILENAME
chosen_image_bytes = chosen_image_path.read_bytes()
board_handle = client.board_repo.get_board_handle(BOARD_ID)
uploaded_image = board_handle.upload_image_data(image_data=chosen_image_bytes, filename=chosen_image_path.name)

# 2. Load workflow definition & create handle
workflow_definition = WorkflowDefinition.from_file(str(WORKFLOW_PATH))
workflow_handle = client.workflow_repo.create_workflow(workflow_definition)

############################
# INPUT DISCOVERY & MAPPING
############################
synced_models = workflow_handle.sync_dnn_model(by_name=True, by_base=True)
console.rule("Model Synchronization")
console.print(f"[bold green]Models synchronized:[/bold green] {len(synced_models)}")
if synced_models:
    tbl = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
    tbl.add_column("Original Name")
    tbl.add_column("Original Key")
    tbl.add_column("Resolved Name")
    tbl.add_column("Resolved Key")
    for orig, resolved in synced_models:
        try:
            tbl.add_row(
                getattr(orig, 'name', '?'),
                getattr(orig, 'key', '?'),
                getattr(resolved, 'name', '?'),
                getattr(resolved, 'key', '?'),
            )
        except Exception:  # pragma: no cover
            continue
    console.print(tbl)

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

# Depth-first indices (stable unless form structure changes)
# ---------------------------------------------------------------------------
# The GUI form (see ASCII header above) is traversed in a pre-order depth-first
# walk of its container tree. Each 'node-field-*' element encountered becomes
# the next workflow input. The constants below are the resulting indices for
# the current workflow JSON. If you add/remove/reorder form elements in the
# workflow definition, all subsequent indices after the change will shift.
# Treat these as a snapshot tied to this workflow version.
# ---------------------------------------------------------------------------
IDX_MODEL = 0
IDX_IMAGE = 1
IDX_T5 = 2
IDX_CLIP = 3
IDX_VAE = 4
IDX_POS_PROMPT = 5
IDX_NEG_PROMPT = 6
IDX_STEPS = 7
IDX_DENOISE_START = 8

positive_prompt = POSITIVE_PROMPT
negative_prompt = NEGATIVE_PROMPT_DEFAULT
uploaded_name = uploaded_image.image_name

def set_and_log(idx: int | None, value):
    """Set a workflow input by depth-first index and log the assignment.

    Parameters
    ----------
    idx : int | None
        Depth-first input index (see IDX_* constants). If None, the call is ignored.
    value : Any
        Value to assign. Must be compatible with the underlying IvkField's ``.value``.

    Returns
    -------
    None

    Notes
    -----
    This uses ``WorkflowHandle.set_input_value_simple`` so the existing field object
    is preserved and only its value/attributes are updated. Validation occurs inside
    that helper. Only the new value is printed (previous value is intentionally omitted
    to keep the log concise).
    """
    if idx is None:
        console.print(f"[yellow][warn][/yellow] Skipping set; index not found for value={value!r}")
        return
    inp = workflow_handle.get_input(idx)
    workflow_handle.set_input_value_simple(idx, value)
    current = getattr(inp.field, 'value', None)
    console.print(f"[bold blue]Set[/bold blue] input[{idx}] [italic]{(inp.label or inp.field_name)!r}[/italic] ({inp.field_name}) = {current!r}")

set_and_log(IDX_IMAGE, uploaded_name)
set_and_log(IDX_POS_PROMPT, positive_prompt)
set_and_log(IDX_NEG_PROMPT, negative_prompt)
set_and_log(IDX_STEPS, STEPS)
set_and_log(IDX_DENOISE_START, 1 - NOISE_RATIO)

console.rule("Effective Configuration")
config_tbl = Table(show_header=False, box=box.MINIMAL_DOUBLE_HEAD)
config_tbl.add_row("POSITIVE_PROMPT", positive_prompt)
config_tbl.add_row("NEGATIVE_PROMPT", negative_prompt)
config_tbl.add_row("STEPS", str(STEPS))
config_tbl.add_row("DENOISING_START", f"{1 - NOISE_RATIO} (derived from NOISE_RATIO={NOISE_RATIO})")
console.print(config_tbl)

############################
# SUBMIT & MONITOR
############################
submission_result = workflow_handle.submit_sync(board_id=BOARD_ID)
_result = workflow_handle.wait_for_completion_sync(
    poll_interval=POLL_INTERVAL_SEC,
    timeout=TIMEOUT_SEC,
    progress_callback=lambda qi: print("Status:", qi.get("status")),
    map_outputs=False,
)
if isinstance(_result, tuple):  # map_outputs=True case (not used here but future-proof)
    queue_item = _result[0]
else:
    queue_item = _result
console.rule("Completion")
console.print(f"Final status: [bold]{queue_item.get('status')}[/bold]")
if queue_item.get("status") == "completed":
    console.print(f"Outputs: [green]{len(queue_item.get('outputs') or [])}[/green]")
