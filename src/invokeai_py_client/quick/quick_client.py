"""
QuickClient - convenience wrapper around InvokeAIClient for common tasks.

Provides a simple API surface for high-level operations that are implemented
using the underlying repositories and workflow subsystem.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, cast

from invokeai_py_client.client import InvokeAIClient
from invokeai_py_client.models import IvkImage
from invokeai_py_client.workflow import WorkflowDefinition
from invokeai_py_client.ivk_fields import IvkImageField, IvkBoardField


class QuickClient:
    """
    A convenience wrapper for the core InvokeAIClient.

    Initialization
    --------------
    >>> client = InvokeAIClient.from_url("http://127.0.0.1:9090")
    >>> qc = QuickClient(client)

    Methods
    -------
    - copy_image_to_board(): Duplicate an existing server-side image into a target board
      using a tiny workflow (no client download/upload, pure server-side).
    """

    def __init__(self, client: InvokeAIClient) -> None:
        self.client = client

    def copy_image_to_board(self, image_name: str, target_board_id: str) -> Optional[IvkImage]:
        """
        Copy an existing image to another board using a tiny workflow (server-side duplication).

        This uses a prebuilt workflow that:
        - Takes an ImageField "image" referencing an existing image by name
        - Saves a new image with Save Image to the provided board

        Parameters
        ----------
        image_name : str
            The name of the existing image on the server to copy.
        target_board_id : str
            The destination board_id to store the new copied image.

        Returns
        -------
        IvkImage | None
            The copied image's metadata (ImageDTO) if successful; None if not found post-run.

        Raises
        ------
        ValueError
            - If target_board_id does not exist
            - If the source image does not exist
            - If API errors occur during submission/execution

        Notes
        -----
        - Purely server-side: no bytes are downloaded to the client or re-uploaded.
        - Implemented with the workflow subsystem in sync mode.
        """

        # 1) Validate target board exists
        board = self.client.board_repo.get_board_by_id(target_board_id)
        if board is None:
            raise ValueError(f"Target board does not exist: {target_board_id}")

        # 2) Validate source image exists
        src_img = self.client.board_repo.get_image_by_name(image_name)
        if src_img is None:
            raise ValueError(f"Source image does not exist on server: {image_name}")

        # 3) Load tiny workflow definition (packaged with the client)
        wf_path = Path(__file__).resolve().parent / "prebuilt-workflows" / "copy-image.json"
        if not wf_path.exists():
            raise ValueError(f"Prebuilt workflow missing: {wf_path}")
        wf_def = WorkflowDefinition.from_file(wf_path)

        # 4) Create workflow handle
        wf = self.client.workflow_repo.create_workflow(wf_def)

        # 5) Set inputs by field_name: "image" and "board"
        image_idx = None
        board_idx = None
        for inp in wf.list_inputs():
            if inp.field_name == "image":
                image_idx = inp.input_index
            elif inp.field_name == "board":
                board_idx = inp.input_index

        if image_idx is None:
            raise ValueError("Workflow input 'image' not found in tiny workflow.")
        if board_idx is None:
            raise ValueError("Workflow input 'board' not found in tiny workflow.")

        # Cast to concrete field types for type-safe value assignment
        image_field = cast(IvkImageField, wf.get_input_value(image_idx))
        if not hasattr(image_field, "value"):
            raise ValueError("Workflow 'image' field does not support .value assignment")
        image_field.value = image_name  # normalized to {'image_name': ...} on submit

        board_field = cast(IvkBoardField, wf.get_input_value(board_idx))
        if not hasattr(board_field, "value"):
            raise ValueError("Workflow 'board' field does not support .value assignment")
        board_field.value = target_board_id  # normalized to {'board_id': ...} on submit

        # 6) Submit synchronously and wait for completion
        try:
            wf.submit_sync()
            queue_item = wf.wait_for_completion_sync(timeout=120)
        except Exception as e:
            raise ValueError(f"Workflow execution failed: {e}") from e

        # 7) Map outputs to image names; the save_image node should appear as an output-capable node
        mappings = wf.map_outputs_to_images(queue_item)
        new_image_name: str | None = None
        # Prefer the mapping for the save_image node if present; otherwise first mapping with image names
        for m in mappings:
            node_type = (m.get("node_type") or "").lower()
            imgs = m.get("image_names") or []
            if node_type == "save_image" and imgs:
                new_image_name = imgs[0]
                break
        if new_image_name is None:
            for m in mappings:
                imgs = m.get("image_names") or []
                if imgs:
                    new_image_name = imgs[0]
                    break

        if not new_image_name:
            # No images found; return None as per contract
            return None

        # 8) Resolve and return the IvkImage metadata
        copied = self.client.board_repo.get_image_by_name(new_image_name)
        return copied