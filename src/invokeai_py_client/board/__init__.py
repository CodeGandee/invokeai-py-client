"""
Board subsystem for InvokeAI client using repository pattern.

This package provides board management functionality following the repository pattern:
- Board: Data model representing a board
- BoardRepository: Manages board lifecycle and creates BoardHandle instances
- BoardHandle: Represents the running state of a board, handles image operations
"""

from invokeai_py_client.board.board_handle import BoardHandle
from invokeai_py_client.board.board_model import Board
from invokeai_py_client.board.board_repo import BoardRepository

__all__ = ["Board", "BoardRepository", "BoardHandle"]
