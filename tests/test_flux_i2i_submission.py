#!/usr/bin/env python
"""End-to-end test for FLUX image-to-image workflow submission.

This test covers:
1. Creating a test board
2. Generating and uploading a test image
3. Configuring workflow inputs with the uploaded image
4. Submitting the workflow
5. Monitoring execution until completion
6. Cleaning up test resources
"""

from __future__ import annotations

import os
import sys
import json
import time
import traceback
import requests
from pathlib import Path
from typing import Optional, Any, Dict, List, Callable
from datetime import datetime
from io import BytesIO

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient  # noqa: E402
from invokeai_py_client.workflow import WorkflowRepository  # noqa: E402
from invokeai_py_client.board import BoardRepository, BoardHandle  # noqa: E402
from invokeai_py_client.dnn_model import (  # noqa: E402
    DnnModelRepository,
    DnnModel,
    DnnModelType,
    BaseDnnModelType,
)
from invokeai_py_client.ivk_fields.model_conversion import to_ivk_model_field  # noqa: E402
from invokeai_py_client.models import IvkImage  # noqa: E402

# Try to import PIL for image generation
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[WARN] PIL not available. Will try to use existing test image.")


# Configuration
BOARD_PREFIX = "test_flux_i2i_"
IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 1024
TEST_PROMPT = (
    "A surreal digital art painting, vibrant colors, dreamlike atmosphere, "
    "abstract elements blending with realistic details, masterpiece quality, "
    "8k resolution, trending on artstation"
)


def generate_test_image(width: int = IMAGE_WIDTH, height: int = IMAGE_HEIGHT) -> bytes:
    """Generate a test image programmatically.
    
    Parameters
    ----------
    width : int
        Image width in pixels
    height : int
        Image height in pixels
    
    Returns
    -------
    bytes
        PNG image data as bytes
    """
    if not HAS_PIL:
        raise RuntimeError("PIL is required to generate test images")
    
    # Create a gradient image with some geometric patterns
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    
    # Create gradient background
    for y in range(height):
        # Gradient from blue to purple
        r = int(100 + (155 * y / height))
        g = int(50 + (50 * y / height))
        b = int(200 - (100 * y / height))
        draw.rectangle([0, y, width, y+1], fill=(r, g, b))
    
    # Add some geometric patterns
    for i in range(5):
        x = int(width * (i + 1) / 6)
        y = int(height / 2)
        radius = 50 + i * 20
        # Draw circles with varying opacity
        for r in range(radius, 0, -5):
            alpha = int(255 * (1 - r / radius))
            color = (255, 200 - i * 30, 100 + i * 20)
            draw.ellipse([x-r, y-r, x+r, y+r], outline=color, width=2)
    
    # Add text overlay
    text = "FLUX I2I TEST"
    try:
        # Try to use default font
        font = ImageFont.load_default()
    except:
        font = None
    
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (width - text_width) // 2
    text_y = height - 100
    
    # Draw text with shadow
    draw.text((text_x + 2, text_y + 2), text, fill="black", font=font)
    draw.text((text_x, text_y), text, fill="white", font=font)
    
    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def create_test_board(client: InvokeAIClient, board_name: str) -> BoardHandle:
    """Create a test board for the workflow.
    
    Parameters
    ----------
    client : InvokeAIClient
        The client instance
    board_name : str
        Name for the test board
    
    Returns
    -------
    BoardHandle
        Handle to the created board
    """
    print(f"\n[BOARD CREATION]")
    board_repo = client.board_repo
    
    # Check if board already exists
    existing_boards = board_repo.list_boards()
    for board in existing_boards:
        if board.board_name == board_name:
            print(f"[OK] Using existing board: {board_name}")
            return board_repo.get_board_handle(board.board_id)
    
    # Create new board
    try:
        board_handle = board_repo.create_board(board_name)
        print(f"[OK] Created board: {board_name} (id={board_handle.board.board_id})")
        return board_handle
    except Exception as e:
        # If board creation fails, use uncategorized board as fallback
        print(f"[WARN] Failed to create board: {e}")
        print("[INFO] Using uncategorized board as fallback")
        # Get handle for uncategorized board
        return board_repo.get_board_handle("none")


def upload_test_image(
    client: InvokeAIClient, 
    board: BoardHandle,
    image_data: bytes
) -> IvkImage:
    """Upload test image to the board.
    
    Parameters
    ----------
    client : InvokeAIClient
        The client instance
    board : BoardHandle
        The board to upload to
    image_data : bytes
        The image data to upload
    
    Returns
    -------
    IvkImage
        The uploaded image object
    """
    print(f"\n[IMAGE UPLOAD]")
    print(f"[INFO] Uploading to board: {board.board_id}")
    print(f"[DEBUG] Upload URL: {client.base_url}/images/upload")
    
    try:
        # Upload image to board
        uploaded_image = board.upload_image_data(
            image_data=image_data,
            filename="test_flux_i2i_input.png"
        )
    except requests.HTTPError as e:
        # Try to provide more detail about the error
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"[ERROR] Upload failed: {e.response.status_code} - {error_detail}")
            except:
                print(f"[ERROR] Upload failed: {e.response.status_code} - {e.response.text[:500]}")
        raise
    
    print(f"[OK] Uploaded image: {uploaded_image.image_name}")
    print(f"     - Dimensions: {uploaded_image.width}x{uploaded_image.height}")
    print(f"     - Board: {uploaded_image.board_id}")
    
    return uploaded_image


def check_models(repo: DnnModelRepository) -> Dict[str, Optional[DnnModel]]:
    """Check available models for the workflow.
    
    Parameters
    ----------
    repo : DnnModelRepository
        The model repository
    
    Returns
    -------
    Dict[str, Optional[DnnModel]]
        Dictionary of model types to model instances
    """
    print("\n[MODEL CHECK]")
    all_models = repo.list_models()
    
    def find_model(pred: Callable[[DnnModel], bool]) -> Optional[DnnModel]:
        for m in all_models:
            if pred(m):
                return m
        return None
    
    models = {
        "flux_main": find_model(
            lambda m: m.type == DnnModelType.Main and m.base == BaseDnnModelType.Flux
        ),
        "t5_encoder": find_model(lambda m: m.type == DnnModelType.T5Encoder),
        "clip_embed": find_model(lambda m: m.type == DnnModelType.CLIPEmbed),
        "flux_vae": find_model(
            lambda m: m.type == DnnModelType.VAE and m.base == BaseDnnModelType.Flux
        ),
    }
    
    for key, model in models.items():
        status = "OK" if model else "MISSING"
        name = getattr(model, "name", "N/A")
        print(f"[{status}] {key}: {name}")
    
    # Check if all required models are available
    missing = [k for k, v in models.items() if v is None]
    if missing:
        print(f"[ERROR] Missing required models: {', '.join(missing)}")
    
    return models


def configure_workflow_inputs(
    workflow: Any,  # WorkflowHandle type
    models: Dict[str, Optional[DnnModel]],
    prompt: str,
    uploaded_image: IvkImage,
    board_id: str
) -> None:
    """Configure all workflow inputs.
    
    Parameters
    ----------
    workflow : WorkflowHandle
        The workflow handle
    models : Dict[str, Optional[DnnModel]]
        Available models
    prompt : str
        The text prompt
    uploaded_image : IvkImage
        The uploaded input image
    board_id : str
        The board ID for outputs
    """
    print("\n[CONFIGURE INPUTS]")
    
    # Build input lookup for easy access
    input_lookup: Dict[tuple[str, str], int] = {}
    for inp in workflow.list_inputs():
        input_lookup[(inp.node_id, inp.field_name)] = inp.input_index
    
    # Set the prompt
    prompt_key = ("01f674f8-b3d1-4df1-acac-6cb8e0bfb63c", "prompt")
    if prompt_key in input_lookup:
        field = workflow.get_input_value(input_lookup[prompt_key])
        if hasattr(field, "value"):
            field.value = prompt
            print(f"[OK] Set prompt: {prompt[:50]}...")
    
    # Set the input image
    # The form shows the image field is on the image node
    image_key = ("7b056f05-a4fe-40d3-b913-1a4b3897230f", "image")
    if image_key in input_lookup:
        field = workflow.get_input_value(input_lookup[image_key])
        if hasattr(field, "value"):
            # Set the image name as the value
            field.value = uploaded_image.image_name
            print(f"[OK] Set input image: {uploaded_image.image_name}")
    else:
        print(f"[WARN] Image input field not found in workflow inputs")
    
    # Set models
    model_node = "f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90"
    
    # FLUX main model
    flux_model = models.get("flux_main")
    if flux_model:
        model_key = (model_node, "model")
        if model_key in input_lookup:
            try:
                field = to_ivk_model_field(flux_model)
                workflow.set_input_value(input_lookup[model_key], field)
                print(f"[OK] Set FLUX model: {flux_model.name}")
            except Exception as e:
                print(f"[WARN] Failed to set FLUX model: {e}")
    
    # T5 encoder
    t5_model = models.get("t5_encoder")
    if t5_model:
        t5_key = (model_node, "t5_encoder_model")
        if t5_key in input_lookup:
            try:
                field = to_ivk_model_field(t5_model)
                workflow.set_input_value(input_lookup[t5_key], field)
                print(f"[OK] Set T5 encoder: {t5_model.name}")
            except Exception as e:
                print(f"[WARN] Failed to set T5 encoder: {e}")
    
    # CLIP embed
    clip_model = models.get("clip_embed")
    if clip_model:
        clip_key = (model_node, "clip_embed_model")
        if clip_key in input_lookup:
            try:
                field = to_ivk_model_field(clip_model)
                workflow.set_input_value(input_lookup[clip_key], field)
                print(f"[OK] Set CLIP embed: {clip_model.name}")
            except Exception as e:
                print(f"[WARN] Failed to set CLIP embed: {e}")
    
    # VAE model
    vae_model = models.get("flux_vae")
    if vae_model:
        vae_key = (model_node, "vae_model")
        if vae_key in input_lookup:
            try:
                field = to_ivk_model_field(vae_model)
                workflow.set_input_value(input_lookup[vae_key], field)
                print(f"[OK] Set VAE model: {vae_model.name}")
            except Exception as e:
                print(f"[WARN] Failed to set VAE model: {e}")
    
    # Set additional parameters if they exist in the form
    # Number of steps
    steps_key = ("9c773392-5647-4f2b-958e-9da1707b6e6a", "num_steps")
    if steps_key in input_lookup:
        field = workflow.get_input_value(input_lookup[steps_key])
        if hasattr(field, "value"):
            field.value = 12  # Reduced for faster testing
            print(f"[OK] Set num_steps: 12")
    
    # Denoising strength (important for i2i)
    denoise_key = ("9c773392-5647-4f2b-958e-9da1707b6e6a", "denoising_strength")
    if denoise_key in input_lookup:
        field = workflow.get_input_value(input_lookup[denoise_key])
        if hasattr(field, "value"):
            field.value = 0.7  # Moderate denoising for i2i
            print(f"[OK] Set denoising_strength: 0.7")
    
    # Board for output
    save_node = "7e5172eb-48c1-44db-a770-8fd83e1435d1"
    board_key = (save_node, "board")
    if board_key in input_lookup:
        field = workflow.get_input_value(input_lookup[board_key])
        if hasattr(field, "value"):
            field.value = board_id
            print(f"[OK] Set output board: {board_id}")


def submit_and_monitor(
    client: InvokeAIClient,
    workflow: Any,  # WorkflowHandle type
    board_id: str
) -> bool:
    """Submit workflow and monitor execution.
    
    Parameters
    ----------
    client : InvokeAIClient
        The client instance
    workflow : WorkflowHandle
        The workflow to submit
    board_id : str
        The board ID for outputs
    
    Returns
    -------
    bool
        True if workflow completed successfully
    """
    print("\n[SUBMIT]")
    
    # Validate inputs
    errors = workflow.validate_inputs()
    if errors:
        print("[ERROR] Input validation failed:")
        for idx, errs in errors.items():
            print(f"  - [{idx}] {', '.join(errs)}")
        return False
    
    try:
        # Submit the workflow
        result = workflow.submit_sync(board_id=board_id)
    except Exception as e:
        print(f"[ERROR] Submission failed: {e}")
        traceback.print_exc()
        return False
    
    batch_id = result.get("batch_id")
    item_ids = result.get("item_ids", [])
    item_id = item_ids[0] if item_ids else None
    session_id = result.get("session_id")
    
    print(f"[OK] Submitted batch={batch_id} item={item_id} session={session_id}")
    
    if not item_id:
        print("[ERROR] No item ID returned")
        return False
    
    # Monitor execution
    item_url = f"{client.base_url}/queue/default/i/{item_id}"
    start_time = time.time()
    last_status = None
    timeout = int(os.environ.get("WF_TIMEOUT", "180"))
    
    while time.time() - start_time < timeout:
        try:
            response = client.session.get(item_url)
            response.raise_for_status()
            queue_item = response.json()
            status = queue_item.get("status")
            
            if status != last_status:
                elapsed = int(time.time() - start_time)
                print(f"  [{elapsed:3d}s] status={status}")
                last_status = status
            
            if status in {"completed", "failed", "canceled"}:
                print(f"[DONE] Final status={status}")
                if status == "completed":
                    outputs = queue_item.get("outputs") or []
                    print(f"[OK] Workflow completed with {len(outputs)} outputs")
                    return True
                else:
                    error = queue_item.get("error") or {}
                    if error:
                        print(f"[ERROR] {error}")
                    # Also check for error_type and error_message
                    error_type = queue_item.get("error_type")
                    error_message = queue_item.get("error_message")
                    if error_type or error_message:
                        print(f"[ERROR] Type: {error_type}, Message: {error_message}")
                    return False
                    
        except Exception as e:
            print(f"  [WARN] Poll error: {e}")
        
        time.sleep(3)
    
    print(f"[ERROR] Timeout after {timeout}s")
    return False


def cleanup_board(client: InvokeAIClient, board_id: str) -> None:
    """Clean up test board and its contents.
    
    Parameters
    ----------
    client : InvokeAIClient
        The client instance
    board_id : str
        The board ID to clean up
    """
    print("\n[CLEANUP]")
    # Don't try to delete uncategorized board
    if board_id == "none":
        print("[INFO] Skipping cleanup for uncategorized board")
        return
    
    try:
        # Delete the board (will also delete contained images)
        client.board_repo.delete_board(board_id, delete_images=True)
        print(f"[OK] Deleted test board: {board_id}")
    except Exception as e:
        print(f"[WARN] Failed to delete board: {e}")


def main() -> int:
    """Main test function.
    
    Returns
    -------
    int
        Exit code (0 for success, 1 for failure)
    """
    print("\n" + "=" * 70)
    print(" FLUX IMAGE-TO-IMAGE WORKFLOW TEST")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize client
    base_url = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090")
    try:
        client = InvokeAIClient(base_url=base_url)
        print(f"[OK] Client ready @ {base_url}")
    except Exception as e:
        print(f"[ERROR] Cannot initialize client: {e}")
        return 1
    
    # Check available models
    models = check_models(client.dnn_model_repo)
    if not all([models.get("flux_main"), models.get("t5_encoder"), 
                models.get("clip_embed"), models.get("flux_vae")]):
        print("[ERROR] Required models not available")
        return 1
    
    # Create test board
    board_name = f"{BOARD_PREFIX}{int(time.time())}"
    try:
        board = create_test_board(client, board_name)
    except Exception as e:
        print(f"[ERROR] Failed to create board: {e}")
        return 1
    
    # Get board ID from handle
    board_id = board.board.board_id if hasattr(board, 'board') else getattr(board, 'board_id', 'none')
    
    # Generate and upload test image
    try:
        print("\n[IMAGE GENERATION]")
        image_data = generate_test_image()
        print(f"[OK] Generated test image ({len(image_data)} bytes)")
        
        uploaded_image = upload_test_image(client, board, image_data)
    except Exception as e:
        print(f"[ERROR] Failed to prepare test image: {e}")
        cleanup_board(client, board_id)
        return 1
    
    # Load workflow
    workflow_path = Path(__file__).parent.parent / "data" / "workflows" / "flux-image-to-image.json"
    if not workflow_path.exists():
        print(f"[ERROR] Workflow file not found: {workflow_path}")
        cleanup_board(client, board_id)
        return 1
    
    workflow_repo = WorkflowRepository(client)
    try:
        workflow = workflow_repo.create_workflow_from_file(str(workflow_path))
        print(f"\n[OK] Loaded workflow '{workflow.definition.name}' with {len(workflow.inputs)} inputs")
    except Exception as e:
        print(f"[ERROR] Failed to load workflow: {e}")
        cleanup_board(client, board_id)
        return 1
    
    # Debug: List all inputs
    print("\n[DEBUG] Available workflow inputs:")
    for inp in workflow.list_inputs():
        print(f"  [{inp.input_index}] {inp.node_id}.{inp.field_name} - {inp.label}")
    
    # Configure workflow inputs
    configure_workflow_inputs(
        workflow,
        models,
        TEST_PROMPT,
        uploaded_image,
        board_id
    )
    
    # Debug: Check image field value
    print("\n[DEBUG] Checking image field values:")
    for inp in workflow.list_inputs():
        if inp.field_name == "image":
            field = workflow.get_input_value(inp.input_index)
            if hasattr(field, "value"):
                print(f"  Input {inp.input_index} ({inp.node_id}): value = {field.value}")
            else:
                print(f"  Input {inp.input_index} ({inp.node_id}): no value attribute")
    
    # Debug: Save the API graph
    import json
    api_graph = workflow._convert_to_api_format(board_id)
    with open("tmp/flux_i2i_api_graph.json", "w") as f:
        json.dump(api_graph, f, indent=2)
    print("\n[DEBUG] Saved API graph to tmp/flux_i2i_api_graph.json")
    
    # Submit and monitor
    success = submit_and_monitor(client, workflow, board_id)
    
    # Clean up (optional - can be disabled for debugging)
    if os.environ.get("KEEP_TEST_BOARD") != "1":
        cleanup_board(client, board_id)
    else:
        print(f"\n[INFO] Test board kept: {board_id}")
    
    # Summary
    print("\n" + "=" * 70)
    print(" RESULT SUMMARY")
    print("=" * 70)
    if success:
        print("[PASS] FLUX image-to-image workflow completed successfully")
        return 0
    else:
        print("[FAIL] FLUX image-to-image workflow failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())