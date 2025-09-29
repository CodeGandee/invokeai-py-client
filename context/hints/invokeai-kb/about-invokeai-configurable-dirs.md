# About InvokeAI Configurable Directories

This note summarizes the main directory paths you can configure in InvokeAI and how to set them. Paths are relative to the InvokeAI “root” unless given as absolute paths.

## Root & Config File
- Root discovery order: `--root <path>` CLI → `INVOKEAI_ROOT` env → current venv’s parent → `~/invokeai`.
- Config file: `invokeai.yaml` in the root. Override with `--config <path>`.

## Key Directories (defaults)
- `models_dir` → `models/`: Installed models.
- `download_cache_dir` → `models/.download_cache`: Dynamically downloaded model files cache.
- `convert_cache_dir` → `models/.convert_cache`: Converted models cache (deprecated; used for migrations).
- `legacy_conf_dir` → `configs/`: Legacy checkpoint config files.
- `db_dir` → `databases/`: SQLite DB location.
- `outputs_dir` → `outputs/`: Generated images, thumbnails, archives.
- `custom_nodes_dir` → `nodes/`: Custom invocation nodes.
- `style_presets_dir` → `style_presets/`: Style preset files.
- `workflow_thumbnails_dir` → `workflow_thumbnails/`: Saved workflow thumbnails.
- `profiles_dir` → `profiles/`: cProfile graph output.

### Container Defaults (when unset)
When running the provided Docker setup and no paths are overridden, the container root is `/invokeai`. All directories resolve under this root:
- `/invokeai/models`
- `/invokeai/models/.download_cache`
- `/invokeai/outputs`
- `/invokeai/nodes`
- `/invokeai/style_presets`
- `/invokeai/workflow_thumbnails`
- `/invokeai/databases` (database file at `/invokeai/databases/invokeai.db`)
- `/invokeai/profiles`

## Configure via YAML
```yaml
# root/invokeai.yaml
models_dir: /mnt/models
outputs_dir: /data/invoke/outputs
db_dir: /data/invoke/databases
custom_nodes_dir: /opt/invoke/nodes
style_presets_dir: /opt/invoke/style_presets
workflow_thumbnails_dir: /data/invoke/workflow_thumbnails
```

## Configure via Environment
```bash
export INVOKEAI_ROOT=/srv/invoke
export INVOKEAI_MODELS_DIR=/mnt/models
export INVOKEAI_OUTPUTS_DIR=/data/invoke/outputs
export INVOKEAI_DB_DIR=/data/invoke/databases
export INVOKEAI_CUSTOM_NODES_DIR=/opt/invoke/nodes
export INVOKEAI_STYLE_PRESETS_DIR=/opt/invoke/style_presets
export INVOKEAI_WORKFLOW_THUMBNAILS_DIR=/data/invoke/workflow_thumbnails
```

## References
- configuration docs: https://invoke-ai.github.io/InvokeAI/configuration/
- local docs: context/refcode/InvokeAI/docs/configuration.md
- config fields: context/refcode/InvokeAI/invokeai/app/services/config/config_default.py:120
