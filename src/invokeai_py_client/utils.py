"""Utility functions for the InvokeAI Python client.

This module provides utility functions for type narrowing, validation,
and common operations used throughout the client library.
"""

from typing import Any, Dict, List, Union, cast
from typing_extensions import TypeAlias, TypeGuard

from .types_extra import APIResponse

# Type narrowing functions for API responses
def is_dict_response(response: APIResponse) -> TypeGuard[Dict[str, Any]]:
    """Type guard to check if response is a dictionary."""
    return isinstance(response, dict)


def is_list_response(response: APIResponse) -> TypeGuard[List[Any]]:
    """Type guard to check if response is a list."""
    return isinstance(response, list)


def is_string_response(response: APIResponse) -> TypeGuard[str]:
    """Type guard to check if response is a string."""
    return isinstance(response, str)


def is_bytes_response(response: APIResponse) -> TypeGuard[bytes]:
    """Type guard to check if response is bytes."""
    return isinstance(response, bytes)


def ensure_dict_response(response: APIResponse, path: str) -> Dict[str, Any]:
    """Ensure response is a dictionary, raise error if not.
    
    Parameters
    ----------
    response : APIResponse
        The API response to check.
    path : str
        The API path for error reporting.
    
    Returns
    -------
    Dict[str, Any]
        The response as a dictionary.
    
    Raises
    ------
    ValueError
        If response is not a dictionary.
    """
    if not is_dict_response(response):
        raise ValueError(f"Expected dict response from {path}, got {type(response)}")
    return response


def ensure_list_response(response: APIResponse, path: str) -> List[Any]:
    """Ensure response is a list, raise error if not.
    
    Parameters
    ----------
    response : APIResponse
        The API response to check.
    path : str
        The API path for error reporting.
    
    Returns
    -------
    List[Any]
        The response as a list.
    
    Raises
    ------
    ValueError
        If response is not a list.
    """
    if not is_list_response(response):
        raise ValueError(f"Expected list response from {path}, got {type(response)}")
    return response


def get_dict_value(data: APIResponse, key: str, default: Any = None) -> Any:
    """Safely get a value from a dictionary response.
    
    Parameters
    ----------
    data : APIResponse
        The API response.
    key : str
        The key to get.
    default : Any
        Default value if key not found.
    
    Returns
    -------
    Any
        The value or default.
    """
    if is_dict_response(data):
        return data.get(key, default)
    return default


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """Merge multiple dictionaries into one.
    
    Parameters
    ----------
    *dicts : Dict[str, Any]
        Dictionaries to merge.
    
    Returns
    -------
    Dict[str, Any]
        Merged dictionary.
    """
    result: Dict[str, Any] = {}
    for d in dicts:
        result.update(d)
    return result