#!/usr/bin/env bash
set -euo pipefail

# Generate a blank/default invokeai.yaml by briefly running the InvokeAI container,
# then copying /invokeai/invokeai.yaml out.

IMAGE="ghcr.io/invoke-ai/invokeai:latest"
OUTPUT=""

usage() {
  cat <<EOF
Usage: $0 [--docker-image-tag IMAGE] [--output FILE]

Options:
  --docker-image-tag IMAGE  Full image ref (default: ghcr.io/invoke-ai/invokeai:latest)
  --output FILE             Write config to FILE; if omitted, prints to stdout
  -h, --help                Show this help

Behavior:
  - Starts a temporary CPU-only container in the background (no ports/volumes)
  - Waits for /invokeai/invokeai.yaml to appear
  - Copies it out and stops/removes the container
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --docker-image-tag)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      IMAGE="$2"; shift 2;;
    --docker-image-tag=*) IMAGE="${1#*=}"; shift;;
    --output)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      OUTPUT="$2"; shift 2;;
    --output=*) OUTPUT="${1#*=}"; shift;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is required" >&2
  exit 1
fi

NAME="invokeai-config-$(date +%s)-$RANDOM"

# Pull image (best effort)
docker pull "$IMAGE" >/dev/null 2>&1 || true

# Start container in background, no ports/volumes; let default CMD initialize config
docker run -d --name "$NAME" "$IMAGE" >/dev/null

cleanup() {
  docker stop -t 0 "$NAME" >/dev/null 2>&1 || true
  docker rm "$NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Wait up to 60s for config to exist
for i in $(seq 1 60); do
  if docker exec "$NAME" test -f /invokeai/invokeai.yaml 2>/dev/null; then
    break
  fi
  # check container still running; if not, bail early
  if ! docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
    echo "Error: container exited before config was created. Check 'docker logs $NAME' for details." >&2
    exit 1
  fi
  sleep 1
done

if ! docker exec "$NAME" test -f /invokeai/invokeai.yaml 2>/dev/null; then
  echo "Error: timed out waiting for /invokeai/invokeai.yaml to be created" >&2
  exit 1
fi

if [[ -n "$OUTPUT" ]]; then
  # Write to file
  docker exec "$NAME" cat /invokeai/invokeai.yaml > "$OUTPUT"
  echo "Wrote $OUTPUT"
else
  # Print to stdout only
  docker exec "$NAME" cat /invokeai/invokeai.yaml
fi

