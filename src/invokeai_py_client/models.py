"""
Data models for InvokeAI API responses and entities.

This module provides Pydantic models for type-safe handling of
InvokeAI API data structures.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """
    InvokeAI job execution states.

    Represents the lifecycle states of a workflow execution job in InvokeAI.
    Jobs transition through these states as they are processed by the queue system.
    """

    PENDING = "pending"  # Job is queued, waiting for execution
    RUNNING = "running"  # Job is actively being processed
    COMPLETED = "completed"  # Job finished successfully with results
    FAILED = "failed"  # Job encountered an error during execution
    CANCELLED = "cancelled"  # Job was cancelled by user or system


class ImageCategory(str, Enum):
    """
    InvokeAI image categorization system.

    Defines the purpose and processing pipeline for images in InvokeAI.
    Each category has specific meaning and affects how the image is used
    in the generation workflow.

    Examples
    --------
    >>> # User uploads a reference photo
    >>> category = ImageCategory.USER

    >>> # ControlNet depth map for guidance
    >>> category = ImageCategory.CONTROL

    >>> # Inpainting mask to define edit regions
    >>> category = ImageCategory.MASK
    """

    USER = "user"
    """User-uploaded images: Personal photos, references, source images.
    These are typically input images provided by users for img2img,
    reference, or as base images for editing."""

    GENERAL = "general"
    """General purpose/AI-generated images: Output from generation models.
    Note: The API uses 'general' not 'generated'. These are typically
    the final output images from txt2img or img2img workflows."""

    CONTROL = "control"
    """ControlNet conditioning images: Depth maps, edge detection, pose, etc.
    Used to guide the generation process with structural information.
    Examples: Canny edges, OpenPose skeletons, depth maps, normal maps."""

    MASK = "mask"
    """Inpainting/outpainting masks: Binary masks defining edit regions.
    Black and white images where white areas indicate regions to regenerate.
    Used in inpainting and outpainting workflows."""

    OTHER = "other"
    """Special purpose images: Any image that doesn't fit standard categories.
    Includes intermediate processing images, custom workflow artifacts, etc."""


class BaseModelEnum(str, Enum):
    """
    InvokeAI base model architectures.

    Identifies the underlying AI model architecture for generation.
    Each architecture has different capabilities, requirements, and output characteristics.

    Model selection affects:
    - Resolution capabilities
    - Memory requirements
    - Generation quality and style
    - Compatible LoRAs and embeddings
    - Processing speed
    """

    SD1 = "sd-1"
    """Stable Diffusion 1.x: Original 512x512 models (SD 1.4, 1.5).
    Fastest, lowest memory requirements, huge ecosystem of fine-tunes."""

    SD2 = "sd-2"
    """Stable Diffusion 2.x: Improved 512x512/768x768 models.
    Better coherence than SD1, different aesthetic, less community support."""

    SDXL = "sdxl"
    """Stable Diffusion XL: High-res 1024x1024 base models.
    Superior quality and detail, higher memory requirements, two-stage pipeline."""

    SDXL_REFINER = "sdxl-refiner"
    """SDXL Refiner: Second stage for SDXL pipeline.
    Enhances details and quality of SDXL base outputs, typically last 20% of steps."""

    FLUX = "flux"
    """FLUX: Next-generation architecture from Black Forest Labs.
    State-of-the-art quality, very high memory requirements (24GB+ VRAM)."""

    FLUX_SCHNELL = "flux-schnell"
    """FLUX Schnell: Fast distilled version of FLUX.
    Optimized for speed (4-8 steps), lower quality than full FLUX but much faster."""


class IvkImage(BaseModel):
    """
    InvokeAI image entity.

    Represents an image stored in the InvokeAI system with its metadata.
    Images can be user uploads, AI generations, or processing artifacts.
    This matches the ImageDTO structure from the InvokeAI API.

    Examples
    --------
    >>> image = IvkImage(image_name="abc-123.png", width=1024, height=768)
    >>> print(f"Image: {image.image_name} ({image.width}x{image.height})")
    """

    image_name: str = Field(..., description="Server-side image identifier")
    board_id: str | None = Field(
        None, description="Associated board ID (None for uncategorized)"
    )
    image_category: ImageCategory = Field(
        ImageCategory.GENERAL, description="Image category type"
    )
    width: int | None = Field(None, gt=0, description="Image width in pixels")
    height: int | None = Field(None, gt=0, description="Image height in pixels")
    created_at: datetime | str | None = Field(
        None, description="Creation timestamp"
    )
    updated_at: datetime | str | None = Field(
        None, description="Last modification timestamp"
    )
    starred: bool = Field(False, description="Whether the image is starred")
    metadata: dict[str, Any] | None = Field(None, description="Generation metadata")
    thumbnail_url: str | None = Field(None, description="URL for thumbnail version")
    image_url: str | None = Field(None, description="URL for full resolution image")
    is_intermediate: bool = Field(
        False, description="Whether this is an intermediate image"
    )
    workflow_id: str | None = Field(None, description="Associated workflow ID")
    node_id: str | None = Field(None, description="Associated node ID")
    session_id: str | None = Field(None, description="Associated session ID")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> IvkImage:
        """
        Create an IvkImage from API response data.

        Handles field mapping from API response to model fields.

        Parameters
        ----------
        data : Dict[str, Any]
            Raw API response dictionary.

        Returns
        -------
        IvkImage
            Parsed image instance.
        """
        # Map image_category string to enum if needed
        if "image_category" in data and isinstance(data["image_category"], str):
            try:
                data["image_category"] = ImageCategory(data["image_category"])
            except ValueError:
                # If unknown category, default to OTHER
                data["image_category"] = ImageCategory.OTHER

        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns
        -------
        Dict[str, Any]
            Image data as dictionary.
        """
        return self.model_dump(exclude_none=True)


class IvkJob(BaseModel):
    """
    InvokeAI workflow execution job.

    Represents a queued or executing workflow in the InvokeAI queue system.
    Jobs are created when workflows are submitted and track the execution
    progress, results, and any errors.

    Examples
    --------
    >>> job = IvkJob(id="job-123", status=JobStatus.RUNNING, progress=0.5)
    >>> print(f"Job {job.id}: {job.status} ({job.progress*100:.0f}%)")
    """

    id: str = Field(..., description="Unique job identifier")
    workflow_id: str | None = Field(None, description="Associated workflow ID")
    status: JobStatus = Field(JobStatus.PENDING, description="Current job status")
    progress: float = Field(
        0.0, ge=0.0, le=1.0, description="Completion progress (0.0 to 1.0)"
    )
    created_at: datetime | None = Field(None, description="Job creation timestamp")
    started_at: datetime | None = Field(
        None, description="Execution start timestamp"
    )
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    error: str | None = Field(None, description="Error message if failed")
    outputs: dict[str, Any] = Field(default_factory=dict, description="Job output data")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional job metadata"
    )

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> IvkJob:
        """
        Create an IvkJob from API response data.

        Parameters
        ----------
        data : Dict[str, Any]
            Raw API response dictionary.

        Returns
        -------
        IvkJob
            Parsed job instance.
        """
        return cls(**data)

    def is_complete(self) -> bool:
        """
        Check if the job has finished execution.

        Returns
        -------
        bool
            True if completed, failed, or cancelled.
        """
        return self.status in [
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        ]

    def is_successful(self) -> bool:
        """
        Check if the job completed successfully.

        Returns
        -------
        bool
            True if status is COMPLETED.
        """
        return self.status == JobStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns
        -------
        Dict[str, Any]
            Job data as dictionary.
        """
        return self.model_dump(exclude_none=True)



class IvkDnnModel(BaseModel):
    """
    InvokeAI deep neural network model metadata.

    Represents a AI model installed in InvokeAI (base models, LoRAs, VAEs, etc.).
    Models are the core components that power image generation and processing.

    Examples
    --------
    >>> model = IvkDnnModel(
    ...     key="sdxl-base",
    ...     name="Stable Diffusion XL Base",
    ...     base=BaseModelEnum.SDXL,
    ...     type="main"
    ... )
    """

    key: str = Field(..., description="Unique model identifier")
    name: str = Field(..., description="Model display name")
    base: BaseModelEnum = Field(..., description="Base architecture type")
    type: str = Field(..., description="Model type (main, vae, lora, etc.)")
    hash: str | None = Field(None, description="Model file hash")
    path: str | None = Field(None, description="Model file path")
    description: str | None = Field(None, description="Model description")
    format: str | None = Field(
        None, description="Model format (diffusers, checkpoint, etc.)"
    )
    variant: str | None = Field(None, description="Model variant (fp16, fp32, etc.)")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional model metadata"
    )

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> IvkDnnModel:
        """
        Create an IvkDnnModel from API response data.

        Parameters
        ----------
        data : Dict[str, Any]
            Raw API response dictionary.

        Returns
        -------
        IvkDnnModel
            Parsed model instance.
        """
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns
        -------
        Dict[str, Any]
            Model data as dictionary.
        """
        return self.model_dump(exclude_none=True)


class SessionEvent(BaseModel):
    """
    InvokeAI real-time session event.

    WebSocket events emitted during workflow execution for progress tracking,
    intermediate results, and completion notifications.

    Examples
    --------
    >>> event = SessionEvent(
    ...     event_type="generation_progress",
    ...     data={"step": 10, "total": 30}
    ... )
    """

    event_type: str = Field(..., description="Event type identifier")
    session_id: str | None = Field(None, description="Associated session ID")
    timestamp: datetime | None = Field(None, description="Event timestamp")
    data: dict[str, Any] = Field(default_factory=dict, description="Event payload data")

    @classmethod
    def from_websocket_message(cls, message: dict[str, Any]) -> SessionEvent:
        """
        Create an event from a WebSocket message.

        Parameters
        ----------
        message : Dict[str, Any]
            Raw WebSocket message.

        Returns
        -------
        SessionEvent
            Parsed event instance.
        """
        return cls(**message)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns
        -------
        Dict[str, Any]
            Event data as dictionary.
        """
        return self.model_dump(exclude_none=True)
