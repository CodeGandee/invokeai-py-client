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
