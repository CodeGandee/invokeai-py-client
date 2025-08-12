# Terminology of this project

## Useful Information

- InvokeAI source code: `context\refcode\InvokeAI`
- InvokeAI knowledge base: `context\hints\invokeai-kb`
- InvokeAI example workflows and data: `data\workflows`
- Client API source code: `src/invokeai_py_client`
- Demo of how to use the InvokeAI REST api: `examples`

## Concepts

Here we list and define key concepts and terms used in this project to ensure consistent naming and understanding.

### InvokeAI (`invokeai`)
The InvokeAI system, source code at `context/refcode/InvokeAI`. Provides a REST API for workflow execution, asset management, and job tracking, essentially the model inference service, and we are wrapping selected parts of its API in a user-friendly Python client library.

### Client API (`client-api`)
This Python wrapper library that provides a user-friendly, Pythonic interface over selected InvokeAI capabilities. Focused on common tasks, not a 1:1 mapping of all backend APIs.

### Client-side InvokeAI instance (`invokeai-client`)
Top-level class representing a connection to an InvokeAI instance. Manages high-level operations (e.g., boards, jobs, assets), and creates/manages `client-workflow` objects.

### Client workflow (`client-workflow`)
An object created from a workflow definition JSON exported from the InvokeAI GUI. Exposes the workflow's public inputs, submits jobs to the server, tracks status, and returns outputs.

### Workflow definition (`workflow-def.json`)
JSON file exported from the InvokeAI GUI that describes a workflow. Includes nodes and a `form` section listing user-exposed inputs.

### Workflow inputs (`workflow-inputs`)
The set of user-exposed parameters defined in the workflow's `form`. Each input has a unique name (required by the client API) and is strongly typed by InvokeAI.

### InvokeAI primitive types (`invokeai-types`)
The primitive input/output types supported by InvokeAI workflows (see `context/hints/invokeai-kb/about-invokeai-workflow-input-types.md`). Used for both inputs and outputs.

### Client types (`client-types`)
Python classes that wrap `invokeai-types` (e.g., `InvokeAIIntegerField`, `InvokeAIStringField`). Handle value access, validation, and type conversion within the client API.


