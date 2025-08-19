#!/usr/bin/env python
"""
Test script to inspect workflow inputs and display their details including JSONPath.
This demonstrates the JSONPath-based field tracking implementation from Task 2.1.1.
"""

import sys
import os
import json
from pathlib import Path
from typing import Any

# Force UTF-8 encoding for Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.syntax import Syntax
from rich.text import Text

from invokeai_py_client.workflow import WorkflowRepository, WorkflowDefinition


def inspect_workflow_inputs(workflow_path: str) -> None:
    """
    Load a workflow and print detailed information about its inputs.
    
    Parameters
    ----------
    workflow_path : str
        Path to the workflow JSON file.
    """
    # Use legacy Windows mode to avoid encoding issues
    console = Console(legacy_windows=True if sys.platform == "win32" else False)
    
    # Header
    console.print(Panel.fit(
        "[bold cyan]WORKFLOW INPUT INSPECTION[/bold cyan]\n" +
        f"[dim]{workflow_path}[/dim]",
        title="[bold]Analysis Tool[/bold]",
        border_style="bright_blue"
    ))
    
    # Load the workflow JSON
    with open(workflow_path, 'r') as f:
        workflow_data = json.load(f)
    
    # Create workflow definition using from_dict to properly store raw_data
    definition = WorkflowDefinition.from_dict(workflow_data)
    
    # Create workflow handle (client=None for inspection only)
    from invokeai_py_client.workflow.workflow_handle import WorkflowHandle
    handle = WorkflowHandle(definition=definition, client=None)
    
    # Print workflow metadata
    metadata_table = Table(title="Workflow Metadata", show_header=False)
    metadata_table.add_column("Property", style="cyan", width=20)
    metadata_table.add_column("Value", style="white")
    
    metadata_table.add_row("Name", definition.name)
    metadata_table.add_row("Author", definition.author)
    metadata_table.add_row("Description", definition.description or "N/A")
    metadata_table.add_row("Version", definition.version)
    metadata_table.add_row("Tags", ', '.join(definition.tags) if definition.tags else 'None')
    metadata_table.add_row("Total Inputs", str(len(handle.inputs)))
    
    console.print(metadata_table)
    console.print()
    
    # Create detailed input table
    input_table = Table(
        title=f"[bold]All Workflow Inputs ({len(handle.inputs)} fields)[/bold]",
        show_lines=True,
        expand=True
    )
    
    input_table.add_column("#", style="bold cyan", width=4)
    input_table.add_column("Label", style="yellow")
    input_table.add_column("Type", style="green")
    input_table.add_column("Node", style="blue")
    input_table.add_column("Field", style="magenta")
    input_table.add_column("Required", style="red", width=8)
    input_table.add_column("Value/Properties", style="white")
    input_table.add_column("JSONPath", style="dim", overflow="fold")
    
    for inp in handle.inputs:
        # Determine field type
        field_type = type(inp.field).__name__.replace("Ivk", "").replace("Field", "")
        
        # Build detailed value representation
        value_info = []
        
        # Get all field attributes
        field_dict = inp.field.model_dump() if hasattr(inp.field, 'model_dump') else {}
        
        # Special handling for different field types
        if hasattr(inp.field, 'value'):
            value = inp.field.value
            if value is not None:
                if isinstance(value, dict):
                    # For model fields, show all properties
                    for k, v in value.items():
                        if isinstance(v, str) and len(v) > 40:
                            v = v[:37] + "..."
                        value_info.append(f"[cyan]{k}:[/cyan] {v}")
                elif isinstance(value, str):
                    if len(value) > 60:
                        value_info.append(f"'{value[:57]}...'")
                    else:
                        value_info.append(f"'{value}'")
                else:
                    value_info.append(str(value))
            else:
                value_info.append("[dim]None[/dim]")
        
        # Add other field properties
        for key, val in field_dict.items():
            if key not in ['value', 'type'] and val is not None:
                if key in ['minimum', 'maximum', 'default']:
                    value_info.append(f"[cyan]{key}:[/cyan] {val}")
        
        # Format value column
        value_display = "\n".join(value_info) if value_info else "[dim]No value[/dim]"
        
        input_table.add_row(
            str(inp.input_index),
            inp.label or "[dim](no label)[/dim]",
            field_type,
            inp.node_name[:30],
            inp.field_name,
            "Yes" if inp.required else "No",
            value_display,
            inp.jsonpath
        )
    
    console.print(input_table)
    console.print()
    
    # Print exposed fields summary
    if definition.exposedFields:
        exposed_tree = Tree("[bold]Exposed Fields Summary[/bold]")
        exposed_tree.add(f"[cyan]Total exposed fields:[/cyan] {len(definition.exposedFields)}")
        
        # Group by node
        nodes_with_fields = {}
        for field in definition.exposedFields:
            node_id = field.get('nodeId', 'unknown')
            field_name = field.get('fieldName', 'unknown')
            if node_id not in nodes_with_fields:
                nodes_with_fields[node_id] = []
            nodes_with_fields[node_id].append(field_name)
        
        nodes_branch = exposed_tree.add(f"[cyan]Nodes with exposed fields:[/cyan] {len(nodes_with_fields)}")
        
        for node_id, fields in nodes_with_fields.items():
            # Try to find node name from the inputs
            node_name = None
            for inp in handle.inputs:
                if inp.node_id == node_id:
                    node_name = inp.node_name
                    break
            
            if node_name:
                node_branch = nodes_branch.add(f"[blue]{node_name}[/blue] ([dim]{node_id[:20]}...[/dim])")
            else:
                node_branch = nodes_branch.add(f"[dim]Node {node_id[:20]}...[/dim]")
            
            for field in fields:
                node_branch.add(f"[magenta]{field}[/magenta]")
        
        console.print(exposed_tree)
        console.print()
    
    # Print field type distribution
    type_counts: dict[str, int] = {}
    for inp in handle.inputs:
        field_type = type(inp.field).__name__.replace("Ivk", "").replace("Field", "")
        type_counts[field_type] = type_counts.get(field_type, 0) + 1
    
    dist_table = Table(title="Field Type Distribution")
    dist_table.add_column("Field Type", style="green")
    dist_table.add_column("Count", style="yellow", justify="right")
    dist_table.add_column("Percentage", style="cyan", justify="right")
    
    total = len(handle.inputs)
    for field_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total) * 100
        dist_table.add_row(
            field_type,
            str(count),
            f"{percentage:.1f}%"
        )
    
    console.print(dist_table)
    
    # Final summary panel
    console.print()
    console.print(Panel.fit(
        f"[bold green]Analysis Complete[/bold green]\n" +
        f"[cyan]Total Fields:[/cyan] {len(handle.inputs)}\n" +
        f"[cyan]Unique JSONPaths:[/cyan] {len(set(inp.jsonpath for inp in handle.inputs))}\n" +
        f"[cyan]Field Types:[/cyan] {len(type_counts)}",
        title="[bold]Summary[/bold]",
        border_style="green"
    ))


def main():
    """Main entry point for the script."""
    # Path to the workflow file
    workflow_path = Path(__file__).parent.parent / "data" / "workflows" / "sdxl-flux-refine.json"
    
    if not workflow_path.exists():
        print(f"Error: Workflow file not found at {workflow_path}")
        sys.exit(1)
    
    try:
        inspect_workflow_inputs(str(workflow_path))
    except Exception as e:
        print(f"\nError loading workflow: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()