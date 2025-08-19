# General Information for All Tasks

- client api source code: `src/invokeai_py_client`
- terminology and concepts: `context/design/terminology.md`
- useful information for testing: `context/tasks/info/info-test-data.md`

if you are not sure about the InvokeAI web APIs:
- Look for the demos first: `<workspace>/examples`
- InvokeAI openapi json: `context\hints\invokeai-kb\invokeai-openapi.json`, use `jq` for faster search
- InvokeAI API list: `context\hints\invokeai-kb\invokeai-api-list.md`

IMPORTANT:
- the `workflow-usecase`: `context\tasks\features\usecase-workflow.md`, we are implementing the workflow subsystem based on this usecase.

## Task 1: implement workflow construction

IMPORTANT reference:
- `context\hints\invokeai-kb\howto-interpret-workflow-form-field.md`, this is a guide to interpret the workflow form field, which is used to find out what input fields are defined in the workflow json file, essential to parse the workflow json file correctly.
- `context\tasks\features\task-explore-workflow.md`, this is a guide to interpret a particular workflow json file, which is used to understand how to construct the workflow definition data model from the workflow json file.

now, implement use case 1 in `workflow-usecase`.

Test environment:
- you can use ``data\workflows\sdxl-flux-refine.json` as a test workflow json file.
- you can access `127.0.0.1:9090` which is a running InvokeAI instance, to test anything related to the InvokeAI APIs.

