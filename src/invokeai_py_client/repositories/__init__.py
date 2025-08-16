"""
InvokeAI Python Client Repositories.

This module contains repository classes that provide model-specific operations
following the Repository pattern for clean separation of concerns.
"""

# New board subsystem using repository pattern
# Legacy board repository (deprecated - use BoardRepository from board_repo instead)
from invokeai_py_client.repositories.board import (
    BoardRepository as LegacyBoardRepository,
)
from invokeai_py_client.repositories.board_handle import BoardHandle
from invokeai_py_client.repositories.board_repo import BoardRepository

__all__ = ["BoardRepository", "BoardHandle", "LegacyBoardRepository"]
