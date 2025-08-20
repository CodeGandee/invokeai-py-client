# Workflow Subsystem – Design & Intended Usage (High‑Level)

This document is a *pre‑implementation* design narrative. It captures the **assumptions, invariants, roles, and user journey** for the client workflow API. Code names and paths are illustrative; low‑level mechanics (registries, concrete class names, environment variable toggles) belong elsewhere and should not dominate this design.


## 1. Purpose
Provide a stable, ergonomic abstraction for configuring and submitting InvokeAI GUI‑authored workflows from Python code, without requiring callers to understand the raw workflow JSON schema or mutate it directly.

## 2. Core Actors
| Actor | Goal |
| ----- | ---- |
| Workflow Author (in GUI) | Exports a workflow definition JSON. |
| API User (Python) | Loads the definition, inspects required inputs, supplies values, submits, awaits results. |
| Extension Author | (Optionally) introduces new semantic input types without editing core client code. |

## 3. Key Assumptions
1. The exported workflow JSON is treated as an authoritative, mostly opaque artifact; we do **value substitution only**, never key creation/removal.
2. Input discoverability is driven exclusively by the `form` tree (its ordered `node-field` entries). The JSON field `exposedFields` is intentionally ignored.
3. A workflow “input index” is defined by depth‑first traversal order of that form tree and is stable for drift detection between revisions.
4. Output relevance (for mapping results) requires both: (a) node has board/output capability, (b) that node’s board field appears in the form (user‑configurable). Otherwise it is a *debug* node.
5. Literal values are retained in the submission even if an edge also supplies that parameter (mirrors GUI behaviour and satisfies server validation models).
6. Input *types* (string, model, board, etc.) are resolved conceptually via an extensible strategy layer (pluggable rules + builders) rather than hard‑coded branching.

## 4. Invariants (Must Always Hold)
| ID | Invariant |
|----|-----------|
| INV‑1 | Original workflow JSON remains structurally intact (no added/removed keys). |
| INV‑2 | Form traversal is the *only* mechanism to derive user‑visible inputs. |
| INV‑3 | Each discovered input stores sufficient metadata: label, node id, field name, required flag, stable index, lightweight path reference. |
| INV‑4 | Field object’s concrete Python type is immutable after first creation (guards downstream assumptions). |
| INV‑5 | Submission payload always includes required literals even when edge‑connected. |
| INV‑6 | Extending supported field kinds never requires editing existing conditional logic (Open/Closed). |

## 5. User Journey (Narrative)
1. User exports a workflow definition from the GUI and saves it locally.
2. User loads the definition into the client API (repository/factory produces a handle object).
3. The handle enumerates inputs (ordered) derived from the form tree. User inspects them (labels, indices, current defaults) before deciding what to set.
4. User sets values using simple index‑oriented helpers (no need to understand internal field classes). An optional bulk helper MAY exist, but bulk mutation is **not** a core design assumption; single‑input setting must remain the primary, always‑available path.
5. User invokes a submit method. Validation occurs; on success the client produces a derived API graph by substituting only the values corresponding to discovered inputs.
6. User waits for completion (polling or event stream) and optionally requests a structured mapping of outputs (board destinations → generated image filenames).
7. User may export an index map to later detect drift if the underlying workflow JSON changes in a future revision.

## 6. Conceptual Architecture (Black Box View)
| Layer | Responsibility | Hidden Internals (Not in this doc) |
|-------|----------------|------------------------------------|
| Definition Loader | Parse persisted JSON into a lightweight model snapshot. | JSON parsing, minimal normalization. |
| Input Discovery | Traverse form structure; build ordered input descriptors. | Type heuristics / plugin evaluation. |
| Field Abstraction | Encapsulate validation + API serialization per semantic type. | Concrete class hierarchy & rule registration. |
| Submission Builder | Merge current input values into a copy of original JSON and extract a queue graph view. | Node filtering, board heuristics. |
| Execution Monitor | Track queue items (sync or async) and surface status & outputs. | Socket/event implementation details. |
| Output Mapper | Provide best‑effort mapping of declared output nodes to produced assets. | Multi‑tier resolution strategy. |

## 7. Extension Strategy (Conceptual)
Extensions contribute new “field kinds” by supplying:
1. A *detection hint* (predicate over node type / field name / field metadata).
2. A *construction recipe* (create a field object with initial metadata / constraints).
The core system evaluates registered hints in priority order. Unrecognized inputs degrade to a generic string‑like field (unless future “strict” mode is enabled). Concrete registration APIs and environment flags are *implementation* concerns and excluded here by design; they live in the technical documentation.

## 8. Error & Validation Model
| Stage | Failure Examples | Surface To User |
|-------|------------------|-----------------|
| Discovery | Malformed form entries | Omit entry; optionally warn (non‑fatal). |
| Value Assignment | Type mismatch, missing required | Indexed error messages. |
| Submission Build | Unexpected structural absence | Raised as submission error with context. |
| Execution | Queue failure / node error | Propagated through wait APIs with status. |

Optional bulk update (if provided) SHOULD be transactional; however, callers must not depend on its presence—design guarantees revolve around single‑value assignment and submission integrity.

## 9. Output Identification Logic (Intent)
We categorize a node as “output” strictly when the user is empowered (via form) to choose its destination (e.g., a board). This filters out diagnostic or intermediary nodes that also produce images but are not part of the user’s configured output surface.

## 10. Drift Detection Rationale
Consumers may version workflows externally; an exported index map (index → stable field path reference) allows a later run to classify inputs as unchanged / moved / missing / new, enabling cautious automation or upgrade scripts without brittle UUID hard‑coding.

## 11. Non‑Goals
| Out of Scope | Reason |
|--------------|-------|
| Direct editing of arbitrary nodes outside discovered inputs | Avoid accidental schema drift & guard invariants. |
| Server‑side optimization (caching, deduping) | Owned by InvokeAI service layer. |
| Rich dependency graph visualization | Orthogonal concern (UI responsibility). |
| Persisted client‑side state management | Kept ephemeral; callers manage their own storage if needed. |

## 12. Open Questions / Future Considerations
| Topic | Notes |
|-------|-------|
| Strict Type Mode | Decide default posture (opt‑in vs opt‑out) after initial feedback. |
| Telemetry / Metrics | Possibly collect detection rule hit counts for tuning heuristics. |
| Advanced Output Semantics | Multi‑asset outputs beyond images (latents, masks) mapping strategy. |
| Partial Resubmission | Incremental re‑execution of subgraphs (requires server support). |

## 13. Minimal User Story (Condensed)
“As a Python user I can load a GUI‑exported workflow, list its configurable inputs in a stable order, set values with simple primitives, submit it, and obtain structured references to the generated images—without learning internal node schema or editing raw JSON.”

## 14. Traceability
Each invariant (INV‑1..INV‑6) will be covered by future automated tests: structural preservation, ordering stability, error surfacing, and extension neutrality.

## 15. Example Workflow Artifacts (Reference Paths to Retain)
These artifact links are part of the design narrative so downstream readers can map concepts to concrete examples. They are *illustrative*; the design does not require their internal structure.

| Use Case | Workflow Definition JSON | Example API Payload (inputs populated) |
|----------|--------------------------|----------------------------------------|
| SDXL Flux Refine | `data/workflows/sdxl-flux-refine.json` | `data/api-calls/call-wf-sdxl-flux-refine.json` |
| SDXL Text to Image | `data/workflows/sdxl-text-to-image.json` | `data/api-calls/call-wf-sdxl-text-to-image.json` |
| FLUX Image to Image | `data/workflows/flux-image-to-image.json` | `data/api-calls/call-wf-flux-image-to-image-1.json` |

(If response examples are later curated, they can be linked in a parallel column without altering core assumptions.)


This design intentionally omits code‑level mechanics. Implementation documents should link back here to demonstrate compliance with the stated invariants and user journey.