"""Minimal HTTP transport abstraction for the client API.

This module intentionally avoids committing to a specific HTTP library.
Implementations may use ``requests``, ``httpx``, or the stdlib. The default
"transport" here is a synchronous, placeholder interface.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .exceptions import InvokeAIConnectionError, InvokeAIRequestError


class HttpTransport:
    """Abstract HTTP transport interface.

    Parameters
    ----------
    base_url : str
        Base URL of the InvokeAI server, e.g., ``"http://localhost:9090"``.
    timeout : float, optional
        Request timeout in seconds.

    Notes
    -----
    This is a placeholder. Replace with a concrete implementation as needed.
    """

    def __init__(self, base_url: str, timeout: Optional[float] = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout or 30.0

    # The following are stubs to be implemented with a real HTTP client

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform a GET request.

        Parameters
        ----------
        path : str
            The request path appended to ``base_url``.
        params : dict, optional
            Query parameters.

        Returns
        -------
        dict
            Parsed JSON response.
        """

        raise InvokeAIConnectionError("HttpTransport.get not implemented")

    def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform a POST request.

        Parameters
        ----------
        path : str
            The request path appended to ``base_url``.
        json : dict, optional
            JSON body to send.

        Returns
        -------
        dict
            Parsed JSON response.
        """

        raise InvokeAIConnectionError("HttpTransport.post not implemented")

    def upload(self, path: str, data: bytes, filename: str, content_type: str = "application/octet-stream") -> Dict[str, Any]:
        """Upload binary data (e.g., image) using multipart or raw upload.

        Parameters
        ----------
        path : str
            The request path appended to ``base_url``.
        data : bytes
            The binary data to send.
        filename : str
            Suggested filename for the server.
        content_type : str, optional
            MIME type of the data.

        Returns
        -------
        dict
            Parsed JSON response.
        """

        raise InvokeAIConnectionError("HttpTransport.upload not implemented")
