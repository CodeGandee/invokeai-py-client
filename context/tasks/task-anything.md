# General Information for All Tasks

- client api source code: `src/invokeai_py_client`
- terminology and concepts: `context/design/terminology.md`
- useful information for testing: `context/tasks/info/info-test-data.md`

if you are not sure about the InvokeAI web APIs:
- Look for the demos first: `<workspace>/examples`
- InvokeAI openapi json: `context\hints\invokeai-kb\invokeai-openapi.json`, use `jq` for faster search
- InvokeAI API list: `context\hints\invokeai-kb\invokeai-api-list.md`

# Task 1: move image to board

test if you can create board using the board subsystem (`src/invokeai_py_client/board`):
- create a board, name it "mytest", and get the board_id `target-board-id`
- move the image `311a6fb0-c8cc-467d-812c-1d66c1c32c1c.png` to the "mytest" using `target-board-id`. 
  - Note that, you are not given the board_id from which this image can be found, so you need to implement a method to find image metadata (IvkImage) through BoardRepository, see if such function exists and correct first.

test scripts should be saved to #file:tests 

# Task 2: implement copy-image-to-board

First, add a `QuickClient` class in `src/invokeai_py_client/quick/quick_client.py`, which wraps around `InvokeAIClient` and provides quick methods for common tasks. `QuickClient` should be initialized with an `InvokeAIClient` instance.

Then,implement a method to copy an image to another board, without removing it from the source board, and without downloading and re-uploading the image. 
- `QuickClient.copy_image_to_board(image_name: str, target_board_id: str) -> IvkImage | None`
  - image_name: the name of the image to copy
  - target_board_id: the board_id of the target board
  - return: the copied IvkImage object if successful, None otherwise
  - raise ValueError if 
    - the target_board_id does not exist
    - the image does not exist
    - other errors during API calls
  - use a tiny workflow to achieve this, the workflow is in `src\invokeai_py_client\quick\prebuilt-workflows\copy-image.json`, use that with the workflow subsystem to execute the copy operation, using sync mode.