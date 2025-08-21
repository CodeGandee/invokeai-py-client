#!/usr/bin/env python
"""Minimal FLUX image-to-image example (sync).

This mirrors the style of the SDXL example: explicit indexed input mapping,
inline assignment, optional dynamic board selection via a form-exposed
``board`` input, rich console tables, and an in-memory ``final_image``
variable for interactive users.

Below is an ASCII representation of the current GUI form layout
(fields in depth‑first order / pre-order traversal):

    +------------------------------------------------------------------+
    |                      FLUX Image-to-Image                         |
    +------------------------------------------------------------------+
    |                                                                  |
    |  Model (dev variant recommended for Image-to-Image)              |
    |  +------------------------------------------------------------+  |
    |  | flux1-schnell                                              |  |
    |  +------------------------------------------------------------+  |
    |                                                                  |
    |  Image (Upload)                                                  |
    |  +------------------------------------------------------------+  |
    |  | [ Image Preview (1024x1024) ]                               |  |
    |  +------------------------------------------------------------+  |
    |                                                                  |
    |  T5 Encoder (Dropdown)                                           |
    |  +------------------------------------------------------------+  |
    |  | t5_bnb_int8_quantized_encoder                              |  |
    |  +------------------------------------------------------------+  |
    |                                                                  |
    |  CLIP Embed (Dropdown)                                           |
    |  +------------------------------------------------------------+  |
    |  | clip-vit-large-patch14                                     |  |
    |  +------------------------------------------------------------+  |
    |                                                                  |
    |  VAE (Dropdown)                                                  |
    |  +------------------------------------------------------------+  |
    |  | FLUX.1-schnell_ae                                          |  |
    |  +------------------------------------------------------------+  |
    |                                                                  |
    |  Positive Prompt (Text)                                          |
    |  +------------------------------------------------------------+  |
    |  | good looking girl                                          |  |
    |  +------------------------------------------------------------+  |
    |                                                                  |
    |  Negative Prompt (Text)                                          |
    |  +------------------------------------------------------------+  |
    |  | naked, adult                                               |  |
    |  +------------------------------------------------------------+  |
    |                                                                  |
    |  Num Steps (Number)                                              |
    |  +------------------------------------------------------------+  |
    |  | 10                                                         |  |
    |  +------------------------------------------------------------+  |
    |                                                                  |
    |  Denoising Start (Number)                                        |
    |  +------------------------------------------------------------+  |
    |  | 0.4                                                        |  |
    |  +------------------------------------------------------------+  |
    |                                                                  |
    |  Board (Dropdown)                                                |
    |  +------------------------------------------------------------+  |
    |  | None (Uncategorized)                                       |  |
    |  +------------------------------------------------------------+  |
    |                                                                  |
    +------------------------------------------------------------------+

Steps:
    1. Pick a sample PNG from data/images
    2. Upload to target board (default: uncategorized 'none')
    3. Load exported workflow JSON
    4. Sync model identifier fields (resolve hashes/keys)
    5. Enumerate inputs (deterministic pre-order form traversal)
    6. Assign prompts, image, sampler params & board
    7. Submit synchronously & wait for completion
    8. Map outputs & optionally save first image

Board Handling:
    * The board id is now supplied ONLY via the workflow's exposed board field.
    * You may set ``BOARD_NAME`` (GUI display name, case-insensitive) to choose
        a specific board. Names are not guaranteed unique; the FIRST match wins.
    * If ``BOARD_NAME`` is None or no match is found, falls back to 'none'.
    * We list all boards (id vs GUI name) for clarity before submission.

Run (InvokeAI at default URL):
  pixi run -e dev python examples/pipelines/flux-image-to-image.py
"""
from __future__ import annotations

from pathlib import Path
import os
import tempfile
from rich.console import Console
from rich.table import Table
from rich import box
from typing import Union, Any
from PIL import Image

# Field type imports for explicit typing of workflow inputs
from invokeai_py_client.ivk_fields import (
    IvkStringField,
    IvkIntegerField,
    IvkFloatField,
    IvkBoardField,
    IvkImageField,
)
from invokeai_py_client.ivk_fields.models import IvkModelIdentifierField  # type: ignore
from invokeai_py_client.workflow.workflow_handle import OutputMapping  # type: ignore
from invokeai_py_client.board.board_handle import BoardHandle  # type: ignore
from invokeai_py_client.models import IvkImage  # type: ignore

# Assumes execution from repository root (pixi run ...). Paths are relative.

from invokeai_py_client import InvokeAIClient  # noqa: E402
from invokeai_py_client.workflow import WorkflowDefinition  # noqa: E402

# ============================================================================
# NOTE FOR INTERACTIVE (e.g. Jupyter) USERS
# ----------------------------------------------------------------------------
# We expose a placeholder variable `final_image` which will be populated with a
# Pillow Image instance of the FIRST generated output (if any) at the end of
# the script. This makes it easy to inspect the result inline in a notebook:
#
#   display(final_image)
#
# If generation fails or produces no images, it will remain None.
# ============================================================================
final_image: Image.Image | None = None  # Will hold a PIL.Image.Image after successful run

#############################################
# SERVER / PATH CONFIG
#############################################
INVOKEAI_BASE_URL = "http://127.0.0.1:9090"  # Running InvokeAI server
IMAGE_DIR = Path("data/images")              # Input images folder
WORKFLOW_PATH = Path("data/workflows/flux-image-to-image.json")  # Exported workflow JSON
BOARD_NAME: str | None = None                # GUI board name to target (None => uncategorized)
DEFAULT_UNCATEGORIZED_ID = "none"           # Stable uncategorized board id
SAMPLE_IMAGE_FILENAME = "8079126e-6cb0-4d47-956a-0eec6b71c600.png"

#############################################
# OUTPUT / SAVE CONFIG (EXTERNAL RESOURCE)
#############################################
# Directory where generated images will be saved. Treat this as an external
# resource configurable by the user of this script. Defaults to system temp.
OUTPUT_DIR = Path(os.getenv("INVOKEAI_EXAMPLE_OUTPUT_DIR") or tempfile.gettempdir())
SAVE_IMAGES = True   # Toggle saving

#############################################
# EXECUTION / POLL PARAMETERS
#############################################
POLL_INTERVAL_SEC = 2.0       # Queue polling interval
TIMEOUT_SEC = 300.0           # Overall wait timeout

#############################################
# GENERATION PARAMETERS
#############################################
STEPS = 10                    # num_steps
NOISE_RATIO = 0.85             # 0..1, used to derive denoising_start = 1 - NOISE_RATIO
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

# Use console for pretty printing
console: Console = Console()

# Initialize the InvokeAI client, connect to InvokeAI server
client: InvokeAIClient = InvokeAIClient.from_url(INVOKEAI_BASE_URL)

# 1. Pick sample image file
chosen_image_path: Path = IMAGE_DIR / SAMPLE_IMAGE_FILENAME
chosen_image_bytes: bytes = chosen_image_path.read_bytes()

# Enumerate boards (id vs GUI name) and resolve board id by name (optional)
try:
    boards = client.board_repo.list_boards(include_uncategorized=True)
except Exception as _e:  # pragma: no cover
    boards = []
    print(f"[WARN] Could not list boards: {_e}")

def _board_table():
    tbl = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
    tbl.add_column("API Board ID", overflow="fold")
    tbl.add_column("Board Name (GUI)")
    tbl.add_column("Images", justify="right")
    tbl.add_column("Uncat?", justify="center")
    for b in boards:
        bid = getattr(b, 'board_id', '?')
        bname = getattr(b, 'board_name', '') or ''
        count = str(getattr(b, 'image_count', ''))
        is_uncat = 'Y' if getattr(b, 'is_uncategorized', lambda: False)() else ''
        tbl.add_row(bid, bname, count, is_uncat)
    return tbl

console.rule("Available Boards (API id vs GUI name)")
console.print(_board_table())

resolved_board_id = DEFAULT_UNCATEGORIZED_ID
if BOARD_NAME and boards:
    target_lower = BOARD_NAME.lower()
    match = next((b for b in boards if getattr(b, 'board_name', '').lower() == target_lower), None)
    if match:
        resolved_board_id = getattr(match, 'board_id', DEFAULT_UNCATEGORIZED_ID)
        console.print(f"[green]Using board by name[/green]: '{BOARD_NAME}' (id={resolved_board_id})")
    else:
        console.print(f"[yellow]Board name '{BOARD_NAME}' not found; using '{resolved_board_id}' (uncategorized).[/yellow]")
else:
    console.print(f"[cyan]Using uncategorized board id[/cyan]: {resolved_board_id}")

# Upload to resolved board
board_handle: BoardHandle = client.board_repo.get_board_handle(resolved_board_id)
uploaded_image: IvkImage = board_handle.upload_image_data(image_data=chosen_image_bytes, filename=chosen_image_path.name)

# 2. Load workflow definition & create handle
workflow_definition: WorkflowDefinition = WorkflowDefinition.from_file(str(WORKFLOW_PATH))
workflow_handle = client.workflow_repo.create_workflow(workflow_definition)

############################
# INPUT DISCOVERY & MAPPING
############################

# Default models in workflow json may not exists in remote, so we need to:
# Sync any model identifier fields so they reference models the server knows:
#   by_name=True  -> try exact model name match first (precise)
#   by_base=True  -> fallback: match by base/architecture if name fails
# Returns list[(orig,resolved)] for changed fields (empty if already valid).
synced_models = workflow_handle.sync_dnn_model(by_name=True, by_base=True)

if True:    # for easy switch off
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

# Retrieve all workflow inputs. Ordering is the GUI form's pre-order (depth-first)
# traversal of its container tree: stable unless the form structure changes. If
# the form has no nested containers, this reduces to simple top-to-bottom order.
# Each position returns a concrete typed Ivk* field (e.g., IvkStringField,
# IvkIntegerField, IvkModelIdentifierField) even though access uses a generic
# getter. Indices below (IDX_*) rely on this deterministic ordering.
inputs = workflow_handle.list_inputs()

if True:    # for easy switch off
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

# Warn early if workflow exposes no output nodes (board fields on output-capable nodes)
exposed_outputs = workflow_handle.list_outputs()
if not exposed_outputs:
    console.print("[bold yellow]Warning:[/bold yellow] This workflow exposes no output board fields in the form.\n"
                  "Output mapping will return an empty list. Ensure the decode/save node's board field is form-exposed if you want automatic mapping.")

# Depth-first indices (stable unless form structure changes). We still expose
# constants for currently-exported workflow revision but dynamically locate the
# board field to avoid silent drift if ordering changes.
IDX_MODEL = 0
IDX_IMAGE = 1
IDX_T5 = 2
IDX_CLIP = 3
IDX_VAE = 4
IDX_POS_PROMPT = 5
IDX_NEG_PROMPT = 6
IDX_STEPS = 7
IDX_DENOISE_START = 8
IDX_OUTPUT_BOARD = 9  # Prior knowledge: board field consistently exported at index 9 for this workflow version

positive_prompt: str = POSITIVE_PROMPT
negative_prompt: str = NEGATIVE_PROMPT_DEFAULT
uploaded_name: str = uploaded_image.image_name

# -------------------------------------------------------------
# Explicitly retrieve & type each workflow input field by index
# -------------------------------------------------------------

# Model field
field_model: IvkModelIdentifierField = workflow_handle.get_input_value(IDX_MODEL)  # type: ignore[assignment]
assert isinstance(field_model, IvkModelIdentifierField), f"IDX_MODEL expected IvkModelIdentifierField, got {type(field_model)}"

# Image field
field_image: IvkImageField = workflow_handle.get_input_value(IDX_IMAGE)  # type: ignore[assignment]
assert isinstance(field_image, IvkImageField), f"IDX_IMAGE expected IvkImageField, got {type(field_image)}"
field_image.value = uploaded_name  # Set immediately after retrieval

# T5 encoder field
field_t5: IvkModelIdentifierField = workflow_handle.get_input_value(IDX_T5)  # type: ignore[assignment]
assert isinstance(field_t5, IvkModelIdentifierField), f"IDX_T5 expected IvkModelIdentifierField, got {type(field_t5)}"

# CLIP field
field_clip: IvkModelIdentifierField = workflow_handle.get_input_value(IDX_CLIP)  # type: ignore[assignment]
assert isinstance(field_clip, IvkModelIdentifierField), f"IDX_CLIP expected IvkModelIdentifierField, got {type(field_clip)}"

# VAE field
field_vae: IvkModelIdentifierField = workflow_handle.get_input_value(IDX_VAE)  # type: ignore[assignment]
assert isinstance(field_vae, IvkModelIdentifierField), f"IDX_VAE expected IvkModelIdentifierField, got {type(field_vae)}"

# Positive prompt field
field_pos_prompt: IvkStringField = workflow_handle.get_input_value(IDX_POS_PROMPT)  # type: ignore[assignment]
assert isinstance(field_pos_prompt, IvkStringField), f"IDX_POS_PROMPT expected IvkStringField, got {type(field_pos_prompt)}"
field_pos_prompt.value = positive_prompt  # Set immediately

# Negative prompt field
field_neg_prompt: IvkStringField = workflow_handle.get_input_value(IDX_NEG_PROMPT)  # type: ignore[assignment]
assert isinstance(field_neg_prompt, IvkStringField), f"IDX_NEG_PROMPT expected IvkStringField, got {type(field_neg_prompt)}"
field_neg_prompt.value = negative_prompt  # Set immediately

# Steps field
field_steps: IvkIntegerField = workflow_handle.get_input_value(IDX_STEPS)  # type: ignore[assignment]
assert isinstance(field_steps, IvkIntegerField), f"IDX_STEPS expected IvkIntegerField, got {type(field_steps)}"
field_steps.value = STEPS  # type: ignore[assignment]  # Set immediately

# Denoise start field
field_denoise_start: IvkFloatField = workflow_handle.get_input_value(IDX_DENOISE_START)  # type: ignore[assignment]
assert isinstance(field_denoise_start, IvkFloatField), f"IDX_DENOISE_START expected IvkFloatField, got {type(field_denoise_start)}"
field_denoise_start.value = 1 - NOISE_RATIO  # type: ignore[assignment]  # Set immediately

field_output_board: Union[IvkStringField, IvkBoardField] = workflow_handle.get_input_value(IDX_OUTPUT_BOARD)  # type: ignore[assignment]
assert isinstance(field_output_board, (IvkStringField, IvkBoardField)), f"IDX_OUTPUT_BOARD unexpected type {type(field_output_board)}"
if hasattr(field_output_board, 'value'):
    field_output_board.value = resolved_board_id  # type: ignore[assignment]

def log_field_set(idx: int, field_obj: object) -> None:
    """Log the effective value of a workflow input previously set.

    This intentionally does no mutation; it demonstrates that the runtime
    type of each index is specific, even though retrieval uses a common API.
    """
    meta = workflow_handle.get_input(idx)
    val = getattr(field_obj, 'value', None)
    console.print(
        f"[bold blue]Configured[/bold blue] input[{idx}] "
        f"[italic]{(meta.label or meta.field_name)!r}[/italic] -> {val!r} (type={type(field_obj).__name__})"
    )

# Log configured inputs of interest
log_field_set(IDX_IMAGE, field_image)
log_field_set(IDX_POS_PROMPT, field_pos_prompt)
log_field_set(IDX_NEG_PROMPT, field_neg_prompt)
log_field_set(IDX_STEPS, field_steps)
log_field_set(IDX_DENOISE_START, field_denoise_start)
log_field_set(IDX_OUTPUT_BOARD, field_output_board)

console.rule("Effective Configuration")
config_tbl = Table(show_header=False, box=box.MINIMAL_DOUBLE_HEAD)
config_tbl.add_row("POSITIVE_PROMPT", positive_prompt)
config_tbl.add_row("NEGATIVE_PROMPT", negative_prompt)
config_tbl.add_row("STEPS", str(STEPS))
config_tbl.add_row("DENOISING_START", f"{1 - NOISE_RATIO} (derived from NOISE_RATIO={NOISE_RATIO})")
config_tbl.add_row("BOARD_ID (input)", resolved_board_id)
console.print(config_tbl)

############################
# SUBMIT & MONITOR
############################
# Submit the prepared workflow graph to the server queue (sync). Returns submission
# metadata: batch_id, list of item_ids, enqueued count, and session_id used for
# later status tracking/event subscription.
submission_result: dict[str, Any] = workflow_handle.submit_sync()  # board chosen via input field

# Poll the queue until the single enqueued item reaches a terminal state.
# Always returns the queue item dict (status, timings, any error info). We separate
# mapping so callers can decide if/when to resolve image outputs.
try:
    queue_item: dict[str, Any] = workflow_handle.wait_for_completion_sync(
        poll_interval=POLL_INTERVAL_SEC,
        timeout=TIMEOUT_SEC,
        progress_callback=lambda qi: print("Status:", qi.get("status")),
    )
except RuntimeError as e:
    # Capture explicit cancellation (server/user initiated) and report cleanly.
    if "canceled" in str(e).lower():
        console.rule("Completion")
        console.print("[red]Workflow was canceled before completion.[/red]")
        queue_item = {"status": "canceled", "error": str(e)}  # sentinel for downstream logic
    else:
        raise
    
# Download the image output if the workflow completed successfully.
console.rule("Completion")
console.print(f"Final status: [bold]{queue_item.get('status')}[/bold]")
if queue_item.get("status") == "completed":
    # Derive form-exposed output image mappings (node -> image names) on demand.
    # This call performs a lightweight traversal of decode/save nodes rather than
    # embedding outputs automatically in wait_for_completion.* returns.
    mappings: list[OutputMapping] = workflow_handle.map_outputs_to_images(queue_item)
    console.print(f"Outputs (form-exposed): {len(mappings)}")
    for m in mappings:
        console.print(f"  Node {m['node_id'][:8]} -> {len(m['image_names'])} image(s) (tier={m['tier']})")

    # --- Optional: save images (separated concern) ---
    if SAVE_IMAGES and mappings:
        try:
            from io import BytesIO
        except Exception:
            console.print("[yellow]Pillow not installed; skipping image save.[/yellow]")
        else:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            console.print(f"Saving images to: {OUTPUT_DIR}")
            saved = 0
            for m in mappings:
                board_id = m.get('board_id') or 'none'
                bh: BoardHandle = client.board_repo.get_board_handle(board_id)
                image_names = m.get('image_names') or []
                # Current FLUX image-to-image workflow decode node emits at most one image
                # (image_output). We still treat it as a list for forward compatibility with
                # possible collection outputs that could yield multiple names.
                if not image_names:
                    continue
                name = image_names[0]
                try:
                    data: bytes = bh.download_image(name, full_resolution=True)
                    img = Image.open(BytesIO(data))  # type: ignore[assignment]
                    if final_image is None:
                        try:
                            final_image = img.copy()
                        except Exception:
                            final_image = img
                    dest: Path = OUTPUT_DIR / name
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
                console.print("[bold cyan]In-memory PIL Image available as variable 'final_image' (first generated image).[/bold cyan]")
else:
    console.print("[red]Workflow did not complete successfully.[/red]")
