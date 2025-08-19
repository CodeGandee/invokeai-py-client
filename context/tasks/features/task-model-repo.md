# General Information for All Tasks

- client api source code: `src/invokeai_py_client`
- terminology and concepts: `context/design/terminology.md`
- useful information for testing: `context/tasks/info/info-test-data.md`

if you are not sure about the InvokeAI web APIs:
- Look for the demos first: `<workspace>/examples`
- InvokeAI openapi json: `context\hints\invokeai-kb\invokeai-openapi.json`, use `jq` for faster search
- InvokeAI API list: `context\hints\invokeai-kb\invokeai-api-list.md`

## Implement the Model Repository subsystem `model-repo` in `client-api`

### Before you start
- to differentiate the "model" in "deep learning model" and "data model", we use `dnn-model` for the former and `data-model` for the latter. In terms of "Model Repository", we mean the `dnn-model` repository.
- The InvokeAI has type system, mainly based on Pydantic, the part related to model is in `context\refcode\InvokeAI\invokeai\app\invocations\model.py`
- We map the InvokeAI type system into our `ivk_fields`, see `src\invokeai_py_client\ivk_fields`
  
- We have a running InvokeAI system, with the web server running on `http://localhost:9090`, you can use this to test your implementation. Denote this as `invokeai-instance`.

- All temporary scripts and files should be placed `<workspace>/tmp`, create subdirectories for each task.


### Task 1: explore the InvokeAI dnn-model APIs

list me all the available dnn-models in the `invokeai-instance`, and their details, such as name, type, description, etc.

### Task 2: design the `model-repo` subsystem

- `model-repo` is a subsystem to manage the dnn-models, its implementation pattern is similar to the `board` subsystem, see `src\invokeai_py_client\board`, you shall read it first

- `dnn-model` is simpler than `board`, because they are considered as "static" data in our current version, so we do not need to implement the full CRUD operations, only the read operations are needed, so we do not need the `handle` class yet (which represents the runtime state of a dnn-model).

- write down its use case here, be concise, just the code and comments are enough.

#### Use Case of `model-repo`

```python
# Use Case 1: Basic Model Discovery
# Get all available models from InvokeAI system (API call)
model_repo = client.model_repo
models = model_repo.list_models()  # Calls /api/v2/models/
print(f"Found {len(models)} models")

# Use Case 2: User-Side Filtering by Type
# Users filter models themselves using InvokeAI enums
from invokeai_py_client.model import ModelType, BaseModelType, ModelFormat

# Get all models once (single API call)
models = model_repo.list_models()

# Users filter by type themselves
main_models = [m for m in models if m.type == ModelType.Main]
controlnets = [m for m in models if m.type == ModelType.ControlNet]
vaes = [m for m in models if m.type == ModelType.VAE]

for model in main_models:
    print(f"{model.name}: {model.base.value} ({model.format_file_size()})")

# Use Case 3: Architecture Compatibility
# Users check compatibility using model helper methods
flux_models = [m for m in models if m.is_compatible_with_base(BaseModelType.Flux)]
sdxl_models = [m for m in models if m.is_compatible_with_base(BaseModelType.StableDiffusionXL)]

print(f"FLUX compatible: {len(flux_models)}")
print(f"SDXL compatible: {len(sdxl_models)}")

# Use Case 4: Specific Model Lookup
# Look up specific model by key (API call)
model = model_repo.get_model_by_key("4ea8c1b5-e56c-47c0-949e-3805d06c1301")  # Calls /api/v2/models/i/{key}
if model:
    print(f"Found: {model.name} ({model.get_category()})")
    print(f"Compatible with FLUX: {model.is_compatible_with_base(BaseModelType.Flux)}")

# Use Case 5: User-Side Name Search
# Users search by name themselves
flux_by_name = [m for m in models if "flux" in m.name.lower()]

# Use Case 6: Workflow Planning
# Users find compatible model sets themselves
flux_components = {}
required_types = [ModelType.Main, ModelType.VAE, ModelType.CLIPEmbed, ModelType.T5Encoder]

for model_type in required_types:
    compatible = [m for m in models 
                 if m.type == model_type and m.is_compatible_with_base(BaseModelType.Flux)]
    flux_components[model_type] = compatible

# Check if workflow is viable
workflow_viable = all(len(flux_components[t]) > 0 for t in required_types)
if workflow_viable:
    print("FLUX workflow viable - all components available")
    
    # Select models for workflow
    main_model = flux_components[ModelType.Main][0]
    vae_model = flux_components[ModelType.VAE][0]
    # Use model.key and model.hash for workflow inputs

# Use Case 7: User-Side Storage Analysis
# Users calculate statistics themselves
models_with_size = [m for m in models if m.file_size is not None]
total_size = sum(m.file_size for m in models_with_size)
large_models = [m for m in models_with_size if m.file_size > 10 * 1024**3]  # >10GB

print(f"Total storage: {total_size / (1024**3):.2f} GB")
for model in large_models:
    print(f"Large: {model.name} ({model.format_file_size()})")

```

**Key Design Principles:**
- Repository only provides APIs that call InvokeAI system (`list_models`, `get_model_by_key`)
- Users perform their own filtering, searching, and analysis
- Uses InvokeAI enums for type safety (`ModelType`, `BaseModelType`, `ModelFormat`)
- No internal iteration methods - users can filter more efficiently themselves
- No caching - repository is stateless, users cache results themselves if needed

# Task 3: implement the `model-repo` subsystem

- implement the `model-repo` subsystem, according to the use case in task 2.
- the file structure and naming convention is similar to the `board` subsystem.
- use `dnn-model` as the name to represent models in InvokeAI, so that we do not confuse it with the data model or pydantic model.
- for data-models, first look at the `ivk_fields` in `src\invokeai_py_client\ivk_fields` to see if there is already a usable data-model defined, use them first.

# Task 3.1: rename `model` to `dnn_model`

- for `model-repo`, we use `dnn_model` to represent the InvokeAI dnn-model, so naming like the below shall be changed:

```python
# change it to DnnModelType
class ModelType(str, Enum):
    """Model type enum from InvokeAI taxonomy."""
    
    ONNX = "onnx"
    Main = "main"
    VAE = "vae"
    LoRA = "lora"
...

# change it to BaseDnnModelType
class BaseModelType(str, Enum):
    """Base model type enum from InvokeAI taxonomy."""
    
    Any = "any"
    StableDiffusion1 = "sd-1"
    StableDiffusion2 = "sd-2"
    StableDiffusion3 = "sd-3"
    StableDiffusionXL = "sdxl"
    StableDiffusionXLRefiner = "sdxl-refiner"

# change it to DnnModelFormat
class ModelFormat(str, Enum):
    """Storage format of model from InvokeAI taxonomy."""
    
    OMI = "omi"
    Diffusers = "diffusers"
    Checkpoint = "checkpoint"
    LyCORIS = "lycoris"
```

- filenames and dir names like `model/` should be changed to `dnn_model/`, `model_model.py` should be changed to `dnn_model_types.py` (avoid repeating "model" in the name), `model_repo.py` should be changed to `dnn_model_repo.py`, etc.

- function names and variable names should avoid beginning with `model_` (conflict with pydantic model), use `dnn_model_` instead. But function names using `model` in the middle of the name like (`get_model_by_key`) is fine.