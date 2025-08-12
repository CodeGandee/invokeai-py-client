"""Custom exceptions for the InvokeAI Python client.

These exceptions model common failure modes when using the client API to
communicate with an InvokeAI instance.

Notes
-----
This module contains simple exception types only; they do not depend on any
external libraries.
"""

from __future__ import annotations


class InvokeAIClientError(Exception):
    """Base class for all client errors.

    This is the root of the client's exception hierarchy. Catch this to
    handle any error raised by this package.
    """


class InvokeAIConnectionError(InvokeAIClientError):
    """Connection-level error (e.g., network failures, timeouts).

    Typically raised when the client cannot reach the InvokeAI server.
    """


class InvokeAIRequestError(InvokeAIClientError):
    """HTTP/API request error.

    Raised when the server returns an error response or when a request is
    malformed.
    """


class InvokeAIWorkflowError(InvokeAIClientError):
    """Workflow-related error.

    Raised for invalid workflow definitions, missing required inputs, or
    other workflow lifecycle issues.
    """


class InvokeAIValidationError(InvokeAIClientError):
    """Client-side validation error.

    Raised when provided input values do not conform to expected types or
    constraints.
    """
