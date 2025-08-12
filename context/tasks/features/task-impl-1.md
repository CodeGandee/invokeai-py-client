# General Information for All Tasks

- client api source code: `src/invokeai_py_client`
- terminology and concepts: `context/design/terminology.md`
- useful information for testing: `context/tasks/info/info-test-data.md`

# Task: implement `InvokeAIClient`

- it should have a factory method `from_url` that takes a URL and returns an instance of `InvokeAIClient`, there is no `api_key` is needed
- all member variables should be defined in the `__init__` method, DO NOT create member variables in other methods
- `__init__` should take general parameters like args and kwargs, and does nothing special, the core logic is in the factory method
- `create_workflow` method should take a `WorkflowDefinition` object, which is constructed from a JSON file exported from the InvokeAI GUI, we shall avoid directly reading the JSON file client methods, these external resources should be used to construct data models, not directly used in methods that require the data, data is usually passed as data model objects.

# Task: refactor data models

typically, data models should be `pydantic` models, do not use plain Python classes to represent data models.
