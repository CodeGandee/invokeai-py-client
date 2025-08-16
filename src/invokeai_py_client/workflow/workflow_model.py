"""
Workflow definition data model for InvokeAI workflows.

This module provides the WorkflowDefinition class which represents a workflow
loaded from a JSON file exported from the InvokeAI GUI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowDefinition(BaseModel):
    """
    Represents a workflow definition loaded from a JSON file.

    This is a flexible data model that can handle any workflow exported from
    the InvokeAI GUI. Currently treats the workflow JSON as a dict without
    requiring specific field definitions, allowing for compatibility with
    different workflow versions and structures.

    Attributes
    ----------
    name : str
        The workflow name (from 'name' field).
    description : str
        The workflow description (from 'description' field).
    version : str
        The workflow schema version (from 'meta.version' field).
    author : str
        The workflow author (from 'author' field).
    contact : str
        Contact information for the workflow author.
    tags : List[str]
        Tags categorizing the workflow.
    notes : str
        Additional notes about the workflow.
    nodes : List[Dict[str, Any]]
        List of workflow nodes with their configurations.
    edges : List[Dict[str, Any]]
        List of connections between nodes.
    form : Dict[str, Any]
        Form structure defining the workflow inputs UI.
    exposedFields : List[Dict[str, Any]]
        Fields exposed for configuration.
    meta : Dict[str, Any]
        Metadata including version and other properties.
    raw_data : Dict[str, Any]
        The complete raw workflow JSON data.

    Examples
    --------
    >>> # Load from file
    >>> workflow_def = WorkflowDefinition.from_file("workflow.json")
    >>> print(workflow_def.name)

    >>> # Load from dict
    >>> with open("workflow.json") as f:
    ...     data = json.load(f)
    >>> workflow_def = WorkflowDefinition.from_dict(data)
    """

    model_config = ConfigDict(extra="allow", validate_assignment=True)

    # Core metadata fields
    name: str = Field(default="Untitled Workflow", description="Workflow name")
    description: str = Field(default="", description="Workflow description")
    author: str = Field(default="", description="Workflow author")
    contact: str = Field(default="", description="Contact information")
    tags: str | list[str] = Field(default_factory=list, description="Workflow tags")
    notes: str = Field(default="", description="Additional notes")

    # Structure fields - using Dict[str, Any] for flexibility
    nodes: list[dict[str, Any]] = Field(
        default_factory=list, description="Workflow nodes"
    )
    edges: list[dict[str, Any]] = Field(
        default_factory=list, description="Node connections"
    )
    form: dict[str, Any] = Field(default_factory=dict, description="Form UI structure")
    exposedFields: list[dict[str, Any]] = Field(
        default_factory=list,
        alias="exposedFields",
        description="Exposed configurable fields",
    )
    meta: dict[str, Any] = Field(default_factory=dict, description="Workflow metadata")

    # Store the complete raw data for access to any additional fields
    raw_data: dict[str, Any] = Field(default_factory=dict, exclude=True)

    @property
    def version(self) -> str:
        """Get the workflow schema version from meta.version."""
        version = self.meta.get("version", "unknown")
        return str(version) if version else "unknown"

    @property
    def node_count(self) -> int:
        """Get the number of nodes in the workflow."""
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Get the number of edges (connections) in the workflow."""
        return len(self.edges)

    @property
    def exposed_field_count(self) -> int:
        """Get the number of exposed configurable fields."""
        return len(self.exposedFields)

    @classmethod
    def from_file(cls, filepath: Path | str) -> WorkflowDefinition:
        """
        Load a workflow definition from a JSON file.

        Parameters
        ----------
        filepath : Path | str
            Path to the workflow JSON file.

        Returns
        -------
        WorkflowDefinition
            The loaded workflow definition.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        json.JSONDecodeError
            If the file is not valid JSON.
        ValueError
            If the JSON structure is invalid.

        Examples
        --------
        >>> workflow_def = WorkflowDefinition.from_file("workflow.json")
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Workflow file not found: {filepath}")

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in workflow file: {e}") from e

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowDefinition:
        """
        Create a workflow definition from a dictionary.

        Parameters
        ----------
        data : Dict[str, Any]
            Workflow data as a dictionary.

        Returns
        -------
        WorkflowDefinition
            The created workflow definition.

        Raises
        ------
        ValueError
            If the data structure is invalid.

        Examples
        --------
        >>> with open("workflow.json") as f:
        ...     data = json.load(f)
        >>> workflow_def = WorkflowDefinition.from_dict(data)
        """
        # Store the raw data
        workflow_data = data.copy()
        workflow_data["raw_data"] = data.copy()

        # Handle tags field - can be string or list
        if "tags" in workflow_data and isinstance(workflow_data["tags"], str):
            # Split comma-separated string into list
            workflow_data["tags"] = [t.strip() for t in workflow_data["tags"].split(",")]

        # Create the instance with all data
        return cls(**workflow_data)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the workflow definition back to a dictionary.

        This returns the original raw data if available, otherwise
        reconstructs from the model fields.

        Returns
        -------
        Dict[str, Any]
            The workflow as a dictionary.
        """
        if self.raw_data:
            return self.raw_data.copy()

        # Reconstruct from fields if raw_data not available
        return self.model_dump(exclude={"raw_data"}, by_alias=True)

    def to_json(self, indent: int = 2) -> str:
        """
        Convert the workflow definition to a JSON string.

        Parameters
        ----------
        indent : int
            Number of spaces for indentation.

        Returns
        -------
        str
            The workflow as a JSON string.
        """
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, filepath: Path | str) -> None:
        """
        Save the workflow definition to a JSON file.

        Parameters
        ----------
        filepath : Path | str
            Path where the workflow should be saved.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    def validate_workflow(self) -> list[str]:
        """
        Validate the workflow structure.

        Returns
        -------
        List[str]
            List of validation error messages. Empty list means valid.
        """
        errors = []

        # Check required structures
        if not self.nodes:
            errors.append("Workflow has no nodes")

        # Check version
        if not self.version or self.version == "unknown":
            errors.append("Workflow version is missing or unknown")

        # Check that edges reference valid nodes
        node_ids = {node.get("id") for node in self.nodes if node.get("id")}
        for edge in self.edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and source not in node_ids:
                errors.append(f"Edge references unknown source node: {source}")
            if target and target not in node_ids:
                errors.append(f"Edge references unknown target node: {target}")

        # Check exposed fields reference valid nodes
        for field in self.exposedFields:
            node_id = field.get("nodeId")
            if node_id and node_id not in node_ids:
                errors.append(f"Exposed field references unknown node: {node_id}")

        return errors

    def get_node_by_id(self, node_id: str) -> dict[str, Any] | None:
        """
        Get a node by its ID.

        Parameters
        ----------
        node_id : str
            The node ID to find.

        Returns
        -------
        Optional[Dict[str, Any]]
            The node data if found, None otherwise.
        """
        for node in self.nodes:
            if node.get("id") == node_id:
                return node
        return None

    def get_nodes_by_type(self, node_type: str) -> list[dict[str, Any]]:
        """
        Get all nodes of a specific type.

        Parameters
        ----------
        node_type : str
            The node type to find.

        Returns
        -------
        List[Dict[str, Any]]
            List of nodes matching the type.
        """
        matching_nodes = []
        for node in self.nodes:
            data = node.get("data", {})
            if data.get("type") == node_type:
                matching_nodes.append(node)
        return matching_nodes

    def has_obsolete_nodes(self) -> bool:
        """
        Check if the workflow contains obsolete node types.

        This is a placeholder that can be extended with actual
        obsolete node detection logic.

        Returns
        -------
        bool
            True if obsolete nodes are detected.
        """
        # This would check against a list of known obsolete node types
        # For now, return False as we don't have the list yet
        return False

    def __repr__(self) -> str:
        """String representation of the workflow definition."""
        return (
            f"WorkflowDefinition(name='{self.name}', "
            f"version='{self.version}', "
            f"nodes={self.node_count}, "
            f"edges={self.edge_count})"
        )
