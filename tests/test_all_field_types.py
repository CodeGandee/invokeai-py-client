#!/usr/bin/env python
"""Test that all field types work correctly with the workflow update pattern."""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowRepository
from invokeai_py_client.ivk_fields import (
    IvkStringField, IvkIntegerField, IvkFloatField, IvkBooleanField,
    IvkImageField, IvkBoardField, IvkLatentsField,
    IvkModelIdentifierField, IvkColorField, IvkBoundingBoxField
)


def test_field_to_api_format() -> None:
    """Test what each field type returns from to_api_format()."""
    print("=== Testing Field Type to_api_format() Outputs ===\n")
    
    # Test primitive fields
    string_field = IvkStringField(value="test")
    print(f"IvkStringField.to_api_format(): {json.dumps(string_field.to_api_format(), indent=2)}")
    
    int_field = IvkIntegerField(value=42)
    print(f"\nIvkIntegerField.to_api_format(): {json.dumps(int_field.to_api_format(), indent=2)}")
    
    float_field = IvkFloatField(value=3.14)
    print(f"\nIvkFloatField.to_api_format(): {json.dumps(float_field.to_api_format(), indent=2)}")
    
    bool_field = IvkBooleanField(value=True)
    print(f"\nIvkBooleanField.to_api_format(): {json.dumps(bool_field.to_api_format(), indent=2)}")
    
    # Test resource fields
    image_field = IvkImageField(value="test.png")
    print(f"\nIvkImageField.to_api_format(): {json.dumps(image_field.to_api_format(), indent=2)}")
    
    board_field = IvkBoardField(value="test_board")
    print(f"\nIvkBoardField.to_api_format(): {json.dumps(board_field.to_api_format(), indent=2)}")
    
    # Test complex fields
    color_field = IvkColorField(r=255, g=128, b=64, a=200)
    print(f"\nIvkColorField.to_api_format(): {json.dumps(color_field.to_api_format(), indent=2)}")
    
    bbox_field = IvkBoundingBoxField(x_min=0, y_min=0, x_max=100, y_max=100)
    print(f"\nIvkBoundingBoxField.to_api_format(): {json.dumps(bbox_field.to_api_format(), indent=2)}")
    
    # Test model fields (no value attribute)
    model_field = IvkModelIdentifierField(
        key="test_key",
        hash="test_hash",
        name="test_model",
        base="sdxl",
        type="main"
    )
    print(f"\nIvkModelIdentifierField.to_api_format(): {json.dumps(model_field.to_api_format(), indent=2)}")


def analyze_workflow_fields(workflow_path: str) -> Dict[str, Any]:
    """Analyze what field types are exposed in a workflow."""
    print(f"\n=== Analyzing {Path(workflow_path).name} ===")
    
    client = InvokeAIClient("http://127.0.0.1:9090")
    repo = WorkflowRepository(client)
    wf = repo.create_workflow_from_file(workflow_path)
    
    field_types = {}
    for inp in wf.list_inputs():
        field_type = type(inp.field).__name__
        if field_type not in field_types:
            field_types[field_type] = []
        field_types[field_type].append({
            "node_id": inp.node_id,
            "field_name": inp.field_name,
            "label": inp.label
        })
    
    print(f"Exposed field types:")
    for ftype, fields in field_types.items():
        print(f"  {ftype}: {len(fields)} field(s)")
        for field in fields[:2]:  # Show first 2 examples
            print(f"    - {field['field_name']} ({field['label']})")
    
    return field_types


def test_workflow_field_update(workflow_path: str, test_name: str) -> bool:
    """Test field updates for a specific workflow."""
    print(f"\n=== Testing Field Updates for {test_name} ===")
    
    client = InvokeAIClient("http://127.0.0.1:9090")
    repo = WorkflowRepository(client)
    wf = repo.create_workflow_from_file(workflow_path)
    
    # Get original raw data structure
    original_raw = wf.definition.raw_data
    
    # Test updating different field types
    test_results = []
    
    for inp in wf.list_inputs():
        field = inp.field
        field_type = type(field).__name__
        
        # Set test values based on field type
        if hasattr(field, 'value'):
            if isinstance(field, IvkStringField):
                field.value = f"test_{test_name}_string"
            elif isinstance(field, IvkIntegerField):
                field.value = 42
            elif isinstance(field, IvkFloatField):
                field.value = 3.14
            elif isinstance(field, IvkBooleanField):
                field.value = True
            elif isinstance(field, IvkImageField):
                field.value = "test_image.png"
            elif isinstance(field, IvkBoardField):
                field.value = "test_board"
        
        # Check that the field can be converted to API format
        try:
            api_format = field.to_api_format()
            test_results.append({
                "field": f"{inp.node_id}.{inp.field_name}",
                "type": field_type,
                "success": True,
                "api_format_keys": list(api_format.keys()) if isinstance(api_format, dict) else "not_dict"
            })
        except Exception as e:
            test_results.append({
                "field": f"{inp.node_id}.{inp.field_name}",
                "type": field_type,
                "success": False,
                "error": str(e)
            })
    
    # Convert to API format
    try:
        api_graph = wf._convert_to_api_format("test_board")
        print(f"[OK] Successfully converted to API format")
        
        # Verify structure
        if "nodes" in api_graph:
            print(f"[OK] API graph has {len(api_graph['nodes'])} nodes")
        
        # Show test results
        success_count = sum(1 for r in test_results if r["success"])
        print(f"\nField conversion results: {success_count}/{len(test_results)} successful")
        
        for result in test_results[:5]:  # Show first 5
            status = "[OK]" if result["success"] else "[FAIL]"
            print(f"  {status} {result['type']}: {result.get('api_format_keys', result.get('error'))}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to convert to API format: {e}")
        return False


def main() -> int:
    """Main test function."""
    print("=" * 70)
    print(" WORKFLOW FIELD TYPE COMPATIBILITY TEST")
    print("=" * 70)
    
    # Test field to_api_format outputs
    test_field_to_api_format()
    
    # Analyze and test each workflow
    workflows = [
        ("data/workflows/sdxl-flux-refine.json", "SDXL-FLUX-Refine"),
        ("data/workflows/sdxl-text-to-image.json", "SDXL-Text-to-Image"),
        ("data/workflows/flux-image-to-image.json", "FLUX-Image-to-Image"),
    ]
    
    results = []
    for workflow_path, name in workflows:
        workflow_file = Path(workflow_path)
        if not workflow_file.exists():
            print(f"\n[SKIP] {name}: File not found: {workflow_path}")
            continue
            
        # Analyze field types
        analyze_workflow_fields(workflow_path)
        
        # Test field updates
        success = test_workflow_field_update(workflow_path, name)
        results.append((name, success))
    
    # Summary
    print("\n" + "=" * 70)
    print(" TEST SUMMARY")
    print("=" * 70)
    
    for name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {name}")
    
    all_passed = all(success for _, success in results)
    if all_passed:
        print("\n[SUCCESS] All workflows passed field type compatibility test")
        return 0
    else:
        print("\n[FAILURE] Some workflows failed field type compatibility test")
        return 1


if __name__ == "__main__":
    sys.exit(main())