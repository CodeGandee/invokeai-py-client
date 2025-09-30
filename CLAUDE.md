# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python client library for InvokeAI APIs. It transforms GUI-exported workflow JSON into typed Python interfaces for batch automation, parameter sweeps, and high-throughput pipelines.

**Core Philosophy**: Treat exported workflow JSON as immutable source of truth. Only substitute values at submission time. Index-based stable ordering ensures scripts remain valid across workflow iterations.

**Target Users**: Existing InvokeAI GUI users who prototype workflows visually and want to automate large runs in Python without re-authoring graphs.

## Development Commands

### Using Pixi (recommended for conda environments)
```bash
# Development setup
pixi run dev-setup        # Install editable package and pre-commit hooks
pixi run quality          # Run all quality checks (lint, typecheck, test)

# Code quality
pixi run lint             # Check code with ruff
pixi run lint-fix         # Fix linting issues
pixi run format           # Format code with ruff
pixi run typecheck        # Type check with mypy

# Testing
pixi run test             # Run tests with pytest
pixi run test-cov         # Run tests with coverage report

# Documentation
pixi run docs-serve       # Serve documentation locally at http://127.0.0.1:8000
pixi run docs-build       # Build documentation to site/

# Docker
pixi run generate-invokeai-compose  # Generate InvokeAI docker-compose setup
```

### Using standard Python tools
```bash
# Installation
pip install -e .                  # Install in development mode
pip install -e ".[dev]"           # Install with dev dependencies

# Testing
python -m pytest tests/ -v        # Run tests verbosely
python -m pytest tests/test_boards.py::TestBoardRepo::test_list_boards  # Run single test

# Code quality
python -m ruff check src/ tests/  # Lint code
python -m ruff format src/ tests/ # Format code
python -m mypy src/               # Type checking
```

## Source Code Structure

```
src/invokeai_py_client/
├── client.py                # InvokeAIClient: HTTP session, WebSocket, repository access
├── exceptions.py            # Custom exception hierarchy (scaffolded)
├── models.py                # Core Pydantic models: IvkImage, IvkJob, IvkDnnModel, SessionEvent
├── utils.py                 # AssetManager, BoardManager, TypeConverter, ProgressTracker
│
├── ivk_fields/              # Field type system (typed, validated workflow inputs)
│   ├── base.py              # IvkField[T] generic base, mixins
│   ├── primitives.py        # String, Integer, Float, Boolean (with .value)
│   ├── resources.py         # Image, Board, Latents, Tensor (with .value, stores refs)
│   ├── models.py            # ModelIdentifier, UNet, CLIP, Transformer, LoRA (no .value)
│   ├── complex.py           # Color (r,g,b,a), BoundingBox (x_min, x_max, y_min, y_max), Collection
│   ├── enums.py             # Enumeration fields (with .value)
│   └── conditioning.py      # SD, FLUX, SD3, CogView4 conditioning types
│
├── board/                   # Board subsystem (Repository pattern)
│   ├── board_model.py       # Board Pydantic model ("none" board_id for uncategorized)
│   ├── board_handle.py      # BoardHandle: stateful board operations (upload, download, list images)
│   └── board_repo.py        # BoardRepository: lifecycle (create, delete, get handles)
│
├── workflow/                # Workflow subsystem
│   ├── workflow_model.py    # WorkflowDefinition: load/parse workflow JSON
│   ├── workflow_handle.py   # WorkflowHandle: stateful workflow (inputs, submit, outputs)
│   ├── workflow_repo.py     # WorkflowRepository: create workflows from definitions
│   ├── upstream_models.py   # Typed-but-forgiving InvokeAI graph/form models
│   └── field_plugins.py     # Pluggy-based field detection (prioritized rules + builders)
│
├── dnn_model/               # DNN model discovery (read-only)
│   ├── dnn_model_repo.py    # DnnModelRepository: list/detail models from v2 API
│   └── dnn_model_types.py   # Model entity + enums
│
└── quick/                   # Convenience flows
    ├── quick_client.py      # High-level helpers (server-side copy, SDXL txt2img)
    └── prebuilt-workflows/  # Embedded workflow JSON templates
```

### File Purpose Details

#### Core Files
- **`client.py`**: Central client managing HTTP session, WebSocket connection, repositories. Uses `_make_request()` for all API calls. Properties: `board_repo`, `workflow_repo`, `dnn_model_repo`.
- **`models.py`**: Shared Pydantic models across subsystems: `IvkImage`, `IvkJob`, `IvkDnnModel`, `SessionEvent`. Enums: `JobStatus`, `ImageCategory`, `BaseModelEnum`.
- **`exceptions.py`**: Custom exception hierarchy (currently scaffolds, not fully implemented).
- **`utils.py`**: `AssetManager` (uploads/downloads), `BoardManager` (board ops), `TypeConverter` (field conversions), `ProgressTracker` (monitoring).

#### Field Type System
Fields provide typed, validated workflow inputs/outputs:

- **`base.py`**: `IvkField[T]` abstract base. Mixins: `PydanticFieldMixin`, `IvkCollectionFieldMixin`. All fields implement: `validate_field()`, `to_api_format()`, `from_api_format()`, `to_json_dict()`, `from_json_dict()`.

- **Fields WITH `.value` property**: Primitives (String, Integer, Float, Boolean), Resources (Image, Board, Latents, Tensor), Collections, Enums. Access/set via `.value`.

- **Fields WITHOUT `.value` property**:
  - `IvkModelIdentifierField`: Uses `.key`, `.hash`, `.name`, `.base`, `.type`
  - `IvkColorField`: Uses `.r`, `.g`, `.b`, `.a`
  - `IvkBoundingBoxField`: Uses `.x_min`, `.x_max`, `.y_min`, `.y_max`

- **`primitives.py`**: `IvkStringField`, `IvkIntegerField`, `IvkFloatField`, `IvkBooleanField`. Support constraints (min/max, regex, etc.).

- **`resources.py`**: Reference fields storing names/IDs, not actual data. `IvkImageField`, `IvkBoardField`, `IvkLatentsField`, `IvkTensorField`, `IvkDenoiseMaskField`, `IvkMetadataField`.

- **`models.py`**: `IvkModelIdentifierField` (base), `IvkUNetField`, `IvkCLIPField`, `IvkTransformerField`, `IvkLoRAField`, plus aliases for SDXL/Flux/T5/CLIPEmbed/VAE.

- **`complex.py`**: `IvkColorField`, `IvkBoundingBoxField`, `IvkCollectionField` (has `.value` for list).

- **`enums.py`**: `IvkEnumField` with `.value` property. Includes `SchedulerName` enum with alias normalization.

- **`conditioning.py`**: Conditioning types for SD, FLUX, SD3, CogView4 pipelines.

#### Board Subsystem
Repository pattern for board/image management:

- **`board_model.py`**: `Board` Pydantic model. Special handling for uncategorized board (board_id="none" string). Helper methods: `uncategorized()`, `is_uncategorized()`.

- **`board_handle.py`**: `BoardHandle` represents active board state. Operations: list/upload/download/star/unstar/delete/move images. Uses modern `board_images` APIs with legacy fallbacks. Multipart upload with auth passthrough.

- **`board_repo.py`**: `BoardRepository` manages lifecycle: create/delete/update boards, resolve uncategorized, get handles (with caching), image lookup, move image to board by name.

#### Workflow Subsystem
Workflow execution and input/output management:

- **`workflow_model.py`**: `WorkflowDefinition` Pydantic model for workflow JSON. Extracts metadata, nodes, edges, exposed fields. Permissive parsing.

- **`workflow_handle.py`**: `WorkflowHandle` manages stateful workflow. `IvkWorkflowInput` for typed inputs. Key methods: `list_inputs()`, `get_input()`, `get_input_value()`, `set_input_value()`, `validate_inputs()`, `submit_sync()`, `submit()`, `wait_for_completion_sync()`, `map_outputs_to_images()`. DNN model sync against installed models.

- **`workflow_repo.py`**: `WorkflowRepository` creates workflow handles from definitions. Handles validation scaffolding.

- **`upstream_models.py`**: Typed-but-forgiving models for InvokeAI graph/form structures. Helpers to enumerate output-capable nodes and update board fields.

- **`field_plugins.py`**: Pluggy-based field detection. Prioritized rules: explicit type → name patterns → node primitives → value-based → enum presence → numeric constraints. Public API: `detect_field_type()`, `build_field()`.

#### DNN Models
Read-only model discovery:

- **`dnn_model_repo.py`**: `DnnModelRepository` stateless repo for v2 model list/detail (no caching).
- **`dnn_model_types.py`**: Model entity + enums.

#### Quick API
Convenience flows:

- **`quick_client.py`**: High-level helpers built atop repos/workflows. Includes server-side image copy (via tiny workflow), SDXL txt2img helper.
- **`prebuilt-workflows/`**: Embedded workflow JSON templates for common tasks.

## Architecture & Design Patterns

### Repository Pattern
Separation of concerns:
- **InvokeAIClient**: Connection, HTTP plumbing, repository access
- **BoardRepository**: Board/image lifecycle and operations
- **WorkflowRepository**: Workflow creation, loading, validation
- **DnnModelRepository**: Read-only model discovery

Handles represent stateful operations:
- **BoardHandle**: Stateful board (image operations)
- **WorkflowHandle**: Stateful workflow (input management, submission, output mapping)

### Workflow Input Discovery (Critical)
**Index-based access is the ONLY stable way to reference inputs.**

1. **Depth-first traversal** of the workflow's Form tree produces ordered `IvkWorkflowInput` list.
2. Each input has: `input_index`, `label`, `field_name`, `node_name`, concrete `field` (Ivk*Field instance).
3. **Ordering rule**: Traverse containers in order they appear; within each, visit child fields top-to-bottom (recursively for nested containers). Think: reading form top-to-bottom, descending into containers as encountered.
4. **Only Form-exposed fields are discoverable.** Fields outside the Form panel remain literals in the graph.
5. **Naming is unreliable**: Many fields lack stable labels, names aren't globally unique. Always use **index** for stable reference.

Example: `wf.get_input_value(3)` retrieves the field at index 3. Indices only shift if Form structure changes (containers/fields added/removed/reordered).

### Workflow Dual Naming
Workflows support two naming systems:
- **System names**: `{node_id}.{field_name}` - Always unique, guaranteed to work
- **User names**: Simple field names - May collide, raises ValueError when ambiguous

### Workflow Submission Pipeline
1. Copy raw workflow JSON
2. Substitute only values users changed (by visiting discovered inputs)
3. POST resulting graph to enqueue endpoint
4. No structural edits: nodes/edges remain intact

### Workflow Output Mapping
Filters form inputs where `field_name == 'board'` and node type is output-capable (implements board persistence). After completion, correlates session/queue data to produce image filename lists per node.

**Only board fields exposed in Form can be configured programmatically.** Non-exposed board outputs must be valid in the workflow JSON itself.

### Field Type System
- All fields inherit from `IvkField[T]` generic base (renamed from `Field` to avoid Pydantic conflicts)
- Plugin-driven detection: predicate → builder (open/closed principle)
- Heavy data (images, models) use reference names, not actual data
- Validation: per-field (Pydantic `validate_assignment=True`) + workflow-level

### Data Models
All API interactions use Pydantic models for type safety:
- Board, IvkImage, IvkJob, IvkDnnModel
- WorkflowDefinition, IvkWorkflowInput
- Enums: JobStatus, ImageCategory, BaseModelEnum, SchedulerName

## Key Implementation Details

### Uncategorized Board Handling
Uses string `"none"` as board_id (not Python `None`) because:
- InvokeAI API expects literal "none" in URL paths: `/api/v1/boards/none/image_names`
- Python `None` serializes to `null` in JSON, unusable in URL paths
- Board model includes `uncategorized()` class method and `is_uncategorized()` instance method

### Workflow Input Management
Process:
1. Parse workflow JSON's Form tree (depth-first traversal)
2. Create `IvkWorkflowInput` instances for each exposed field
3. Handle potential naming conflicts between nodes
4. Provide index-based access via `get_input_value()` and `set_input_value()`
5. Enforce type safety through `_lock_field_type()` mechanism
6. Support both direct field modification and complete field replacement

**Critical**: Input discovery reflects GUI Form semantics, NOT node graph topological order.

### Heavy Data Management
Images and models are handled by reference:
- Upload returns a name/ID from InvokeAI backend
- Workflows reference data by these names (not embedding actual bytes)
- After execution, explicitly delete uploaded assets to free backend storage

### Workflow Invariants
- Ordered inputs reflect GUI form structure, not node graph topology
- Field concrete class is stable post-discovery (no runtime type replacement)
- Literals remain even if an edge also supplies a value (mirrors GUI precedence)
- No hidden mutation of original workflow definition object
- Index-based access is the only stable reference mechanism

### Field Plugin System
Pluggy-based extensible detection:
1. Register predicate (identifies field type) + builder (creates field instance)
2. Prioritized evaluation: explicit type → name patterns → node primitives → value-based → enum → numeric constraints
3. New field types can register externally (open/closed principle)

### Execution Modes
| Mode | When | API |
|------|------|-----|
| Blocking | Simple scripts | `submit_sync()` + `wait_for_completion_sync()` |
| Async + Events | Concurrent UI / dashboards | `await submit(subscribe_events=True)` + callbacks |
| Hybrid Streaming | Need events while blocking | `async for evt in submit_sync_monitor_async()` |

## Testing & API Reference

### InvokeAI Test Servers
- **v6.3**: `http://localhost:9090` (API: `/api/v1`)
- **v6.8**: `http://localhost:19090` (API: `/api/v1`, some `/api/v2`)

### OpenAPI Specifications
- **v6.3**: `context/hints/invokeai-kb/invokeai-openapi-v6.3.json`
- **v6.8**: `context/hints/invokeai-kb/invokeai-openapi-v6.8.json`

### Test Data Locations
- **Example workflows**: `data/workflows/` (SDXL, FLUX templates)
- **API call examples**: `data/api-calls/` (request payloads)
- **Demo scripts**: `examples/` (working API demonstrations)
- **Context documentation**: `context/` (design docs, howtos, KB articles)

### Testing Commands
```bash
pixi run test              # Run all tests
pixi run test-cov          # Run with coverage
python -m pytest tests/test_boards.py::TestBoardRepo::test_list_boards  # Single test
```

### Other Tools
- `jq` for JSON processing
- `yq` for YAML processing
- `httpie` for user-friendly HTTP client

## Development Priorities

See `ROADMAP.md` for current development priorities. Upcoming features:

1. **Job/Queue APIs (v6.8 endpoints)**: List queue items, fetch details, compute busy status, cancel jobs, prune completed/errored, clear queue.

2. **Model Management Write Operations**: Install (add), delete (remove), convert, scan, prune/cancel install jobs, cache management, HF login. Will introduce `ModelManagerRepository` (write-capable) complementing read-only `DnnModelRepository`.

3. **Videos API (v6.8)**: List/detail/star/delete, board_videos helpers mirroring images/boards.

### Known Stubs / Gaps
- `InvokeAIClient.list_jobs()`, `get_job()`, `cancel_job()` are placeholders
- `IvkImageField.upload()` / `download()` are placeholders (uploads handled by `BoardHandle`)
- Exception hierarchy scaffolded but not fully implemented

## Important Development Practices

**Do what has been asked; nothing more, nothing less.**

- NEVER create files unless absolutely necessary for achieving the goal
- ALWAYS prefer editing an existing file to creating a new one
- NEVER proactively create documentation files (*.md) or README files unless explicitly requested
- Follow existing code patterns and architecture
- Maintain type safety (Python 3.11+, strict mypy)
- Add tests for new functionality
- Run `pixi run quality` before committing (lint + typecheck + test)

### Code Quality Standards
- **Python version**: 3.11+
- **Linting**: Ruff (configured in pyproject.toml)
- **Type checking**: Mypy strict mode
- **Testing**: Pytest with coverage
- **Pre-commit**: Hooks for consistency

### Contributing
1. Review invariants in `context/design/usage-pattern.md`
2. Keep public method signatures stable when feasible
3. Add/adjust tests for discovery, submission, mapping, or field changes
4. Sync documentation with behavior changes (README + design notes)
5. CI must pass `pixi run quality` locally before PR