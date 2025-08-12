# Design the InvokeAI python client API

we want to design a python client API (denote this as `client-api`) for InvokeAI, which wraps the InvokeAI APIs in a user-friendly and pythonic way, with these design choices: 
-  we do not try to map all the APIs to the client API, InvokeAI itself is implemented in python, one can always use the InvokeAI python code directly if needed.
-  we design our client API with focused on accomplishing certain commonly used tasks, such as text-to-image generation, image-to-image generation, controlnet, image prompt support, etc.
-  we will design our API in object oriented way, with many classes supporting the major tasks.
-  we will use InvokeAI instances as a model inference service, so the python clients DO NOT have to run on a GPU machine, they do not have to know how to load, manage and run the models, they use this python API like using ComfyUI in a programmatic way, but with InvokeAI as the backend.

## Useful Information

- the client API code will be implmemented in `src/invokeai_py_client`
- InvokeAI docs: `context\refcode\InvokeAI\docs`

## use case of the Client API

### using a custom workflow created in InvokeAI GUI

- User create workflow in InvokeAI GUI, download the workflow json file, denote this json as `workflow-def.json`, see `data\workflows\sdxl-text-to-image.json` as an example.
  
- In `client-api`, user first create a `invokeai-client` instance, with address and port of the InvokeAI instance, this instance will represent the InvokeAI instance, and will manage many top-level operations, like getting board names, listing jobs, uploading and downloading assets, etc. `invokeai-client` will also create and manage top-level objects in `client-api`, like creating and managing `client-workflow` instances (see below), etc.

- User uses `client-api` to create a `client-workflow` instance with the `workflow-def.json` file, and then user interact with the `client-workflow` instance to set the input fields of the workflow, and then submit the workflow to the InvokeAI instance for execution, and get back results. Inside `client-workflow`, it has a reference to the `invokeai-client` instance, so it can use the `invokeai-client` instance to do the actual API calls to the InvokeAI instance.
  
- The workflow have their designed input fields in the `form` key in the `workflow-def.json`, because InvokeAI GUI allows user to designate some of the input fields of the nodes as inputs to the workflow, much like a public interface of the workflow. Other users of the workflow will usually just consider these input fields as adjustable parameters of the workflow, and will not tweak the fields in the workflow itself. Denote these input fields as `workflow-inputs`.
  
- `workflow-inputs` are named in the GUI with custom names, we assume these names are UNIQUE in the `workflow-inputs`, which can be used to identify the input fields. Though this is not a requirement in GUI, it IS a requirement in the client API because we need a way to identify the input fields. Below is part of a `workflow-def.json`, you can see there is a `fieldName` there, that is the user-specified name of the input field in GUI (if that field is in the `workflow-inputs`):

```json
...
"node-field-A4rGCtrNvu": {
    "id": "node-field-A4rGCtrNvu",
    "type": "node-field",
    "parentId": "root",
    "data": {
        "fieldIdentifier": {"nodeId": "noise:f4Bv4UWa22", "fieldName": "height"},
        "settings": {"type": "integer-field-config", "component": "number-input"},
        "showDescription": true
    }
},
...
```

- In `client-workflow`, user sets the `workflow-inputs` by name. And note that:
  - these inputs are typed in InvokeAI, see `context\hints\invokeai-kb\about-invokeai-workflow-input-types.md` for the types of the inputs. consider these as InvokeAI primitive types, call them `invokeai-types`, can be used in both input and output.
  - the `workflow-inputs` will only have these `invokeai-types` as inputs.
  - `workflow-def.json` will have dynamic number of inputs, so the `client-workflow` should be able to handle dynamic inputs, like using a single input function that takes a name and a value, checks the type of the value, and sets the input field.
  - each type of `invokeai-types` will have its own class in the `client-api`, like `InvokeAIIntegerField`, `InvokeAIStringField`, etc, denote these asd `client-types`. These classes will have methods to set and get the value of the input field, and will handle the type checking and conversion.

- After setting the `workflow-inputs`, user can submit the workflow to the InvokeAI instance, query for the job status, and get the results back when job is done. The results will be in the form of `client-types`, which can be used to get the output.

- Note that, the InvokeAI backend refers to "heavy" input data like images and masks by their names, not the actual data, so the `client-api` should handle the uploading of these "heavy" data to the InvokeAI instance, and get back the names, and use these names as inputs to the workflow. The `client-api` should also handle the downloading of these "heavy" output data from the InvokeAI instance when getting results.