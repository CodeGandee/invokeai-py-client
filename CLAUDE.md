# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python client library for interacting with InvokeAI APIs. The project provides a Pythonic interface over selected InvokeAI capabilities, focusing on common tasks like workflow execution, asset management, and job tracking.

**Current Status**: Repository pattern implementation complete (Task 3.1-3.7), workflow subsystem partially implemented, field types stubbed but not implemented.

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
    ├── exceptions.py            # Custom exception hierarchy (NotImplementedError stubs)
    ├── fields.py                # IvkField base class and typed field implementations
    ├── models.py                # Core Pydantic models (IvkImage, IvkJob, enums)
    ├── utils.py                 # Utility classes (AssetManager, BoardManager, etc.)
    │
    ├── board/                   # Board subsystem (complete implementation)
    │   ├── __init__.py          # Exports: Board, BoardHandle, BoardRepository
    │   ├── board_model.py       # Board Pydantic model with uncategorized handling
    │   ├── board_handle.py      # BoardHandle: manages board state, image operations
    │   └── board_repo.py        # BoardRepository: board lifecycle, creates handles
    │
    └── workflow/                # Workflow subsystem (partial implementation)
        ├── __init__.py          # Exports: WorkflowDefinition, WorkflowHandle, WorkflowRepository
        ├── workflow_model.py    # WorkflowDefinition: Pydantic model for workflow JSON
        ├── workflow_handle.py   # WorkflowHandle: manages workflow state, inputs, execution
        └── workflow_repo.py     # WorkflowRepository: workflow lifecycle, creates handles
```

### File Purpose Details

#### Core Files
- **`client.py`**: Central client class that maintains HTTP session, WebSocket connection, and provides access to repositories. Contains `_make_request()` helper for API calls.
- **`models.py`**: Shared Pydantic models used across subsystems - `IvkImage`, `IvkJob`, `IvkDnnModel`, `SessionEvent`, and enums (`JobStatus`, `ImageCategory`, `BaseModelEnum`).
- **`fields.py`**: Type system for workflow inputs - `IvkField[T]` base class and concrete implementations (`IntegerField`, `StringField`, `ImageField`, etc.). All methods currently `NotImplementedError`.
- **`exceptions.py`**: Custom exception hierarchy for error handling (currently all stubs).
- **`utils.py`**: Helper classes - `AssetManager` for uploads/downloads, `BoardManager` for board operations, `TypeConverter` for field conversions, `ProgressTracker` for monitoring (all stubs).

#### Board Subsystem (Complete)
- **`board_model.py`**: `Board` Pydantic model with special handling for uncategorized board ("none" board_id), includes helper methods like `uncategorized()` and `is_uncategorized()`.
- **`board_handle.py`**: `BoardHandle` class representing active board state - handles image upload/download, listing, starring, and board refresh operations.
- **`board_repo.py`**: `BoardRepository` manages board lifecycle - creates/deletes boards, retrieves board handles, maintains handle cache, special handling for uncategorized board.

#### Workflow Subsystem (In Progress)
- **`workflow_model.py`**: `WorkflowDefinition` Pydantic model for loading/parsing workflow JSON files, extracts metadata, nodes, edges, and exposed fields.
- **`workflow_handle.py`**: `WorkflowHandle` manages workflow execution state, `InkWorkflowInput` model for typed inputs. Methods for listing/setting inputs, submission, job tracking (all stubs).
- **`workflow_repo.py`**: `WorkflowRepository` creates workflow handles, manages workflow lifecycle, handles definition loading and validation (mostly stubs).

## Architecture & Design Patterns

### Repository Pattern Architecture
The client uses a Repository pattern to separate concerns:
- **InvokeAIClient**: Main client class, manages connection and high-level operations
- **BoardRepository**: Handles all board and image management operations
- **WorkflowRepository** (planned): Will manage workflow definitions and execution

Example usage flow:
```python
client = InvokeAIClient("localhost", 9090)
boards = client.board_repo.list_boards()  # Repository pattern access
```

### Workflow Subsystem Design
Workflows support dual naming systems for inputs:
- **System names**: `{node_id}.{field_name}` - Always unique, guaranteed to work
- **User names**: Simple field names - May collide, raises ValueError when ambiguous

Key workflow components:
- **WorkflowDefinition**: Pydantic model for workflow JSON structure
- **InkWorkflowInput**: Data model containing field metadata and typed field instance
- **Ink* Field Types**: Type-safe field models with Pydantic validation (InkStringField, InkImageField, etc.)

### Field Type System
Field types follow a consistent pattern with abstract base class:
- All fields inherit from `IvkField[T]` generic base class (renamed from Field to avoid Pydantic conflicts)
- Each field implements: `validate()`, `to_api_format()`, `from_api_format()`
- Heavy data (images, models) use reference names, not actual data
- Validation happens at two levels: per-field and workflow-level

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

### Workflow Input Resolution
When loading workflows, the client must:
1. Parse the workflow JSON's "exposedFields" section
2. Create InkWorkflowInput instances for each exposed field
3. Handle potential naming conflicts between nodes
4. Provide both system and user name access methods

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

### Key API Patterns
```python
# Board operations use Repository pattern
boards = client.board_repo.list_boards()
board = client.board_repo.get_board_by_id(board_id)

# Workflow execution flow
workflow = client.create_workflow(workflow_def)
inputs = workflow.list_inputs()  # Returns List[InkWorkflowInput]
workflow.set_input("prompt", "A beautiful landscape")
job = workflow.submit_sync()
results = workflow.wait_for_completion_sync()
```

## Current Implementation Status

### ✅ Completed
- Repository pattern for boards (BoardRepository)
- Board subsystem with BoardHandle/BoardRepository pattern
- Workflow subsystem with WorkflowHandle/WorkflowRepository pattern
- Pydantic models for core entities (Board, IvkImage, IvkJob, WorkflowDefinition)
- Subsystem reorganization into dedicated directories (board/, workflow/)
- IvkField base class and field type stubs
- Project configuration (pyproject.toml with pixi integration)

### 🚧 In Progress
- Workflow handle methods (all NotImplementedError)
- Field type implementations (base classes exist, methods not implemented)
- InkWorkflowInput implementation

### 📋 Next Steps (from task-impl-workflow.md)
1. Implement WorkflowHandle methods (list_inputs, get_input, set_input, submit)
2. Create InkWorkflowInput and complete field type models
3. Implement workflow submission and job tracking
4. Add asset cleanup after workflow completion
5. Write comprehensive tests for all components

## Important Constraints

- **No file creation**: Only edit existing files unless absolutely necessary
- **No documentation files**: Don't create *.md files unless explicitly requested
- **Repository pattern**: All resource management through repository classes
- **Type safety**: Use Pydantic models for all API data
- **Dual naming**: Support both system and user names for workflow inputs