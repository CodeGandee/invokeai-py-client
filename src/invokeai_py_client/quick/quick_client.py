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
from invokeai_py_client.ivk_fields import (
    IvkImageField,
    IvkBoardField,
    IvkStringField,
    IvkIntegerField,
    IvkFloatField,
    IvkSchedulerField,
    SchedulerName,
)
from invokeai_py_client.ivk_fields.models import IvkModelIdentifierField


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
        - Intentional duplication: if the source image already belongs to the
            target board, this method still runs the tiny workflow and creates a
            NEW image (distinct image_name & metadata) on that same board. This
            is useful for creating variants or preserving the original while
            generating a copy without first checking board membership.
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

    def generate_image_sdxl_t2i(
        self,
        positive_prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int | None = None,
        model_name: str | None = None,
        scheduler: str | None = None,
        board_id: str | None = None,
    ) -> Optional[IvkImage]:
        """
        Create an SDXL text-to-image generation task using a prebuilt workflow, wait for completion,
        and return the resulting image metadata.

        Parameters
        ----------
        positive_prompt : str
            Positive prompt for generation.
        negative_prompt : str
            Negative prompt for generation.
        width : int
            Desired output width (rounded to nearest multiple of 8).
        height : int
            Desired output height (rounded to nearest multiple of 8).
        steps : int | None
            Denoising steps; if None, use workflow default.
        model_name : str | None
            Substring-matched model name; if None, first SDXL main model is used.
        scheduler : str | None
            Scheduler name (see SchedulerName); if None, workflow default is used.
        board_id : str | None
            Destination board id; if None, 'none' (uncategorized) is used.

        Returns
        -------
        IvkImage | None
            First generated image's metadata; None if canceled or no images produced.

        Raises
        ------
        ValueError
            On API/workflow errors (except cancellation, which returns None).
        """
        # Helpers
        def _round8(n: int) -> int:
            try:
                return max(8, int(round(int(n) / 8) * 8))
            except Exception:
                return 8

        width8 = _round8(width)
        height8 = _round8(height)

        # Resolve board id (validate if provided)
        resolved_board_id = "none" if board_id is None else board_id
        if resolved_board_id != "none":
            if self.client.board_repo.get_board_by_id(resolved_board_id) is None:
                raise ValueError(f"Target board does not exist: {resolved_board_id}")

        # Load workflow definition
        wf_path = Path(__file__).resolve().parent / "prebuilt-workflows" / "sdxl-text-to-image.json"
        if not wf_path.exists():
            raise ValueError(f"Prebuilt workflow missing: {wf_path}")
        wf_def = WorkflowDefinition.from_file(wf_path)

        # Create workflow
        wf = self.client.workflow_repo.create_workflow(wf_def)

        # Discover inputs
        idx_model: int | None = None
        idx_pos: int | None = None
        idx_neg: int | None = None
        idx_w: int | None = None
        idx_h: int | None = None
        idx_steps: int | None = None
        idx_sched: int | None = None
        idx_board: int | None = None

        for inp in wf.list_inputs():
            fn = getattr(inp, "field_name", "")
            lbl = (getattr(inp, "label", None) or "").lower()
            if fn == "model":
                idx_model = inp.input_index
            elif fn == "width":
                idx_w = inp.input_index
            elif fn == "height":
                idx_h = inp.input_index
            elif fn == "steps":
                idx_steps = inp.input_index
            elif fn == "scheduler":
                idx_sched = inp.input_index
            elif fn == "board":
                idx_board = inp.input_index
            elif fn == "value":
                if "positive" in lbl:
                    idx_pos = inp.input_index
                elif "negative" in lbl:
                    idx_neg = inp.input_index

        # Positive / Negative prompt
        if idx_pos is not None:
            fld_pos = wf.get_input_value(idx_pos)
            if hasattr(fld_pos, "value"):
                cast(IvkStringField, fld_pos).value = positive_prompt
        if idx_neg is not None:
            fld_neg = wf.get_input_value(idx_neg)
            if hasattr(fld_neg, "value"):
                cast(IvkStringField, fld_neg).value = negative_prompt

        # Dimensions
        if idx_w is not None:
            fld_w = wf.get_input_value(idx_w)
            if hasattr(fld_w, "value"):
                cast(IvkIntegerField, fld_w).value = width8  # type: ignore[assignment]
        if idx_h is not None:
            fld_h = wf.get_input_value(idx_h)
            if hasattr(fld_h, "value"):
                cast(IvkIntegerField, fld_h).value = height8  # type: ignore[assignment]

        # Steps (optional)
        if steps is not None and idx_steps is not None:
            fld_steps = wf.get_input_value(idx_steps)
            if hasattr(fld_steps, "value"):
                cast(IvkIntegerField, fld_steps).value = int(steps)  # type: ignore[assignment]

        # Scheduler (optional)
        if scheduler and idx_sched is not None:
            fld_sched = wf.get_input_value(idx_sched)
            if hasattr(fld_sched, "value"):
                try:
                    canonical = IvkSchedulerField.normalize_alias(str(scheduler))
                    # Validate against enum if possible; fall back to provided
                    if canonical.lower() in [s.lower() for s in IvkSchedulerField().get_choices()]:
                        cast(IvkSchedulerField, fld_sched).value = canonical  # type: ignore[assignment]
                    else:
                        cast(IvkSchedulerField, fld_sched).value = str(scheduler)  # type: ignore[assignment]
                except Exception:
                    cast(IvkSchedulerField, fld_sched).value = str(scheduler)  # type: ignore[assignment]

        # Board id
        if idx_board is not None:
            fld_board = wf.get_input_value(idx_board)
            if hasattr(fld_board, "value"):
                cast(IvkBoardField, fld_board).value = resolved_board_id

        # Model selection
        def _choice_text(v: object) -> str:
            return getattr(v, "value", str(v)).lower()

        chosen_main = None
        try:
            all_models = self.client.dnn_model_repo.list_models()
        except Exception as e:
            raise ValueError(f"Failed to list models: {e}") from e

        mains = []
        for m in all_models:
            try:
                t = _choice_text(getattr(m, "type", None))
                b = _choice_text(getattr(m, "base", None))
                if "main" in t and "sdxl" in b:
                    mains.append(m)
            except Exception:
                continue

        if model_name:
            name_l = model_name.lower()
            chosen_main = next((m for m in mains if name_l in getattr(m, "name", "").lower()), None)
        if not chosen_main and mains:
            chosen_main = mains[0]

        if not chosen_main:
            raise ValueError("No SDXL 'main' model available on server")

        if idx_model is not None:
            fld_model = wf.get_input_value(idx_model)
            if isinstance(fld_model, IvkModelIdentifierField) or hasattr(fld_model, "key"):
                try:
                    # Populate identifier fields from selected model
                    if hasattr(fld_model, "key"):
                        setattr(fld_model, "key", getattr(chosen_main, "key", None))
                    if hasattr(fld_model, "hash"):
                        setattr(fld_model, "hash", getattr(chosen_main, "hash", None))
                    if hasattr(fld_model, "name"):
                        setattr(fld_model, "name", getattr(chosen_main, "name", None))
                    if hasattr(fld_model, "base"):
                        setattr(fld_model, "base", "sdxl")
                    if hasattr(fld_model, "type"):
                        setattr(fld_model, "type", "main")
                except Exception:
                    # Fall back to name-only; sync should resolve
                    if hasattr(fld_model, "name"):
                        try:
                            setattr(fld_model, "name", getattr(chosen_main, "name", None))
                        except Exception:
                            pass

        # Try syncing model field to server-known identifiers (best-effort)
        try:
            wf.sync_dnn_model(by_name=True, by_base=True)
        except Exception:
            pass

        # Submit and wait
        try:
            wf.submit_sync()
            queue_item = wf.wait_for_completion_sync(timeout=240)
        except RuntimeError as e:
            if "canceled" in str(e).lower():
                return None
            raise ValueError(f"Workflow execution failed: {e}") from e
        except Exception as e:
            raise ValueError(f"Workflow execution failed: {e}") from e

        # Map outputs to image names; prefer l2i/canvas_output-like nodes
        mappings = wf.map_outputs_to_images(queue_item)
        new_image_name: str | None = None
        for m in mappings:
            node_type = (m.get("node_type") or "").lower()
            imgs = m.get("image_names") or []
            if imgs and (node_type in {"l2i", "canvas_output", "save_image"}):
                new_image_name = imgs[0]
                break
        if new_image_name is None:
            for m in mappings:
                imgs = m.get("image_names") or []
                if imgs:
                    new_image_name = imgs[0]
                    break

        if not new_image_name:
            return None

        return self.client.board_repo.get_image_by_name(new_image_name)