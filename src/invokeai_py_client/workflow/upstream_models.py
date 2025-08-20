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
from collections.abc import Iterable
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

    # --- Higher level helpers (do not alter original field types to avoid breaking callers) ---
    def iter_typed_nodes(self) -> Iterable[WorkflowNode]:
        """Yield nodes as `WorkflowNode` models.

        We intentionally keep the underlying storage (`nodes` list of dict) intact for
        backward compatibility with existing code/tests that expect raw dicts.
        """
        for nd in self.nodes:
            # Guard against malformed entries
            if not isinstance(nd, dict) or 'id' not in nd or 'data' not in nd:
                continue
            try:
                yield WorkflowNode(**nd)  # type: ignore[arg-type]
            except Exception:
                # Skip nodes that fail validation (forward compatibility)
                continue

    def get_typed_node(self, node_id: str) -> WorkflowNode | None:
        for n in self.iter_typed_nodes():
            if n.id == node_id:
                return n
        return None

    def replace_typed_node(self, node: WorkflowNode) -> None:
        """Replace underlying raw dict for a node with contents of provided `WorkflowNode`.

        If node id not found, it will be appended (mirrors permissive behavior).
        """
        dumped = node.model_dump(exclude_none=True)
        for idx, nd in enumerate(self.nodes):
            if isinstance(nd, dict) and nd.get('id') == node.id:
                self.nodes[idx] = dumped
                return
        self.nodes.append(dumped)

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

OUTPUT_CAPABLE_TYPES = {
    "save_image",
    "l2i",
    "flux_vae_decode",
    "flux_vae_encode",
    "hed_edge_detection",
    # Common additional decode / save patterns (heuristic growth point)
    "image_output",
}

def is_output_node_type(node_type: str | None) -> bool:
    """Heuristic to decide if a node type is image-output capable.

    Rules (short-circuit):
    1. Explicit membership in OUTPUT_CAPABLE_TYPES.
    2. Contains 'save' substring.
    3. Ends with '_to_image'.
    4. Contains 'decode'.
    """
    if not node_type:
        return False
    lt = node_type.lower()
    return (
        lt in OUTPUT_CAPABLE_TYPES
        or 'save' in lt
        or lt.endswith('_to_image')
        or 'decode' in lt
    )

def load_workflow_json(data: dict[str, Any]) -> WorkflowRoot:
    """Load raw workflow JSON dict into `WorkflowRoot` model preserving unknown fields."""
    return WorkflowRoot(**data)

def workflow_to_dict(root: WorkflowRoot) -> dict[str, Any]:
    """Serialize `WorkflowRoot` (and any in-place mutations) back to InvokeAI-compatible dict.

    Notes
    -----
    * Unknown/extra fields preserved by Pydantic due to `extra='allow'`.
    * We exclude None values to keep output clean and closer to original schema.
    * Consumers can `json.dumps()` the result for persistence or submission.
    """
    return root.model_dump(exclude_none=True)

def update_node_input_value(root: WorkflowRoot, node_id: str, field_name: str, value: Any) -> bool:
    """Convenience mutator: update a node input field's `.value` if present.

    Returns True if updated, False if node or field not found.
    This mutates the underlying raw dict directly for efficiency and to avoid a full reparse.
    """
    for nd in root.nodes:
        if isinstance(nd, dict) and nd.get('id') == node_id:
            inputs = ((nd.get('data') or {}).get('inputs') or {})
            field_dict = inputs.get(field_name)
            if isinstance(field_dict, dict):
                field_dict['value'] = value
                return True
            return False
    return False

def is_field_connected(root: WorkflowRoot, node_id: str, field_name: str) -> bool:
    """Return True if an edge targets (node_id, field_name)."""
    for e in root.edges:
        try:
            if (
                isinstance(e, dict)
                and e.get('target') == node_id
                and e.get('targetHandle') == field_name
            ):
                return True
        except Exception:
            continue
    return False

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
    """Yield tuples of (node_id, node_type, has_board_field_exposed).

    Uses heuristic `is_output_node_type` plus explicit board field exposure detection.
    """
    exposed_board_node_ids = {n for (n, fname, _eid, _f) in iter_form_input_fields(root) if fname == 'board'}
    for node in root.nodes:
        if not isinstance(node, dict):
            continue
        nid = node.get('id')
        ntype = (node.get('data') or {}).get('type')
        if is_output_node_type(ntype):
            yield nid, ntype, (nid in exposed_board_node_ids)

def update_output_boards(root: WorkflowRoot, board_id: str, override: bool = False) -> int:
    """Assign a board_id to output-capable nodes lacking one (or override if specified).

    Returns number of nodes updated.
    """
    updated = 0
    for node in root.nodes:
        if not isinstance(node, dict):
            continue
        data = node.get('data') or {}
        ntype = data.get('type')
        if not is_output_node_type(ntype):
            continue
        inputs = data.get('inputs') or {}
        board_field = inputs.get('board')
        if board_field is None or not isinstance(board_field, dict):
            # create board field structure
            inputs['board'] = {'value': {'board_id': board_id}}
            updated += 1
        else:
            # Accept both nested value pattern and direct board object
            if 'value' in board_field and isinstance(board_field['value'], dict):
                if override or board_field['value'].get('board_id') in (None, 'auto', 'none'):
                    board_field['value']['board_id'] = board_id
                    updated += 1
            elif override:
                board_field['board_id'] = board_id
                updated += 1
    return updated

def build_input_jsonpath(node_id: str, field_name: str) -> str:
    """Replicate existing JSONPath pattern used by partial system."""
    return f"$.nodes[?(@.id='{node_id}')].data.inputs.{field_name}"

__all__ = [
    'WorkflowRoot', 'WorkflowNode', 'WorkflowNodeData', 'WorkflowNodeField', 'WorkflowEdge', 'WorkflowEdgeEndpoint',
    'WorkflowForm', 'WorkflowFormElement', 'WorkflowFormElementData', 'load_workflow_json', 'iter_form_input_fields',
    'enumerate_output_nodes', 'build_input_jsonpath', 'OUTPUT_CAPABLE_TYPES', 'workflow_to_dict', 'update_node_input_value', 'is_field_connected', 'is_output_node_type', 'update_output_boards'
]
