"""Client workflow abstraction ("client-workflow").

This object wraps a workflow definition JSON exported from the InvokeAI GUI.
It exposes typed inputs, supports setting values by name, and submits jobs to
an InvokeAI instance via the ``InvokeAIClient``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .exceptions import InvokeAIValidationError, InvokeAIWorkflowError
from . import types as t
from .models import JobInfo


class InvokeAIWorkflow:
    """A client-side representation of a workflow.

    Parameters
    ----------
    client : Any
        Reference to the owning ``InvokeAIClient``. Typed as ``Any`` to avoid
        circular imports in stubs.
    workflow_def : Dict[str, Any]
        Parsed JSON dict of the workflow definition.

    Notes
    -----
    - Inputs are defined by the workflow's ``form`` section, and are strongly
      typed by InvokeAI. This class models them as ``types.BaseField``
      subclasses and supports setting values by input name.
    - This is a stub and does not perform real server calls.
    """

    def __init__(self, client: Any, workflow_def: Dict[str, Any]) -> None:
        self._client = client
        self._def = workflow_def
        self._inputs: Dict[str, t.BaseField] = {}
        self._parse_form_inputs()

    # Construction helpers

    @classmethod
    def from_file(cls, client: Any, path: str | Path) -> "InvokeAIWorkflow":
        """Create a workflow from a JSON file.

        Parameters
        ----------
        client : Any
            An ``InvokeAIClient`` instance.
        path : str or Path
            Path to a workflow JSON exported from the InvokeAI GUI.

        Returns
        -------
        InvokeAIWorkflow
            A new workflow instance.
        """

        import json

        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls(client, data)

    # Inputs API

    def input_names(self) -> Iterable[str]:
        """Return the names of available workflow inputs.

        Returns
        -------
        Iterable[str]
            A collection of input names.
        """

        return self._inputs.keys()

    def set_input(self, name: str, value: Any) -> None:
        """Set a workflow input by name with type validation.

        Parameters
        ----------
        name : str
            The input name as defined in the workflow's ``form``.
        value : Any
            The value to assign. Must match the expected type.

        Raises
        ------
        InvokeAIValidationError
            If the input name is unknown or value type mismatches the field.
        """

        field = self._inputs.get(name)
        if field is None:
            raise InvokeAIValidationError(f"Unknown workflow input: {name}")
        field.set(value)

    def get_input(self, name: str) -> Any:
        """Get the current value of a workflow input by name."""

        field = self._inputs.get(name)
        if field is None:
            raise InvokeAIValidationError(f"Unknown workflow input: {name}")
        return field.get()

    # Submission API (stubs)

    def submit(self) -> JobInfo:
        """Submit the workflow for execution.

        Returns
        -------
        JobInfo
            Placeholder job info. Real implementation will call the server via
            ``InvokeAIClient`` and return the created job's metadata.
        """

        return self._client._submit_workflow(self)  # type: ignore[attr-defined]

    # Internal helpers

    def _parse_form_inputs(self) -> None:
        """Parse the workflow definition and populate ``_inputs``.

        Notes
        -----
        - This is a light stub that attempts to inspect a simplified form
          structure. During real implementation, adapt this to the exact
          workflow JSON layout from InvokeAI.
        """

        # Expected simplified structure (example):
        # workflow["form"] = [ {"name": "height", "type": "integer"}, ... ]
        form = self._def.get("form")
        if not isinstance(form, list):
            return
        for item in form:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            type_name = item.get("type")
            if not isinstance(name, str) or not isinstance(type_name, str):
                continue
            field = self._make_field(type_name, name)
            if field is not None:
                self._inputs[name] = field

    def _make_field(self, type_name: str, name: str) -> Optional[t.BaseField]:
        """Create a field instance from a primitive type name.

        Parameters
        ----------
        type_name : str
            Primitive type from the workflow (e.g., ``"integer"``).
        name : str
            Field name.

        Returns
        -------
        Optional[BaseField]
            A field instance or ``None`` if the type is unknown.
        """

        mapping = {
            "integer": t.InvokeAIIntegerField,
            "float": t.InvokeAIFloatField,
            "string": t.InvokeAIStringField,
            "boolean": t.InvokeAIBooleanField,
            "image": t.InvokeAIImageRefField,
        }
        cls = mapping.get(type_name.lower())
        return cls(name=name) if cls else None
