#!/usr/bin/env bash
set -euo pipefail

# Generate .env (absolute paths) and docker-compose.yml based on CLI options.
#
# Summary
# - Produces two files in OUT_DIR:
#   - OUT_DIR/.env                 (absolute paths and config)
#   - OUT_DIR/docker-compose.yml   (references variables from .env)
# - Chooses service automatically (CPU/CUDA/ROCm) or via --gpu-driver.
# - Always mounts the InvokeAI root; optional subdirs are mounted only if provided.
#
# Quick Examples
#   # CPU (auto)
#   ./dockers/generate-docker-compose.sh ./tmp/invokeai-compose
#   docker compose -f ./tmp/invokeai-compose/docker-compose.yml up -d
#
#   # CUDA with explicit models/outputs mounts
#   ./dockers/generate-docker-compose.sh ./tmp/compose \
#     --gpu-driver cuda \
#     --host-models-dir ~/invokeai/models \
#     --host-outputs-dir ~/invokeai/outputs
#
#   # ROCm with render group id and custom config
#   ./dockers/generate-docker-compose.sh ./tmp/compose \
#     --gpu-driver rocm --render-group-id 107 \
#     --host-config-yaml ~/invokeai/invokeai.yaml
#
#   # CUDA selecting specific GPUs (IDs 0 and 2)
#   ./dockers/generate-docker-compose.sh ./tmp/compose \
#     --gpu-driver cuda --gpu-ids 0,2
#
#   # CUDA using env-based selection (allocate all, then filter to first 2)
#   ./dockers/generate-docker-compose.sh ./tmp/compose \
#     --gpu-driver cuda --use-nvidia-env --gpu-count 2
#
# After generation, edit OUT_DIR/.env to tweak paths/ports and re-run docker compose.
# A helper script OUT_DIR/regen-compose.sh is also created to regenerate with the same options.

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

# Image
BASE_IMAGE_DEFAULT="ghcr.io/invoke-ai/invokeai:latest"
BASE_IMAGE="$BASE_IMAGE_DEFAULT"

# Optional subdirs (host/container)
HOST_MODELS_DIR=""; CONTAINER_MODELS_DIR=""
HOST_DOWNLOAD_CACHE_DIR=""; CONTAINER_DOWNLOAD_CACHE_DIR=""
HOST_OUTPUTS_DIR=""; CONTAINER_OUTPUTS_DIR=""
HOST_CUSTOM_NODES_DIR=""; CONTAINER_CUSTOM_NODES_DIR=""
HOST_EXTRA_DIR=""; CONTAINER_EXTRA_DIR=""
HOST_CONFIG_YAML=""

# GPU selection controls
GPU_IDS=""
GPU_COUNT=""
USE_NVIDIA_ENV=false
NO_REGEN_SCRIPT=false
WITH_INVOKEAI_YAML=false

usage() {
  cat <<EOF
Usage: $0 OUT_DIR [options]

Description
  Generate a portable Docker Compose setup for InvokeAI. Writes OUT_DIR/.env and
  OUT_DIR/docker-compose.yml. Defaults are safe; edit .env after generation if needed.

Requirements
  - Docker with the 'docker compose' plugin (v2+) installed and working.
  - The specified image must exist locally; this script does not pull images.

Outputs
  - ".env": absolute paths and ports consumed by docker-compose.yml
  - "docker-compose.yml": references variables from .env

Root & network
  --host-invokeai-root PATH         Host root for InvokeAI data (default: ~/invokeai)
  --container-invokeai-root PATH    Container root (default: /invokeai)
  --host-port PORT                  Host port (default: 9090)
  --container-port PORT             Container port (default: 9090)
  --gpu-driver (cuda|rocm)          Force GPU service (default: auto-detect)
  --render-group-id GID             Group ID for render (ROCm)
  --gpu-ids CSV                     Comma-separated GPU indices to use
  --gpu-count N|all                 Number of GPUs to use, or 'all' (mutually exclusive with --gpu-ids)
  --use-nvidia-env                  CUDA only: allocate all GPUs, then filter via NVIDIA_VISIBLE_DEVICES
  --no-regen-script                 Do not write OUT_DIR/regen-compose.sh

Image & config
  --base-image IMAGE:TAG            Docker image to use (default: ghcr.io/invoke-ai/invokeai:latest)
  --with-invokeai-yaml              Generate OUT_DIR/invokeai.yaml from the image (temporary container)

Optional subdirs (mounted only if provided)
  --host-models-dir PATH            Host models directory
  --container-models-dir PATH       Container models directory
  --host-download-cache-dir PATH    Host download cache directory
  --container-download-cache-dir PATH  Container download cache directory
  --host-outputs-dir PATH           Host outputs directory
  --container-outputs-dir PATH      Container outputs directory
  --host-custom-nodes-dir PATH      Host custom nodes directory
  --container-custom-nodes-dir PATH Container custom nodes directory

Other mounts
  --host-config-yaml PATH           Host path to mount as \
                                    CONTAINER_INVOKEAI_ROOT/invokeai.yaml
  --host-extra-dir PATH             Host path to mount as extra resources dir
  --container-extra-dir PATH        Container path for extra dir (default: /mnt/extra)

Notes
  - --gpu-ids and --gpu-count are mutually exclusive.
  - With --use-nvidia-env (CUDA), the compose requests all GPUs and uses
    NVIDIA_VISIBLE_DEVICES to restrict visibility. With --gpu-count N, the
    default selection is GPUs 0..N-1. For ROCm, HIP_VISIBLE_DEVICES is used.

Examples
  # CPU (auto-select)
  $0 ./tmp/invokeai-compose

  # Force CUDA and mount models/outputs
  $0 ./tmp/compose --gpu-driver cuda \
       --host-models-dir ~/invokeai/models \
       --host-outputs-dir ~/invokeai/outputs

  # ROCm with render group id
  $0 ./tmp/compose --gpu-driver rocm --render-group-id 107

  # CUDA: specific GPUs
  $0 ./tmp/compose --gpu-driver cuda --gpu-ids 0,2

  # CUDA: env-based selection of first 2 GPUs
  $0 ./tmp/compose --gpu-driver cuda --use-nvidia-env --gpu-count 2

Next steps
  docker compose -f OUT_DIR/docker-compose.yml up -d

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

    --gpu-ids)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      GPU_IDS="$2"; shift 2;;
    --gpu-ids=*) GPU_IDS="${1#*=}"; shift;;

    --gpu-count)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      GPU_COUNT="$2"; shift 2;;
    --gpu-count=*) GPU_COUNT="${1#*=}"; shift;;

    --use-nvidia-env)
      USE_NVIDIA_ENV=true; shift;;

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

    --no-regen-script)
      NO_REGEN_SCRIPT=true; shift;;

    --base-image)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      BASE_IMAGE="$2"; shift 2;;
    --base-image=*) BASE_IMAGE="${1#*=}"; shift;;

    --with-invokeai-yaml)
      WITH_INVOKEAI_YAML=true; shift;;

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
SELF_PATH=$(to_abs "$0")

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

# Validate mutually exclusive GPU flags
if [[ -n "$GPU_IDS" && -n "$GPU_COUNT" ]]; then
  echo "Error: --gpu-ids and --gpu-count cannot be used together" >&2
  exit 1
fi

# Normalize gpu-count token to lowercase for comparisons
GPU_COUNT_LC="${GPU_COUNT,,}"

# Helper: produce CSV 0..N-1
_first_n_csv() {
  local n="$1"; local out=""; local i
  if [[ -z "$n" || ! "$n" =~ ^[0-9]+$ || "$n" -le 0 ]]; then
    printf ""; return 0
  fi
  for ((i=0; i<n; i++)); do
    if [[ -z "$out" ]]; then out="$i"; else out+=",$i"; fi
  done
  printf "%s" "$out"
}

# Derive CUDA and ROCm GPU selection settings
CUDA_USE_GPUS_ALL=false
CUDA_NV_VISIBLE_DEVICES=""
CUDA_DEPLOY_DEVICE_IDS_YAML=""
CUDA_DEPLOY_COUNT=""

ROCM_HIP_VISIBLE_DEVICES=""

if [[ "$SERVICE" == "invokeai-cuda" ]]; then
  if $USE_NVIDIA_ENV; then
    # Allocate all GPUs and filter via env
    CUDA_USE_GPUS_ALL=true
    if [[ -n "$GPU_IDS" ]]; then
      CUDA_NV_VISIBLE_DEVICES="${GPU_IDS}"
    elif [[ -n "$GPU_COUNT" ]]; then
      if [[ "$GPU_COUNT_LC" == "all" ]]; then
        CUDA_NV_VISIBLE_DEVICES="all"
      elif [[ "$GPU_COUNT" =~ ^[0-9]+$ ]]; then
        CUDA_NV_VISIBLE_DEVICES="$(_first_n_csv "$GPU_COUNT")"
      fi
    else
      CUDA_NV_VISIBLE_DEVICES="all"
    fi
  else
    # Use deploy reservations (preferred declarative method)
    if [[ -n "$GPU_IDS" ]]; then
      # Build YAML array of quoted ids: ["0","2"]
      IFS=',' read -r -a _ids_arr <<< "$GPU_IDS"
      CUDA_DEPLOY_DEVICE_IDS_YAML="["
      for idx in "${_ids_arr[@]}"; do
        if [[ "$CUDA_DEPLOY_DEVICE_IDS_YAML" != "[" ]]; then
          CUDA_DEPLOY_DEVICE_IDS_YAML+=", "
        fi
        CUDA_DEPLOY_DEVICE_IDS_YAML+="\"${idx}\""
      done
      CUDA_DEPLOY_DEVICE_IDS_YAML+="]"
    elif [[ -n "$GPU_COUNT" ]]; then
      if [[ "$GPU_COUNT_LC" == "all" ]]; then
        CUDA_USE_GPUS_ALL=true
      elif [[ "$GPU_COUNT" =~ ^[0-9]+$ ]]; then
        CUDA_DEPLOY_COUNT="$GPU_COUNT"
      fi
    else
      CUDA_DEPLOY_COUNT="1"
    fi
  fi
fi

if [[ "$SERVICE" == "invokeai-rocm" ]]; then
  # ROCm prefers HIP_VISIBLE_DEVICES masking; allocate broad and filter via env
  if [[ -n "$GPU_IDS" ]]; then
    ROCM_HIP_VISIBLE_DEVICES="${GPU_IDS}"
  elif [[ -n "$GPU_COUNT" ]]; then
    if [[ "$GPU_COUNT_LC" == "all" ]]; then
      ROCM_HIP_VISIBLE_DEVICES="all"
    elif [[ "$GPU_COUNT" =~ ^[0-9]+$ ]]; then
      ROCM_HIP_VISIBLE_DEVICES="$(_first_n_csv "$GPU_COUNT")"
    fi
  else
    ROCM_HIP_VISIBLE_DEVICES="all"
  fi
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
  fi
  if $include_download_cache; then
    echo "HOST_DOWNLOAD_CACHE_DIR=$HOST_DOWNLOAD_CACHE_DIR"
    echo "CONTAINER_DOWNLOAD_CACHE_DIR=$CONTAINER_DOWNLOAD_CACHE_DIR"
  fi
  if $include_outputs; then
    echo "HOST_OUTPUTS_DIR=$HOST_OUTPUTS_DIR"
    echo "CONTAINER_OUTPUTS_DIR=$CONTAINER_OUTPUTS_DIR"
  fi
  if $include_custom_nodes; then
    echo "HOST_CUSTOM_NODES_DIR=$HOST_CUSTOM_NODES_DIR"
    echo "CONTAINER_CUSTOM_NODES_DIR=$CONTAINER_CUSTOM_NODES_DIR"
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
ENV_LINES+=("INVOKEAI_MODELS_DIR: ${D}{CONTAINER_MODELS_DIR:-/invokeai/models}")
ENV_LINES+=("INVOKEAI_DOWNLOAD_CACHE_DIR: ${D}{CONTAINER_DOWNLOAD_CACHE_DIR:-/invokeai/models/.download_cache}")
ENV_LINES+=("INVOKEAI_OUTPUTS_DIR: ${D}{CONTAINER_OUTPUTS_DIR:-/invokeai/outputs}")
ENV_LINES+=("INVOKEAI_CUSTOM_NODES_DIR: ${D}{CONTAINER_CUSTOM_NODES_DIR:-/invokeai/nodes}")
if [[ "$SERVICE" == "invokeai-rocm" ]]; then
  # Use HIP_VISIBLE_DEVICES for ROCm selection (default: all)
  if [[ -n "$ROCM_HIP_VISIBLE_DEVICES" ]]; then
    ENV_LINES+=("HIP_VISIBLE_DEVICES: $ROCM_HIP_VISIBLE_DEVICES")
  else
    ENV_LINES+=("HIP_VISIBLE_DEVICES: all")
  fi
  ENV_LINES+=("RENDER_GROUP_ID: ${D}{RENDER_GROUP_ID:-}")
fi
if [[ "$SERVICE" == "invokeai-cuda" && $USE_NVIDIA_ENV == true ]]; then
  # Filter CUDA GPUs via env if requested
  if [[ -n "$CUDA_NV_VISIBLE_DEVICES" ]]; then
    ENV_LINES+=("NVIDIA_VISIBLE_DEVICES: $CUDA_NV_VISIBLE_DEVICES")
  else
    ENV_LINES+=("NVIDIA_VISIBLE_DEVICES: all")
  fi
fi

# Volumes block (conditionally add subdir mounts)
declare -a VOL_LINES
VOL_LINES+=("\"${D}{HOST_INVOKEAI_ROOT}:${D}{CONTAINER_INVOKEAI_ROOT:-/invokeai}\"")
$include_models && VOL_LINES+=("\"${D}{HOST_MODELS_DIR}:${D}{CONTAINER_MODELS_DIR:-/invokeai/models}\"")
$include_download_cache && VOL_LINES+=("\"${D}{HOST_DOWNLOAD_CACHE_DIR}:${D}{CONTAINER_DOWNLOAD_CACHE_DIR:-/invokeai/models/.download_cache}\"")
$include_outputs && VOL_LINES+=("\"${D}{HOST_OUTPUTS_DIR}:${D}{CONTAINER_OUTPUTS_DIR:-/invokeai/outputs}\"")
$include_custom_nodes && VOL_LINES+=("\"${D}{HOST_CUSTOM_NODES_DIR}:${D}{CONTAINER_CUSTOM_NODES_DIR:-/invokeai/nodes}\"")
$include_config_yaml && VOL_LINES+=("\"${D}{HOST_CONFIG_YAML}:${D}{CONTAINER_INVOKEAI_ROOT:-/invokeai}/invokeai.yaml\"")
$include_extra && VOL_LINES+=("\"${D}{HOST_EXTRA_DIR}:${D}{CONTAINER_EXTRA_DIR:-/mnt/extra}\"")

{
  echo "services:"
  echo "  $SERVICE:"
  echo "    image: $BASE_IMAGE"
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
    if $USE_NVIDIA_ENV || $CUDA_USE_GPUS_ALL; then
      echo "    gpus: all"
    else
      echo "    deploy:"
      echo "      resources:"
      echo "        reservations:"
      echo "          devices:"
      echo "            - driver: nvidia"
      if [[ -n "$CUDA_DEPLOY_DEVICE_IDS_YAML" ]]; then
        echo "              device_ids: $CUDA_DEPLOY_DEVICE_IDS_YAML"
      else
        echo "              count: ${CUDA_DEPLOY_COUNT:-1}"
      fi
      echo "              capabilities: [gpu]"
    fi
  fi
  if [[ "$SERVICE" == "invokeai-rocm" ]]; then
    echo "    runtime: amd"
    echo "    gpus: all"
  fi
} > "$OUT_COMPOSE"

echo "Generated:"
echo "  $OUT_ENV"
echo "  $OUT_COMPOSE (service: $SERVICE)"
echo "Run: docker compose -f '$OUT_COMPOSE' up -d"

# Optionally generate a fresh invokeai.yaml from the selected image
if $WITH_INVOKEAI_YAML; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "Error: --with-invokeai-yaml requires docker to be installed" >&2
    exit 1
  fi
  NAME="invokeai-config-$(date +%s)-$RANDOM"
  OUT_YAML="$OUTPUT_DIR/invokeai.yaml"
  echo "Generating invokeai.yaml using image $BASE_IMAGE ..."
  if ! docker image inspect "$BASE_IMAGE" >/dev/null 2>&1; then
    echo "Error: image '$BASE_IMAGE' not found locally. Please 'docker pull $BASE_IMAGE' first." >&2
    exit 1
  fi
  docker run -d --name "$NAME" "$BASE_IMAGE" >/dev/null
  cleanup_cfg() { docker stop -t 0 "$NAME" >/dev/null 2>&1 || true; docker rm "$NAME" >/dev/null 2>&1 || true; }
  trap cleanup_cfg EXIT
  for i in $(seq 1 60); do
    if docker exec "$NAME" test -f /invokeai/invokeai.yaml 2>/dev/null; then
      break
    fi
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
  docker exec "$NAME" cat /invokeai/invokeai.yaml > "$OUT_YAML"
  echo "  Wrote $OUT_YAML"
  cleanup_cfg
  trap - EXIT
fi

# Generate regen script (replay this command with absolute paths)
if ! $NO_REGEN_SCRIPT; then
  REGEN_SH="$OUTPUT_DIR/regen-compose.sh"
  REGEN_GPU_DRIVER="$GPU_DRIVER"
  if [[ -z "$REGEN_GPU_DRIVER" ]]; then
    if [[ "$SERVICE" == "invokeai-cuda" ]]; then REGEN_GPU_DRIVER="cuda"; fi
    if [[ "$SERVICE" == "invokeai-rocm" ]]; then REGEN_GPU_DRIVER="rocm"; fi
  fi

  {
    echo "#!/usr/bin/env bash"
    echo "set -euo pipefail"
    echo "# Auto-generated; re-run the compose generator with the same options"
    printf '"%s" "%s" \\\n' "$SELF_PATH" "$OUTPUT_DIR"
    printf '  --host-invokeai-root "%s" \\\n' "$HOST_INVOKEAI_ROOT"
    printf '  --container-invokeai-root "%s" \\\n' "$CONTAINER_INVOKEAI_ROOT"
    printf '  --host-port "%s" \\\n' "$HOST_INVOKEAI_PORT"
    printf '  --container-port "%s"' "$CONTAINER_INVOKEAI_PORT"
    # Base image (always include for reproducibility)
    printf ' \\\n  --base-image "%s"' "$BASE_IMAGE"

    # GPU driver selection
    if [[ -n "$REGEN_GPU_DRIVER" ]]; then
      printf ' \\\n  --gpu-driver %s' "$REGEN_GPU_DRIVER"
    fi
    # ROCm render group id
    if [[ -n "$RENDER_GROUP_ID" ]]; then
      printf ' \\\n  --render-group-id %s' "$RENDER_GROUP_ID"
    fi
    # GPU selection
    if $USE_NVIDIA_ENV; then
      printf ' \\\n  --use-nvidia-env'
    fi
    if [[ -n "$GPU_IDS" ]]; then
      printf ' \\\n  --gpu-ids "%s"' "$GPU_IDS"
    fi
    if [[ -n "$GPU_COUNT" ]]; then
      printf ' \\\n  --gpu-count %s' "$GPU_COUNT"
    fi

    # Include with-invokeai-yaml flag if used
    if $WITH_INVOKEAI_YAML; then
      printf ' \\
  --with-invokeai-yaml'
    fi

    # Prevent regen script from overwriting itself on replay
    printf ' \\\n  --no-regen-script'



    # Optional mounts
    if $include_models; then
      printf ' \\\n  --host-models-dir "%s" \\\n' "$HOST_MODELS_DIR"
      printf '  --container-models-dir "%s"' "$CONTAINER_MODELS_DIR"
    fi
    if $include_download_cache; then
      printf ' \\\n  --host-download-cache-dir "%s" \\\n' "$HOST_DOWNLOAD_CACHE_DIR"
      printf '  --container-download-cache-dir "%s"' "$CONTAINER_DOWNLOAD_CACHE_DIR"
    fi
    if $include_outputs; then
      printf ' \\\n  --host-outputs-dir "%s" \\\n' "$HOST_OUTPUTS_DIR"
      printf '  --container-outputs-dir "%s"' "$CONTAINER_OUTPUTS_DIR"
    fi
    if $include_custom_nodes; then
      printf ' \\\n  --host-custom-nodes-dir "%s" \\\n' "$HOST_CUSTOM_NODES_DIR"
      printf '  --container-custom-nodes-dir "%s"' "$CONTAINER_CUSTOM_NODES_DIR"
    fi
    if $include_config_yaml; then
      printf ' \\\n  --host-config-yaml "%s"' "$HOST_CONFIG_YAML"
    fi
    if $include_extra; then
      printf ' \\\n  --host-extra-dir "%s" \\\n' "$HOST_EXTRA_DIR"
      printf '  --container-extra-dir "%s"' "$CONTAINER_EXTRA_DIR"
    fi
    echo
  } > "$REGEN_SH"
  chmod +x "$REGEN_SH"
  echo "Regen script: $REGEN_SH"
fi
