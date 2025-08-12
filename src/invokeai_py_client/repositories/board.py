"""
Board repository for board-specific operations.

This module implements the Repository pattern for board-related operations,
keeping data models pure while providing rich functionality.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Dict, List, Optional, Union

import requests

from invokeai_py_client.models import Board, Image

if TYPE_CHECKING:
    from invokeai_py_client.client import InvokeAIClient


class BoardRepository:
    """
    Repository for board-specific operations.
    
    This class provides all board-related operations including image management,
    following the Repository pattern to keep models pure and operations separate.
    
    Attributes
    ----------
    _client : InvokeAIClient
        Reference to the InvokeAI client for API calls.
    
    Examples
    --------
    >>> client = InvokeAIClient.from_url("http://localhost:9090")
    >>> board_repo = BoardRepository(client)
    >>> images = board_repo.list_images("board-id-123")
    """
    
    def __init__(self, client: InvokeAIClient) -> None:
        """
        Initialize the BoardRepository.
        
        Parameters
        ----------
        client : InvokeAIClient
            The InvokeAI client instance to use for API calls.
        """
        self._client = client
    
    def list_images(
        self,
        board_id: str,
        limit: Optional[int] = None,
        order_dir: str = "DESC",
        starred_first: bool = False
    ) -> List[Image]:
        """
        List images in a board.
        
        Parameters
        ----------
        board_id : str
            The board ID. Use "none" for uncategorized images.
        limit : int, optional
            Maximum number of images to return.
        order_dir : str, optional
            Sort order: "DESC" (newest first) or "ASC" (oldest first), by default "DESC".
        starred_first : bool, optional
            Whether to show starred images first, by default False.
        
        Returns
        -------
        List[Image]
            List of Image objects in the board.
        
        Examples
        --------
        >>> # Get all images in a board
        >>> images = board_repo.list_images("board-id-123")
        
        >>> # Get latest 10 images
        >>> latest = board_repo.list_images("board-id-123", limit=10)
        
        >>> # Get starred images first
        >>> starred = board_repo.list_images("board-id-123", starred_first=True)
        """
        # First get image names using the optimized API endpoint
        params: Dict[str, Any] = {
            "board_id": board_id,
            "order_dir": order_dir,
            "starred_first": starred_first
        }
        
        if limit is not None:
            params["limit"] = limit
        
        try:
            # Get sorted image names
            response = self._client._make_request('GET', '/images/names', params=params)
            result = response.json()
            
            # Handle response format
            if isinstance(result, dict):
                image_names = result.get('image_names', [])
            else:
                image_names = result  # It's already a list
            
            if not image_names:
                return []
            
            # Get full image DTOs
            dto_response = self._client._make_request(
                'POST',
                '/images/images_by_names',
                json={"image_names": image_names}
            )
            
            image_dtos = dto_response.json()
            
            # Convert to Image models
            images = []
            for dto in image_dtos:
                images.append(Image.from_api_response(dto))
            
            return images
            
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return []
            raise
    
    def upload_image(
        self,
        file_path: Union[str, Path],
        board_id: Optional[str] = None,
        image_category: str = "user",
        is_intermediate: bool = False
    ) -> Image:
        """
        Upload an image to a board.
        
        Parameters
        ----------
        file_path : Union[str, Path]
            Path to the image file to upload.
        board_id : str, optional
            Target board ID. If None, image goes to uncategorized.
        image_category : str, optional
            Image category: "user", "generated", etc., by default "user".
        is_intermediate : bool, optional
            Whether this is an intermediate image, by default False.
        
        Returns
        -------
        Image
            The uploaded Image object with server-assigned metadata.
        
        Raises
        ------
        FileNotFoundError
            If the image file does not exist.
        ValueError
            If the upload fails.
        
        Examples
        --------
        >>> # Upload to specific board
        >>> image = board_repo.upload_image("photo.png", board_id="board-123")
        
        >>> # Upload to uncategorized
        >>> image = board_repo.upload_image("photo.png")
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")
        
        # Prepare multipart form data
        try:
            with open(file_path, 'rb') as image_file:
                files = {
                    'file': (file_path.name, image_file, self._get_mime_type(file_path))
                }
                
                params: Dict[str, Any] = {
                    'image_category': image_category,
                    'is_intermediate': is_intermediate
                }
                
                if board_id is not None:
                    params['board_id'] = board_id
                
                # Use the session's post method directly for multipart
                url = f"{self._client.base_url}/images/upload"
                response = self._client.session.post(
                    url,
                    files=files,
                    params=params,
                    timeout=self._client.timeout
                )
                response.raise_for_status()
                
                return Image.from_api_response(response.json())
                
        except requests.HTTPError as e:
            if e.response is not None:
                error_msg = f"Upload failed: {e.response.status_code}"
                try:
                    error_detail = e.response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {e.response.text}"
                raise ValueError(error_msg)
            raise
    
    def get_image(self, image_name: str) -> Optional[Image]:
        """
        Get a specific image by name.
        
        Parameters
        ----------
        image_name : str
            The server-side image name/ID.
        
        Returns
        -------
        Optional[Image]
            The Image object if found, None otherwise.
        
        Examples
        --------
        >>> image = board_repo.get_image("abc-123.png")
        >>> if image:
        ...     print(f"Image size: {image.width}x{image.height}")
        """
        try:
            response = self._client._make_request('GET', f'/images/i/{image_name}')
            return Image.from_api_response(response.json())
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise
    
    def delete_image(self, image_name: str) -> bool:
        """
        Delete an image.
        
        Parameters
        ----------
        image_name : str
            The server-side image name/ID to delete.
        
        Returns
        -------
        bool
            True if deletion was successful, False if image not found.
        
        Examples
        --------
        >>> success = board_repo.delete_image("abc-123.png")
        >>> if success:
        ...     print("Image deleted")
        """
        try:
            # The delete endpoint expects a JSON body with image name
            self._client._make_request(
                'POST',
                '/images/delete',
                json={"image_name": image_name}
            )
            return True
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return False
            raise
    
    def download_image(
        self,
        image_name: str,
        output_path: Optional[Union[str, Path]] = None,
        full_resolution: bool = True
    ) -> Path:
        """
        Download an image from the server.
        
        Parameters
        ----------
        image_name : str
            The server-side image name/ID.
        output_path : Union[str, Path], optional
            Where to save the image. If None, uses current directory with original name.
        full_resolution : bool, optional
            Whether to download full resolution (True) or thumbnail (False), by default True.
        
        Returns
        -------
        Path
            Path to the downloaded image file.
        
        Raises
        ------
        ValueError
            If the image does not exist.
        IOError
            If the download or save fails.
        
        Examples
        --------
        >>> # Download to current directory
        >>> path = board_repo.download_image("abc-123.png")
        
        >>> # Download to specific location
        >>> path = board_repo.download_image("abc-123.png", "downloads/photo.png")
        
        >>> # Download thumbnail
        >>> path = board_repo.download_image("abc-123.png", full_resolution=False)
        """
        # Determine endpoint
        endpoint = f'/images/i/{image_name}/full' if full_resolution else f'/images/i/{image_name}/thumbnail'
        
        try:
            response = self._client._make_request('GET', endpoint)
            
            # Determine output path
            if output_path is None:
                output_path = Path(image_name)
            else:
                output_path = Path(output_path)
            
            # Create parent directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the image
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return output_path
            
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise ValueError(f"Image not found: {image_name}")
            raise IOError(f"Download failed: {e}")
    
    def move_image_to_board(self, image_name: str, board_id: str) -> bool:
        """
        Move an image to a different board.
        
        Parameters
        ----------
        image_name : str
            The image to move.
        board_id : str
            Target board ID. Use "none" to move to uncategorized.
        
        Returns
        -------
        bool
            True if successful.
        
        Examples
        --------
        >>> # Move to specific board
        >>> board_repo.move_image_to_board("image.png", "board-123")
        
        >>> # Move to uncategorized
        >>> board_repo.move_image_to_board("image.png", "none")
        """
        try:
            # Update the image with new board_id
            self._client._make_request(
                'PATCH',
                f'/images/i/{image_name}',
                json={"board_id": board_id if board_id != "none" else None}
            )
            return True
        except requests.HTTPError:
            return False
    
    def star_image(self, image_name: str) -> bool:
        """
        Star an image.
        
        Parameters
        ----------
        image_name : str
            The image to star.
        
        Returns
        -------
        bool
            True if successful.
        """
        try:
            self._client._make_request(
                'POST',
                '/images/star',
                json={"image_name": image_name}
            )
            return True
        except requests.HTTPError:
            return False
    
    def unstar_image(self, image_name: str) -> bool:
        """
        Unstar an image.
        
        Parameters
        ----------
        image_name : str
            The image to unstar.
        
        Returns
        -------
        bool
            True if successful.
        """
        try:
            self._client._make_request(
                'POST',
                '/images/unstar',
                json={"image_name": image_name}
            )
            return True
        except requests.HTTPError:
            return False
    
    def get_starred_images(self, board_id: str) -> List[Image]:
        """
        Get only starred images from a board.
        
        Parameters
        ----------
        board_id : str
            The board ID.
        
        Returns
        -------
        List[Image]
            List of starred images only.
        """
        # Get all images with starred first
        all_images = self.list_images(board_id, starred_first=True)
        
        # Filter for starred only
        return [img for img in all_images if img.starred]
    
    @staticmethod
    def _get_mime_type(file_path: Path) -> str:
        """
        Get MIME type for an image file.
        
        Parameters
        ----------
        file_path : Path
            Path to the image file.
        
        Returns
        -------
        str
            MIME type string.
        """
        ext = file_path.suffix.lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff'
        }
        return mime_types.get(ext, 'application/octet-stream')