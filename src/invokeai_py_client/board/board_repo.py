"""
Board repository for managing board instances using the repository pattern.

This module implements the Repository pattern for board-related operations,
creating and managing BoardHandle instances from Board models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import requests

from invokeai_py_client.board.board_handle import BoardHandle
from invokeai_py_client.board.board_model import Board
from invokeai_py_client.models import IvkImage  # added for image metadata lookups

if TYPE_CHECKING:
    from invokeai_py_client.client import InvokeAIClient


class BoardRepository:
    """
    Repository for board management operations.

    This class provides board management operations following the Repository
    pattern. It creates BoardHandle instances for interacting with specific
    boards and manages the lifecycle of boards in the InvokeAI system.

    Attributes
    ----------
    _client : InvokeAIClient
        Reference to the InvokeAI client for API calls.

    Examples
    --------
    >>> client = InvokeAIClient.from_url("http://localhost:9090")
    >>> board_repo = client.board_repo
    >>>
    >>> # List all boards
    >>> boards = board_repo.list_boards()
    >>>
    >>> # Get a board handle for operations
    >>> board_handle = board_repo.get_board_handle("board-id-123")
    >>> images = board_handle.list_images()
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
        self._cached_handles: dict[str, BoardHandle] = {}

    def list_boards(
        self, all: bool = True, include_uncategorized: bool = False
    ) -> list[Board]:
        """
        List all available boards in the InvokeAI instance.

        Note: The uncategorized board is not included by default as it's system-managed.

        Parameters
        ----------
        all : bool, optional
            Whether to fetch all boards or use pagination, by default True.
        include_uncategorized : bool, optional
            Whether to include the uncategorized board in the list, by default False.

        Returns
        -------
        List[Board]
            List of board objects containing board metadata.

        Examples
        --------
        >>> boards = board_repo.list_boards()
        >>> for board in boards:
        ...     print(f"{board.board_name}: {board.image_count} images")

        >>> # Include uncategorized board
        >>> boards = board_repo.list_boards(include_uncategorized=True)
        >>> for board in boards:
        ...     if board.is_uncategorized():
        ...         print(f"Uncategorized: {board.image_count} images")
        """
        params = {"all": all}
        response = self._client._make_request("GET", "/boards/", params=params)

        data = response.json()

        # Handle both paginated and non-paginated responses
        if isinstance(data, list):
            # Direct list response when all=True
            boards_data = data
        elif isinstance(data, dict) and "items" in data:
            # Paginated response
            boards_data = data["items"]
        else:
            # Unexpected response format
            boards_data = []

        # Convert to Board objects
        boards = [Board(**board_data) for board_data in boards_data]

        # Add uncategorized board if requested
        if include_uncategorized:
            uncategorized = self.get_uncategorized_board()
            boards.insert(0, uncategorized)

        return boards

    def get_board_by_id(self, board_id: str) -> Board | None:
        """
        Get a board by its ID.

        Parameters
        ----------
        board_id : str
            The unique board identifier. Use "none" for uncategorized board.

        Returns
        -------
        Board | None
            The board object if found, None otherwise.

        Examples
        --------
        >>> board = board_repo.get_board_by_id("board-123")
        >>> if board:
        ...     print(f"Found: {board.board_name}")

        >>> # Get uncategorized board
        >>> uncategorized = board_repo.get_board_by_id("none")
        """
        # Special handling for uncategorized board
        if board_id == "none" or board_id is None:
            return self.get_uncategorized_board()

        try:
            response = self._client._make_request("GET", f"/boards/{board_id}")
            return Board(**response.json())
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def get_boards_by_name(self, name: str) -> list[Board]:
        """
        Get boards by name (exact match).

        Parameters
        ----------
        name : str
            The board name to search for.

        Returns
        -------
        List[Board]
            List of boards with matching name (can be multiple).

        Examples
        --------
        >>> boards = board_repo.get_boards_by_name("My Project")
        >>> for board in boards:
        ...     print(f"ID: {board.board_id}")
        """
        all_boards = self.list_boards(all=True, include_uncategorized=False)
        return [board for board in all_boards if board.board_name == name]

    def create_board(self, name: str, is_private: bool = False) -> BoardHandle:
        """
        Create a new board and return its handle.

        Parameters
        ----------
        name : str
            The name for the new board.
        is_private : bool, optional
            Whether the board should be private, by default False.

        Returns
        -------
        BoardHandle
            Handle for the newly created board.

        Raises
        ------
        ValueError
            If board creation fails.

        Examples
        --------
        >>> board_handle = board_repo.create_board("My Artwork")
        >>> board_handle.upload_image("art.png")
        """
        # API expects these as query parameters, not JSON body
        params = {"board_name": name, "is_private": is_private}

        try:
            response = self._client._make_request("POST", "/boards/", params=params)
            board = Board(**response.json())
            return self.get_board_handle(board.board_id)
        except requests.HTTPError as e:
            if e.response is not None:
                error_msg = f"Failed to create board: {e.response.status_code}"
                try:
                    error_detail = e.response.json()
                    error_msg += f" - {error_detail}"
                except Exception:
                    error_msg += f" - {e.response.text}"
                raise ValueError(error_msg) from e
            raise

    def delete_board(self, board_id: str, delete_images: bool = False) -> bool:
        """
        Delete a board from the InvokeAI instance.

        Parameters
        ----------
        board_id : str
            The ID of the board to delete.
        delete_images : bool, optional
            Whether to also delete all images in the board, by default False.
            If False, images are moved to uncategorized.

        Returns
        -------
        bool
            True if deletion was successful.

        Raises
        ------
        ValueError
            If attempting to delete the uncategorized board.

        Examples
        --------
        >>> # Delete board and move images to uncategorized
        >>> success = board_repo.delete_board("board-123")

        >>> # Delete board and all its images
        >>> success = board_repo.delete_board("board-123", delete_images=True)
        """
        if board_id == "none" or board_id is None:
            raise ValueError("Cannot delete the uncategorized board")

        params = {"include_images": delete_images}

        try:
            self._client._make_request("DELETE", f"/boards/{board_id}", params=params)

            # Remove from cache if present
            if board_id in self._cached_handles:
                del self._cached_handles[board_id]

            return True
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return False
            raise

    def get_board_handle(self, board_id: str | None) -> BoardHandle:
        """
        Get a board handle for performing operations on a board.

        Parameters
        ----------
        board_id : str | None
            The board ID. Use None or "none" for uncategorized board.

        Returns
        -------
        BoardHandle
            Handle for interacting with the board.

        Raises
        ------
        ValueError
            If the board does not exist.

        Examples
        --------
        >>> # Get handle for specific board
        >>> board_handle = board_repo.get_board_handle("board-123")
        >>> images = board_handle.list_images()

        >>> # Get handle for uncategorized board
        >>> uncategorized_handle = board_repo.get_board_handle(None)
        >>> uncategorized_handle.upload_image("new.png")
        """
        # Normalize board_id
        if board_id is None or board_id == "none":
            board_id = "none"

        # Check cache first
        if board_id in self._cached_handles:
            # Refresh the board info to ensure it's current
            self._cached_handles[board_id].refresh()
            return self._cached_handles[board_id]

        # Get the board
        board = self.get_board_by_id(board_id)
        if board is None:
            raise ValueError(f"Board not found: {board_id}")

        # Create and cache the handle
        handle = BoardHandle(self._client, board)
        self._cached_handles[board_id] = handle
        return handle

    def get_board_handle_by_name(self, name: str) -> BoardHandle | None:
        """
        Get a board handle by board name.

        If multiple boards have the same name, returns the first one.

        Parameters
        ----------
        name : str
            The board name to search for.

        Returns
        -------
        BoardHandle | None
            Handle for the board if found, None otherwise.

        Examples
        --------
        >>> board_handle = board_repo.get_board_handle_by_name("My Project")
        >>> if board_handle:
        ...     board_handle.upload_image("project.png")
        """
        boards = self.get_boards_by_name(name)
        if boards:
            return self.get_board_handle(boards[0].board_id)
        return None

    def get_uncategorized_board(self) -> Board:
        """
        Get the uncategorized board.

        The uncategorized board is a special system-managed board that
        contains all images not assigned to any specific board.

        Returns
        -------
        Board
            The uncategorized board object.

        Examples
        --------
        >>> uncategorized = board_repo.get_uncategorized_board()
        >>> print(f"Uncategorized images: {uncategorized.image_count}")
        """
        # Derive image count for uncategorized (sentinel id 'none') by listing image names
        count = 0
        try:
            resp = self._client._make_request("GET", "/boards/none/image_names")
            data = resp.json()
            if isinstance(data, list):
                count = len(data)
        except requests.HTTPError:
            pass
        return Board.uncategorized(image_count=count)

    def get_uncategorized_handle(self) -> BoardHandle:
        """
        Get a handle for the uncategorized board.

        Convenience method for getting the uncategorized board handle.

        Returns
        -------
        BoardHandle
            Handle for the uncategorized board.

        Examples
        --------
        >>> uncategorized = board_repo.get_uncategorized_handle()
        >>> images = uncategorized.list_images()
        """
        return self.get_board_handle("none")

    def clear_cache(self) -> None:
        """
        Clear the cached board handles.

        This forces fresh board data to be fetched on next access.

        Examples
        --------
        >>> board_repo.clear_cache()
        """
        self._cached_handles.clear()

    def get_image_by_name(self, image_name: str) -> IvkImage | None:
        """
        Fetch image metadata by image name.

        Parameters
        ----------
        image_name : str
            The server-side image identifier (e.g., 'abc-123.png').

        Returns
        -------
        IvkImage | None
            The image metadata if found, otherwise None.

        Notes
        -----
        Uses GET /images/i/{image_name}. Returns None on 404.
        """
        try:
            resp = self._client._make_request("GET", f"/images/i/{image_name}")
            data = resp.json()
            return IvkImage.from_api_response(data)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def get_image_current_board_id(self, image_name: str) -> str | None:
        """
        Get the current board_id associated with an image.

        Parameters
        ----------
        image_name : str
            The image identifier.

        Returns
        -------
        str | None
            The board_id if associated, or None if uncategorized or not found.
        """
        img = self.get_image_by_name(image_name)
        return None if img is None else img.board_id

    def move_image_to_board_by_name(self, image_name: str, target_board_name: str) -> bool:
        """
        Move an image to a target board by board name, creating the board if necessary.

        Parameters
        ----------
        image_name : str
            The image identifier to move.
        target_board_name : str
            The destination board's name.

        Returns
        -------
        bool
            True if moved successfully; False if the image was not found or move failed.
        """
        # Resolve or create the board handle
        handle = self.get_board_handle_by_name(target_board_name)
        if handle is None:
            handle = self.create_board(target_board_name)

        # Determine current board handle for performing the move
        # If image has an associated board_id, use that; otherwise use uncategorized
        current_board_id = self.get_image_current_board_id(image_name)
        try:
            source_handle = self.get_board_handle(current_board_id or "none")
        except ValueError:
            # If current board not found, fallback to uncategorized sentinel
            source_handle = self.get_uncategorized_handle()

        # Execute move
        return source_handle.move_image_to(image_name, handle.board_id)

    def update_board(
        self, board_id: str, name: str | None = None, is_private: bool | None = None
    ) -> Board | None:
        """
        Update board properties.

        Parameters
        ----------
        board_id : str
            The board ID to update.
        name : str, optional
            New name for the board.
        is_private : bool, optional
            New privacy setting.

        Returns
        -------
        Board | None
            Updated board object if successful, None if board not found.

        Examples
        --------
        >>> updated = board_repo.update_board("board-123", name="New Name")
        >>> if updated:
        ...     print(f"Updated: {updated.board_name}")
        """
        if board_id == "none" or board_id is None:
            raise ValueError("Cannot update the uncategorized board")

        data: dict[str, Any] = {}
        if name is not None:
            data["board_name"] = name
        if is_private is not None:
            data["is_private"] = is_private

        if not data:
            # Nothing to update
            return self.get_board_by_id(board_id)

        try:
            response = self._client._make_request(
                "PATCH", f"/boards/{board_id}", json=data
            )
            board = Board(**response.json())

            # Update cached handle if present
            if board_id in self._cached_handles:
                self._cached_handles[board_id].board = board

            return board
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def __repr__(self) -> str:
        """String representation of the board repository."""
        return f"BoardRepository(client={self._client.base_url})"
