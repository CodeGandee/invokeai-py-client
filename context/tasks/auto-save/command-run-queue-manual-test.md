Command: Run manual queue busy/cancel observation script

- Ensure the server endpoint is set in environment:
  - `export INVOKE_AI_ENDPOINT=http://localhost:19090`
- Source project `.env` to load the variable if present:
  - `set -a && source .env && set +a`
- Execute the script using Pixi's test environment (Python available):
  - `pixi run -e test python tmp/queue_busy_cancel_observe.py`

Files referenced
- tmp/queue_busy_cancel_observe.py
- data/workflows/sdxl-text-to-image.json
