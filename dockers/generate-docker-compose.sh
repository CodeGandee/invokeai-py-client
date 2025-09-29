#!/usr/bin/env bash
set -euo pipefail

# Generate .env (absolute paths) and docker-compose.yml based on CLI options.

OUTPUT_DIR=""
OUT_ENV=".env"
OUT_COMPOSE="docker-compose.yml"

# Absolute path helpers that do not cd
to_abs() {
  local p="$1"
  [[ -z "$p" ]] && return 0
  # expand ~
  case "$p" in
    ~*) p="${p/#\~/$HOME}" ;;
  esac
  if [[ "$p" = /* ]]; then
    printf "%s\n" "$p"
  else
    printf "%s/%s\n" "$PWD" "$p"
  fi
}

to_container_abs() {
  local p="$1"
  [[ -z "$p" ]] && return 0
  case "$p" in
    /*) printf "%s\n" "$p" ;;
    ~*) p="${p/#\~/$HOME}"; printf "%s\n" "$p" ;;
    *) printf "/%s\n" "$p" ;;
  esac
}

# Defaults
HOST_INVOKEAI_ROOT=""
CONTAINER_INVOKEAI_ROOT="/invokeai"
HOST_INVOKEAI_PORT="9090"
CONTAINER_INVOKEAI_PORT="9090"
GPU_DRIVER=""
RENDER_GROUP_ID=""

# Optional subdirs (host/container)
HOST_MODELS_DIR=""; CONTAINER_MODELS_DIR=""
HOST_DOWNLOAD_CACHE_DIR=""; CONTAINER_DOWNLOAD_CACHE_DIR=""
HOST_OUTPUTS_DIR=""; CONTAINER_OUTPUTS_DIR=""
HOST_CUSTOM_NODES_DIR=""; CONTAINER_CUSTOM_NODES_DIR=""
HOST_EXTRA_DIR=""; CONTAINER_EXTRA_DIR=""
HOST_CONFIG_YAML=""

usage() {
  cat <<EOF
Usage: $0 OUT_DIR [options]

Root & network:
  --host-invokeai-root PATH         Host root directory for InvokeAI data (default: ~/invokeai)
  --container-invokeai-root PATH    Container root directory (default: /invokeai)
  --host-port PORT                  Host port (default: 9090)
  --container-port PORT             Container port (default: 9090)
  --gpu-driver (cuda|rocm)          Force GPU service (default: auto-detect)
  --render-group-id GID             Group ID for render (ROCm)

Optional subdirs (mount if provided):
  --host-models-dir PATH            Host models directory
  --container-models-dir PATH       Container models directory
  --host-download-cache-dir PATH    Host download cache directory
  --container-download-cache-dir PATH  Container download cache directory
  --host-outputs-dir PATH           Host outputs directory
  --container-outputs-dir PATH      Container outputs directory
  --host-custom-nodes-dir PATH      Host custom nodes directory
  --container-custom-nodes-dir PATH Container custom nodes directory

Other mounts:
  --host-config-yaml PATH           Host path to invokeai.yaml to mount as \
                                    CONTAINER_INVOKEAI_ROOT/invokeai.yaml
  --host-extra-dir PATH             Host path to mount as extra resources dir
  --container-extra-dir PATH        Container path for extra dir (default: /mnt/extra)

EOF
}

OUTPUT_DIR=""

# Parse CLI (supports both '--opt value' and '--opt=value'); OUT_DIR is positional and required
while [[ $# -gt 0 ]]; do
  case "$1" in
    --host-invokeai-root)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      HOST_INVOKEAI_ROOT="$2"; shift 2;;
    --host-invokeai-root=*) HOST_INVOKEAI_ROOT="${1#*=}"; shift;;

    --container-invokeai-root)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      CONTAINER_INVOKEAI_ROOT="$2"; shift 2;;
    --container-invokeai-root=*) CONTAINER_INVOKEAI_ROOT="${1#*=}"; shift;;

    --host-port)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      HOST_INVOKEAI_PORT="$2"; shift 2;;
    --host-port=*) HOST_INVOKEAI_PORT="${1#*=}"; shift;;

    --container-port)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      CONTAINER_INVOKEAI_PORT="$2"; shift 2;;
    --container-port=*) CONTAINER_INVOKEAI_PORT="${1#*=}"; shift;;


    --gpu-driver)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      GPU_DRIVER="$2"; shift 2;;
    --gpu-driver=*) GPU_DRIVER="${1#*=}"; shift;;

    --render-group-id)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      RENDER_GROUP_ID="$2"; shift 2;;
    --render-group-id=*) RENDER_GROUP_ID="${1#*=}"; shift;;

    --host-models-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      HOST_MODELS_DIR="$2"; shift 2;;
    --host-models-dir=*) HOST_MODELS_DIR="${1#*=}"; shift;;

    --container-models-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      CONTAINER_MODELS_DIR="$2"; shift 2;;
    --container-models-dir=*) CONTAINER_MODELS_DIR="${1#*=}"; shift;;

    --host-download-cache-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      HOST_DOWNLOAD_CACHE_DIR="$2"; shift 2;;
    --host-download-cache-dir=*) HOST_DOWNLOAD_CACHE_DIR="${1#*=}"; shift;;

    --container-download-cache-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      CONTAINER_DOWNLOAD_CACHE_DIR="$2"; shift 2;;
    --container-download-cache-dir=*) CONTAINER_DOWNLOAD_CACHE_DIR="${1#*=}"; shift;;

    --host-outputs-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      HOST_OUTPUTS_DIR="$2"; shift 2;;
    --host-outputs-dir=*) HOST_OUTPUTS_DIR="${1#*=}"; shift;;

    --container-outputs-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      CONTAINER_OUTPUTS_DIR="$2"; shift 2;;
    --container-outputs-dir=*) CONTAINER_OUTPUTS_DIR="${1#*=}"; shift;;

    --host-custom-nodes-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      HOST_CUSTOM_NODES_DIR="$2"; shift 2;;
    --host-custom-nodes-dir=*) HOST_CUSTOM_NODES_DIR="${1#*=}"; shift;;

    --container-custom-nodes-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      CONTAINER_CUSTOM_NODES_DIR="$2"; shift 2;;
    --container-custom-nodes-dir=*) CONTAINER_CUSTOM_NODES_DIR="${1#*=}"; shift;;

    --host-config-yaml)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      HOST_CONFIG_YAML="$2"; shift 2;;
    --host-config-yaml=*) HOST_CONFIG_YAML="${1#*=}"; shift;;

    --host-extra-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      HOST_EXTRA_DIR="$2"; shift 2;;
    --host-extra-dir=*) HOST_EXTRA_DIR="${1#*=}"; shift;;
    --container-extra-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      CONTAINER_EXTRA_DIR="$2"; shift 2;;
    --container-extra-dir=*) CONTAINER_EXTRA_DIR="${1#*=}"; shift;;

    -h|--help) usage; exit 0 ;;
    --*) echo "Unknown option: $1" >&2; usage; exit 1 ;;
    *)
      if [[ -z "$OUTPUT_DIR" ]]; then
        OUTPUT_DIR="$1"; shift;
      else
        echo "Unexpected argument: $1" >&2; usage; exit 1;
      fi
      ;;
  esac
done

# Defaults for roots
if [[ -z "$HOST_INVOKEAI_ROOT" ]]; then
  HOST_INVOKEAI_ROOT="$HOME/invokeai"
fi

# Normalize to absolute paths
HOST_INVOKEAI_ROOT=$(to_abs "$HOST_INVOKEAI_ROOT")
CONTAINER_INVOKEAI_ROOT=$(to_container_abs "$CONTAINER_INVOKEAI_ROOT")

# Resolve output directory
if [[ -z "$OUTPUT_DIR" ]]; then
  echo "Error: OUT_DIR is required" >&2
  usage
  exit 1
fi
OUTPUT_DIR=$(to_abs "$OUTPUT_DIR")
mkdir -p "$OUTPUT_DIR"
OUT_ENV="$OUTPUT_DIR/.env"
OUT_COMPOSE="$OUTPUT_DIR/docker-compose.yml"

# Platform selection -> service
OS=$(uname -s || echo unknown)
ARCH=$(uname -m || echo unknown)

SERVICE="invokeai-cpu"
if [[ -n "$GPU_DRIVER" ]]; then
  case "$GPU_DRIVER" in
    cuda) SERVICE="invokeai-cuda" ;;
    rocm) SERVICE="invokeai-rocm" ;;
    *) SERVICE="invokeai-cpu" ;;
  esac
else
  case "$OS" in
    Darwin) SERVICE="invokeai-cpu" ;;
    Linux)
      case "$ARCH" in
        x86_64|amd64) SERVICE="invokeai-cuda" ;;
        aarch64|arm64) SERVICE="invokeai-cpu" ;;
        *) SERVICE="invokeai-cpu" ;;
      esac
      ;;
    MINGW*|MSYS*|CYGWIN*) SERVICE="invokeai-cpu" ;;
    *) SERVICE="invokeai-cpu" ;;
  esac
fi

# Normalize subdir paths if provided
HOST_MODELS_DIR=$(to_abs "${HOST_MODELS_DIR}") || true
CONTAINER_MODELS_DIR=$(to_container_abs "${CONTAINER_MODELS_DIR}") || true
HOST_DOWNLOAD_CACHE_DIR=$(to_abs "${HOST_DOWNLOAD_CACHE_DIR}") || true
CONTAINER_DOWNLOAD_CACHE_DIR=$(to_container_abs "${CONTAINER_DOWNLOAD_CACHE_DIR}") || true
HOST_OUTPUTS_DIR=$(to_abs "${HOST_OUTPUTS_DIR}") || true
CONTAINER_OUTPUTS_DIR=$(to_container_abs "${CONTAINER_OUTPUTS_DIR}") || true
HOST_CUSTOM_NODES_DIR=$(to_abs "${HOST_CUSTOM_NODES_DIR}") || true
CONTAINER_CUSTOM_NODES_DIR=$(to_container_abs "${CONTAINER_CUSTOM_NODES_DIR}") || true
HOST_CONFIG_YAML=$(to_abs "${HOST_CONFIG_YAML}") || true
HOST_EXTRA_DIR=$(to_abs "${HOST_EXTRA_DIR}") || true
CONTAINER_EXTRA_DIR=$(to_container_abs "${CONTAINER_EXTRA_DIR}") || true

# Decide which optional mounts are included (if any side provided)
include_models=false
include_download_cache=false
include_outputs=false
include_custom_nodes=false
include_config_yaml=false
include_extra=false

[[ -n "$HOST_MODELS_DIR$CONTAINER_MODELS_DIR" ]] && include_models=true
[[ -n "$HOST_DOWNLOAD_CACHE_DIR$CONTAINER_DOWNLOAD_CACHE_DIR" ]] && include_download_cache=true
[[ -n "$HOST_OUTPUTS_DIR$CONTAINER_OUTPUTS_DIR" ]] && include_outputs=true
[[ -n "$HOST_CUSTOM_NODES_DIR$CONTAINER_CUSTOM_NODES_DIR" ]] && include_custom_nodes=true
[[ -n "$HOST_CONFIG_YAML" ]] && include_config_yaml=true
[[ -n "$HOST_EXTRA_DIR$CONTAINER_EXTRA_DIR" ]] && include_extra=true

# Compute effective defaults for included mounts
if $include_models; then
  : "${HOST_MODELS_DIR:=$HOST_INVOKEAI_ROOT/models}"
  : "${CONTAINER_MODELS_DIR:=$CONTAINER_INVOKEAI_ROOT/models}"
fi
if $include_download_cache; then
  # default under models dir
  : "${HOST_DOWNLOAD_CACHE_DIR:=${HOST_MODELS_DIR:-$HOST_INVOKEAI_ROOT/models}/.download_cache}"
  : "${CONTAINER_DOWNLOAD_CACHE_DIR:=${CONTAINER_MODELS_DIR:-$CONTAINER_INVOKEAI_ROOT/models}/.download_cache}"
fi
if $include_outputs; then
  : "${HOST_OUTPUTS_DIR:=$HOST_INVOKEAI_ROOT/outputs}"
  : "${CONTAINER_OUTPUTS_DIR:=$CONTAINER_INVOKEAI_ROOT/outputs}"
fi
if $include_custom_nodes; then
  : "${HOST_CUSTOM_NODES_DIR:=$HOST_INVOKEAI_ROOT/nodes}"
  : "${CONTAINER_CUSTOM_NODES_DIR:=$CONTAINER_INVOKEAI_ROOT/nodes}"
fi
if $include_extra; then
  : "${CONTAINER_EXTRA_DIR:=/mnt/extra}"
fi

# Generate .env with absolute values (editable post-generation)
{
  echo "# Generated by generate-docker-compose.sh"
  echo "HOST_INVOKEAI_ROOT=$HOST_INVOKEAI_ROOT"
  echo "CONTAINER_INVOKEAI_ROOT=$CONTAINER_INVOKEAI_ROOT"
  echo "HOST_INVOKEAI_PORT=$HOST_INVOKEAI_PORT"
  echo "CONTAINER_INVOKEAI_PORT=$CONTAINER_INVOKEAI_PORT"
  if [[ -n "$GPU_DRIVER" ]]; then echo "GPU_DRIVER=$GPU_DRIVER"; fi
  if [[ -n "$RENDER_GROUP_ID" ]]; then echo "RENDER_GROUP_ID=$RENDER_GROUP_ID"; fi

  # Optional subdirs (only if included)
  if $include_models; then
    echo "HOST_MODELS_DIR=$HOST_MODELS_DIR"
    echo "CONTAINER_MODELS_DIR=$CONTAINER_MODELS_DIR"
    echo "INVOKEAI_MODELS_DIR=$CONTAINER_MODELS_DIR"
  fi
  if $include_download_cache; then
    echo "HOST_DOWNLOAD_CACHE_DIR=$HOST_DOWNLOAD_CACHE_DIR"
    echo "CONTAINER_DOWNLOAD_CACHE_DIR=$CONTAINER_DOWNLOAD_CACHE_DIR"
    echo "INVOKEAI_DOWNLOAD_CACHE_DIR=$CONTAINER_DOWNLOAD_CACHE_DIR"
  fi
  if $include_outputs; then
    echo "HOST_OUTPUTS_DIR=$HOST_OUTPUTS_DIR"
    echo "CONTAINER_OUTPUTS_DIR=$CONTAINER_OUTPUTS_DIR"
    echo "INVOKEAI_OUTPUTS_DIR=$CONTAINER_OUTPUTS_DIR"
  fi
  if $include_custom_nodes; then
    echo "HOST_CUSTOM_NODES_DIR=$HOST_CUSTOM_NODES_DIR"
    echo "CONTAINER_CUSTOM_NODES_DIR=$CONTAINER_CUSTOM_NODES_DIR"
    echo "INVOKEAI_CUSTOM_NODES_DIR=$CONTAINER_CUSTOM_NODES_DIR"
  fi
  if $include_config_yaml; then
    echo "HOST_CONFIG_YAML=$HOST_CONFIG_YAML"
  fi
  if $include_extra; then
    echo "HOST_EXTRA_DIR=$HOST_EXTRA_DIR"
    echo "CONTAINER_EXTRA_DIR=$CONTAINER_EXTRA_DIR"
  fi
} > "$OUT_ENV"

# Build compose file (references env variables from .env)

 D='$'

# Environment block (always include keys with sane defaults)
declare -a ENV_LINES
ENV_LINES+=("INVOKEAI_ROOT: ${D}{CONTAINER_INVOKEAI_ROOT:-/invokeai}")
ENV_LINES+=("INVOKEAI_PORT: ${D}{CONTAINER_INVOKEAI_PORT:-9090}")
ENV_LINES+=("INVOKEAI_MODELS_DIR: ${D}{INVOKEAI_MODELS_DIR:-/invokeai/models}")
ENV_LINES+=("INVOKEAI_DOWNLOAD_CACHE_DIR: ${D}{INVOKEAI_DOWNLOAD_CACHE_DIR:-/invokeai/models/.download_cache}")
ENV_LINES+=("INVOKEAI_OUTPUTS_DIR: ${D}{INVOKEAI_OUTPUTS_DIR:-/invokeai/outputs}")
ENV_LINES+=("INVOKEAI_CUSTOM_NODES_DIR: ${D}{INVOKEAI_CUSTOM_NODES_DIR:-/invokeai/nodes}")
if [[ "$SERVICE" == "invokeai-rocm" ]]; then
  ENV_LINES+=("AMD_VISIBLE_DEVICES: all")
  ENV_LINES+=("RENDER_GROUP_ID: ${D}{RENDER_GROUP_ID:-}")
fi

# Volumes block (conditionally add subdir mounts)
declare -a VOL_LINES
VOL_LINES+=("\"${D}{HOST_INVOKEAI_ROOT}:${D}{CONTAINER_INVOKEAI_ROOT:-/invokeai}\"")
$include_models && VOL_LINES+=("\"${D}{HOST_MODELS_DIR}:${D}{INVOKEAI_MODELS_DIR:-/invokeai/models}\"")
$include_download_cache && VOL_LINES+=("\"${D}{HOST_DOWNLOAD_CACHE_DIR}:${D}{INVOKEAI_DOWNLOAD_CACHE_DIR:-/invokeai/models/.download_cache}\"")
$include_outputs && VOL_LINES+=("\"${D}{HOST_OUTPUTS_DIR}:${D}{INVOKEAI_OUTPUTS_DIR:-/invokeai/outputs}\"")
$include_custom_nodes && VOL_LINES+=("\"${D}{HOST_CUSTOM_NODES_DIR}:${D}{INVOKEAI_CUSTOM_NODES_DIR:-/invokeai/nodes}\"")
$include_config_yaml && VOL_LINES+=("\"${D}{HOST_CONFIG_YAML}:${D}{CONTAINER_INVOKEAI_ROOT:-/invokeai}/invokeai.yaml\"")
$include_extra && VOL_LINES+=("\"${D}{HOST_EXTRA_DIR}:${D}{CONTAINER_EXTRA_DIR:-/mnt/extra}\"")

{
  echo "services:"
  echo "  $SERVICE:"
  echo "    image: ghcr.io/invoke-ai/invokeai:latest"
  echo "    env_file:"
  echo "      - .env"
  echo "    environment:"
  for e in "${ENV_LINES[@]}"; do echo "      $e"; done
  echo "    ports:"
  echo "      - \"${D}{HOST_INVOKEAI_PORT:-9090}:${D}{CONTAINER_INVOKEAI_PORT:-9090}\""
  echo "    tty: true"
  echo "    stdin_open: true"
  echo "    volumes:"
  for v in "${VOL_LINES[@]}"; do echo "      - $v"; done
  if [[ "$SERVICE" == "invokeai-cuda" ]]; then
    echo "    deploy:"
    echo "      resources:"
    echo "        reservations:"
    echo "          devices:"
    echo "            - driver: nvidia"
    echo "              count: 1"
    echo "              capabilities: [gpu]"
  fi
  if [[ "$SERVICE" == "invokeai-rocm" ]]; then
    echo "    runtime: amd"
  fi
} > "$OUT_COMPOSE"

echo "Generated:"
echo "  $OUT_ENV"
echo "  $OUT_COMPOSE (service: $SERVICE)"
echo "Run: docker compose -f '$OUT_COMPOSE' up -d"
