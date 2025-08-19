# General Information for All Tasks

- client api source code: `src/invokeai_py_client`
- terminology and concepts: `context/design/terminology.md`
- useful information for testing: `context/tasks/info/info-test-data.md`

if you are not sure about the InvokeAI web APIs:
- Look for the demos first: `<workspace>/examples`
- InvokeAI openapi json: `context\hints\invokeai-kb\invokeai-openapi.json`, use `jq` for faster search
- InvokeAI API list: `context\hints\invokeai-kb\invokeai-api-list.md`

# Task 1: verify the workflow submission and tracking

- use case description is in `context\tasks\features\usecase-workflow.md`, denote this as `workflow-usecase`

we have implemented use case 3.1 in `workflow-usecase`, but not yet tested, now you need to write a test case to verify the workflow submission and tracking.

test environment:
- a running InvokeAI system, with the web server running on `http://localhost:9090`
- the workflow 