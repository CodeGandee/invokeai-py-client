# HowTo: Specify GPU IDs in `docker-compose.yml`

## Overview
When running InvokeAI or other GPU-accelerated services via Docker Compose on a multi-GPU host, you often need to control *which* GPU(s) a container may access. This guide explains the supported approaches, prioritizing modern, declarative syntax while documenting compatible fallbacks.

## When To Use
Use this when:
- The host has multiple NVIDIA GPUs and you want workload isolation.
- You need to allocate distinct GPUs per service (e.g., inference vs. training).
- You want a portable, documented Compose configuration instead of ad‑hoc `docker run` flags.

## Prerequisites
- NVIDIA drivers installed on host (`nvidia-smi` works on the host).
- NVIDIA Container Toolkit installed (formerly nvidia-docker2). Docs: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
- Docker Engine & Docker Compose plugin (v2). Check:
  ```bash
  docker --version
  docker compose version
  ```
- For `deploy.resources.reservations.devices` syntax: recent Docker/Compose (Compose V2+). This syntax now works in regular (non-Swarm) compose usage.

## Method 1 (Recommended): Device Reservations Block
Declarative, explicit, future-proof.
```yaml
services:
  invokeai:
    image: your-org/invokeai:latest
    # ... other config (volumes, ports, etc.) ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["0"]      # Target GPU indices exactly
              capabilities: [gpu]
```
Multiple specific GPUs:
```yaml
            - driver: nvidia
              device_ids: ["0", "2"]
              capabilities: [gpu]
```
Request any N GPUs (not fixed IDs):
```yaml
            - driver: nvidia
              count: 2
              capabilities: [gpu]
```
Request ALL GPUs (two equivalent forms):
```yaml
services:
  invokeai:
    image: your-org/invokeai:latest
    gpus: all   # Simple shorthand (Compose v2+)
```

Or using an explicit reservation (engine interprets count == total available):
```yaml
services:
  invokeai:
    image: your-org/invokeai:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 9999        # Effectively "all"; Docker caps at available
              capabilities: [gpu]
```
Prefer the shorthand `gpus: all` for readability. Use the reservation form only if you need to stay stylistically consistent with other `deploy.resources` constraints.

Rules:
- Use *either* `device_ids` *or* `count` in a single entry.
- `capabilities` must include `gpu`; you can add `utility`, `video`, etc., if needed.

### Why prefer this?
- Clear intent checked by Docker engine.
- Avoids legacy runtime flags.
- Plays nicely with future orchestration features.

## Method 2: NVIDIA Visibility Environment Variables
Simpler, widely compatible, but less structured.
```yaml
services:
  invokeai:
    image: your-org/invokeai:latest
    environment:
      - NVIDIA_VISIBLE_DEVICES=0          # Single GPU
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
```
Multiple explicit GPUs:
```yaml
      - NVIDIA_VISIBLE_DEVICES=0,2
```
All GPUs:
```yaml
      - NVIDIA_VISIBLE_DEVICES=all
```
Hide all GPUs (debugging / CPU fallback):
```yaml
      - NVIDIA_VISIBLE_DEVICES=none
```

## Method 3 (Deprecated / Legacy): `runtime: nvidia`
Old style—avoid unless constrained.
```yaml
services:
  invokeai:
    image: your-org/invokeai:latest
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=0
```

## Choosing a Strategy
| Scenario | Use |
|----------|-----|
| Modern Compose, want clarity | Method 1 |
| Need broad backward compatibility | Method 2 |
| Stuck on very old Docker Engine | Method 3 (temporary) |

## Verifying GPU Assignment
After launching:
```bash
docker compose up -d
# Inspect inside container
docker compose exec invokeai nvidia-smi
```
You should only see the GPUs you allowed (check the "GPU" column and active processes).

Programmatic test (Python/TensorFlow example):
```bash
docker compose exec invokeai python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

## Troubleshooting
| Symptom | Cause | Fix |
|---------|-------|-----|
| Container sees all GPUs despite filtering | Older Docker ignoring `deploy` reservations | Upgrade Docker Engine & Compose; fall back to Method 2 if upgrade blocked |
| `nvidia-smi` missing inside container | Image lacks drivers interface (runtime/toolkit not installed) | Install NVIDIA Container Toolkit on host; recreate container |
| `Could not select device driver "nvidia"` | Toolkit not correctly registered with Docker | Reinstall / restart Docker (`sudo systemctl restart docker`) |
| `device_ids` ignored | Mixed with `count` or wrong indentation | Remove `count`; validate YAML spacing |
| Zero GPUs visible | Wrong `NVIDIA_VISIBLE_DEVICES` value (`none`/typo) | Set proper IDs or `all` |

## Minimal Combined Example
```yaml
services:
  invokeai:
    image: your-org/invokeai:latest
    ports:
      - "9090:9090"
    volumes:
      - ./data:/workspace/data
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["1"]
              capabilities: [gpu]
```

## Inline Comparison (Same Service, Two Styles)
Declarative (preferred):
```yaml
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["0"]
              capabilities: [gpu]
```
Env-based fallback:
```yaml
    environment:
      - NVIDIA_VISIBLE_DEVICES=0
```

## References / Further Reading
- Docker Official Docs (GPU in Compose): https://docs.docker.com/compose/how-tos/gpu-support/
- NVIDIA Container Toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/
- Compose Spec Devices: https://compose-spec.io/

## (Advanced) AMD ROCm / AMD GPU Notes
While this guide focuses on NVIDIA, AMD ROCm containers can also be managed with Docker Compose. Key differences:

| Aspect | NVIDIA | AMD ROCm |
|--------|--------|----------|
| Generic Compose shorthand | `gpus: all` (works; requests GPU resources) | Also supported (allocates all discoverable GPU devices) |
| Device selection env var | `NVIDIA_VISIBLE_DEVICES=0,2` | `HIP_VISIBLE_DEVICES=0,2` (preferred) or `ROCR_VISIBLE_DEVICES` (older) |
| Mandatory device nodes | Handled by toolkit runtime | Must mount `/dev/kfd` and `/dev/dri` (or use `--device` entries) |
| Common caps/security tweaks | Usually none extra | Often need `--group-add video`, maybe relaxed seccomp/apparmor for some ML stacks |
| Framework visibility | CUDA enumeration | HIP runtime enumerates GPUs filtered by `HIP_VISIBLE_DEVICES` |

### Minimal ROCm Compose Example (all GPUs)
```yaml
services:
  rocm-worker:
    image: rocm/pytorch:latest  # or rocm/vllm:... etc.
    gpus: all
    devices:
      - /dev/kfd
      - /dev/dri
    group_add:
      - video
    environment:
      - HSA_FORCE_FINE_GRAIN_PCIE=1          # (optional tuning)
      - HIP_VISIBLE_DEVICES=0,1              # Restrict if NOT using all
    security_opt:
      - seccomp=unconfined                   # Only if required by debug tools
      - apparmor=unconfined                  # Only if required
    cap_add:
      - SYS_PTRACE                           # Optional (profiling/debug)
```

### Selecting Specific AMD GPUs
Prefer environment filtering over implicit enumeration:
```yaml
environment:
  - HIP_VISIBLE_DEVICES=0,2
```
This masks other GPUs from HIP-enabled frameworks (PyTorch, TensorFlow ROCm builds, vLLM, etc.). Unlike NVIDIA's `device_ids` reservation (which integrates with the engine), AMD GPU isolation in Compose still often relies on environment-level filtering plus exposing the shared device nodes.

### Notes & Caveats
1. If you omit `/dev/kfd` or `/dev/dri`, ROCm user-space will not detect GPUs.
2. `gpus: all` currently acts broadly; fine-grained per-GPU reservation semantics for AMD may not provide hard isolation—processes with access to `/dev/kfd` and `/dev/dri` plus HIP env vars govern visibility.
3. Some performance tooling (rocprof) or debuggers need added capabilities (`SYS_PTRACE`) or unconfined seccomp—add only when necessary.
4. Use `HIP_VISIBLE_DEVICES` rather than `ROCR_VISIBLE_DEVICES` unless targeting very old ROCm.
5. Mixed vendor hosts (NVIDIA + AMD) are uncommon; if present, ensure images/frameworks compiled for the correct backend—`gpus: all` may enumerate only one vendor depending on runtime support.

### Quick Validation Inside Container
```bash
docker compose exec rocm-worker rocminfo | grep -E "Name:|Marketing" 
docker compose exec rocm-worker python -c "import torch; print(torch.cuda.device_count())"  # Torch ROCm still reports via CUDA-like API name space
```

### References (ROCm)
- ROCm Docker usage examples (vLLM): https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference/benchmark-docker/vllm
- HIP environment variables: https://rocm.docs.amd.com/
- General ROCm docs: https://rocm.docs.amd.com/


## Source Attribution
Examples adapted and condensed from Docker documentation and NVIDIA toolkit references (see links above).

---
*Revision:* 2025-09-30
