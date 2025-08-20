# Task: Extract InvokeAI Workflow Data Models for Complete JSON → Pydantic Mapping

Command Breakdown:
- Analyze current partial workflow mapping in `src/invokeai_py_client/workflow/`.
- Inspect upstream InvokeAI reference code under `context/refcode/InvokeAI/invokeai/` for workflow/invocation graph structures.
- Design robust Pydantic models that fully represent workflow JSON (nodes, edges, form, inputs, metadata) with forward compatibility.
- Implement new module (e.g. `src/invokeai_py_client/workflow/upstream_models.py`) using `extra='allow'` to tolerate future fields.
- Provide converter function to load a workflow JSON file into these models.
- Expose helper to enumerate inputs/outputs and pre-compute input JSONPaths.
- Avoid modifying existing partial system immediately; add new repository/helper for incremental adoption.
- Document rationale and usage in a hint file (`context/hints/howto-extract-invokeai-workflow-models.md`).
- Future: Optionally refactor existing `WorkflowRepository` to leverage new complete models.
