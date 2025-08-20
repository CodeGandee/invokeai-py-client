# About: Upstream Workflow Data Model Rationale

Purpose: Explain why and how the `upstream_models` module represents InvokeAI workflow JSON, the compatibility guarantees, trade‑offs, and extension path.

## Goals
- Load any current InvokeAI GUI workflow JSON into typed Pydantic models without breaking on unknown fields.
- Mutate only safe value areas (typically `node.data.inputs.<field>.value`).
- Round‑trip back to a dict suitable for queue submission (no structural loss).
- Introspect form exposure (for depth‑first input indexing) and output‑capable nodes.
- Remain forward‑compatible when upstream adds new keys or nested structures.

## Design Principles
1. Permissive schema: `extra='allow'` everywhere; we *never* reject unexpected keys.
2. Minimal required fields: only IDs/types that current logic depends on are mandated.
3. Shallow typing: Keep `root.nodes` as `list[dict]` to preserve raw ordering & unknown shapes; offer *typed views* (`iter_typed_nodes`) instead of forcing conversion.
4. Non-invasive mutation: Helpers (`update_node_input_value`) operate directly on stored dicts to avoid re‑serialization drift.
5. Deterministic addressing: JSONPath pattern mirrors existing implementation: `$.nodes[?(@.id='NODE')].data.inputs.FIELD`.
6. Output detection heuristic kept explicit & overridable (`OUTPUT_CAPABLE_TYPES`).

## Compatibility Assessment
| Aspect | Strategy | Result |
|--------|----------|--------|
| Top-level unknown keys | Allowed via `extra='allow'` | Preserved |
| Node ordering | Raw list preserved | Stable |
| Node inputs shape | Dict-of-dicts kept; partial model for common keys | Extra keys retained |
| Edges | Stored as raw dicts (optionally cast individually) | Lossless |
| Form elements | Map preserved; only minimal typed subset | Layout metadata retained |
| Serialization | `workflow_to_dict()` with `exclude_none=True` | Clean & InvokeAI-compatible |
| Future new node types | Not enumerated; treated as opaque | Safe by design |
| Output node expansion | Requires extending `OUTPUT_CAPABLE_TYPES` or heuristic | Manual tune-up |

## Safe vs. Unsafe Mutations
| Action | Safe? | Reason |
|--------|-------|--------|
| Updating `inputs.<field>.value` | Yes | Matches GUI user edits |
| Adding/removing nodes | Risky | May break internal references / edges |
| Editing node IDs | Unsafe | IDs referenced by edges & form.fieldIdentifier |
| Deleting form elements | Risky | Breaks exposed field mapping |
| Injecting new arbitrary keys | Usually safe | Extra keys tolerated upstream (but unverified) |

## Helper Overview
```python
from invokeai_py_client.workflow.upstream_models import (
    load_workflow_json,
    iter_form_input_fields,
    enumerate_output_nodes,
    update_node_input_value,
    workflow_to_dict,
)

root = load_workflow_json(raw_workflow_dict)

# Iterate exposed inputs (depth-first ordering is applied elsewhere)
for node_id, field_name, element_id, field_dict in iter_form_input_fields(root):
    print(node_id, field_name, field_dict.get('value'))

# Update a prompt value
update_node_input_value(root, node_id='positive_prompt:1234', field_name='value', value='A luminous castle')

# Detect output-capable nodes
for nid, ntype, has_board in enumerate_output_nodes(root):
    print('out:', nid, ntype, has_board)

# Serialize for submission
payload = workflow_to_dict(root)
```

## JSONPath Parity
The existing system uses filtered list expressions. Example:
```text
$.nodes[?(@.id='negative_prompt:abcd')].data.inputs.value
```
Rationale: Avoids positional assumptions if node ordering changes, while remaining simple (no recursive descent).

## Output Node Detection
Current constant (`OUTPUT_CAPABLE_TYPES`):
```python
OUTPUT_CAPABLE_TYPES = {"save_image", "l2i", "flux_vae_decode", "flux_vae_encode", "hed_edge_detection"}
```
Recommended enhancement (heuristic):
```python
if ntype.endswith('_to_image') or 'save' in ntype or 'decode' in ntype:
    # treat as potentially output-capable
```
Include board exposure check (`board` field in form) to prioritize explicit mapping.

## Edge-Aware Input Mutation (Future)
Before overwriting an input value, we can verify it is *not* fed by an edge:
```python
def is_field_connected(root, node_id, field_name):
    for e in root.edges:
        dst = e.get('destination', {})
        if dst.get('node_id') == node_id and dst.get('field') == field_name:
            return True
    return False
```
This prevents accidental override of dynamic (computed) values.

## Forward Compatibility Strategy
- Accept everything now; constrain later only if necessary (opt‑in validators).
- Keep mutation helpers pure & minimal; higher layers enforce business rules (e.g. index locking, validation).
- Add new optional attributes (e.g. `ui_type`, `placeholder`, `default`) *without* breaking callers.

## Common Pitfalls & Mitigations
| Pitfall | Mitigation |
|---------|------------|
| Missing new output node types | Allow downstream injection into `OUTPUT_CAPABLE_TYPES` |
| Overwriting edge-connected input | Add `is_field_connected` guard |
| Drift in JSONPath pattern | Centralize builder `build_input_jsonpath()` |
| Node shape changes (list->dict) | Provide adapter if upstream introduces mapping container |
| Performance (large workflows) | Iterators avoid copying; selective model wrapping |

## Integration Path Into `WorkflowHandle`
1. Parse once: `self._root = load_workflow_json(raw_dict)`.
2. Build depth-first input index using `iter_form_input_fields(self._root)`.
3. On user mutation: call `update_node_input_value` instead of manual JSONPath merge.
4. On submission: `workflow_to_dict(self._root)` then apply board override.
5. (Optional) Maintain legacy path behind feature flag for regression fallback.

## Extensibility Hooks
- Pluggable output detection: function override or set union.
- Custom field resolvers: map (node_id, field_name) -> adapter object.
- Validation layer: run semantic checks (e.g. width % 8) after updates but before submission.

## Source References
- InvokeAI repository: https://github.com/invoke-ai/InvokeAI
- Typical invocation node definitions: `invokeai/app/invocations/*.py`
- GUI form element construction logic (reference): frontend sources (panels & field exposure).

## Minimal Diff Example (Before vs After Mutation)
```python
original = load_workflow_json(raw)
update_node_input_value(original, 'positive_prompt:xyz', 'value', 'A misty valley at dawn')
mutated = workflow_to_dict(original)
# Only the targeted input value changes; structural keys untouched.
```

## When Not To Use These Models
- Low-level performance‑sensitive bulk transformations (prefer streaming JSON tools).
- Direct manipulation of latent connections or edge rewiring (needs domain rules beyond scope here).

## Summary
The upstream workflow data model balances safety (permissive, lossless) with convenience (typed accessors, mutation helpers) while deliberately avoiding over‑specification that could break on upstream evolution. It is suitable now for read/modify/write of input values and output node analysis, and is structured for incremental hardening.
