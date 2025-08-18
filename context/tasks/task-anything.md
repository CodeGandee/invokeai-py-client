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

# Task 1.1: revise `WorkflowHandle`

- we provide a new method `set_input_value(self, index, value: IvkField[Any]) -> None:` that allows users to update the value of an input field by passing an `IvkField` instance. This method will:
  - validate that the input index exists, and the type of the value matches the input field type
  - after setting, validate the input field using `IvkWorkflowInput.validate_input()`
- we provide a new method `get_input_value(self, index: int) -> IvkField[Any]:` that returns `IvkField` instance for the given input index. This allows users to access the field directly and modify its properties. 

After this change, also modify the use case description in `context/tasks/features/workflow-usecase.md` to reflect these changes.

# Task 2: provide json-constructor for `IvkField` subclasses

- `IvkField` should have a `from_json_dict(data: dict[str, Any]) -> IvkField` class method that creates an instance from a JSON-like dictionary, and a `to_json_dict()-> dict[str, Any]` instance method that serializes the field to a JSON-like dictionary. By default, throw `NotImplementedError` in both methods.

- revised all subclasses of `IvkField` to implement the json conversion methods, note that, because almost all subclasses of `IvkField` are Pydantic models, you should avoid code duplication, you can either do that in base class by detecting if the class is a Pydantic model, or you can use a mixin class that implements the json conversion methods and inherit it in all subclasses of `IvkField`.

# Task 3: revise use case 2 in `workflow-usecase.md`

The new design of `IvkField` does not guarantee that the `value` property is always present, revise use case 2 to avoid using `value` directly, unless you are sure the `value` property is present. Also look at other aspects (like json conversion etc) and revise the use case description accordingly.