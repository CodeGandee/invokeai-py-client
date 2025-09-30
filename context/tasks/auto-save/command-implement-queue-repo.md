Command: Implement QueueRepository → QueueHandle → JobHandle with integration tests

- Create queue package under `src/invokeai_py_client/queue/`:
  - `__init__.py` exporting `QueueRepository`, `QueueHandle`, `JobHandle`
  - `queue_models.py` with Pydantic models (QueueAndProcessorStatus, QueueItem, etc.)
  - `queue_handle.py` for queue-scoped operations
  - `job_handle.py` for job-scoped operations
- Wire `client.queue_repo` in `src/invokeai_py_client/client.py` using `QueueRepository.from_client(self)`
- Add integration tests (no mocks) under `unittests/queue/` that:
  - require `INVOKE_AI_ENDPOINT` to be set
  - submit a small SDXL text-to-image workflow (512x512, ~10–20 steps)
  - verify queue status transitions, current item retrieval, and cancel flow
- Use `data/workflows/sdxl-text-to-image.json` for the workflow definition
- Ensure strong typing per `.magic-context/instructions/strongly-typed.md` and follow `.magic-context/general/python-coding-guide.md`
- Reference upstream API in `context/hints/invokeai-kb/invokeai-openapi-v6.8.json` as needed
