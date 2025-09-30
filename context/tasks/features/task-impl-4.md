# General Information for All Tasks

- client api source code: `src/invokeai_py_client`
- terminology and concepts: `context/design/terminology.md`
- useful information for testing: `context/tasks/info/info-test-data.md`

if you are not sure about the InvokeAI web APIs:
- Look for the demos first: `<workspace>/examples`
- InvokeAI openapi json: `context\hints\invokeai-kb\invokeai-openapi-v6.3.json`, use `jq` for faster search
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

# Task 2.1.2: test the `flux-image-to-image` workflow

try this workflow `data\workflows\flux-image-to-image.json`, you need to:
- create a test board, name whatever you like, do not conflict with existing boards
- upload an image to the board
- use the image as the input to the workflow
- prepare all other inputs as required by the workflow
- submit the workflow and wait until it is completed

# Task 3: retrieve the workflow result

- workflow is given in `data\workflows\sdxl-flux-refine.json`
- example API call payload is in `data\api-calls\call-wf-sdxl-flux-refine.json`, use this for debug and reference
- a running InvokeAI system, with the web server running on `http://127.0.0.1:9090/`
- `tests\test_sdxl_flux_refine_workflow.py` have successfully submitted the workflow 

Before you start:
- read about the definition of `output-nodes` in `context/design/usage-pattern.md`
- DO NOT process the json directly, use the already implemented workflow subsystem to load the workflow and get the output nodes.


### Task 3.1: list the output nodes

- load the given workflow json, and list the output nodes, print their details with `rich` library, the test script should be put in `<workspace>/tmp` dir.

### Task 3.2: identify where the output goes

- example API call payload contains information about where the output goes, for each of the output nodes in previous step, you need to find out where the output goes, i.e. which board and which image, list them
- submit the workflow with random prompts, using models in the current InvokeAI system (127.0.0.1:9090), and wait until the workflow is completed
- through the response, find out for each output node, which board and which image it goes to, print the information in a readable format. YOU MUST rely on analyzing the response, DO NOT try to get images by time (finding the latest images in the board)

DONE:
result: `context\hints\howto-map-workflow-image-nodes-to-boards.md` and `tests\test_node_to_image_output_mapping.py`


### Task 3.3: revise `WorkflowHandle` about how to map output nodes to image names

based on the result of previous task, you need to revise the `WorkflowHandle` to map output nodes to image names after the workflow is submitted and completed, and use return that mapping to the user, so that user can download the images for specific output nodes.

test environment:
- a running InvokeAI system, with the web server running on `http://127.0.0.1:9090/`
