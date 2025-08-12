"""
Board repository for board-specific operations.

This module implements the Repository pattern for board-related operations,
keeping data models pure while providing rich functionality.
"""

from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Dict, List, Optional, Union

import requests

from invokeai_py_client.models import Board, IvkImage, ImageCategory

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
    ) -> List[IvkImage]:
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
        List[IvkImage]
            List of IvkImage objects in the board.
        
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
            
            # Convert to IvkImage models
            images = []
            for dto in image_dtos:
                images.append(IvkImage.from_api_response(dto))
            
            return images
            
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return []
            raise
    
    def upload_image_by_file(
        self,
        file_path: Union[str, Path],
        board_id: Optional[str] = None,
        image_category: Union[ImageCategory, str] = ImageCategory.USER,
        is_intermediate: bool = False
    ) -> IvkImage:
        """
        Upload an image from a file to a board.
        
        Parameters
        ----------
        file_path : Union[str, Path]
            Path to the image file to upload.
        board_id : str, optional
            Target board ID. If None, image goes to uncategorized.
        image_category : Union[ImageCategory, str], optional
            Image category type for the uploaded image.
            Use ImageCategory enum values (USER, GENERAL, CONTROL, MASK, OTHER).
            Accepts strings for backward compatibility.
        is_intermediate : bool, optional
            Whether this is an intermediate image, by default False.
        
        Returns
        -------
        IvkImage
            The uploaded IvkImage object with server-assigned metadata.
        
        Raises
        ------
        FileNotFoundError
            If the image file does not exist.
        ValueError
            If the upload fails.
        
        Examples
        --------
        >>> # Upload to specific board
        >>> image = board_repo.upload_image_by_file("photo.png", board_id="board-123")
        
        >>> # Upload to uncategorized
        >>> image = board_repo.upload_image_by_file("photo.png")
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
                
                # Convert ImageCategory enum to string for API
                category_str = image_category.value if isinstance(image_category, ImageCategory) else image_category
                
                params: Dict[str, Any] = {
                    'image_category': category_str,
                    'is_intermediate': is_intermediate
                }
                
                if board_id is not None:
                    params['board_id'] = board_id
                
                # Use the session's post method directly for multipart
                # Note: Remove Content-Type header for multipart form data
                url = f"{self._client.base_url}/images/upload"
                
                # Temporarily store and remove Content-Type header
                original_content_type = self._client.session.headers.get('Content-Type')
                if 'Content-Type' in self._client.session.headers:
                    del self._client.session.headers['Content-Type']
                
                try:
                    response = self._client.session.post(
                        url,
                        files=files,
                        params=params,
                        timeout=self._client.timeout
                    )
                    response.raise_for_status()
                finally:
                    # Restore Content-Type header
                    if original_content_type:
                        self._client.session.headers['Content-Type'] = original_content_type
                
                return IvkImage.from_api_response(response.json())
                
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
    
    def get_image(self, image_name: str) -> Optional[IvkImage]:
        """
        Get a specific image by name.
        
        Parameters
        ----------
        image_name : str
            The server-side image name/ID.
        
        Returns
        -------
        Optional[IvkImage]
            The IvkImage object if found, None otherwise.
        
        Examples
        --------
        >>> image = board_repo.get_image("abc-123.png")
        >>> if image:
        ...     print(f"Image size: {image.width}x{image.height}")
        """
        try:
            response = self._client._make_request('GET', f'/images/i/{image_name}')
            return IvkImage.from_api_response(response.json())
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
            # The delete endpoint expects a JSON body with image names (list)
            self._client._make_request(
                'POST',
                '/images/delete',
                json={"image_names": [image_name]}
            )
            return True
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return False
            raise
    
    def download_image(
        self,
        image_name: str,
        full_resolution: bool = True
    ) -> bytes:
        """
        Download an image from the server as bytes.
        
        Parameters
        ----------
        image_name : str
            The server-side image name/ID.
        full_resolution : bool, optional
            Whether to download full resolution (True) or thumbnail (False), by default True.
        
        Returns
        -------
        bytes
            Image data as bytes that can be decoded with imageio.imdecode().
        
        Raises
        ------
        ValueError
            If the image does not exist.
        IOError
            If the download fails.
        
        Examples
        --------
        >>> import imageio.v3 as iio
        >>> import numpy as np
        >>> 
        >>> # Download and decode image
        >>> image_bytes = board_repo.download_image("abc-123.png")
        >>> image_array = iio.imread(image_bytes)  # RGB/RGBA numpy array
        >>> print(f"Image shape: {image_array.shape}")
        
        >>> # Download thumbnail
        >>> thumb_bytes = board_repo.download_image("abc-123.png", full_resolution=False)
        >>> thumb_array = iio.imread(thumb_bytes)
        """
        # Determine endpoint
        endpoint = f'/images/i/{image_name}/full' if full_resolution else f'/images/i/{image_name}/thumbnail'
        
        try:
            response = self._client._make_request('GET', endpoint)
            # response.content is bytes in requests library
            content: bytes = response.content
            return content
            
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
        
        >>> # Move to uncategorized (removes from current board)
        >>> board_repo.move_image_to_board("image.png", "none")
        """
        try:
            if board_id == "none" or board_id is None:
                # Remove from board (move to uncategorized)
                self._client._make_request(
                    'DELETE',
                    '/board_images/',
                    json={"image_name": image_name}
                )
            else:
                # Add to specific board
                self._client._make_request(
                    'POST',
                    '/board_images/',
                    json={
                        "board_id": board_id,
                        "image_name": image_name
                    }
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
        
        Examples
        --------
        >>> board_repo.star_image("abc-123.png")
        """
        try:
            # The star endpoint expects a list of image names
            self._client._make_request(
                'POST',
                '/images/star',
                json={"image_names": [image_name]}
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
        
        Examples
        --------
        >>> board_repo.unstar_image("abc-123.png")
        """
        try:
            # The unstar endpoint expects a list of image names
            self._client._make_request(
                'POST',
                '/images/unstar',
                json={"image_names": [image_name]}
            )
            return True
        except requests.HTTPError:
            return False
    
    
    def upload_image_by_data(
        self,
        image_data: bytes,
        file_extension: str,
        board_id: Optional[str] = None,
        image_category: Union[ImageCategory, str] = ImageCategory.USER,
        is_intermediate: bool = False,
        filename: Optional[str] = None
    ) -> IvkImage:
        """
        Upload an image from encoded bytes to a board.
        
        This method is useful when you have image data in memory
        (e.g., from imageio.imencode() or cv2.imencode()).
        
        Parameters
        ----------
        image_data : bytes
            Encoded image data as bytes.
        file_extension : str
            File extension to determine mime type (e.g., '.png', 'png').
        board_id : str, optional
            Target board ID. If None, image goes to uncategorized.
        image_category : Union[ImageCategory, str], optional
            Image category type for the uploaded image.
            Use ImageCategory enum values (USER, GENERAL, CONTROL, MASK, OTHER).
            Accepts strings for backward compatibility.
        is_intermediate : bool, optional
            Whether this is an intermediate image, by default False.
        filename : str, optional
            Filename to use for the upload. If None, generates a default.
        
        Returns
        -------
        IvkImage
            The uploaded IvkImage object with server-assigned metadata.
        
        Raises
        ------
        ValueError
            If the upload fails or extension is invalid.
        
        Examples
        --------
        >>> import imageio.v3 as iio
        >>> # Read and encode image
        >>> img = iio.imread("photo.png")
        >>> encoded = iio.imwrite("<bytes>", img, extension=".png")
        >>> # Upload encoded data
        >>> image = board_repo.upload_image_by_data(
        ...     encoded, ".png", board_id="board-123"
        ... )
        
        >>> # Using cv2 (note: cv2 uses BGR, may need conversion)
        >>> import cv2
        >>> img = cv2.imread("photo.jpg")
        >>> success, encoded = cv2.imencode('.jpg', img)
        >>> if success:
        ...     image = board_repo.upload_image_by_data(
        ...         encoded.tobytes(), '.jpg'
        ...     )
        """
        # Normalize extension
        if not file_extension.startswith('.'):
            file_extension = f'.{file_extension}'
        
        # Get mime type
        mime_type = self._get_mime_type_from_extension(file_extension)
        
        # Generate filename if not provided
        if filename is None:
            import uuid
            filename = f"upload_{uuid.uuid4().hex[:8]}{file_extension}"
        elif not filename.endswith(file_extension):
            filename = f"{filename}{file_extension}"
        
        # Prepare multipart form data
        try:
            # Create a file-like object from bytes
            file_like = BytesIO(image_data)
            
            files = {
                'file': (filename, file_like, mime_type)
            }
            
            params: Dict[str, Any] = {
                'image_category': image_category,
                'is_intermediate': is_intermediate
            }
            
            if board_id is not None:
                params['board_id'] = board_id
            
            # Use the session's post method directly for multipart
            # Note: Remove Content-Type header for multipart form data
            url = f"{self._client.base_url}/images/upload"
            
            # Temporarily store and remove Content-Type header
            original_content_type = self._client.session.headers.get('Content-Type')
            if 'Content-Type' in self._client.session.headers:
                del self._client.session.headers['Content-Type']
            
            try:
                response = self._client.session.post(
                    url,
                    files=files,
                    params=params,
                    timeout=self._client.timeout
                )
                response.raise_for_status()
            finally:
                # Restore Content-Type header
                if original_content_type:
                    self._client.session.headers['Content-Type'] = original_content_type
            
            return IvkImage.from_api_response(response.json())
            
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
        return BoardRepository._get_mime_type_from_extension(ext)
    
    @staticmethod
    def _get_mime_type_from_extension(extension: str) -> str:
        """
        Get MIME type from file extension.
        
        Parameters
        ----------
        extension : str
            File extension (e.g., '.png' or 'png').
        
        Returns
        -------
        str
            MIME type string.
        """
        # Normalize extension
        if not extension.startswith('.'):
            extension = f'.{extension}'
        extension = extension.lower()
        
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
        return mime_types.get(extension, 'application/octet-stream')