<div align="center">

# InvokeAI Python Client

**Turn InvokeAI GUI workflows into high-throughput Python batch pipelines**

[![PyPI](https://img.shields.io/pypi/v/invokeai-py-client.svg)](https://pypi.org/project/invokeai-py-client/)
[![Python Version](https://img.shields.io/pypi/pyversions/invokeai-py-client.svg)](https://pypi.org/project/invokeai-py-client/)
[![License](https://img.shields.io/github/license/CodeGandee/invokeai-py-client.svg)](https://github.com/CodeGandee/invokeai-py-client/blob/main/LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/CodeGandee/invokeai-py-client.svg)](https://github.com/CodeGandee/invokeai-py-client/stargazers)

</div>

## What is InvokeAI Python Client?

InvokeAI Python Client is a powerful library that bridges the gap between [InvokeAI](https://github.com/invoke-ai/InvokeAI)'s visual workflow editor and programmatic automation. Export your carefully crafted GUI workflows and run them at scale with typed Python code.

!!! success "Key Benefits"
    - **GUI-First Design**: Design visually, execute programmatically
    - **Type Safety**: Strongly-typed field system with Pydantic validation
    - **Batch Processing**: Run thousands of generations with parameter sweeps
    - **Index-Based Stability**: Reliable input access that survives workflow updates
    - **Zero Graph Manipulation**: Your workflow JSON stays exactly as designed

## Core Features

<div class="grid cards" markdown>

-   :material-workflow: **Workflow Automation**

    ---

    Load exported workflow JSON and execute with full control over inputs

    [:octicons-arrow-right-24: Workflow Guide](user-guide/workflow-basics.md)

-   :material-form-select: **Typed Field System**

    ---

    Strongly-typed fields with validation for strings, numbers, models, and more

    [:octicons-arrow-right-24: Field Types](user-guide/field-types.md)

-   :material-image-multiple: **Board & Image Management**

    ---

    Organize outputs, upload assets, and download results programmatically

    [:octicons-arrow-right-24: Board Management](user-guide/boards.md)

-   :material-map: **Output Mapping**

    ---

    Track which nodes produced which images with deterministic mapping

    [:octicons-arrow-right-24: Output Mapping](user-guide/output-mapping.md)

</div>

## Quick Example

```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

# Connect to InvokeAI server
client = InvokeAIClient.from_url("http://localhost:9090")

# Load your exported workflow
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("my-workflow.json")
)

# Discover and set inputs by index
for inp in wf.list_inputs():
    print(f"[{inp.input_index}] {inp.label}")

# Set values on typed fields
prompt = wf.get_input_value(0)  # Get by stable index
if hasattr(prompt, "value"):
    prompt.value = "A cinematic sunset over snowy mountains"

# Submit and wait
submission = wf.submit_sync()
result = wf.wait_for_completion_sync(timeout=180)

# Map outputs to images
for mapping in wf.map_outputs_to_images(result):
    print(f"Node {mapping['node_id']} -> {mapping.get('image_names')}")
```

## Who Is This For?

### Primary Audience
**InvokeAI GUI users** who want to automate their visual workflows for:
- Batch processing hundreds of images
- Parameter sweeps and A/B testing
- Scheduled generation jobs
- Regression testing and comparisons
- Building higher-level automation tools

### Secondary Audiences
- **Tool Builders**: Create CLIs and services on stable APIs
- **Contributors**: Extend with new field types and capabilities
- **Researchers**: Run controlled experiments with reproducible parameters

## Design Philosophy

!!! info "Core Principles"
    1. **Immutable Workflows**: Exported JSON is never modified structurally
    2. **Index-Based Access**: Form position determines stable indices
    3. **Type Safety**: Each field has a concrete, validated type
    4. **No Hidden Mutations**: Clear, explicit operations only

## Installation

=== "Pixi (Recommended)"

    ```bash
    pixi add invokeai-py-client
    pixi run python your_script.py
    ```

=== "pip"

    ```bash
    pip install invokeai-py-client
    ```

=== "Development"

    ```bash
    git clone https://github.com/CodeGandee/invokeai-py-client
    cd invokeai-py-client
    pixi run dev-setup
    ```

## Next Steps

<div class="grid cards" markdown>

-   :material-rocket-launch: **Get Started**

    Install the client and run your first workflow

    [:octicons-arrow-right-24: Quick Start](getting-started/quickstart.md)

-   :material-book-open-variant: **Learn Concepts**

    Understand indices, fields, and workflow execution

    [:octicons-arrow-right-24: Core Concepts](getting-started/concepts.md)

-   :material-code-tags: **Browse Examples**

    Explore working code for common use cases

    [:octicons-arrow-right-24: Examples](examples/index.md)

-   :material-api: **API Reference**

    Detailed documentation of all classes and methods

    [:octicons-arrow-right-24: API Docs](api-reference/index.md)

</div>

## Community & Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/CodeGandee/invokeai-py-client/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/CodeGandee/invokeai-py-client/discussions)
- **Contributing**: [See our contribution guide](developer-guide/contributing.md)

## License

This project is licensed under the MIT License. See [LICENSE](https://github.com/CodeGandee/invokeai-py-client/blob/main/LICENSE) for details.