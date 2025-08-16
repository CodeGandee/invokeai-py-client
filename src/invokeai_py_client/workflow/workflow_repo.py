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
                if auto_fix:
                    definition = self._attempt_fixes(definition, errors)
                    # Re-validate after fixes
                    remaining_errors = self.validate_workflow_definition(definition)
                    if remaining_errors:
                        raise ValueError(
                            f"Could not fix all workflow issues: {'; '.join(remaining_errors)}"
                        )
                else:
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

        # Check for obsolete nodes
        if definition.has_obsolete_nodes():
            errors.append("Workflow contains obsolete node types")

        # Check model availability
        model_errors = self._check_model_availability(definition)
        errors.extend(model_errors)

        # Check for version compatibility
        version = definition.version
        if version and not self._is_version_compatible(version):
            errors.append(f"Workflow version {version} may not be fully compatible")

        return errors

    def _check_model_availability(self, definition: WorkflowDefinition) -> list[str]:
        """
        Check if models referenced in the workflow are available.

        Parameters
        ----------
        definition : WorkflowDefinition
            The workflow definition to check.

        Returns
        -------
        List[str]
            List of model-related errors.
        """
        errors: list[str] = []

        # This is a placeholder - actual implementation would:
        # 1. Extract model references from nodes
        # 2. Query the InvokeAI instance for available models
        # 3. Check if each referenced model exists

        # For now, we'll just check for model loader nodes
        model_loaders = definition.get_nodes_by_type("sdxl_model_loader")
        model_loaders.extend(definition.get_nodes_by_type("flux_model_loader"))

        # In a real implementation, we'd check each model's availability
        # via the API and report missing ones

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

    def _attempt_fixes(
        self, definition: WorkflowDefinition, errors: list[str]
    ) -> WorkflowDefinition:
        """
        Attempt to fix common workflow issues.

        Parameters
        ----------
        definition : WorkflowDefinition
            The workflow definition to fix.
        errors : List[str]
            The validation errors to address.

        Returns
        -------
        WorkflowDefinition
            The fixed workflow definition.
        """
        # Create a working copy
        data = definition.to_dict()
        modified = False

        # Fix obsolete nodes if present
        if any("obsolete" in error.lower() for error in errors):
            data, nodes_fixed = self._fix_obsolete_nodes(data)
            modified = modified or nodes_fixed

        # Fix missing models if present
        if any("model" in error.lower() for error in errors):
            data, models_fixed = self._fix_missing_models(data)
            modified = modified or models_fixed

        # Return modified definition if changes were made
        if modified:
            return WorkflowDefinition.from_dict(data)

        return definition

    def _fix_obsolete_nodes(self, data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """
        Fix obsolete nodes in workflow data.

        Parameters
        ----------
        data : Dict[str, Any]
            The workflow data to fix.

        Returns
        -------
        tuple[Dict[str, Any], bool]
            Fixed data and whether any changes were made.
        """
        # This is a placeholder - actual implementation would:
        # 1. Identify obsolete node types
        # 2. Replace with modern equivalents
        # 3. Update connections as needed

        return data, False

    def _fix_missing_models(self, data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """
        Fix missing model references in workflow data.

        Parameters
        ----------
        data : Dict[str, Any]
            The workflow data to fix.

        Returns
        -------
        tuple[Dict[str, Any], bool]
            Fixed data and whether any changes were made.
        """
        # This is a placeholder - actual implementation would:
        # 1. Find model references in nodes
        # 2. Query available models via API
        # 3. Replace missing models with available alternatives
        # 4. Or clear the model field to require user input

        return data, False

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
