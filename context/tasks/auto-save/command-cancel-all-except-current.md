Command: Cancel all jobs except the running one

- Source environment variables from project .env:
  - `set -a && source .env && set +a`
- Issue the cancel-all-except-current request (default queue):
  - `curl -sf -X PUT "$INVOKE_AI_ENDPOINT/api/v1/queue/default/cancel_all_except_current"`
- Optional: extract canceled count with jq:
  - `jq -r '.canceled // 0'`
