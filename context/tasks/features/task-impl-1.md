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

# Task 3.4: implement board image upload

the current `upload_image` method should be refactored into two methods:
- `upload_image_by_file`: takes a file path and uploads the image to the board, returns the uploaded image object. This will automatically handle the mime type and file size
- `upload_image_by_data`: upload image by encoded data, takes a byte array of encoded image (with imageio.imencode() or cv2.imencode()) and file extensions (can be something like `.png` or `png`), where file extension is used to determine the mime type, and uploads the image to the board, returns the uploaded image object. This will automatically handle the mime type and file size.

Note that, whenever possible, use `imageio` instead of `cv2` for image encoding/decoding, as it is more flexible and supports more formats, and will not have the rgb/bgr issue.

# Task 3.5: implement remaining image operations

- check if the following functions are correct:
  - `get_image`
  - `delete_image`
  - `move_image_to_board`
  - `star_image`
  - `unstar_image`
- remove `upload_image` method, it is not needed anymore, we have more specific methods for uploading images
- remove `get_starred_images` method, it is not needed anymore, we have `list_images` method that can filter by starred images
- `download_image` should not take a file path, it should return the image data as bytes, so that using `imageio`.imdecode() can decode the bytes into np.ndarray, in RGB/RGBA format, depending on the image type. To test this, you should upload an image to the board, then download it, and check if the image is correctly decoded by `imageio`.