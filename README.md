# InvokeAI Python Client

Typed Python client for interacting with an InvokeAI server (selected REST endpoints + optional Socket.IO events). It bridges GUI‑authored workflow definitions and programmatic automation: load an exported workflow JSON, inspect ordered user‑configurable inputs (derived purely from the workflow `form` tree), set values, submit, and monitor progress.

This README targets two audiences:
- Users: How to load, configure, and run workflows (usage pattern & quick start).
- Developers / Contributors: Design invariants, architecture layers, extensibility model.

NOTE: Earlier drafts referenced direct JSONPath patching. The current design treats the workflow JSON as an opaque artifact: we perform value‑only substitutions for discovered inputs and retain literals even if also supplied by edges (mirrors GUI behavior). Stored JSONPath strings now primarily support drift detection tooling rather than runtime mutation logic.

---
## ✨ Core Domains
1. Workflows – load exported GUI workflow JSON, list & set inputs, submit (sync/async/stream), map outputs to images.
2. Boards & Images – enumerate/create boards, upload images, associate outputs.
3. DNN Models – discover installed models (v2 endpoints) and bind them to workflow model fields.

---
## 🎯 Goals (High-Level)
- Treat exported GUI workflow JSON as the unmodified source of truth.
- Derive stable, index‑oriented public inputs from the `form` element tree (ignore `exposedFields`).
- Provide strongly typed but ergonomic field objects (`Ivk*Field`) with validation.
- Support sync, async, and streaming submission patterns.
- Offer an open/closed field type system (extensible detection & construction rules without editing core branches).
- Keep core library state light; no heavy local persistence.

Non‑Goals (for now): full coverage of every InvokeAI endpoint, advanced graph editing, subgraph re‑execution, or rich visualization.

---
## 🧭 Usage Pattern (User Story)
1. Export a workflow JSON from the InvokeAI GUI.
2. Load it into a `WorkflowDefinition` and create a `WorkflowHandle` via the client repository.
3. Enumerate inputs (ordered, stable) and view labels & types.
4. Set values (single assignment helpers; bulk update is optional and not required for core flow).
5. Submit; the client builds an API graph by substituting only those input values (no key additions/removals).
6. Poll or stream execution events; optionally map declared output nodes to produced image filenames.
7. (Optional) Export an input index map for future drift detection when the definition changes.

Invariants (summary): structure preserved; only form-derived inputs are user‑visible; field concrete type locked after creation; retain literals even when edge-connected; adding new field kinds should not require modifying existing conditionals.

---
## 🚀 Quick Start
```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

client = InvokeAIClient.from_url("http://localhost:9090")
wf_def = WorkflowDefinition.from_file("data/workflows/sdxl-text-to-image.json")
workflow = client.workflow_repo.create_workflow(wf_def)

for inp in workflow.list_inputs():
    print(f"[{inp.input_index}] {inp.label} -> {type(inp.field).__name__}")

prompt_field = workflow.get_input_value(0)
if hasattr(prompt_field, 'value'):
    prompt_field.value = "A cinematic sunset over mountains"

submission = workflow.submit_sync(board_id="my-board")
print("Submitted batch", submission["batch_id"], "session", submission["session_id"])
queue_item = workflow.wait_for_completion_sync(timeout=120)
print("Final status:", queue_item.get("status"))
```

Async streaming example:
```python
import asyncio
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

async def main():
    client = InvokeAIClient.from_url("http://localhost:9090")
    wf_def = WorkflowDefinition.from_file("data/workflows/sdxl-text-to-image.json")
    wf = client.workflow_repo.create_workflow(wf_def)
    field0 = wf.get_input_value(0)
    if hasattr(field0, 'value'):
        field0.value = "A watercolor fox in a forest"

    def on_progress(evt):
        p = evt.get('progress')
        if p is not None:
            print(f"Progress: {p*100:.0f}%")

    await wf.submit(subscribe_events=True, on_invocation_progress=on_progress)
    result = await wf.wait_for_completion(timeout=90)
    print("Completed with status:", result.get("status"))

asyncio.run(main())
```

---
## 🔑 Field Type System (Extensibility Overview)
Field detection & construction use a plugin registry (rules + builders). New kinds can be introduced externally without editing core `if/elif` blocks:
- Detection: prioritized predicates over (node_type, field_name, metadata).
- Construction: builder functions producing a concrete `IvkField` instance.
Fallback is a generic string field (unless a future strict mode is enabled). End users just interact with typed fields surfaced by the handle.

Design doc: `context/design/usage-pattern.md` (conceptual invariants & journey).

---
## 📚 Key Terminology (summary)
Full glossary in `context/design/terminology.md`.

| Term | Meaning |
|------|---------|
| InvokeAI (`invokeai`) | The running inference backend. |
| Client API (`client-api`) | This Python wrapper project. |
| InvokeAI Client (`InvokeAIClient`) | Connection façade exposing repositories. |
| Workflow Definition (`WorkflowDefinition`) | Preserved raw JSON + light helpers. |
| Workflow Handle (`WorkflowHandle`) | Mutable execution state & submission logic. |
| Workflow Inputs (`IvkWorkflowInput`) | Public parameters derived from `form`. |
| Field Types (`Ivk*Field`) | Typed wrappers for InvokeAI values/resources. |

Field concrete class is locked after discovery—replacement must use the exact same class.

---
## ✅ Current Feature Set
- Workflows: definition loading, ordered input discovery, single & optional bulk value updates, submission (sync/async/stream), progress & completion helpers.
- Boards: list/create/update/delete, upload images, uncategorized fallback.
- DNN Models: enumerate & filter, single lookup, rich taxonomy.
- Field System: typed primitives (string/int/float/bool/enum) + resources (model/board/image) + extensible plugin detection.
- Output Mapping: best‑effort image filename resolution for declared output nodes.
- Event Streaming: Socket.IO callbacks for invocation lifecycle.
- Validation: pre‑submission input validation & basic drift tooling.

---
## 🧪 Examples
See runnable scripts in `examples/` and template workflows in `data/workflows/`.

### Example Workflow Artifacts
| Use Case | Workflow JSON | Example Populated Payload |
|----------|---------------|---------------------------|
| SDXL Flux Refine | `data/workflows/sdxl-flux-refine.json` | `data/api-calls/call-wf-sdxl-flux-refine.json` |
| SDXL Text To Image | `data/workflows/sdxl-text-to-image.json` | `data/api-calls/call-wf-sdxl-text-to-image.json` |
| FLUX Image To Image | `data/workflows/flux-image-to-image.json` | `data/api-calls/call-wf-flux-image-to-image-1.json` |

---
## 🚦 Execution Patterns
| Pattern | When to Use | API |
|---------|-------------|-----|
| Blocking | Simple scripts / CLI | `submit_sync()` + `wait_for_completion_sync()` |
| Async + Events | Dashboards / concurrency | `await submit(subscribe_events=True)` + callbacks |
| Hybrid Streaming | Need simplicity + events | `async for evt in submit_sync_monitor_async()` |

---
## 🔍 Validation & Drift
`validate_inputs()` reports indexed errors before submission. Drift utilities export the current index/label/path mapping and later compare a new workflow version to classify inputs as unchanged / moved / missing / new.

---
## 🧱 Architectural Summary
| Layer | Responsibility |
|-------|----------------|
| Definition Loader | Parse JSON, retain raw data. |
| Input Discovery | Depth‑first traversal of `form` → ordered public inputs. |
| Field System | Typed validation + API serialization; open/closed extension model. |
| Submission Builder | Value‑only substitution into a copy of raw JSON; produce queue graph. |
| Execution Monitor | Poll or stream progress (event handler registration). |
| Output Mapper | Tiered image filename resolution. |
| Drift Tools | Export & verify index mapping across versions. |

See `context/design/usage-pattern.md` for conceptual narrative & invariants.

---
## 🗺️ Roadmap (Indicative)
| Area | Direction |
|------|-----------|
| Diagnostics | Optional stats on field detection & fallback occurrences |
| Strict Mode | Opt‑in enforcement for unknown field types (early failure) |
| Payload Introspection | Public helper to preview submission graph without enqueueing |
| Output Mapping | Extend beyond images (latents / masks) |
| Performance | Cache immutable per‑workflow discovery artifacts |

Out‑of‑Scope: arbitrary graph mutation, server caching policy shaping, rich visualization.

---
## 🤝 Contributing
1. Review invariants in `context/design/usage-pattern.md` before proposing changes.
2. Preserve backward compatibility of public method signatures when feasible.
3. Add or update tests when altering discovery, submission building, or field behaviors.
4. Keep README changes in sync with design doc evolution.

---
## 🧪 Testing
```bash
pixi run test
```

---
## 📄 License
See [LICENSE](LICENSE).

---
If something here diverges from actual behavior, open an issue or PR—docs and code should evolve together.