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

# Task 2: explore workflow submission and the generated image correspondence

we need to explore the InvokeAI API to find out that the workflow submission and the generated image correspondence, so that we can implement the workflow subsystem result retrieval.

# Task 2.1: submit a workflow

submit a workflow using the current workflow subsystem implementation, and wait until the workflow is completed.

- do it using the `sync` method
- workflow is given in `data\workflows\sdxl-text-to-image.json`
- a running InvokeAI system, with the web server running on `http://127.0.0.1:9090/`

# Task 2.1.1: revise the `WorkflowHandle` about how to craft the submission request

- when given `workflow-inputs`, you need to convert everything into a InvokeAI-compatible api request, part of the request is the workflow json content with inputs filled in.
- note that, by design, our `client-api` cannot construct the workflow json directly from scratch, because we did not map all InvokeAI workflow-related objects to the client api. What we need to do is to modify a copy of the original workflow json content, and then submit it to the InvokeAI API.
- original workflow json can be accessed by `WorkflowHandle.raw_data`
- you can use `jsonpath-ng` to find the fields in the workflow json that need to be filled in with the inputs, and then fill them in. It is actually better to just store the jsonpath in `IvkWorkflowInput` when you first parse the workflow json, so that you can use it later to fill in the inputs.

revise the implementation of relevant methods workflow subsystem.

- useful references
- - example workflow json: `data\workflows\sdxl-text-to-image.json`
- - example query sent to the InvokeAI API: `data\api-calls\call-wf-sdxl-text-to-image.json` with the `workflow-inputs` filled in.