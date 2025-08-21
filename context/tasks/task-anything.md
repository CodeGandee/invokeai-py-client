# General Information for All Tasks

- client api source code: `src/invokeai_py_client`
- terminology and concepts: `context/design/terminology.md`
- useful information for testing: `context/tasks/info/info-test-data.md`

if you are not sure about the InvokeAI web APIs:
- Look for the demos first: `<workspace>/examples`
- InvokeAI openapi json: `context\hints\invokeai-kb\invokeai-openapi.json`, use `jq` for faster search
- InvokeAI API list: `context\hints\invokeai-kb\invokeai-api-list.md`

# Task 1: revise the workflow subsystem

## Task 1.1: document the current implementation

- using example workflow json: `data\workflows\sdxl-flux-refine.json`
- example API call response: `data\api-calls\call-wf-sdxl-flux-refine.json`

the current workflow subsystem parses a
