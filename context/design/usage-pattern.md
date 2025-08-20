# General Information for All Tasks

- client api source code: `src/invokeai_py_client`
- terminology and concepts: `context/design/terminology.md`
- useful information for testing: `context/tasks/info/info-test-data.md`

if you are not sure about the InvokeAI web APIs:
- Look for the demos first: `<workspace>/examples`
- InvokeAI openapi json: `context\hints\invokeai-kb\invokeai-openapi.json`, use `jq` for faster search
- InvokeAI API list: `context\hints\invokeai-kb\invokeai-api-list.md`

# Intended usage pattern and implementation of workflow subsystem

## CRITICAL

DO NOT read the "exposedFields" field in the workflow json, like this one, we DO NOT use these:

```json
{
    "name": "flux-image-to-image",
    ...
    "exposedFields": [
        {"nodeId": "f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90", "fieldName": "model"           },
        {"nodeId": "f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90", "fieldName": "t5_encoder_model"},
        {"nodeId": "f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90", "fieldName": "clip_embed_model"},
        {"nodeId": "f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90", "fieldName": "vae_model"       },
        {"nodeId": "01f674f8-b3d1-4df1-acac-6cb8e0bfb63c", "fieldName": "prompt"          },
        {"nodeId": "2981a67c-480f-4237-9384-26b68dbf912b", "fieldName": "image"           }
    ],

}
```

## Files
- example workflow json: `data\workflows\flux-image-to-image.json`, denote this as `workflow-def`
- example payload sent to the InvokeAI API: `data\api-calls\call-wf-flux-image-to-image-1.json` with the `workflow-inputs` filled in.

### Input and Output of Workflow
- When the workflow is created in GUI, the user selected some of the fields in the `wf-node` (nodes within a workflow), and add them to the `form` field in the workflow definition, these are essentially references to the fields of `wf-node`. These fields in the `form` can be considered as the `input-fields` of the workflow, other fields in the `wf-node` with values are considered as default values, usually NOT supposed to be changed by the user. 
- Some of the `input-fields` are related to output of the workflow, specifying the destination of the output, in particular, output to which `board`. 
- `output-nodes` refer to the `wf-node` of the that has `board` output, for example, the `save_image`or `l2i` node (see `context\refcode\InvokeAI\invokeai\app\invocations\image.py`), which in python has a `WithBoard` mixin, like below. There is another VERY IMPORTANT condition for a node to be an `output-node`, that is, its output board IS specified in the `form` field, that is, belongs to the `input-fields` of the workflow. Otherwise, those nodes are considered as `debug-nodes`

## Intended Usage Pattern

- user create make a `workflow-def` through InvokeAI's GUI, and download it for use.
- user creates a `WorkflowDefinition` instance from the `workflow-def` json file (see `src\invokeai_py_client\workflow\workflow_model.py`). IMPORTANT: `WorkflowDefinition.raw_data` is the original workflow json content, which is not modified by the client api, and we need this to craft the submission payload, denote this as `original_workflow_json`. 
  
- user load the `workflow-def` into the client api using `WorkflowRepository.create_workflow()`, get a `WorkflowHandle` instance. 
- - During parsing `workflow-def`, we will record the `jsonpath` of each input field in the `WorkflowHandle`, that `jsonpath` will point to an `dict` object in the (copy of)`WorkflowDefinition.raw_data`, which will be OVERWRITEN by contents of `IvkWorkflowInput.field.to_api_format()` (by matching keys) when the user sets the input value, the OVERWRITING process NEVER creates or deletes keys in the `original_workflow_json`, it only modifies the values of the fields. THIS IS VERY IMPORTANT, if you found a key that you do not know about, leave it as is, do not modify it. To do this correctly, you need to consult the InvokeAI api doc in `context\hints\invokeai-kb\invokeai-openapi.json`, and `context\hints\invokeai-kb\about-invokeai-workflow-input-types.md`, and its source code in `context\refcode\InvokeAI\invokeai`.

- user gets the input fields of the workflow using `WorkflowHandle.list_inputs()`, and fill in the inputs using `WorkflowHandle.set_input_value()`.
- - input fields are identified by looking at a `form` field in the `workflow-def`, you can see this in `.list_inputs()`. DO NOT look at the `exposedFields` in the json, it is irrelevant to the client api.

- user configures the inputs of the workflow using `WorkflowHandle.set_input_value()`, which will modify a copy of the `original_workflow_json` to fill in the inputs.
- - IMPORTANT: in this process, you NEVER modify the keys of the `original_workflow_json`, you only modify the values of the fields.
- - NOTE ON EDGE-CONNECTED INPUTS: The client API retains all literal input values in the final submission payload, even if they are also supplied by an incoming edge. This matches the behavior of the InvokeAI GUI and is required for server-side validation.

- craft a request based on the updated `WorkflowHandle.raw_data and submit it to the InvokeAI API.

- wait for the workflow to complete, and retrieve the results.

For more info, see `context\tasks\features\usecase-workflow.md`.

## Examples

### sdxl-flux-refine workflow
- workflow json: `data\workflows\sdxl-flux-refine.json`
- example API call: `data\api-calls\call-wf-sdxl-flux-refine.json`

### sdxl-text-to-image workflow
- workflow json: `data\workflows\sdxl-text-to-image.json`
- example API call: `data\api-calls\call-wf-sdxl-text-to-image.json`

### flux-image-to-image workflow
- workflow json: `data\workflows\flux-image-to-image.json`
- example API call: `data\api-calls\call-wf-flux-image-to-image-1.json`