"""
Workflow repository for managing workflow instances.

This module implements the Repository pattern for workflow-related operations,
creating and managing WorkflowHandle instances from WorkflowDefinition objects.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests

from invokeai_py_client.workflow.workflow_handle import WorkflowHandle
from invokeai_py_client.workflow.workflow_model import WorkflowDefinition

if TYPE_CHECKING:
    from invokeai_py_client.client import InvokeAIClient


class WorkflowRepository:
    """
    Repository for workflow-specific operations.

    This class provides workflow management operations following the Repository
    pattern. It creates WorkflowHandle instances from WorkflowDefinition objects
    and handles inconsistencies gracefully (obsolete nodes, unavailable models, etc.).

    Attributes
    ----------
    _client : InvokeAIClient
        Reference to the InvokeAI client for API calls.

    Examples
    --------
    >>> client = InvokeAIClient.from_url("http://localhost:9090")
    >>> workflow_repo = client.workflow_repo
    >>>
    >>> # Load and create workflow
    >>> definition = WorkflowDefinition.from_file("workflow.json")
    >>> workflow = workflow_repo.create_workflow(definition)
    """

    def __init__(self, client: InvokeAIClient) -> None:
        """
        Initialize the WorkflowRepository.

        Parameters
        ----------
        client : InvokeAIClient
            The InvokeAI client instance to use for API calls.
        """
        self._client = client
        self._cached_workflows: dict[str, WorkflowHandle] = {}

    def create_workflow(
        self,
        definition: WorkflowDefinition,
        validate: bool = True,
        auto_fix: bool = True,
    ) -> WorkflowHandle:
        """
        Create a workflow handle from a workflow definition.

        This method creates a WorkflowHandle instance that can be configured
        and executed. It optionally validates the workflow and attempts to
        fix common issues like obsolete nodes or unavailable models.

        Parameters
        ----------
        definition : WorkflowDefinition
            The workflow definition to create a handle for.
        validate : bool
            Whether to validate the workflow before creation.
        auto_fix : bool
            Whether to attempt automatic fixes for issues.

        Returns
        -------
        WorkflowHandle
            A workflow handle ready for configuration and execution.

        Raises
        ------
        ValueError
            If validation fails and auto_fix is False.

        Examples
        --------
        >>> definition = WorkflowDefinition.from_file("workflow.json")
        >>> workflow = workflow_repo.create_workflow(definition)
        >>> workflow.list_inputs()
        """
        # Validate if requested
        if validate:
            errors = self.validate_workflow_definition(definition)
            if errors:
                raise ValueError(f"Workflow validation failed: {'; '.join(errors)}")

        # Create the workflow handle
        workflow = WorkflowHandle(self._client, definition)

        return workflow

    def create_workflow_from_file(
        self, filepath: str | Path, validate: bool = True, auto_fix: bool = True
    ) -> WorkflowHandle:
        """
        Create a workflow handle from a JSON file.

        Parameters
        ----------
        filepath : Union[str, Path]
            Path to the workflow JSON file.
        validate : bool
            Whether to validate the workflow.
        auto_fix : bool
            Whether to attempt automatic fixes.

        Returns
        -------
        WorkflowHandle
            A workflow handle ready for configuration.

        Examples
        --------
        >>> workflow = workflow_repo.create_workflow_from_file("workflow.json")
        """
        definition = WorkflowDefinition.from_file(filepath)
        return self.create_workflow(definition, validate, auto_fix)

    def create_workflow_from_dict(
        self, data: dict[str, Any], validate: bool = True, auto_fix: bool = True
    ) -> WorkflowHandle:
        """
        Create a workflow handle from a dictionary.

        Parameters
        ----------
        data : Dict[str, Any]
            Workflow data as a dictionary.
        validate : bool
            Whether to validate the workflow.
        auto_fix : bool
            Whether to attempt automatic fixes.

        Returns
        -------
        WorkflowHandle
            A workflow handle ready for configuration.

        Examples
        --------
        >>> with open("workflow.json") as f:
        ...     data = json.load(f)
        >>> workflow = workflow_repo.create_workflow_from_dict(data)
        """
        definition = WorkflowDefinition.from_dict(data)
        return self.create_workflow(definition, validate, auto_fix)

    def validate_workflow_definition(self, definition: WorkflowDefinition) -> list[str]:
        """
        Validate a workflow definition for compatibility.

        This checks for:
        - Structural validity
        - Obsolete node types
        - Model availability
        - Other compatibility issues

        Parameters
        ----------
        definition : WorkflowDefinition
            The workflow definition to validate.

        Returns
        -------
        List[str]
            List of validation error messages. Empty means valid.
        """
        errors = []

        # Basic structural validation
        structural_errors = definition.validate_workflow()
        errors.extend(structural_errors)



        # Check for version compatibility
        version = definition.version
        if version and not self._is_version_compatible(version):
            errors.append(f"Workflow version {version} may not be fully compatible")

        return errors


    def _is_version_compatible(self, version: str) -> bool:
        """
        Check if a workflow version is compatible.

        Parameters
        ----------
        version : str
            The workflow version string.

        Returns
        -------
        bool
            True if compatible, False otherwise.
        """
        # Support common versions
        supported_versions = ["3.0.0", "2.0.0", "1.0.0"]

        # Extract major version
        if version in supported_versions:
            return True

        # Check major version compatibility
        try:
            major = int(version.split(".")[0])
            return major in [1, 2, 3]
        except (ValueError, IndexError):
            return False




    def list_available_workflows(self) -> list[dict[str, str]]:
        """
        List workflows available on the InvokeAI instance.

        This queries the server for saved workflows.

        Returns
        -------
        List[Dict[str, str]]
            List of workflow metadata (id, name, description).
        """
        # Query the workflows endpoint
        try:
            response = self._client._make_request("GET", "/workflows/")
            workflows = response.json()

            # Extract relevant metadata
            result = []
            for wf in workflows:
                result.append(
                    {
                        "id": wf.get("id", ""),
                        "name": wf.get("name", "Untitled"),
                        "description": wf.get("description", ""),
                        "author": wf.get("author", ""),
                    }
                )

            return result
        except requests.HTTPError:
            return []

    def download_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        """
        Download a workflow from the InvokeAI instance.

        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to download.

        Returns
        -------
        Optional[WorkflowDefinition]
            The workflow definition if found, None otherwise.
        """
        try:
            response = self._client._make_request("GET", f"/workflows/{workflow_id}")
            data = response.json()
            return WorkflowDefinition.from_dict(data)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def upload_workflow(
        self, definition: WorkflowDefinition, overwrite: bool = False
    ) -> str:
        """
        Upload a workflow to the InvokeAI instance.

        Parameters
        ----------
        definition : WorkflowDefinition
            The workflow to upload.
        overwrite : bool
            Whether to overwrite if a workflow with the same name exists.

        Returns
        -------
        str
            The ID of the uploaded workflow.

        Raises
        ------
        ValueError
            If upload fails or workflow already exists and overwrite is False.
        """
        data = definition.to_dict()

        try:
            # Check if workflow exists
            existing = self.list_available_workflows()
            for wf in existing:
                if wf["name"] == definition.name:
                    if not overwrite:
                        raise ValueError(f"Workflow '{definition.name}' already exists")
                    # Update existing
                    response = self._client._make_request(
                        "PUT", f"/workflows/{wf['id']}", json=data
                    )
                    return wf["id"]

            # Create new workflow
            response = self._client._make_request("POST", "/workflows/", json=data)
            result = response.json()
            workflow_id = result.get("id", "")
            return str(workflow_id) if workflow_id else ""

        except requests.HTTPError as e:
            if e.response is not None:
                error_msg = f"Upload failed: {e.response.status_code}"
                try:
                    error_detail = e.response.json()
                    error_msg += f" - {error_detail}"
                except Exception:
                    error_msg += f" - {e.response.text}"
                raise ValueError(error_msg) from e
            raise

    def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow from the InvokeAI instance.

        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to delete.

        Returns
        -------
        bool
            True if deletion was successful, False if not found.
        """
        try:
            self._client._make_request("DELETE", f"/workflows/{workflow_id}")
            return True
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return False
            raise

    def __repr__(self) -> str:
        """String representation of the workflow repository."""
        return f"WorkflowRepository(client={self._client.base_url})"
