"""Top-level client for interacting with an InvokeAI instance ("invokeai-client").

This client manages high-level operations like listing boards, submitting
workflows, tracking jobs, and uploading/downloading assets.

The implementation here is a stub to establish the public API surface. The
transport layer is abstracted by ``HttpTransport`` and can be implemented
later using ``requests``/``httpx``/stdlib.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional, TYPE_CHECKING

from .exceptions import (
    InvokeAIClientError,
    InvokeAIConnectionError,
    InvokeAIRequestError,
    InvokeAIWorkflowError,
)
from .models import AssetInfo, BoardInfo, JobInfo, JobState
from .transport import HttpTransport

if TYPE_CHECKING:  # pragma: no cover - typing-only import to satisfy linters
    from .workflow import InvokeAIWorkflow


class InvokeAIClient:
    """Client-side representation of a remote InvokeAI instance.

    Parameters
    ----------
    base_url : str
        Base URL of the InvokeAI server, e.g., ``"http://localhost:9090"``.
    timeout : float, optional
        Request timeout in seconds for transport operations.
    transport : HttpTransport, optional
        Custom transport implementation; if not provided, a default stub is
        used.

    Notes
    -----
    The client acts as a factory for ``InvokeAIWorkflow`` instances and
    provides convenience methods around common InvokeAI operations.
    """

    def __init__(self, base_url: str, timeout: Optional[float] = 30.0, transport: Optional[HttpTransport] = None) -> None:
        self._transport = transport or HttpTransport(base_url=base_url, timeout=timeout)

    # --- Boards API (stubs) -------------------------------------------------

    def list_boards(self) -> Iterable[BoardInfo]:
        """List available boards in the InvokeAI instance.

        Returns
        -------
        Iterable[BoardInfo]
            A collection of boards (stubbed).
        """

        # Placeholder; to be implemented with real HTTP calls
        return []

    # --- Assets API (stubs) -------------------------------------------------

    def upload_image(self, data: bytes, filename: str) -> AssetInfo:
        """Upload an image to the server and return its asset reference.

        Parameters
        ----------
        data : bytes
            Image bytes.
        filename : str
            Suggested filename.

        Returns
        -------
        AssetInfo
            Information about the uploaded asset; ``name`` can be used as an
            input reference for workflows.
        """

        # Placeholder; to be implemented with real HTTP calls
        return AssetInfo(name=filename, kind="image")

    # --- Workflow API -------------------------------------------------------

    def load_workflow(self, path: str | Path) -> "InvokeAIWorkflow":
        """Load a workflow JSON exported from the GUI and return a client object.

        Parameters
        ----------
        path : str or Path
            Path to the workflow definition JSON file.

        Returns
        -------
        InvokeAIWorkflow
            A workflow bound to this client instance.
        """

        from .workflow import InvokeAIWorkflow  # local import to avoid cycle

        return InvokeAIWorkflow.from_file(self, path)

    # --- Jobs API (stubs) ---------------------------------------------------

    def get_job(self, job_id: str) -> Optional[JobInfo]:
        """Retrieve job metadata by ID (stub).

        Parameters
        ----------
        job_id : str
            Job identifier.

        Returns
        -------
        Optional[JobInfo]
            Job information if found.
        """

        return None

    def wait_for_job(self, job_id: str, poll_interval: float = 1.0, timeout: Optional[float] = None) -> JobInfo:
        """Poll job status until it completes, fails, or times out (stub).

        Parameters
        ----------
        job_id : str
            Job to wait on.
        poll_interval : float, optional
            Seconds between polls.
        timeout : float, optional
            Maximum seconds to wait; ``None`` means indefinite.

        Returns
        -------
        JobInfo
            Final job state.
        """

        # Placeholder behavior: immediately return completed
        return JobInfo(id=job_id, state=JobState.COMPLETED)

    # --- Internal methods used by InvokeAIWorkflow (stubs) ------------------

    def _submit_workflow(self, workflow: Any) -> JobInfo:
        """Internal hook: called by ``InvokeAIWorkflow.submit``.

        Parameters
        ----------
        workflow : Any
            The workflow instance being submitted.

        Returns
        -------
        JobInfo
            Metadata for the newly created job (stub).
        """

        # In a real implementation, this would serialize the workflow
        # definition and inputs, send to the InvokeAI REST API, and return the
        # created job metadata.
        return JobInfo(id="job-stub", state=JobState.PENDING)
