# Contributing and Testing Guide

Purpose
- Provide a concise contributor guide covering development setup, coding standards, test strategy, invariants to preserve, and a PR checklist.
- Help new maintainers ramp quickly and make safe, reviewable changes that align with public behaviors.

Audience
- Engineers contributing features like new field types, model sync strategies, board/image operations, or workflow utilities.
- Maintainers reviewing PRs for compatibility and adherence to invariants.

Development setup
- Clone repo and open in your IDE.
- Recommended environment: Python 3.10+.
- Run tests:
  - [Bash.pixirun](README.md:321)
- Explore examples:
  - Pipelines: [examples/pipelines](examples/pipelines)
  - Raw REST demos: [examples/raw-apis](examples/raw-apis)

Repository touchpoints
- Client core (entry and repos): [src/invokeai_py_client](src/invokeai_py_client)
- Examples:
  - SDXL text-to-image: [examples/pipelines/sdxl-text-to-image.py](examples/pipelines/sdxl-text-to-image.py)
  - FLUX image-to-image: [examples/pipelines/flux-image-to-image.py](examples/pipelines/flux-image-to-image.py)
  - SDXL→FLUX refine: [examples/pipelines/sdxl-flux-refine.py](examples/pipelines/sdxl-flux-refine.py)
  - Boards API demo: [examples/raw-apis/api-demo-boards.py](examples/raw-apis/api-demo-boards.py)
  - Queue demos: [examples/raw-apis/api-demo-job-queue.py](examples/raw-apis/api-demo-job-queue.py)
- Upstream API references:
  - Endpoint list: [context/hints/invokeai-kb/invokeai-api-list.md](context/hints/invokeai-kb/invokeai-api-list.md)
  - OpenAPI JSON: [context/hints/invokeai-kb/invokeai-openapi-v6.3.json](context/hints/invokeai-kb/invokeai-openapi-v6.3.json)

Coding standards
- Maintain strongly-typed field model: new fields should have a precise Ivk*Field with a predictable `.value` type.
- Avoid side effects: do not mutate the original `WorkflowDefinition` object—submission should operate on a derived copy.
- Input indices are authoritative: do not introduce label/name-based public APIs for setting fields; labels/names are not globally stable.

Key invariants to preserve (must-read)
- Inputs reflect GUI Form semantics (not graph topology). Index is sole stable handle while the Form layout remains unchanged:
  - [Markdown.README](README.md:63)
- Exported workflow JSON is immutable; only value substitution on submit:
  - [Markdown.README](README.md:38)
  - [Markdown.README](README.md:292)
- Concrete field types remain stable post‑discovery; no dynamic swapping:
  - [Markdown.README](README.md:299)
- No hidden mutation of the original definition:
  - [Markdown.README](README.md:41)
- Output mapping contract: board-exposed output nodes should be discoverable and mapped to produced image names using runtime session/queue data:
  - [Markdown.README](README.md:153)

Test strategy
- Run all tests locally:
  - [Bash.pixirun](README.md:321)
- Add tests when:
  - Introducing a new field type or changing detection rules
  - Adjusting submission pipeline logic
  - Modifying output mapping logic for output-capable nodes
  - Changing model sync strategies
- Suggested test categories:
  - Field discovery: verify index order and Ivk*Field concrete types for a fixture workflow
  - Submission building: ensure only changed values are substituted; nodes/edges remain intact
  - Output mapping: given a simulated queue item/session, verify mapping returns expected node_id → image_names and index correlations
  - Model sync: verify resolution behavior for name/base (and that unchanged models are not modified)
- Determinism:
  - Ensure discovery order is deterministic (depth‑first pre-order over the Form)
  - Assert snapshot of input index → field type mappings for representative workflows

Common development tasks

1) Adding a new field type (e.g., IvkXYZField)
- Implement a new Ivk*Field class in the field system
- Register a predicate → builder in the detection registry
- Add tests to validate detection and typed behavior
- Update docs where relevant:
  - Usage Pattern: [context/summaries/developer/01-usage-pattern.md](context/summaries/developer/01-usage-pattern.md)
  - Architecture: [context/summaries/developer/02-architecture.md](context/summaries/developer/02-architecture.md)

2) Adjusting output mapping for a new output-capable node
- Extend the classification logic so the node is recognized as output-capable (board-persisting)
- Ensure its board field can be exposed in the Form and discovered as an input
- Add mapping tests with representative results payloads

3) Enhancing model synchronization
- Consider a layered approach: by_name → by_base → (optionally) by hash
- Ensure no surprise changes to already-valid model identifiers
- Add tests for the exact resolution paths and logging/reporting of changes

PR checklist (copy into your PR description)
- [ ] Preserved core invariants (indices-as-API, immutable submission, stable types, no hidden mutation)
- [ ] Added or updated tests for affected areas (discovery, submission, mapping, model sync)
- [ ] Updated developer docs if public behaviors changed:
  - Overview: [context/summaries/developer/00-overview.md](context/summaries/developer/00-overview.md)
  - Usage Pattern: [context/summaries/developer/01-usage-pattern.md](context/summaries/developer/01-usage-pattern.md)
  - Architecture: [context/summaries/developer/02-architecture.md](context/summaries/developer/02-architecture.md)
  - Upstream APIs: [context/summaries/developer/03-upstream-apis.md](context/summaries/developer/03-upstream-apis.md)
  - Examples Index: [context/summaries/developer/04-examples-index.md](context/summaries/developer/04-examples-index.md)
- [ ] Considered backward compatibility for public functions/classes
- [ ] Included links to example usage if applicable (pipelines/raw-apis)
- [ ] Provided migration notes if indices or discovery changed for example workflows

Troubleshooting matrix
- No inputs discovered you expected:
  - Ensure the field is placed in the GUI Form (not just present on a node)
  - Re-export the workflow and re-run discovery: [Python.workflow_handle.list_inputs()](examples/pipelines/sdxl-text-to-image.py:143)
- Outputs not mapped:
  - Expose board fields for output-capable nodes in the Form; re-export and re-run
  - Check output enumeration: [Python.workflow_handle.list_outputs()](examples/pipelines/flux-image-to-image.py:285)
- Model resolution failures:
  - Use synchronization: [Python.workflow_handle.sync_dnn_model()](examples/pipelines/sdxl-text-to-image.py:136)
- Image download fails:
  - Verify board_id and image_name; download via:
    - [Python.BoardHandle.download_image()](examples/pipelines/sdxl-text-to-image.py:349)

Process recommendations
- Small, focused PRs with tests are reviewed faster and safer to revert.
- Prefer additive changes to detection registries and capability classifications rather than invasive refactors.
- Keep examples runnable; update their index snapshots if the workflow JSONs change.

Pointers to broader context
- Scope, design principles, invariants: [README.md](README.md)
- Developer overview: [context/summaries/developer/00-overview.md](context/summaries/developer/00-overview.md)
- Usage pattern: [context/summaries/developer/01-usage-pattern.md](context/summaries/developer/01-usage-pattern.md)
- Architecture: [context/summaries/developer/02-architecture.md](context/summaries/developer/02-architecture.md)
- Upstream API mappings: [context/summaries/developer/03-upstream-apis.md](context/summaries/developer/03-upstream-apis.md)
- Examples index: [context/summaries/developer/04-examples-index.md](context/summaries/developer/04-examples-index.md)

Appendix — quick links to examples
- SDXL T2I: [examples/pipelines/sdxl-text-to-image.py](examples/pipelines/sdxl-text-to-image.py)
- FLUX I2I: [examples/pipelines/flux-image-to-image.py](examples/pipelines/flux-image-to-image.py)
- SDXL→FLUX Refine: [examples/pipelines/sdxl-flux-refine.py](examples/pipelines/sdxl-flux-refine.py)
- Boards (REST): [examples/raw-apis/api-demo-boards.py](examples/raw-apis/api-demo-boards.py)
- Queue (REST): [examples/raw-apis/api-demo-job-queue.py](examples/raw-apis/api-demo-job-queue.py)
- Latest image (REST): [examples/raw-apis/api-demo-latest-image.py](examples/raw-apis/api-demo-latest-image.py)
- Upload (REST): [examples/raw-apis/api-demo-upload-image.py](examples/raw-apis/api-demo-upload-image.py)
