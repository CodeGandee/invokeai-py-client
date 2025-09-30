Command: Check running and pending job counts

- Source environment variables from project .env:
  - `set -a && source .env && set +a`
- Fetch default queue status from the InvokeAI API:
  - `curl -sf "$INVOKE_AI_ENDPOINT/api/v1/queue/default/status"`
- Extract running and pending counts using jq:
  - `jq -r '"running=\(.queue.in_progress) pending=\(.queue.pending)"'`
