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

# Task 3: revise use case 2

based on the recent changes of the workflow subsystem, we need to revise the use case 2 in `context\tasks\features\usecase-workflow.md`, note that you can refer to use case 1 which is already implemented. source code of workflow subsystem is in `src\invokeai_py_client\workflow`.

# Task 4: refactor the `ivk_fields` module

`ivk_fields` module (`src\invokeai_py_client\ivk_fields`) contains various field types used in workflows, they have corresponding InvokeAI data models (see `context\hints\invokeai-kb\about-invokeai-workflow-input-types.md`). Now our `ivk_fields` is too complex and contains too much redundant information, we need to refactor them to make it more like the InvokeAI data models. Specifically:

- for each `ivk_field` type, in its docstring, it should contain the corresponding InvokeAI data model name, just for reference

- current `ivk_field`'s base and subclasses contain duplicated information, for example like below, both base and subclass have `value`, `name`, and `description` fields. Actually the base class should not contain any member fields at all, it should only contain the common methods, and raise `NotImplementedError` for methods that should be implemented by subclasses, and provide default implementations for methods that can be meaningfully shared across all subclasses. The base class acts like abstract class, but DO NOT use `abc` module, just use `NotImplementedError` to indicate that a method should be implemented by subclasses.

```python
class IvkField(Generic[T]):
    def __init__(
        self,
        value: T | None = None,
        name: str | None = None,
        description: str | None = None,
        **kwargs: Any
    ) -> None:
        """Initialize the field."""
        self._value = value
        self.name = name
        self.description = description
        self.metadata: dict[str, Any] = {}
```

```python
class IvkUNetField(BaseModel, IvkField[dict[str, Any]]):
    """
    UNet field with configuration for SD models.
    
    Contains UNet model, scheduler, LoRAs, and other configuration.
    
    Examples
    --------
    >>> field = IvkUNetField()
    >>> field.unet_model = {"key": "unet-key", "base": "sdxl", "type": "main"}
    >>> field.scheduler = {"key": "scheduler-key", "base": "any", "type": "scheduler"}
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[dict[str, Any]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    unet_model: Optional[dict[str, str]] = None
    scheduler: Optional[dict[str, str]] = None
    loras: list[dict[str, Any]] = []
    seamless_axes: list[str] = []
    freeu_config: Optional[dict[str, Any]] = None
```

- by design, `ivk_fields` ARE VALUES by themselves, they typically do not contain a `value` field, but rather the value is the instance itself, for example like below, you can see that the InvokeAI data model does not have a `value` field, it has `tokenizer`, `text_encoder`, etc. fields directly, so we should remove the `value` field from the `ivk_fields` base class and its subclasses.
- to/from InvokeAI api: I can see that the original `IvkField.value: dict[str, Any]` is used to store data that are directly sent to InvokeAI API, that is unnecessary. In our `IvkField` base class has two methods `to_api_format()` and `from_api_format()` that do the conversions, that is a good design, because our `IvkFields` are not exact replication of the InvokeAI data models, we may have additional fields or change the field names, so we need to convert them to/from the InvokeAI data models when sending/receiving data from the InvokeAI system. But we do not need to store the InvokeAI-compatible data in a `value` field, we can just let subclass do the conversion using their own fields.
- EXCEPTION: for primitive types like `string`, `int`, `float`, etc., we can keep the `value` field, because they are simple values wrapped into pydantic models, and they are used in workflows as inputs/outputs, so they should have a `value` field to represent the actual value. But that is also a decision left to subclass.

```python
# In our implementation, to represent a CLIP field.
class IvkCLIPField(BaseModel, IvkField[dict[str, Any]]):
    """
    CLIP field with text encoder configuration.
    
    Contains tokenizer, text encoder, and LoRA configuration.
    
    Examples
    --------
    >>> field = IvkCLIPField()
    >>> field.tokenizer = {"key": "tokenizer-key", "base": "sdxl", "type": "clip"}
    >>> field.text_encoder = {"key": "encoder-key", "base": "sdxl", "type": "text_encoder"}
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[dict[str, Any]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    tokenizer: Optional[dict[str, str]] = None
    text_encoder: Optional[dict[str, str]] = None
    skipped_layers: int = 0
    loras: list[dict[str, Any]] = []
```

```python
# context\refcode\InvokeAI\invokeai\app\invocations\model.py
# In InvokeAI system, the CLIP field is represented as:
class CLIPField(BaseModel):
    tokenizer: ModelIdentifierField = Field(description="Info to load tokenizer submodel")
    text_encoder: ModelIdentifierField = Field(description="Info to load text_encoder submodel")
    skipped_layers: int = Field(description="Number of skipped layers in text_encoder")
    loras: List[LoRAField] = Field(description="LoRAs to apply on model loading")
```

```python
# In InvokeAI system, primtive types DO HAVE a `value` field, we can also keep that for primitive types.
@invocation("string", title="String Primitive", tags=["primitives", "string"], category="primitives", version="1.0.1")
class StringInvocation(BaseInvocation):
    """A string primitive value"""

    value: str = InputField(default="", description="The string value", ui_component=UIComponent.Textarea)

    def invoke(self, context: InvocationContext) -> StringOutput:
        return StringOutput(value=self.value)
```