# Design the InvokeAI python client API

we want to design a python client API for InvokeAI, which wraps the InvokeAI APIs in a user-friendly and pythonic way, with these design choices: 
-  we do not try to map all the APIs to the client API, InvokeAI itself is implemented in python, one can always use the InvokeAI python code directly if needed.
-  we design our client API with focused on accomplishing certain commonly used tasks, such as text-to-image generation, image-to-image generation, controlnet, image prompt support, etc.
-  we will design our API in object oriented way, with many classes supporting the major tasks.
-  we will use InvokeAI instances as a model inference service, so the python clients DO NOT have to run on a GPU machine, they do not have to know how to load, manage and run the models, they use this python API like using ComfyUI in a programmatic way, but with InvokeAI as the backend.

## Scope of the Client API

Here is what it is supposed to provide:

### using InvokeAI workflow as an image generation service in Python

User can:
- create a workflow based on a given workflow json file, such as `data\workflows\sdxl-text-to-image.json`, the workflow is created in the InvokeAI GUI and downloaded as a json file, denote this json as `workflow-def.json`. We DO NOT provide a way to create a workflow in the client API, this is quite complex and better done in the InvokeAI GUI. Denote this python-side workflow class as `WorkflowService`.
- the user set input to the `WorkflowService` instance, such as the text prompt, image, etc, and when everything is set, the user can call `WorkflowService.submit()` to submit the job to the InvokeAI backend, and get back a `WorkflowJob` instance. Inside the `WorkflowJob` instance, the user can get the job status, job details, and the generated image when the job is completed (using asyncio `Future`).
- because  `workflow-def.json` can have any number of input fields, the `WorkflowService` instance should provide a way to set the input fields in a dynamic manner, with these considerations:
  - InvokeAI has a fixed number of types of input/output fields, see 
  - for each input type, say `image`, we will have a corresponding python type, such as `ImagePrmitive`, which has a method `set_image(image: np.ndarray)` to set the image, and a method `get_image(): np.ndarray` to get the image.
