# General Information for All Tasks

- client api source code: `src/invokeai_py_client`
- terminology and concepts: `context/design/terminology.md`
- useful information for testing: `context/tasks/info/info-test-data.md`

if you are not sure about the InvokeAI web APIs:
- Look for the demos first: `<workspace>/examples`
- InvokeAI openapi json: `context\hints\invokeai-kb\invokeai-openapi.json`, use `jq` for faster search
- InvokeAI API list: `context\hints\invokeai-kb\invokeai-api-list.md`

# Task 1: using repository pattern to implement workflow subsystem

- read `src\invokeai_py_client\repositories\board.py`, we are using repository pattern to manage boards in our InvokeAI client api, understand how it works
- read `context\tasks\features\task-impl-workflow.md`, that is the current design for the workflow subsystem, to be revised.
- we are going to apply the repo pattern to manage workflows, that is:
  - `workflow-handle` object should be created and managed by a repository `workflow-repo`.
  - `workflow-repo` creates `workflow-handle` based on a given `workflow-def` definition data model, which is constructed from a workflow json file. If the `workflow-def` is somehow inconsistent with the current InvokeAI system (e.g., using obsolete nodes, have some default models that are not available, etc.), `workflow-repo` should be able to handle it gracefully.
  - `workflow-handle` represents the running state of a workflow, like a handle, where workflow parameters, setting input, getting output is managed by the `workflow-handle`.

now, here is the task:
- create a workflow repository `src/invokeai_py_client/workflow/workflow_repo.py` based on the above design
- create a workflow definition data model `src/invokeai_py_client/workflow/workflow_def.py` to represent the workflow json file. Currently, you can just treat the whole json file as dict, without defining pythonic fields for the keys in the json.
- create a workflow handle `src/invokeai_py_client/workflow/workflow_handle.py` to represent the running state of a workflow, this will replace `src\invokeai_py_client\workflow.py`, and in the `task-impl-workflow.md` you can see such code block below, the `workflow-handle` is the `workflow` object in the code block, and we shall name its class as `WorkflowHandle` and object as `workflow_handle`.

```python
# Step 1: Read workflow JSON and create WorkflowDefinition data model
with open("data/workflows/sdxl-flux-refine.json", "r") as f:
    workflow_dict = json.load(f)

workflow_def = WorkflowDefinition.from_dict(workflow_dict)

# Step 2: Create workflow instance from the definition
workflow = client.create_workflow(workflow_def)
```

# Task 2: refactor the board subsystem

the current board subsystem should be refactored to follow similar pattern as the workflow subsystem, boards are something like a folder or album in InvokeAI system, so:
- it does not have `board-def` data model, because to create aboard, you only need to provide a name and some simple flags, see the current `src\invokeai_py_client\repositories\board.py`
- it has a `board-info` data model to represent the board information, just like the `Board` class in `src\invokeai_py_client\models.py`
- it has a `board-handle` to represent the running state of a board, which is similar to the `workflow-handle`, you can upload or download images to/from the board using the handle.
- it has a `board-repo` to manage the board handles, similar to the `workflow-repo`, this `board-repo` is a manager that represents the entry point of the board subsystem.