"""
Board handle for managing board state and operations.

This module provides the BoardHandle class which represents the running state
of a board and manages image operations within that board.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests

from invokeai_py_client.board.board_model import Board
from invokeai_py_client.models import ImageCategory, IvkImage

if TYPE_CHECKING:
    from invokeai_py_client.client import InvokeAIClient


class BoardHandle:
    """
    Manages the running state of a board instance.

    This class handles board-specific operations including image uploads,
    downloads, and management. It provides a pythonic interface for
    interacting with a specific board in the InvokeAI system.

    Parameters
    ----------
    client : InvokeAIClient
        The client instance for API communication.
    board : Board
        The board information model.

    Attributes
    ----------
    client : InvokeAIClient
        Reference to the parent client.
    board : Board
        The board metadata and information.

    Examples
    --------
    >>> # Created by BoardRepository
    >>> board_handle = repo.get_board_handle("board-id-123")
    >>> images = board_handle.list_images()
    >>> board_handle.upload_image("photo.png")
    """

    def __init__(self, client: InvokeAIClient, board: Board) -> None:
        """Initialize the board handle."""
        self.client = client
        self.board = board

    @property
    def board_id(self) -> str:
        """Get the board ID."""
        # For uncategorized board, return "none" as expected by API
        if self.board.board_id is None:
            return "none"
        return self.board.board_id

    @property
    def board_name(self) -> str:
        """Get the board name."""
        return self.board.board_name or "Uncategorized"

    @property
    def is_uncategorized(self) -> bool:
        """Check if this is the uncategorized board."""
        return self.board.is_uncategorized()

    def refresh(self) -> None:
        """
        Refresh the board information from the server.

        Updates the internal board state with the latest data from
        the InvokeAI instance.

        Raises
        ------
        ValueError
            If the board no longer exists.
        """
        if self.is_uncategorized:
            # Special-case: uncategorized board is a sentinel (id 'none') and
            # not a real board resource. There is no images_count endpoint.
            # We derive the count by listing its image names.
            try:
                resp = self.client._make_request("GET", "/boards/none/image_names")
                data = resp.json()
                if isinstance(data, list):
                    self.board.image_count = len(data)
            except requests.HTTPError:
                # Leave existing count if request fails
                pass
            return

        # Normal board: fetch latest metadata (no trailing slash)
        response = self.client._make_request("GET", f"/boards/{self.board_id}")
        self.board = Board(**response.json())

    def list_images(
        self,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_dir: str = "DESC",
        starred_first: bool = False,
        search_term: str | None = None,
    ) -> list[str]:
        """
        List images in this board.

        Parameters
        ----------
        offset : int
            Number of images to skip.
        limit : int
            Maximum number of images to return.
        order_by : str
            Field to order by (e.g., "created_at", "starred").
        order_dir : str
            Sort order: "DESC" or "ASC".
        starred_first : bool
            Whether to show starred images first.
        search_term : str, optional
            Search term to filter images.

        Returns
        -------
        List[str]
            List of image names in the board.

        Examples
        --------
        >>> images = board_handle.list_images(limit=50)
        >>> starred = board_handle.list_images(starred_first=True)
        """
        params = {
            "offset": offset,
            "limit": limit,
            "order_by": order_by,
            "order_dir": order_dir,
            "starred_first": starred_first,
        }

        if search_term:
            params["search_term"] = search_term

        # Use the appropriate endpoint for board images
        if self.is_uncategorized:
            # Use dedicated endpoint for uncategorized board image names
            response = self.client._make_request("GET", "/boards/none/image_names")
        else:
            response = self.client._make_request(
                "GET", f"/boards/{self.board_id}/image_names"
            )

        data = response.json()

        # Extract image names from response
        if isinstance(data, list):
            # Direct list of image names
            return data
        elif isinstance(data, dict):
            if "image_names" in data:
                # List of image names in dict
                names = data["image_names"]
                return names if isinstance(names, list) else []
            elif "items" in data:
                # Paginated response with image objects
                return [item.get("image_name", item.get("name", "")) for item in data["items"]]

        return []

    def upload_image(
        self,
        file_path: str | Path,
        is_intermediate: bool = False,
    # Default to USER category so uploads appear under the GUI's Assets tab
    image_category: ImageCategory = ImageCategory.USER,
        session_id: str | None = None,
    ) -> IvkImage:
        """
        Upload an image file to this board.

        Parameters
        ----------
        file_path : str | Path
            Path to the image file to upload.
        is_intermediate : bool
            Whether this is an intermediate image.
        image_category : ImageCategory
            The category of the image. Defaults to ImageCategory.USER (Assets tab).
        session_id : str, optional
            Session ID to associate with the upload.

        Returns
        -------
        IvkImage
            The uploaded image object with metadata.

        Raises
        ------
        FileNotFoundError
            If the image file does not exist.
        ValueError
            If upload fails.

        Examples
        --------
        >>> image = board_handle.upload_image("landscape.png")
        >>> print(f"Uploaded: {image.image_name}")
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        # Prepare the multipart form data
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, self._get_mime_type(file_path))}

            # API expects these as query parameters, not form data
            params = {
                "image_category": image_category.value,
                "is_intermediate": is_intermediate,
            }
            # IMPORTANT: The backend treats "uncategorized" images as those with
            # no board association (board_id omitted). Passing the sentinel 'none'
            # causes an (ignored) failure when attempting to associate with a
            # non-existent board record. We therefore omit board_id when the
            # handle refers to the uncategorized pseudo-board so the image shows
            # up in the GUI's Uncategorized > Images view.
            if self.board_id not in ("none", "", None):
                params["board_id"] = self.board_id

            if session_id:
                params["session_id"] = session_id

            # Use plain requests.post for multipart upload to avoid session header conflicts
            # The session's Content-Type: application/json breaks multipart uploads
            import requests as req
            
            # Copy auth headers if present
            headers = {}
            if "Authorization" in self.client.session.headers:
                headers["Authorization"] = self.client.session.headers["Authorization"]
            
            response = req.post(
                f"{self.client.base_url}/images/upload",
                files=files,
                params=params,
                headers=headers,
                timeout=self.client.timeout,
            )

        response.raise_for_status()
        result = response.json()

        # Update board image count
        self.board.image_count += 1

        return IvkImage(**result)

    def upload_image_data(
        self,
        image_data: bytes,
        filename: str | None = None,
        is_intermediate: bool = False,
        # Default to USER category so uploads appear under the GUI's Assets tab
        image_category: ImageCategory = ImageCategory.USER,
        session_id: str | None = None,
    ) -> IvkImage:
        """
        Upload image data directly to this board.

        Parameters
        ----------
        image_data : bytes
            Raw image data to upload.
        filename : str, optional
            Filename to use for the upload.
        is_intermediate : bool
            Whether this is an intermediate image.
        image_category : ImageCategory
            The category of the image. Defaults to ImageCategory.USER (Assets tab).
        session_id : str, optional
            Session ID to associate with the upload.

        Returns
        -------
        IvkImage
            The uploaded image object.

        Examples
        --------
        >>> with open("image.png", "rb") as f:
        ...     data = f.read()
        >>> image = board_handle.upload_image_data(data, "custom.png")
        """
        # Determine filename
        if filename is None:
            filename = "upload.png"

        # Determine MIME type from filename
        mime_type = self._get_mime_type_from_filename(filename)

        # Create file-like object
        file_obj = BytesIO(image_data)
        file_obj.seek(0)  # Ensure we're at the beginning of the buffer

        files = {"file": (filename, file_obj, mime_type)}

        # API expects these as query parameters, not form data
        params = {
            "image_category": image_category.value,
            "is_intermediate": is_intermediate,
        }
        if self.board_id not in ("none", "", None):
            params["board_id"] = self.board_id

        if session_id:
            params["session_id"] = session_id

        # Use plain requests.post for multipart upload to avoid session header conflicts
        # The session's Content-Type: application/json breaks multipart uploads
        import requests as req
        
        # Copy auth headers if present
        headers = {}
        if "Authorization" in self.client.session.headers:
            headers["Authorization"] = self.client.session.headers["Authorization"]
        
        response = req.post(
            f"{self.client.base_url}/images/upload",
            files=files,
            params=params,
            headers=headers,
            timeout=self.client.timeout,
        )

        response.raise_for_status()
        result = response.json()

        # Update board image count
        self.board.image_count += 1

        return IvkImage(**result)

    def download_image(self, image_name: str, full_resolution: bool = True) -> bytes:
        """
        Download an image from this board.

        Parameters
        ----------
        image_name : str
            The name/ID of the image to download.
        full_resolution : bool
            Whether to download full resolution or thumbnail.

        Returns
        -------
        bytes
            The raw image data.

        Raises
        ------
        ValueError
            If the image is not found in this board.

        Examples
        --------
        >>> data = board_handle.download_image("img-123.png")
        >>> with open("downloaded.png", "wb") as f:
        ...     f.write(data)
        """
        # First, verify the image is in this board
        images = self.list_images()
        if image_name not in images:
            raise ValueError(f"Image {image_name} not found in board {self.board_name}")

        # Determine endpoint based on resolution
        if full_resolution:
            endpoint = f"/images/i/{image_name}/full"
        else:
            endpoint = f"/images/i/{image_name}/thumbnail"

        try:
            response = self.client._make_request("GET", endpoint)
            content: bytes = response.content
            return content
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise ValueError(f"Image not found: {image_name}") from e
            raise OSError(f"Download failed: {e}") from e

    def move_image_to(self, image_name: str, target_board_id: str) -> bool:
        """
        Move an image from this board to another board.

        Parameters
        ----------
        image_name : str
            The image to move.
        target_board_id : str
            The target board ID. Use "none" to move to uncategorized.

        Returns
        -------
        bool
            True if successful.

        Notes
        -----
        - Preferred API (as used by the InvokeAI GUI):
          - Add to board:  POST /api/v1/board_images/        {"image_name", "board_id"}
                            or POST /api/v1/board_images/batch {"image_names", "board_id"}
          - Remove board:  POST /api/v1/board_images/batch/delete {"image_names"}
        - Backward-compatibility fallback:
          - PATCH /api/v1/images/i/{image_name} with board_id in JSON or as query param.

        Examples
        --------
        >>> success = board_handle.move_image_to("img-123.png", "board-456")
        >>> success = board_handle.move_image_to("img-123.png", "none")  # to uncategorized
        """
        # Normalize target board
        to_uncategorized = target_board_id in ("none", "", None)

        # Try the modern board_images routes first (matches GUI behavior)
        try:
            if to_uncategorized:
                # Remove association -> uncategorized
                payload = {"image_names": [image_name]}
                self.client._make_request("POST", "/board_images/batch/delete", json=payload)
            else:
                # Prefer single-image endpoint; fallback to batch if needed
                try:
                    payload_single = {"image_name": image_name, "board_id": target_board_id}
                    self.client._make_request("POST", "/board_images/", json=payload_single)
                except requests.HTTPError:
                    payload_batch = {"image_names": [image_name], "board_id": target_board_id}
                    self.client._make_request("POST", "/board_images/batch", json=payload_batch)
        except requests.HTTPError:
            # Fallback to legacy PATCH images route
            data = {"board_id": None if to_uncategorized else target_board_id}
            try:
                resp = self.client._make_request("PATCH", f"/images/i/{image_name}", json=data)
                if resp.status_code >= 400:
                    raise requests.HTTPError(f"Bad status {resp.status_code}")
            except requests.HTTPError:
                # Fallback as query params
                try:
                    params = {"board_id": data["board_id"]}
                    self.client._make_request("PATCH", f"/images/i/{image_name}", params=params)
                except requests.HTTPError:
                    return False

        # Update image counts (best-effort) on the source handle
        self.board.image_count = max(0, self.board.image_count - 1)
        return True

    def remove_image(self, image_name: str) -> bool:
        """
        Remove an image from this board (moves to uncategorized).

        Parameters
        ----------
        image_name : str
            The image to remove from the board.

        Returns
        -------
        bool
            True if successful.

        Examples
        --------
        >>> success = board_handle.remove_image("img-123.png")
        """
        if self.is_uncategorized:
            # Can't remove from uncategorized
            return False

        return self.move_image_to(image_name, "none")

    def delete_image(self, image_name: str) -> bool:
        """
        Delete an image permanently from this board.

        Parameters
        ----------
        image_name : str
            The image to delete.

        Returns
        -------
        bool
            True if deletion was successful.

        Notes
        -----
        The upstream API returns 200 even if the image did not exist (deleted_images empty).
        We therefore parse the response and only return True if the image_name appears in
        the 'deleted_images' list.
        """
        try:
            resp = self.client._make_request("DELETE", f"/images/i/{image_name}")
            # Upstream returns DeleteImagesResult: {'deleted_images': [...], 'affected_boards': [...]}
            try:
                payload = resp.json()
            except Exception:
                payload = {}
            deleted_list = payload.get("deleted_images") or []
            deleted = image_name in deleted_list

            if deleted:
                # Update local count only on confirmed deletion
                self.board.image_count = max(0, self.board.image_count - 1)
            return bool(deleted)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return False
            raise

    def star_image(self, image_name: str) -> bool:
        """
        Star an image in this board.

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
            self.client._make_request("PATCH", f"/images/i/{image_name}", json={"starred": True})
            return True
        except requests.HTTPError:
            return False

    def unstar_image(self, image_name: str) -> bool:
        """
        Unstar an image in this board.

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
            self.client._make_request("PATCH", f"/images/i/{image_name}", json={"starred": False})
            return True
        except requests.HTTPError:
            return False

    def get_image_count(self) -> int:
        """
        Get the current number of images in this board.

        Returns
        -------
        int
            The number of images.
        """
        # image_count has a default of 0, so it's never None
        return self.board.image_count

    def to_dict(self) -> dict[str, Any]:
        """
        Export the board information as a dictionary.

        Returns
        -------
        Dict[str, Any]
            Board data as a dictionary.
        """
        return self.board.model_dump()

    @staticmethod
    def _get_mime_type(file_path: Path) -> str:
        """Get MIME type from file path."""
        extension = file_path.suffix.lower()
        return BoardHandle._get_mime_type_from_extension(extension)

    @staticmethod
    def _get_mime_type_from_filename(filename: str) -> str:
        """Get MIME type from filename."""
        extension = Path(filename).suffix.lower()
        return BoardHandle._get_mime_type_from_extension(extension)

    @staticmethod
    def _get_mime_type_from_extension(extension: str) -> str:
        """Get MIME type from file extension."""
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            ".webp": "image/webp",
        }
        return mime_types.get(extension, "application/octet-stream")

    def __repr__(self) -> str:
        """String representation of the board handle."""
        return (
            f"BoardHandle(name='{self.board_name}', "
            f"id='{self.board_id}', "
            f"images={self.get_image_count()})"
        )
