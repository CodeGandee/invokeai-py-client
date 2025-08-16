"""
Board data model for the InvokeAI board subsystem.

This module provides the Board model which represents a board (album/folder)
for organizing generated images in the InvokeAI system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Board(BaseModel):
    """
    InvokeAI board for organizing generated images.

    Boards are InvokeAI's organizational system for managing generated images,
    similar to folders or albums. They help users organize outputs by project,
    style, or any custom categorization.

    This matches the BoardDTO structure from the InvokeAI API.
    Supports both regular boards and the special "uncategorized" board.

    The uncategorized board is a system-managed board that:
    - Cannot be created or deleted by users
    - Always exists in the system
    - Uses "none" as its board_id in API calls
    - Holds all images not assigned to any board

    Examples
    --------
    >>> board = Board(board_id="abc123", board_name="Landscapes")
    >>> print(f"{board.board_name}: {board.image_count} images")

    >>> uncategorized = Board.uncategorized(image_count=10)
    >>> print(f"Uncategorized: {uncategorized.image_count} images")
    >>> print(f"Is system board: {uncategorized.is_system_board()}")
    """

    board_id: str | None = Field(
        None, description="The unique ID of the board (None for uncategorized)"
    )
    board_name: str | None = Field(
        None, description="The name of the board (None for uncategorized)"
    )
    created_at: datetime | str | None = Field(
        None, description="The created timestamp of the board"
    )
    updated_at: datetime | str | None = Field(
        None, description="The updated timestamp of the board"
    )
    deleted_at: datetime | str | None = Field(
        None, description="The deleted timestamp of the board"
    )
    cover_image_name: str | None = Field(
        None, description="The name of the board's cover image"
    )
    archived: bool = Field(False, description="Whether or not the board is archived")
    is_private: bool | None = Field(None, description="Whether the board is private")
    image_count: int = Field(0, ge=0, description="The number of images in the board")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> Board:
        """
        Create a Board from API response data.

        Parameters
        ----------
        data : Dict[str, Any]
            Raw API response dictionary.

        Returns
        -------
        Board
            Parsed board instance.
        """
        return cls(**data)

    @classmethod
    def uncategorized(cls, image_count: int = 0) -> Board:
        """
        Create a special uncategorized board instance.

        The uncategorized board represents images not assigned to any board.

        Important: We use the string "none" as board_id rather than Python's None
        because:
        - InvokeAI API expects the literal string "none" in URL paths
        - API endpoint: /api/v1/boards/none/image_names requires "none" as a path parameter
        - Python's None would serialize to null in JSON, which cannot be used in URL paths
        - "none" is InvokeAI's established convention for uncategorized items

        Parameters
        ----------
        image_count : int
            Number of uncategorized images.

        Returns
        -------
        Board
            Uncategorized board instance with board_id="none".
        """
        from datetime import datetime

        now = datetime.now().isoformat()
        return cls(
            board_id="none",
            board_name="Uncategorized",
            created_at=now,
            updated_at=now,
            deleted_at=None,
            cover_image_name=None,
            image_count=image_count,
            archived=False,
            is_private=False,
        )

    def is_uncategorized(self) -> bool:
        """
        Check if this is the uncategorized board.

        We check for both "none" (the API convention) and Python's None
        (for edge cases) to handle different scenarios:
        - board_id == "none": Standard uncategorized board from API
        - board_id is None: Fallback for edge cases or uninitialized boards

        Returns
        -------
        bool
            True if this is the uncategorized board.
        """
        return self.board_id == "none" or self.board_id is None

    def is_system_board(self) -> bool:
        """
        Check if this is a system-managed board.

        System boards cannot be created or deleted by users.
        Currently only the uncategorized board is a system board.

        Returns
        -------
        bool
            True if this is a system-managed board.
        """
        return self.is_uncategorized()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns
        -------
        Dict[str, Any]
            Board data as dictionary.
        """
        return self.model_dump(exclude_none=True)
