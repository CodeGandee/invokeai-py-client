"""Upstream-Compatible InvokeAI Workflow Data Models.

Purpose
-------
Provide a *complete* (best‑effort) Pydantic representation of the InvokeAI
workflow JSON format (nodes, edges, form) so we can:
  * Load workflow JSON into strongly typed models.
  * Manipulate / introspect using attribute access instead of fragile dict ops.
  * Re‑extract / regenerate models if upstream format evolves.
  * Preserve unknown fields to maintain forward compatibility.

Design Principles
-----------------
1. Non‑blocking: Do not break if new fields appear (``model_config = extra='allow'``).
2. Minimal required fields only; optional for everything else.
3. Use enums sparingly; many upstream "type" fields are free‑form.
4. Provide helper utilities to:
   - Enumerate exposed form inputs.
   - Enumerate output‑capable nodes (board field exposed or WithBoard types).
   - Build JSONPath expressions replicating current partial system.
5. Keep this module orthogonal; existing `workflow_handle` remains unchanged until migration.

DISCLAIMER: This is a pragmatic snapshot, not an authoritative schema.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict

# ---------------------------------------------------------------------------
# Core Graph Models
# ---------------------------------------------------------------------------

class WorkflowEdgeEndpoint(BaseModel):
    model_config = ConfigDict(extra='allow')
    node_id: str = Field(..., alias='node_id')
    field: Optional[str] = None

class WorkflowEdge(BaseModel):
    model_config = ConfigDict(extra='allow')
    source: WorkflowEdgeEndpoint
    destination: WorkflowEdgeEndpoint

class WorkflowNodeField(BaseModel):
    """Represents a single input field entry under node.data.inputs.<field_name>."""
    model_config = ConfigDict(extra='allow')
    label: Optional[str] = None
    description: Optional[str] = None
    value: Any = None
    required: Optional[bool] = None
    type: Optional[str] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    options: Optional[list[Any]] = None
    ui_choices: Optional[list[Any]] = None

class WorkflowNodeData(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: Optional[str] = None  # sometimes duplicated
    type: Optional[str] = None
    label: Optional[str] = None
    inputs: dict[str, WorkflowNodeField] = Field(default_factory=dict)
    # board, image, etc. left as arbitrary

class WorkflowNode(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: str
    data: WorkflowNodeData

class WorkflowGraph(BaseModel):
    model_config = ConfigDict(extra='allow')
    nodes: dict[str, dict[str, Any]] | list[WorkflowNode] | dict[str, WorkflowNode] = Field(default_factory=dict)
    edges: list[WorkflowEdge] = Field(default_factory=list)

class WorkflowFormElementData(BaseModel):
    model_config = ConfigDict(extra='allow')
    # Flexible for container/node-field
    fieldIdentifier: Optional[dict[str, Any]] = None
    children: Optional[list[str]] = None

class WorkflowFormElement(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: str
    type: str
    data: WorkflowFormElementData

class WorkflowForm(BaseModel):
    model_config = ConfigDict(extra='allow')
    elements: dict[str, WorkflowFormElement] = Field(default_factory=dict)

class WorkflowRoot(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    form: WorkflowForm = Field(default_factory=WorkflowForm)

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

OUTPUT_CAPABLE_TYPES = {"save_image", "l2i", "flux_vae_decode", "flux_vae_encode", "hed_edge_detection"}

def load_workflow_json(data: dict[str, Any]) -> WorkflowRoot:
    """Load raw workflow JSON dict into `WorkflowRoot` model preserving unknown fields."""
    return WorkflowRoot(**data)

def iter_form_input_fields(root: WorkflowRoot):
    """Yield tuples (node_id, field_name, element_id, field_model)."""
    elements = root.form.elements
    for elem in elements.values():
        if elem.type == 'node-field' and elem.data.fieldIdentifier:
            fid = elem.data.fieldIdentifier
            node_id = fid.get('nodeId')
            field_name = fid.get('fieldName')
            # Find node data
            node_obj = next((n for n in root.nodes if n.get('id') == node_id), {})
            inputs = ((node_obj.get('data') or {}).get('inputs') or {})
            field_model = inputs.get(field_name)
            yield node_id, field_name, elem.id, field_model

def enumerate_output_nodes(root: WorkflowRoot):
    """Yield node_id, node_type, has_board_field_exposed bool."""
    exposed_board_node_ids = {n for (n, fname, _eid, _f) in iter_form_input_fields(root) if fname == 'board'}
    for node in root.nodes:
        nid = node.get('id')
        ntype = (node.get('data') or {}).get('type')
        if ntype in OUTPUT_CAPABLE_TYPES:
            yield nid, ntype, (nid in exposed_board_node_ids)

def build_input_jsonpath(node_id: str, field_name: str) -> str:
    """Replicate existing JSONPath pattern used by partial system."""
    return f"$.nodes[?(@.id='{node_id}')].data.inputs.{field_name}"

__all__ = [
    'WorkflowRoot', 'WorkflowNode', 'WorkflowNodeData', 'WorkflowNodeField', 'WorkflowEdge', 'WorkflowEdgeEndpoint',
    'WorkflowForm', 'WorkflowFormElement', 'WorkflowFormElementData', 'load_workflow_json', 'iter_form_input_fields',
    'enumerate_output_nodes', 'build_input_jsonpath', 'OUTPUT_CAPABLE_TYPES'
]
