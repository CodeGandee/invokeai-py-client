# General Information for All Tasks

- client api source code: `src/invokeai_py_client`
- terminology and concepts: `context/design/terminology.md`
- useful information for testing: `context/tasks/info/info-test-data.md`

if you are not sure about the InvokeAI web APIs:
- Look for the demos first: `<workspace>/examples`
- InvokeAI openapi json: `context\hints\invokeai-kb\invokeai-openapi.json`, use `jq` for faster search
- InvokeAI API list: `context\hints\invokeai-kb\invokeai-api-list.md`

# Task 1: implement `InvokeAIClient`

- it should have a factory method `from_url` that takes a URL and returns an instance of `InvokeAIClient`, there is no `api_key` is needed
- all member variables should be defined in the `__init__` method, DO NOT create member variables in other methods
- `__init__` should take general parameters like args and kwargs, and does nothing special, the core logic is in the factory method
- `create_workflow` method should take a `WorkflowDefinition` object, which is constructed from a JSON file exported from the InvokeAI GUI, we shall avoid directly reading the JSON file client methods, these external resources should be used to construct data models, not directly used in methods that require the data, data is usually passed as data model objects.

# Task 2: refactor data models

typically, data models should be `pydantic` models, do not use plain Python classes to represent data models.

# Task 3: implement board apis of `InvokeAIClient`

implement the following methods in `InvokeAIClient`:
- `list_boards`
- `get_board`
- `create_board`

# Task 3.1: uncategorized board

the board api should handle the uncategorized board, see the demo about how to handle the uncategorized board, it is treated as a special board, without a name.

# Task 3.2: get board by name

split the `get_board` method into two methods:
- `get_boards_by_name`: takes a board name and returns the all the boards with this name, if not found, returns empty list. Note that, board names are not unique, so this method returns a list of boards. Handle the uncategorized board as well, its name is "Uncategorized" (case sensitive).
- `get_board_by_id`: takes a board id and returns the board, if not found, returns `None` (python value). The board id is a string used in the InvokeAI API url.

# Task 3.3: query for images in a board

- implement `list_images`, `upload_image`, `get_image`, `delete_image`, `download_image` methods for board, using Repository pattern, see `context\hints\impl\about-api-client-architecture-patterns.md`

