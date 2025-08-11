# InvokeAI Workflow Schema and Node Reference Guide

This comprehensive guide covers the InvokeAI workflow JSON schema structure and predefined node system, based on analysis of the InvokeAI source code and documentation.

## Overview

InvokeAI uses a **graph-based workflow system** where:
- **Workflows** are enriched abstractions over graphs containing nodes and edges
- **Nodes** are invocations that process data (similar to functions)
- **Edges** connect nodes via their input/output fields
- **Fields** have typed data that dictates connection compatibility

## Workflow JSON Schema Structure

### Core Workflow Object (Version 3.0.0)

```json
{
  "name": "workflow-name",
  "author": "author-name", 
  "description": "workflow description",
  "version": "1.0.0",
  "contact": "contact-info",
  "tags": "tag1,tag2",
  "notes": "workflow notes",
  "exposedFields": [],
  "meta": {
    "category": "user",
    "version": "3.0.0"
  },
  "id": "unique-workflow-id",
  "form": {
    "elements": {
      // Form element definitions for linear view
    }
  },
  "nodes": [
    // Array of workflow nodes
  ],
  "edges": [
    // Array of workflow edges
  ]
}
```

### Node Structure

Each node in the `nodes` array follows this structure:

```json
{
  "id": "unique-node-id",
  "type": "invocation",
  "data": {
    "id": "unique-node-id",
    "version": "1.0.1",
    "nodePack": "invokeai",
    "label": "Custom Label",
    "notes": "Node notes",
    "type": "node_type_name",
    "inputs": {
      "field_name": {
        "name": "field_name",
        "label": "Field Label",
        "description": "Field description",
        "value": "field_value"
      }
    },
    "isOpen": true,
    "isIntermediate": false,
    "useCache": true
  },
  "position": {
    "x": 100.0,
    "y": 200.0
  }
}
```

### Edge Structure

Each edge in the `edges` array connects nodes:

```json
{
  "id": "unique-edge-id",
  "type": "default",
  "source": "source-node-id",
  "target": "target-node-id", 
  "sourceHandle": "output_field_name",
  "targetHandle": "input_field_name"
}
```

## Discovering Node Schemas

### How to Find Node JSON Schema

When you need to understand the schema for specific nodes, InvokeAI provides several discovery methods:

#### 1. OpenAPI Schema Endpoint

The most comprehensive source is the OpenAPI schema endpoint:

```bash
# Get complete schema with all node definitions
curl http://localhost:9090/openapi.json > invokeai-schema.json
```

This returns the full OpenAPI specification containing:
- All available invocation types
- Input/output field definitions  
- Field constraints and validation rules
- Default values and descriptions

#### 2. Schema Analysis Workflow

To find a specific node schema:

1. **Search by Node Type**: Look for `"type": "node_name"` in the OpenAPI JSON
2. **Find Component Schema**: Navigate to `components.schemas.NodeNameInvocation`
3. **Extract Properties**: The `properties` object contains all input fields
4. **Check Outputs**: Look for corresponding `NodeNameInvocationOutput` schema

**Example: Finding SDXL Model Loader Schema**

```json
// In components.schemas.SDXLModelLoaderInvocation
{
  "properties": {
    "type": {"default": "sdxl_model_loader"},
    "model": {
      "$ref": "#/components/schemas/MainModelField",
      "description": "SDXL Main model (UNet, VAE, CLIP1, CLIP2) to load"
    },
    "id": {"type": "string"},
    "is_intermediate": {"type": "boolean", "default": true},
    "use_cache": {"type": "boolean", "default": true}
  }
}
```

#### 3. Runtime Schema Discovery

Use the InvokeAI API to discover available nodes at runtime:

```python
import requests

# Get all available node types
response = requests.get("http://localhost:9090/api/v1/sessions/")
schema_url = "http://localhost:9090/openapi.json"
schema = requests.get(schema_url).json()

# Extract all invocation schemas
invocations = {}
for schema_name, schema_def in schema["components"]["schemas"].items():
    if schema_name.endswith("Invocation") and schema_name != "BaseInvocation":
        node_type = schema_def["properties"]["type"]["default"]
        invocations[node_type] = schema_def

# Find specific node
sdxl_loader = invocations.get("sdxl_model_loader")
print(f"SDXL Loader inputs: {list(sdxl_loader['properties'].keys())}")
```

#### 4. Source Code Analysis

For detailed understanding, examine the Python source:

```bash
# Find invocation class definitions
find ./invokeai/app/invocations/ -name "*.py" -exec grep -l "@invocation" {} \;

# Example: Look at SDXL model loader
grep -A 20 'class SDXLModelLoaderInvocation' invokeai/app/invocations/model.py
```

#### 5. Workflow Inspection

Examine existing workflows to see node usage patterns:

```python
import json

# Load existing workflow
with open("data/workflows/sdxl-text-to-image.json") as f:
    workflow = json.load(f)

# Extract node types and their configurations
for node in workflow["nodes"]:
    if node["data"]["type"] == "sdxl_model_loader":
        print("SDXL Model Loader Configuration:")
        print(json.dumps(node["data"]["inputs"], indent=2))
```

#### 6. Node Template Generation

InvokeAI's frontend generates node templates from OpenAPI schema:

```typescript
// Frontend parsing logic (reference)
const parseNodeSchema = (openApiSchema) => {
  const nodeType = openApiSchema.properties.type.default;
  const inputs = {};
  
  for (const [fieldName, fieldSchema] of Object.entries(openApiSchema.properties)) {
    if (!isReservedField(fieldName)) {
      inputs[fieldName] = parseFieldSchema(fieldSchema);
    }
  }
  
  return { type: nodeType, inputs };
};
```

### Schema Discovery Best Practices

1. **Start with OpenAPI**: Always begin with the complete OpenAPI schema
2. **Cross-reference Examples**: Look at existing workflows for real usage
3. **Check Version Compatibility**: Node schemas evolve, verify version matching
4. **Validate Field Types**: Ensure input/output compatibility in connections
5. **Test Incrementally**: Build simple workflows first, then add complexity

### Common Schema Lookup Patterns

**Find All Image Processing Nodes:**
```bash
jq '.components.schemas | to_entries | map(select(.value.properties.type.default | contains("img_"))) | map(.value.properties.type.default)' openapi.json
```

**Get Field Constraints:**
```bash
jq '.components.schemas.SDXLModelLoaderInvocation.properties.model' openapi.json
```

**List All Available Node Types:**
```bash
jq '.components.schemas | to_entries | map(select(.key | endswith("Invocation"))) | map(.value.properties.type.default)' openapi.json
```

## Using jq for Schema Discovery and Analysis

The `jq` command-line JSON processor is extremely powerful for exploring InvokeAI's OpenAPI schema. Here are proven patterns for schema discovery:

### Essential jq Commands for Schema Analysis

#### 1. Extract Complete Node Schema
```bash
# Get full schema for a specific node type
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "NODE_TYPE")) | .[0].value' openapi.json

# Example: Get FLUX ControlNet schema
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "flux_controlnet")) | .[0].value' openapi.json
```

#### 2. Filter Input Fields Only
```bash
# Extract only input fields with their properties
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "NODE_TYPE")) | .[0].value | {title, description, category, version, properties: (.properties | with_entries(select(.value.field_kind == "input")))}' openapi.json
```

#### 3. Get Input Field Names List
```bash
# Simple list of input field names for a node
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "NODE_TYPE")) | .[0].value | {title, input_fields: [.properties | to_entries[] | select(.value.field_kind == "input") | .key]}' openapi.json
```

#### 4. Extract Node Types from Workflow
```bash
# Get all node types used in a workflow file
jq '.nodes[].data.type' workflow.json

# Get unique node types with counts
jq '.nodes[].data.type | group_by(.) | map({type: .[0], count: length})' workflow.json
```

#### 5. Find Nodes by Category
```bash
# Find all nodes in a specific category (e.g., "image", "math", "controlnet")
jq '.components.schemas | to_entries | map(select(.value.properties.category.default == "CATEGORY")) | map(.value.properties.type.default)' openapi.json

# Example: Find all image processing nodes
jq '.components.schemas | to_entries | map(select(.value.properties.category.default == "image")) | map(.value.properties.type.default)' openapi.json
```

#### 6. Schema Field Analysis
```bash
# Get field types and constraints for a specific node
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "NODE_TYPE")) | .[0].value.properties | to_entries[] | select(.value.field_kind == "input") | {field: .key, type: .value.type, default: .value.default, constraints: {minimum: .value.minimum, maximum: .value.maximum, description: .value.description}}' openapi.json
```

#### 7. Find Required vs Optional Fields
```bash
# List required fields for a node
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "NODE_TYPE")) | .[0].value.properties | to_entries[] | select(.value.orig_required == true) | .key' openapi.json

# List optional fields with defaults
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "NODE_TYPE")) | .[0].value.properties | to_entries[] | select(.value.orig_required != true and .value.default) | {field: .key, default: .value.default}' openapi.json
```

#### 8. Output Field Discovery
```bash
# Find output schema for a node
jq '.components.schemas | to_entries | map(select(.key | endswith("Output"))) | map(select(.value.properties.type.default == "NODE_TYPE_output")) | .[0].value' openapi.json

# Example: Find output fields for denoise_latents
jq '.components.schemas.DenoiseLatentsInvocationOutput' openapi.json
```

#### 9. Version and Compatibility Check
```bash
# Get version information for all nodes
jq '.components.schemas | to_entries | map(select(.key | endswith("Invocation"))) | map({type: .value.properties.type.default, version: .value.properties.version.default, category: .value.properties.category.default})' openapi.json
```

#### 10. Advanced Field Type Analysis
```bash
# Find all unique field types used across all nodes
jq '.components.schemas | to_entries | map(select(.key | endswith("Invocation"))) | map(.value.properties | to_entries[] | select(.value.field_kind == "input") | .value.type) | unique' openapi.json

# Find nodes using specific field types (e.g., ImageField)
jq '.components.schemas | to_entries | map(select(.key | endswith("Invocation"))) | map(select(.value.properties | to_entries[] | select(.value["$ref"] == "#/components/schemas/ImageField"))) | map(.value.properties.type.default)' openapi.json
```

### Workflow-Specific jq Analysis

#### Analyze Existing Workflows
```bash
# Get workflow metadata
jq '{name, author, description, version, category: .meta.category, schema_version: .meta.version}' workflow.json

# Count nodes by type in workflow
jq '.nodes | group_by(.data.type) | map({type: .[0].data.type, count: length})' workflow.json

# Extract all edges with connection details
jq '.edges[] | {from: .source, to: .target, output_field: .sourceHandle, input_field: .targetHandle}' workflow.json

# Find disconnected nodes (nodes with no edges)
jq '.nodes[] | select(.id as $id | [.] | map(.id) - ([.edges[].source, .edges[].target] | unique) | length > 0) | .data.type' workflow.json
```

#### Node Position and Layout Analysis
```bash
# Get node positions for layout analysis
jq '.nodes[] | {type: .data.type, x: .position.x, y: .position.y, label: .data.label}' workflow.json

# Find nodes by position range
jq '.nodes[] | select(.position.x > 100 and .position.x < 500) | {type: .data.type, position: .position}' workflow.json
```

### Practical Schema Discovery Workflow

Here's a complete workflow for discovering and understanding any node:

```bash
# Step 1: Find if node exists
NODE_TYPE="flux_denoise"
jq --arg type "$NODE_TYPE" '.components.schemas | to_entries | map(select(.value.properties.type.default == $type)) | length' openapi.json

# Step 2: Get basic info
jq --arg type "$NODE_TYPE" '.components.schemas | to_entries | map(select(.value.properties.type.default == $type)) | .[0].value | {title, description, category: .properties.category.default, version: .properties.version.default}' openapi.json

# Step 3: List input fields
jq --arg type "$NODE_TYPE" '.components.schemas | to_entries | map(select(.value.properties.type.default == $type)) | .[0].value.properties | to_entries[] | select(.value.field_kind == "input") | .key' openapi.json

# Step 4: Get field details
jq --arg type "$NODE_TYPE" '.components.schemas | to_entries | map(select(.value.properties.type.default == $type)) | .[0].value.properties | to_entries[] | select(.value.field_kind == "input") | {field: .key, type: .value.type, required: .value.orig_required, default: .value.default, description: .value.description}' openapi.json

# Step 5: Find output schema
jq --arg type "$NODE_TYPE" --arg output_type "${NODE_TYPE}_output" '.components.schemas | to_entries | map(select(.key | test(".*Output$"))) | map(select(.value.properties.type.default == $output_type)) | .[0].value' openapi.json
```

### PowerShell-Specific jq Usage

When using jq in PowerShell, be aware of these syntax considerations:

```powershell
# Use single quotes to avoid PowerShell string interpolation
jq '.components.schemas | keys' openapi.json

# For complex queries, use here-strings or escape properly
$query = @'
.components.schemas | to_entries | 
map(select(.value.properties.type.default == "flux_denoise")) | 
.[0].value
'@
jq $query openapi.json

# Pipe to file in PowerShell
jq '.components.schemas | keys' openapi.json | Out-File -Encoding UTF8 schema_keys.txt
```

### Schema Validation with jq

```bash
# Validate workflow schema version
jq 'if .meta.version == "3.0.0" then "Valid schema version" else "Invalid schema version: " + .meta.version end' workflow.json

# Check for required workflow fields
jq 'if (.nodes and .edges and .meta) then "Valid workflow structure" else "Missing required fields" end' workflow.json

# Validate node structure
jq '.nodes[] | if (.id and .type and .data and .position) then empty else "Invalid node: " + .id end' workflow.json
```

These jq commands provide a comprehensive toolkit for exploring, analyzing, and validating InvokeAI workflow schemas. They're particularly useful when developing custom workflows or debugging existing ones.

## Complete Workflow Analysis Methodology

This section provides a systematic approach for analyzing any InvokeAI workflow JSON file to extract node information, schemas, and source code implementations.

### Step-by-Step Workflow Analysis Process

#### Step 1: Extract Node Types from Workflow

```bash
# Get all unique node types in the workflow
jq '.nodes[].data.type | unique' workflow.json

# Get node types with counts
jq '.nodes | group_by(.data.type) | map({type: .[0].data.type, count: length})' workflow.json

# Save node types to a file for processing
jq -r '.nodes[].data.type | unique | .[]' workflow.json > node_types.txt
```

#### Step 2: Extract Node Schemas from OpenAPI

For each node type found, extract its complete schema:

```bash
# Method A: Extract single node schema
NODE_TYPE="flux_denoise"
jq --arg type "$NODE_TYPE" '
  .components.schemas | to_entries | 
  map(select(.value.properties.type.default == $type)) | 
  .[0].value
' openapi.json

# Method B: Extract all schemas for multiple nodes at once
jq '
  .components.schemas | to_entries | 
  map(select(.value.properties.type.default as $type | 
    ["add", "flux_controlnet", "flux_denoise", "denoise_latents", "image", "noise"] | 
    index($type)
  )) | 
  map({
    node_type: .value.properties.type.default,
    title: .value.title,
    category: .value.properties.category.default,
    version: .value.properties.version.default,
    schema: .value
  })
' openapi.json
```

#### Step 3: Find Source Code Files

Use systematic searching to locate the Python implementation files:

```bash
# Method A: Search by invocation decorator
grep -r "@invocation.*\"NODE_TYPE\"" invokeai/app/invocations/

# Method B: Search by class name pattern
grep -r "class.*NODE_TYPE.*Invocation" invokeai/app/invocations/

# Method C: Direct file matching (for predictable patterns)
# Many nodes follow the pattern: node_type.py contains NodeTypeInvocation
ls invokeai/app/invocations/ | grep -E "(NODE_TYPE|related_pattern)\.py"
```

#### Step 4: Extract Python Class Headers

Once the source file is found, extract the class definition and key methods:

```bash
# Extract class definition with decorator
grep -A 20 "@invocation.*\"NODE_TYPE\"" source_file.py

# Extract just the class header and docstring
sed -n '/class.*Invocation/,/def invoke/p' source_file.py | head -20

# Get complete class signature with fields
awk '/class.*Invocation/,/def invoke/' source_file.py
```

### Complete Analysis Example

Here's a complete example analyzing the `data/workflows/example-nodes.json` workflow:

#### Example Workflow Analysis Script

```bash
#!/bin/bash
# analyze_workflow.sh - Complete workflow analysis script

WORKFLOW_FILE="data/workflows/example-nodes.json"
OPENAPI_FILE="context/hints/invokeai-kb/invokeai-openapi.json"
INVOKEAI_SOURCE="context/refcode/InvokeAI/invokeai/app/invocations"
OUTPUT_FILE="workflow_analysis.md"

echo "# Workflow Analysis Report" > $OUTPUT_FILE
echo "Generated on: $(date)" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

# Step 1: Extract workflow metadata
echo "## Workflow Overview" >> $OUTPUT_FILE
jq -r '
  "- **Name**: " + (.name // "N/A"),
  "- **Description**: " + (.description // "N/A"),
  "- **Version**: " + (.version // "N/A"),
  "- **Schema Version**: " + .meta.version,
  "- **Total Nodes**: " + (.nodes | length | tostring),
  "- **Total Edges**: " + (.edges | length | tostring)
' $WORKFLOW_FILE >> $OUTPUT_FILE

echo "" >> $OUTPUT_FILE

# Step 2: List all node types
echo "## Node Types Found" >> $OUTPUT_FILE
jq -r '.nodes | group_by(.data.type) | map("- **" + .[0].data.type + "**: " + (length | tostring) + " instance(s)") | .[]' $WORKFLOW_FILE >> $OUTPUT_FILE

echo "" >> $OUTPUT_FILE

# Step 3: Detailed node analysis
echo "## Detailed Node Analysis" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

# Get unique node types
NODE_TYPES=$(jq -r '.nodes[].data.type | unique | .[]' $WORKFLOW_FILE)

for NODE_TYPE in $NODE_TYPES; do
    echo "### Node: $NODE_TYPE" >> $OUTPUT_FILE
    echo "" >> $OUTPUT_FILE
    
    # Extract schema information
    SCHEMA_INFO=$(jq --arg type "$NODE_TYPE" '
      .components.schemas | to_entries | 
      map(select(.value.properties.type.default == $type)) | 
      if length > 0 then
        .[0].value | {
          title: .title,
          category: .properties.category.default,
          version: .properties.version.default,
          description: .description,
          input_count: [.properties | to_entries[] | select(.value.field_kind == "input")] | length
        }
      else
        {title: "Schema not found", category: "unknown", version: "unknown", description: "N/A", input_count: 0}
      end
    ' $OPENAPI_FILE)
    
    echo "**Schema Information:**" >> $OUTPUT_FILE
    echo '```json' >> $OUTPUT_FILE
    echo "$SCHEMA_INFO" | jq '.' >> $OUTPUT_FILE
    echo '```' >> $OUTPUT_FILE
    echo "" >> $OUTPUT_FILE
    
    # Find source file
    echo "**Source Code Location:**" >> $OUTPUT_FILE
    SOURCE_FILE=$(find $INVOKEAI_SOURCE -name "*.py" -exec grep -l "@invocation.*\"$NODE_TYPE\"" {} \; 2>/dev/null | head -1)
    
    if [ -n "$SOURCE_FILE" ]; then
        echo "- **File**: \`$SOURCE_FILE\`" >> $OUTPUT_FILE
        
        # Extract class definition
        CLASS_DEF=$(grep -A 5 "@invocation.*\"$NODE_TYPE\"" "$SOURCE_FILE" 2>/dev/null)
        if [ -n "$CLASS_DEF" ]; then
            echo "- **Class Definition**:" >> $OUTPUT_FILE
            echo '```python' >> $OUTPUT_FILE
            echo "$CLASS_DEF" >> $OUTPUT_FILE
            echo '```' >> $OUTPUT_FILE
        fi
    else
        echo "- **File**: Not found in provided source tree" >> $OUTPUT_FILE
    fi
    
    echo "" >> $OUTPUT_FILE
    
    # Extract usage in workflow
    echo "**Usage in Workflow:**" >> $OUTPUT_FILE
    USAGE=$(jq --arg type "$NODE_TYPE" '
      .nodes[] | select(.data.type == $type) | {
        id: .id,
        label: .data.label,
        position: .position,
        inputs: (.data.inputs | keys)
      }
    ' $WORKFLOW_FILE)
    echo '```json' >> $OUTPUT_FILE
    echo "$USAGE" >> $OUTPUT_FILE
    echo '```' >> $OUTPUT_FILE
    echo "" >> $OUTPUT_FILE
done

echo "Analysis complete. Results saved to $OUTPUT_FILE"
```

### Automated Analysis Functions

#### PowerShell Functions for Windows

```powershell
# analyze_workflow.ps1 - PowerShell functions for workflow analysis

function Get-WorkflowNodes {
    param([string]$WorkflowPath)
    
    $nodes = jq '.nodes[].data.type | unique' $WorkflowPath | ConvertFrom-Json
    return $nodes
}

function Get-NodeSchema {
    param(
        [string]$NodeType,
        [string]$OpenAPIPath
    )
    
    $schema = jq --arg type $NodeType '.components.schemas | to_entries | map(select(.value.properties.type.default == $type)) | .[0].value' $OpenAPIPath | ConvertFrom-Json
    return $schema
}

function Find-NodeSourceFile {
    param(
        [string]$NodeType,
        [string]$SourceDir
    )
    
    $files = Get-ChildItem -Path $SourceDir -Recurse -Filter "*.py" | 
        Where-Object { (Select-String -Path $_.FullName -Pattern "@invocation.*`"$NodeType`"" -Quiet) }
    
    return $files[0].FullName
}

function Get-NodeClassDefinition {
    param(
        [string]$SourceFile,
        [string]$NodeType
    )
    
    $content = Get-Content $SourceFile
    $startLine = $content | Select-String -Pattern "@invocation.*`"$NodeType`"" | Select-Object -First 1 | ForEach-Object { $_.LineNumber - 1 }
    
    if ($startLine -ge 0) {
        $classLines = $content[$startLine..($startLine + 20)]
        return $classLines -join "`n"
    }
    
    return "Class definition not found"
}

# Usage example:
# $nodes = Get-WorkflowNodes "data/workflows/example-nodes.json"
# foreach ($node in $nodes) {
#     $schema = Get-NodeSchema $node "openapi.json"
#     $sourceFile = Find-NodeSourceFile $node "invokeai/app/invocations"
#     $classDef = Get-NodeClassDefinition $sourceFile $node
# }
```

#### Python Analysis Script

```python
#!/usr/bin/env python3
# analyze_workflow.py - Python script for comprehensive workflow analysis

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

class WorkflowAnalyzer:
    def __init__(self, workflow_path: str, openapi_path: str, source_dir: str):
        self.workflow_path = workflow_path
        self.openapi_path = openapi_path
        self.source_dir = Path(source_dir)
        
        with open(workflow_path) as f:
            self.workflow = json.load(f)
        with open(openapi_path) as f:
            self.openapi = json.load(f)
    
    def get_node_types(self) -> List[str]:
        """Extract all unique node types from workflow."""
        node_types = set()
        for node in self.workflow.get('nodes', []):
            node_types.add(node['data']['type'])
        return sorted(list(node_types))
    
    def get_node_schema(self, node_type: str) -> Optional[Dict]:
        """Get OpenAPI schema for a specific node type."""
        schemas = self.openapi.get('components', {}).get('schemas', {})
        
        for schema_name, schema_def in schemas.items():
            if (schema_name.endswith('Invocation') and 
                schema_def.get('properties', {}).get('type', {}).get('default') == node_type):
                return {
                    'schema_name': schema_name,
                    'title': schema_def.get('title', ''),
                    'description': schema_def.get('description', ''),
                    'category': schema_def.get('properties', {}).get('category', {}).get('default', ''),
                    'version': schema_def.get('properties', {}).get('version', {}).get('default', ''),
                    'full_schema': schema_def
                }
        return None
    
    def find_source_file(self, node_type: str) -> Optional[str]:
        """Find the Python source file containing the node implementation."""
        for py_file in self.source_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for @invocation decorator with node type
                    pattern = f'@invocation\\s*\\(\\s*["\']\\s*{re.escape(node_type)}\\s*["\']'
                    if re.search(pattern, content):
                        return str(py_file)
            except Exception:
                continue
        return None
    
    def extract_class_definition(self, source_file: str, node_type: str) -> Optional[str]:
        """Extract the class definition from source file."""
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find the @invocation decorator line
            invocation_line = -1
            for i, line in enumerate(lines):
                if f'@invocation' in line and node_type in line:
                    invocation_line = i
                    break
            
            if invocation_line >= 0:
                # Extract decorator + class definition + docstring
                result_lines = []
                i = invocation_line
                
                # Get decorator and class definition
                while i < len(lines) and not lines[i].strip().startswith('def invoke'):
                    result_lines.append(lines[i].rstrip())
                    i += 1
                
                return '\n'.join(result_lines)
        except Exception as e:
            return f"Error reading file: {e}"
        
        return None
    
    def analyze_workflow(self) -> Dict:
        """Perform complete workflow analysis."""
        analysis = {
            'workflow_info': {
                'name': self.workflow.get('name', 'N/A'),
                'description': self.workflow.get('description', 'N/A'),
                'version': self.workflow.get('version', 'N/A'),
                'schema_version': self.workflow.get('meta', {}).get('version', 'N/A'),
                'total_nodes': len(self.workflow.get('nodes', [])),
                'total_edges': len(self.workflow.get('edges', []))
            },
            'nodes': {}
        }
        
        for node_type in self.get_node_types():
            node_analysis = {
                'node_type': node_type,
                'schema': self.get_node_schema(node_type),
                'source_file': self.find_source_file(node_type),
                'class_definition': None,
                'usage_count': sum(1 for n in self.workflow['nodes'] if n['data']['type'] == node_type)
            }
            
            if node_analysis['source_file']:
                node_analysis['class_definition'] = self.extract_class_definition(
                    node_analysis['source_file'], node_type
                )
            
            analysis['nodes'][node_type] = node_analysis
        
        return analysis
    
    def generate_report(self, output_file: str):
        """Generate markdown report of the analysis."""
        analysis = self.analyze_workflow()
        
        with open(output_file, 'w') as f:
            f.write("# Workflow Analysis Report\n\n")
            f.write(f"**Generated on**: {__import__('datetime').datetime.now().isoformat()}\n\n")
            
            # Workflow overview
            f.write("## Workflow Overview\n\n")
            info = analysis['workflow_info']
            f.write(f"- **Name**: {info['name']}\n")
            f.write(f"- **Description**: {info['description']}\n")
            f.write(f"- **Version**: {info['version']}\n")
            f.write(f"- **Schema Version**: {info['schema_version']}\n")
            f.write(f"- **Total Nodes**: {info['total_nodes']}\n")
            f.write(f"- **Total Edges**: {info['total_edges']}\n\n")
            
            # Node analysis
            f.write("## Node Analysis\n\n")
            for node_type, node_info in analysis['nodes'].items():
                f.write(f"### {node_type}\n\n")
                
                if node_info['schema']:
                    schema = node_info['schema']
                    f.write("**Schema Information:**\n")
                    f.write(f"- **Title**: {schema['title']}\n")
                    f.write(f"- **Category**: {schema['category']}\n")
                    f.write(f"- **Version**: {schema['version']}\n")
                    f.write(f"- **Description**: {schema['description']}\n\n")
                
                if node_info['source_file']:
                    f.write(f"**Source File**: `{node_info['source_file']}`\n\n")
                    
                    if node_info['class_definition']:
                        f.write("**Class Definition:**\n")
                        f.write("```python\n")
                        f.write(node_info['class_definition'])
                        f.write("\n```\n\n")
                else:
                    f.write("**Source File**: Not found\n\n")
                
                f.write(f"**Usage Count**: {node_info['usage_count']} instance(s)\n\n")

# Usage example:
if __name__ == "__main__":
    analyzer = WorkflowAnalyzer(
        workflow_path="data/workflows/example-nodes.json",
        openapi_path="context/hints/invokeai-kb/invokeai-openapi.json", 
        source_dir="context/refcode/InvokeAI/invokeai/app/invocations"
    )
    
    analyzer.generate_report("workflow_analysis_report.md")
    print("Analysis complete. Report saved to workflow_analysis_report.md")
```

### Quick Reference Commands

#### One-liner Analysis Commands

```bash
# Quick node type extraction
jq -r '.nodes[].data.type | unique | .[]' workflow.json

# Node count summary
jq '.nodes | group_by(.data.type) | map("\(.[0].data.type): \(length)")' workflow.json

# Find all source files for workflow nodes
NODES=$(jq -r '.nodes[].data.type | unique | .[]' workflow.json)
for node in $NODES; do
    echo "=== $node ==="
    find invokeai/app/invocations -name "*.py" -exec grep -l "@invocation.*\"$node\"" {} \;
done

# Extract all schemas for workflow nodes
jq --slurpfile nodes <(jq '.nodes[].data.type | unique' workflow.json) '
  .components.schemas | to_entries | 
  map(select(.value.properties.type.default as $type | $nodes[0] | index($type))) |
  map({node_type: .value.properties.type.default, schema: .value})
' openapi.json
```

### Future Workflow Analysis Template

For any new workflow analysis, follow this template:

1. **Extract Node Types**: Use `jq '.nodes[].data.type | unique'`
2. **Get Schemas**: For each node, extract from OpenAPI with jq filters
3. **Find Source Files**: Search with `grep -r "@invocation.*\"NODE_TYPE\""`
4. **Extract Class Definitions**: Use grep/awk to get class headers
5. **Document Results**: Generate markdown report with findings

This methodology provides a complete, reusable approach for analyzing any InvokeAI workflow file and understanding its component nodes at both the schema and implementation levels.

## Field Types and Schema

### Field Type Structure

Fields are typed with cardinality information:

```typescript
type FieldType = {
  name: string;
  cardinality: 'SINGLE' | 'COLLECTION' | 'SINGLE_OR_COLLECTION';
};
```

### Common Field Types

| Field Type | Description | Example Values |
|------------|-------------|----------------|
| `StringField` | Text input | `"hello world"` |
| `IntegerField` | Numeric input | `512`, `1024` |
| `FloatField` | Decimal input | `7.5`, `0.8` |
| `BooleanField` | True/false | `true`, `false` |
| `ImageField` | Image reference | `{"image_name": "uuid.png"}` |
| `LatentsField` | Latent tensors | `{"latents_name": "uuid"}` |
| `ConditioningField` | Text conditioning | `{"conditioning_name": "uuid"}` |
| `UNetField` | UNet model | `{"unet": {...}}` |
| `ClipField` | CLIP model | `{"clip": {...}}` |
| `VaeField` | VAE model | `{"vae": {...}}` |
| `ModelField` | Main model | `{"key": "model-id", "hash": "...", "name": "model-name", "base": "sdxl", "type": "main"}` |
| `LoRAField` | LoRA model | `{"lora": {...}}` |
| `ControlField` | ControlNet | `{"control": {...}}` |
| `ColorField` | RGBA color | `{"r": 255, "g": 0, "b": 0, "a": 255}` |

### Field Validation

Fields support pydantic-style validation:

```python
width: int = InputField(default=512, ge=64, le=2048, description="Width of image")
```

Translated to JSON schema with constraints:
- `ge`: Greater than or equal (minimum)
- `le`: Less than or equal (maximum)
- `gt`: Greater than
- `lt`: Less than

## References

- [InvokeAI Workflow Documentation](https://github.com/invoke-ai/invokeai/blob/main/docs/contributing/frontend/workflows.md)
- [Custom Node Development Guide](https://github.com/invoke-ai/invokeai/blob/main/docs/contributing/INVOCATIONS.md)
- [Node API Reference](https://github.com/invoke-ai/invokeai/blob/main/docs/nodes/invocation-api.md)
- [OpenAPI Schema Generation](https://github.com/invoke-ai/invokeai/blob/main/docs/contributing/frontend/index.md)

This guide provides the foundational knowledge for understanding and working with InvokeAI workflows. The modular, typed field system enables powerful graph-based AI image generation pipelines with extensive customization capabilities.
