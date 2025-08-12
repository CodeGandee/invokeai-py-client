"""
Utility classes and functions for InvokeAI client.

This module provides helper utilities for asset management,
data conversion, and common operations.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Callable, Dict, List, Optional, Type, Union

from invokeai_py_client.fields import Field
from invokeai_py_client.models import Board, IvkImage

if TYPE_CHECKING:
    from invokeai_py_client.client import InvokeAIClient


class AssetManager:
    """
    Manages upload and download of assets (images, masks, etc.).
    
    This class handles the transfer of heavy data between the client
    and the InvokeAI server, including automatic chunking, retries,
    and progress tracking.
    
    Parameters
    ----------
    client : InvokeAIClient
        Parent client instance.
    chunk_size : int, optional
        Size of chunks for streaming, by default 8192.
    max_retries : int, optional
        Maximum retry attempts, by default 3.
    
    Attributes
    ----------
    client : InvokeAIClient
        Reference to the parent client.
    chunk_size : int
        Chunk size for streaming operations.
    max_retries : int
        Maximum number of retry attempts.
    
    Examples
    --------
    >>> assets = AssetManager(client)
    >>> image = await assets.upload_image("input.png")
    >>> await assets.download_image(image.name, "output.png")
    """
    
    def __init__(
        self,
        client: InvokeAIClient,
        chunk_size: int = 8192,
        max_retries: int = 3
    ) -> None:
        """Initialize the asset manager."""
        raise NotImplementedError
    
    async def upload_image(
        self,
        source: Union[str, Path, BinaryIO],
        board_id: Optional[str] = None,
        category: str = "user",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> IvkImage:
        """
        Upload an image to the server.
        
        Parameters
        ----------
        source : Union[str, Path, BinaryIO]
            Image source (file path or file-like object).
        board_id : str, optional
            Target board for the image.
        category : str, optional
            Image category, by default "user".
        progress_callback : callable, optional
            Callback for upload progress (bytes_sent, total_bytes).
        
        Returns
        -------
        IvkImage
            Uploaded image object with server metadata.
        
        Raises
        ------
        FileNotFoundError
            If source file doesn't exist.
        FileError
            If upload fails.
        
        Examples
        --------
        >>> def on_progress(sent, total):
        raise NotImplementedError     print(f"Uploaded {sent}/{total} bytes")
        >>> image = await assets.upload_image(
        raise NotImplementedError     "input.png",
        raise NotImplementedError     progress_callback=on_progress
        raise NotImplementedError )
        """
        raise NotImplementedError
    
    async def download_image(
        self,
        image_name: str,
        destination: Union[str, Path, BinaryIO],
        full_resolution: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Path:
        """
        Download an image from the server.
        
        Parameters
        ----------
        image_name : str
            Server-side image identifier.
        destination : Union[str, Path, BinaryIO]
            Download destination.
        full_resolution : bool, optional
            Download full resolution, by default True.
        progress_callback : callable, optional
            Callback for download progress.
        
        Returns
        -------
        Path
            Path to the downloaded file.
        
        Raises
        ------
        ResourceNotFoundError
            If image doesn't exist.
        FileError
            If download fails.
        """
        raise NotImplementedError
    
    async def upload_batch(
        self,
        files: List[Union[str, Path]],
        board_id: Optional[str] = None,
        category: str = "user",
        parallel: int = 3
    ) -> List[IvkImage]:
        """
        Upload multiple images in parallel.
        
        Parameters
        ----------
        files : List[Union[str, Path]]
            List of file paths to upload.
        board_id : str, optional
            Target board for all images.
        category : str, optional
            Image category.
        parallel : int, optional
            Number of parallel uploads, by default 3.
        
        Returns
        -------
        List[IvkImage]
            List of uploaded image objects.
        
        Examples
        --------
        >>> images = await assets.upload_batch(
        raise NotImplementedError     ["img1.png", "img2.png", "img3.png"],
        raise NotImplementedError     board_id="my-board"
        raise NotImplementedError )
        """
        raise NotImplementedError
    
    async def download_batch(
        self,
        image_names: List[str],
        output_dir: Union[str, Path],
        full_resolution: bool = True,
        parallel: int = 3
    ) -> List[Path]:
        """
        Download multiple images in parallel.
        
        Parameters
        ----------
        image_names : List[str]
            List of image identifiers.
        output_dir : Union[str, Path]
            Directory for downloaded files.
        full_resolution : bool, optional
            Download full resolution.
        parallel : int, optional
            Number of parallel downloads.
        
        Returns
        -------
        List[Path]
            Paths to downloaded files.
        """
        raise NotImplementedError
    
    def validate_image_format(self, file_path: Union[str, Path]) -> bool:
        """
        Check if a file is a supported image format.
        
        Parameters
        ----------
        file_path : Union[str, Path]
            Path to the image file.
        
        Returns
        -------
        bool
            True if format is supported.
        """
        raise NotImplementedError


class BoardManager:
    """
    High-level board management utilities.
    
    Provides convenient methods for board operations beyond
    basic CRUD functionality.
    
    Parameters
    ----------
    client : InvokeAIClient
        Parent client instance.
    
    Examples
    --------
    >>> boards = BoardManager(client)
    >>> archived = await boards.get_archived_boards()
    >>> await boards.move_images("board1", "board2", ["img1", "img2"])
    """
    
    def __init__(self, client: InvokeAIClient) -> None:
        """Initialize the board manager."""
        raise NotImplementedError
    
    async def create_or_get_board(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Board:
        """
        Get existing board or create if it doesn't exist.
        
        Parameters
        ----------
        name : str
            Board name.
        description : str, optional
            Board description for new boards.
        
        Returns
        -------
        Board
            The board object.
        """
        raise NotImplementedError
    
    async def get_board_by_name(self, name: str) -> Optional[Board]:
        """
        Find a board by name.
        
        Parameters
        ----------
        name : str
            Board name to search for.
        
        Returns
        -------
        Optional[Board]
            Board if found, None otherwise.
        """
        raise NotImplementedError
    
    async def archive_board(self, board_id: str) -> Board:
        """
        Archive a board.
        
        Parameters
        ----------
        board_id : str
            Board to archive.
        
        Returns
        -------
        Board
            Updated board object.
        """
        raise NotImplementedError
    
    async def unarchive_board(self, board_id: str) -> Board:
        """
        Unarchive a board.
        
        Parameters
        ----------
        board_id : str
            Board to unarchive.
        
        Returns
        -------
        Board
            Updated board object.
        """
        raise NotImplementedError
    
    async def get_archived_boards(self) -> List[Board]:
        """
        Get all archived boards.
        
        Returns
        -------
        List[Board]
            List of archived boards.
        """
        raise NotImplementedError
    
    async def move_images(
        self,
        source_board_id: str,
        target_board_id: str,
        image_names: List[str]
    ) -> int:
        """
        Move images between boards.
        
        Parameters
        ----------
        source_board_id : str
            Source board ID.
        target_board_id : str
            Target board ID.
        image_names : List[str]
            Images to move.
        
        Returns
        -------
        int
            Number of images moved.
        """
        raise NotImplementedError
    
    async def copy_board(
        self,
        board_id: str,
        new_name: str,
        include_images: bool = False
    ) -> Board:
        """
        Create a copy of a board.
        
        Parameters
        ----------
        board_id : str
            Board to copy.
        new_name : str
            Name for the new board.
        include_images : bool, optional
            Whether to copy images too.
        
        Returns
        -------
        Board
            The new board.
        """
        raise NotImplementedError
    
    async def merge_boards(
        self,
        board_ids: List[str],
        target_name: str,
        delete_source: bool = False
    ) -> Board:
        """
        Merge multiple boards into one.
        
        Parameters
        ----------
        board_ids : List[str]
            Boards to merge.
        target_name : str
            Name for merged board.
        delete_source : bool, optional
            Delete source boards after merge.
        
        Returns
        -------
        Board
            The merged board.
        """
        raise NotImplementedError
    
    async def export_board(
        self,
        board_id: str,
        output_dir: Union[str, Path],
        include_metadata: bool = True
    ) -> Path:
        """
        Export a board with all images.
        
        Parameters
        ----------
        board_id : str
            Board to export.
        output_dir : Union[str, Path]
            Export destination.
        include_metadata : bool, optional
            Include generation metadata.
        
        Returns
        -------
        Path
            Path to export directory.
        """
        raise NotImplementedError


class TypeConverter:
    """
    Utilities for converting between client types and API formats.
    
    Handles the conversion of field types, workflow data structures,
    and other data formats between the pythonic client interface
    and the InvokeAI API format.
    
    Examples
    --------
    >>> converter = TypeConverter()
    >>> api_data = converter.field_to_api(my_field)
    >>> field = converter.api_to_field(api_data, field_type="integer")
    """
    
    @staticmethod
    def field_to_api(field: Field[Any]) -> Dict[str, Any]:
        """
        Convert a client field to API format.
        
        Parameters
        ----------
        field : Field
            Client field instance.
        
        Returns
        -------
        Dict[str, Any]
            API-compatible dictionary.
        """
        raise NotImplementedError
    
    @staticmethod
    def api_to_field(data: Dict[str, Any], field_type: str) -> Field[Any]:
        """
        Convert API data to a client field.
        
        Parameters
        ----------
        data : Dict[str, Any]
            API response data.
        field_type : str
            Target field type name.
        
        Returns
        -------
        Field
            Appropriate field instance.
        """
        raise NotImplementedError
    
    @staticmethod
    def workflow_to_api(workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert workflow definition to API format.
        
        Parameters
        ----------
        workflow : Dict[str, Any]
            Client workflow structure.
        
        Returns
        -------
        Dict[str, Any]
            API-compatible workflow.
        """
        raise NotImplementedError
    
    @staticmethod
    def api_to_workflow(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert API workflow to client format.
        
        Parameters
        ----------
        data : Dict[str, Any]
            API workflow data.
        
        Returns
        -------
        Dict[str, Any]
            Client workflow structure.
        """
        raise NotImplementedError
    
    @staticmethod
    def parse_field_type(field_def: Dict[str, Any]) -> str:
        """
        Determine field type from definition.
        
        Parameters
        ----------
        field_def : Dict[str, Any]
            Field definition from workflow.
        
        Returns
        -------
        str
            Field type identifier.
        """
        raise NotImplementedError
    
    @staticmethod
    def validate_type_compatibility(
        value: Any,
        expected_type: str
    ) -> bool:
        """
        Check if a value matches expected type.
        
        Parameters
        ----------
        value : Any
            Value to check.
        expected_type : str
            Expected type name.
        
        Returns
        -------
        bool
            True if compatible.
        """
        raise NotImplementedError


class ProgressTracker:
    """
    Track and report progress for long-running operations.
    
    Provides a unified interface for progress reporting across
    different operation types (uploads, downloads, generation).
    
    Parameters
    ----------
    total : int, optional
        Total units of work.
    unit : str, optional
        Unit name (bytes, steps, etc.).
    description : str, optional
        Operation description.
    
    Examples
    --------
    >>> tracker = ProgressTracker(total=100, unit="steps")
    >>> tracker.update(10)
    >>> print(tracker.get_progress())  # 0.1
    """
    
    def __init__(
        self,
        total: Optional[int] = None,
        unit: str = "units",
        description: Optional[str] = None
    ) -> None:
        """Initialize the progress tracker."""
        raise NotImplementedError
    
    def update(self, amount: int = 1) -> None:
        """
        Update progress by amount.
        
        Parameters
        ----------
        amount : int, optional
            Progress increment, by default 1.
        """
        raise NotImplementedError
    
    def set_progress(self, current: int) -> None:
        """
        Set absolute progress value.
        
        Parameters
        ----------
        current : int
            Current progress value.
        """
        raise NotImplementedError
    
    def get_progress(self) -> float:
        """
        Get progress as percentage.
        
        Returns
        -------
        float
            Progress from 0.0 to 1.0.
        """
        raise NotImplementedError
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get detailed progress statistics.
        
        Returns
        -------
        Dict[str, Any]
            Statistics including rate, ETA, etc.
        """
        raise NotImplementedError
    
    def reset(self) -> None:
        """Reset progress to zero."""
        raise NotImplementedError
    
    def complete(self) -> None:
        """Mark operation as complete."""
        raise NotImplementedError