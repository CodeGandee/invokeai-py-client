# General Information for All Tasks

- client api source code: `src/invokeai_py_client`
- terminology and concepts: `context/design/terminology.md`
- useful information for testing: `context/tasks/info/info-test-data.md`

if you are not sure about the InvokeAI web APIs:
- Look for the demos first: `<workspace>/examples`
- InvokeAI openapi json: `context\hints\invokeai-kb\invokeai-openapi-v6.3.json`, use `jq` for faster search
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

# Task 3: create an sdxl text to image in quick client

Implement a method in `QuickClient` to create an SDXL text-to-image generation task, submit it, wait for it to complete, and return the resulting image metadata.
- `QuickClient.generate_image_sdxl_t2i(positive_prompt: str, negative_prompt: str, width: int, height: int, steps: int | None, model_name : str | None, scheduler : str | None, board_id : str | None) -> IvkImage | None`
  - positive_prompt: the positive prompt for the generation
  - negative_prompt: the negative prompt for the generation
  - width: the width of the generated image, will be rounded to the nearest multiple of 8
  - height: the height of the generated image, will be rounded to the nearest multiple of 8
  - steps: the number of steps for the generation, if not set then use workflow default
  - model_name: the name of the model to use, if None, use the first model that has `sdxl` as its base type. Note that, the model_name will be matched to the available models in the server as a SUBSTRING MATCH, case insensitive. For example, if model_name is `dreamshaper`, and the server has a model named `DreamShaper_v10.safetensors`, then it will be matched. For multiple matches, the first one will be used.
  - scheduler: the scheduler to use, if None, use the workflow default. Scheduler names can be found in `src\invokeai_py_client\ivk_fields\enums.py`, the `SchedulerName` enum.
  - board_id: the board_id to save the generated image, if None, save to uncategorized board.
  - return: the IvkImage object of the generated image, None if failed or cancelled
  - raise ValueError if 
    - other errors during API calls, except cancellation (return None in this case)
  - use workflow to achieve this, the workflow is in `src\invokeai_py_client\quick\prebuilt-workflows\sdxl-text-to-image.json`, use that with the workflow subsystem to execute the generation task, using sync mode, you can check `examples\pipelines\sdxl-text-to-image.py` dir to find out how to use it (they are essentially the same workflow json).
