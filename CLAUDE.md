# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python client library for interacting with InvokeAI APIs. The project provides a Pythonic interface over selected InvokeAI capabilities, focusing on common tasks like workflow execution, asset management, and job tracking.

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
pixi run docs-serve       # Serve documentation locally
pixi run docs-build       # Build documentation
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
src/
└── invokeai_py_client/
    ├── __init__.py              # Package initialization, public API exports
    ├── client.py                # Main InvokeAIClient class, connection management
    ├── exceptions.py            # Custom exception hierarchy
    ├── models.py                # Core Pydantic models (IvkImage, IvkJob, enums)
    ├── utils.py                 # Utility classes (AssetManager, BoardManager, etc.)
    │
    ├── ivk_fields/              # Field type system
    │   ├── __init__.py          # Public API exports for all field types
    │   ├── base.py              # IvkField[T] base class, mixins (Pydantic, Collection)
    │   ├── primitives.py        # Basic types: String, Integer, Float, Boolean (with value)
    │   ├── resources.py         # Resource refs: Image, Board, Latents, Tensor (with value)
    │   ├── models.py            # Model fields: ModelIdentifier, UNet, CLIP, Transformer, LoRA (no value)
    │   ├── complex.py           # Complex types: Color, BoundingBox, Collection (varied)
    │   └── enums.py             # Enumeration fields for predefined options
    │
    ├── board/                   # Board subsystem
    │   ├── __init__.py          # Exports: Board, BoardHandle, BoardRepository
    │   ├── board_model.py       # Board Pydantic model with uncategorized handling
    │   ├── board_handle.py      # BoardHandle: manages board state, image operations
    │   └── board_repo.py        # BoardRepository: board lifecycle, creates handles
    │
    └── workflow/                # Workflow subsystem
        ├── __init__.py          # Exports: WorkflowDefinition, WorkflowHandle, WorkflowRepository, IvkWorkflowInput
        ├── workflow_model.py    # WorkflowDefinition: Pydantic model for workflow JSON
        ├── workflow_handle.py   # WorkflowHandle: manages workflow state and inputs
        └── workflow_repo.py     # WorkflowRepository: workflow lifecycle, creates handles
```

### File Purpose Details

#### Core Files
- **`client.py`**: Central client class that maintains HTTP session, WebSocket connection, and provides access to repositories. Contains `_make_request()` helper for API calls.
- **`models.py`**: Shared Pydantic models used across subsystems - `IvkImage`, `IvkJob`, `IvkDnnModel`, `SessionEvent`, and enums (`JobStatus`, `ImageCategory`, `BaseModelEnum`).
- **`exceptions.py`**: Custom exception hierarchy for error handling.
- **`utils.py`**: Helper classes - `AssetManager` for uploads/downloads, `BoardManager` for board operations, `TypeConverter` for field conversions, `ProgressTracker` for monitoring.

#### Field Type System
- **`ivk_fields/base.py`**: `IvkField[T]` generic base class, `PydanticFieldMixin` for Pydantic integration, `IvkCollectionFieldMixin` for collection operations.
- **`ivk_fields/primitives.py`**: Basic field types with `value` property - `IvkStringField`, `IvkIntegerField`, `IvkFloatField`, `IvkBooleanField`. Support validation constraints.
- **`ivk_fields/resources.py`**: Resource reference fields with `value` property - `IvkImageField`, `IvkBoardField`, `IvkLatentsField`, `IvkTensorField`. Store references, not actual data.
- **`ivk_fields/models.py`**: Model-related fields WITHOUT `value` property - `IvkModelIdentifierField` (uses key, hash, name, base, type), `IvkUNetField`, `IvkCLIPField`, `IvkTransformerField`, `IvkLoRAField`.
- **`ivk_fields/complex.py`**: Complex fields - `IvkColorField` (no value, uses r,g,b,a), `IvkBoundingBoxField` (no value, uses x_min, x_max, y_min, y_max), `IvkCollectionField` (has value for list).
- **`ivk_fields/enums.py`**: Enumeration field with `value` property for predefined options.

#### Board Subsystem
- **`board_model.py`**: `Board` Pydantic model with special handling for uncategorized board ("none" board_id), includes helper methods like `uncategorized()` and `is_uncategorized()`.
- **`board_handle.py`**: `BoardHandle` class representing active board state - handles image upload/download, listing, starring, and board refresh operations.
- **`board_repo.py`**: `BoardRepository` manages board lifecycle - creates/deletes boards, retrieves board handles, maintains handle cache, special handling for uncategorized board.

#### Workflow Subsystem
- **`workflow_model.py`**: `WorkflowDefinition` Pydantic model for loading/parsing workflow JSON files, extracts metadata, nodes, edges, and exposed fields.
- **`workflow_handle.py`**: `WorkflowHandle` manages workflow state. `IvkWorkflowInput` model for typed inputs. Key methods: `get_input_value()`, `set_input_value()`, `validate_inputs()`.
- **`workflow_repo.py`**: `WorkflowRepository` creates workflow handles, manages workflow lifecycle, handles definition loading and validation.

## Architecture & Design Patterns

### Repository Pattern Architecture
The client uses a Repository pattern to separate concerns:
- **InvokeAIClient**: Main client class, manages connection and high-level operations
- **BoardRepository**: Handles all board and image management operations
- **WorkflowRepository**: Manages workflow definitions and execution

### Workflow Subsystem Design
Workflows support dual naming systems for inputs:
- **System names**: `{node_id}.{field_name}` - Always unique, guaranteed to work
- **User names**: Simple field names - May collide, raises ValueError when ambiguous

Key workflow components:
- **WorkflowDefinition**: Pydantic model for workflow JSON structure
- **IvkWorkflowInput**: Data model containing field metadata and typed field instance
- **Ivk* Field Types**: Type-safe field models with Pydantic validation (IvkStringField, IvkImageField, etc.)

### Field Type System
Field types follow a consistent pattern with abstract base class:
- All fields inherit from `IvkField[T]` generic base class (renamed from Field to avoid Pydantic conflicts)
- Each field implements: `validate_field()`, `to_api_format()`, `from_api_format()`, `to_json_dict()`, `from_json_dict()`
- **Fields WITH `value` property**: Primitives (String, Integer, Float, Boolean), Resources (Image, Board, Latents, Tensor), Collections, Enums
- **Fields WITHOUT `value` property**: IvkModelIdentifierField (uses key, hash, name, base, type), IvkColorField (uses r,g,b,a), IvkBoundingBoxField (uses x_min, x_max, y_min, y_max)
- Heavy data (images, models) use reference names, not actual data
- Validation happens at two levels: per-field (Pydantic `validate_assignment=True`) and workflow-level

### Data Models (Pydantic)
All API interactions use Pydantic models for type safety:
- **Board**: Board management with special "none" board_id for uncategorized
- **IvkImage, IvkJob**: Image and job tracking
- **WorkflowDefinition**: Workflow structure from JSON
- **Enums**: JobStatus, ImageCategory, BaseModelEnum

## Key Implementation Details

### Uncategorized Board Handling
The uncategorized board uses string "none" as board_id (not Python None) because:
- InvokeAI API expects literal "none" in URL paths: `/api/v1/boards/none/image_names`
- Python None would serialize to null in JSON, unusable in URL paths

### Workflow Input Management
When managing workflow inputs, the client:
1. Parses the workflow JSON's "exposedFields" section
2. Creates IvkWorkflowInput instances for each exposed field
3. Handles potential naming conflicts between nodes
4. Provides index-based access via `get_input_value()` and `set_input_value()`
5. Enforces type safety through `_lock_field_type()` mechanism
6. Supports both direct field modification and complete field replacement

### Heavy Data Management
Images and models are handled by reference:
- Upload returns a name/ID from InvokeAI backend
- Workflows reference data by these names
- After execution, explicitly delete uploaded assets to free space

## Testing & API Reference

### InvokeAI Test Server
- Default: `http://localhost:9090`
- API version: `/api/v1`
- OpenAPI spec: `context/hints/invokeai-kb/invokeai-openapi.json`

### Test Data Locations
- Example workflows: `data/workflows/` (SDXL, FLUX templates)
- API call examples: `data/api-calls/` (request payloads)
- Demo scripts: `examples/` (working API demonstrations)

## Important Constraints

- **No file creation**: Only edit existing files unless absolutely necessary
- **No documentation files**: Don't create *.md files unless explicitly requested
- **Repository pattern**: All resource management through repository classes
- **Type safety**: Use Pydantic models for all API data