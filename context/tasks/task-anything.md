# General Information for All Tasks

- client api source code: `src/invokeai_py_client`
- terminology and concepts: `context/design/terminology.md`
- useful information for testing: `context/tasks/info/info-test-data.md`

if you are not sure about the InvokeAI web APIs:
- Look for the demos first: `<workspace>/examples`
- InvokeAI openapi json: `context\hints\invokeai-kb\invokeai-openapi.json`, use `jq` for faster search
- InvokeAI API list: `context\hints\invokeai-kb\invokeai-api-list.md`

# Task 1: revise `WorkflowHandle` and `workflow-usecase`

- source code of `WorkflowHandle` is in `src\invokeai_py_client\workflow\workflow_handle.py`
- use case description is in `context\tasks\features\workflow-usecase.md`

- `get_all_inputs()` and `list_inputs()` are duplicated, keep only `list_inputs()`
- `def set_input(self, index: int, value: Any) -> None:` should be removed, user should modify input field directly, first get them and then set its properties
- `def get_missing_required_input_indices(self) -> list[int]:` should be removed, user can check `IvkWorkflowInput.required` by themselves
- `def validate_inputs(self) -> dict[int, list[str]]:` should delegate the validation task to the `IvkWorkflowInput` class, which should have a `validate_input()` method that redirects the call to the `IvkField` instance's `validate_field()`, return True/False and raises an exception if validation fails (this is also handled by the `IvkField` class, you do not have to capture the exception in `IvkWorkflowInput`)