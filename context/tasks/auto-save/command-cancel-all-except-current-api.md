Command: Cancel all except current using client API

- Source env vars from project .env:
  - `set -a && source .env && set +a`
- Run the Python script with Pixi test env:
  - `pixi run -e test python tmp/queue_cancel_all_except_current.py`

Files referenced
- tmp/queue_cancel_all_except_current.py
