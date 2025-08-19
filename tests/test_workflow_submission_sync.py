#!/usr/bin/env python3
"""
Test script for Task 2.1: Submit workflow using sync method and track execution.

This test submits an SDXL text-to-image workflow synchronously, tracks its 
progress, and explores the relationship between workflow submission and 
generated images.

Based on working example from api-demo-job-submission.py
"""

import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition, WorkflowHandle
from invokeai_py_client.board import BoardHandle
from invokeai_py_client.models import IvkImage
from invokeai_py_client.dnn_model import DnnModelRepository, BaseDnnModelType, DnnModelType
from invokeai_py_client.ivk_fields.model_conversion import to_ivk_model_field


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


# Note: These helper functions are no longer needed since WorkflowHandle
# internally handles conversion and we set inputs through its API


def test_workflow_submission_sync():
    """Test workflow submission using sync method."""
    
    print_section("TASK 2.1: WORKFLOW SUBMISSION TEST (SYNC)")
    
    # Initialize client
    print("\n[1] Initializing InvokeAI client...")
    client = InvokeAIClient.from_url("http://127.0.0.1:9090")
    dnn_model_repo = DnnModelRepository(client)
    
    # Verify connection using version endpoint
    try:
        response = client._make_request("GET", "/app/version")
        version_info = response.json()
        print(f"    Connected to InvokeAI server v{version_info.get('version', 'unknown')}")
    except Exception as e:
        print(f"ERROR: Cannot connect to InvokeAI at http://127.0.0.1:9090 - {e}")
        return 1
    
    # List available SDXL models
    print("\n[2] Discovering available SDXL models...")
    try:
        models = dnn_model_repo.list_models()
        # Filter for SDXL main models
        sdxl_models = [
            m for m in models 
            if m.base == BaseDnnModelType.StableDiffusionXL and m.type == DnnModelType.Main
        ]
        
        if not sdxl_models:
            print("ERROR: No SDXL models found in InvokeAI")
            print("    Please install an SDXL model first")
            return 1
        
        # Use the first available SDXL model
        selected_model = sdxl_models[0]
        print(f"    Found {len(sdxl_models)} SDXL model(s)")
        print(f"    Selected: {selected_model.name}")
        print(f"    Model key: {selected_model.key}")
        print(f"    Format: {selected_model.format}")
        
    except Exception as e:
        print(f"ERROR: Failed to list models - {e}")
        return 1
    
    # Load workflow using WorkflowDefinition and create handle
    print("\n[3] Loading workflow definition...")
    workflow_path = Path("data/workflows/sdxl-text-to-image.json")
    if not workflow_path.exists():
        print(f"ERROR: Workflow file not found: {workflow_path}")
        return 1
    
    workflow_def = WorkflowDefinition.from_file(str(workflow_path))
    print(f"    Loaded workflow: {workflow_def.name}")
    print(f"    Version: {workflow_def.version}")
    print(f"    Nodes: {len(workflow_def.nodes)}")
    
    # Create workflow handle
    print("\n[4] Creating workflow handle...")
    workflow = client.workflow_repo.create_workflow(workflow_def)
    print(f"    Workflow handle created")
    print(f"    Exposed inputs: {len(workflow.list_inputs())}")
    
    # Set workflow inputs
    print("\n[5] Setting workflow inputs...")
    positive_prompt = "A majestic mountain landscape at sunset, highly detailed, 8k, photorealistic"
    negative_prompt = "blurry, low quality, distorted, ugly, text, watermark"
    
    # Debug: Show all inputs with their node IDs
    print("    Available inputs:")
    for i, input_info in enumerate(workflow.list_inputs()):
        print(f"      [{i}] Node: {input_info.node_id[:20]}... Field: {input_info.field_name} Label: '{input_info.label}'")
    
    # Find and set model input
    for i, input_info in enumerate(workflow.list_inputs()):
        field_name = input_info.field_name
        field_label = input_info.label
        field_type = input_info.field.__class__.__name__
        node_id = input_info.node_id
        
        # Check both field name and label for model references
        if ('model' in field_name.lower() or 'model' in field_label.lower()) and 'IvkModelIdentifierField' in field_type:
            # Convert DnnModel to IvkModelIdentifierField using Protocol
            model_field = to_ivk_model_field(selected_model)
            workflow.set_input_value(i, value=model_field)
            print(f"    Set model input: {selected_model.name} on node {node_id[:20]}")
        elif 'positive' in field_label.lower():
            # For string fields, set the value directly on the field
            input_info.field.value = positive_prompt
            print(f"    Set positive prompt on node {node_id[:20]}")
        elif 'negative' in field_label.lower() or node_id == "484ecc77-b7a0-4e19-b793-cc313f20fbe6":
            # For string fields, set the value directly on the field
            input_info.field.value = negative_prompt
            print(f"    Set negative prompt on node {node_id[:20]}")
    
    # Validate inputs before submission
    print("\n[6] Validating workflow inputs...")
    missing = workflow.validate_inputs()
    if missing:
        print(f"    Warning: Missing inputs: {missing}")
    else:
        print(f"    All required inputs are set")
    
    # Submit workflow using WorkflowHandle
    print("\n[7] Submitting workflow...")
    try:
        submission_start = time.time()
        
        # Debug: Show what inputs we have set
        print("    Current inputs:")
        for i, inp in enumerate(workflow.inputs):
            field_type = inp.field.__class__.__name__
            if hasattr(inp.field, 'value'):
                print(f"      [{i}] {inp.label}: {field_type} = {str(inp.field.value)[:50]}")
            elif hasattr(inp.field, 'name'):
                print(f"      [{i}] {inp.label}: {field_type} = {inp.field.name}")
            else:
                print(f"      [{i}] {inp.label}: {field_type}")
        
        # Use WorkflowHandle's submit_sync method - this returns a dict, not IvkJob
        result = workflow.submit_sync()
        
        print(f"\n    SUBMISSION SUCCESSFUL!")
        print(f"    Batch ID: {result.get('batch', {}).get('batch_id')}")
        print(f"    Item IDs: {result.get('item_ids', [])}")
        print(f"    Submit time: {time.time() - submission_start:.3f}s")
        
        # Extract IDs for monitoring
        batch_id = result.get('batch', {}).get('batch_id')
        item_ids = result.get('item_ids', [])
        item_id = item_ids[0] if item_ids else None
        session_id = None  # Will get from queue item
        
    except Exception as e:
        print(f"\n    ERROR: Submission failed: {e}")
        # Try to get more details about the error
        if hasattr(e, '__cause__') and e.__cause__:
            if hasattr(e.__cause__, 'response'):
                response = e.__cause__.response
                if response is not None:
                    try:
                        error_detail = response.json()
                        print(f"    Server error details:")
                        print(json.dumps(error_detail, indent=4)[:2000])
                    except:
                        print(f"    Response text: {response.text[:1000]}")
        return 1
    
    # Queue item URL for monitoring
    item_url = f"{client.base_url}/queue/default/i/{item_id}"
    
    # Monitor execution
    print("\n[8] Monitoring workflow execution...")
    max_wait = 120
    start_time = time.time()
    last_status = None
    check_count = 0
    
    while time.time() - start_time < max_wait:
        check_count += 1
        
        try:
            # Check queue item status
            item_response = client.session.get(item_url)
            item_response.raise_for_status()
            queue_item = item_response.json()
            
            current_status = queue_item.get('status')
            
            if current_status != last_status:
                elapsed = time.time() - start_time
                print(f"    [{elapsed:.1f}s] Status: {current_status} (check #{check_count})")
                last_status = current_status
            
            # Check if complete
            if current_status in ['completed', 'failed', 'canceled']:
                print(f"\n    Job finished with status: {current_status}")
                print(f"    Total time: {time.time() - start_time:.1f}s")
                
                # Get error details if failed
                if current_status == 'failed':
                    error_reason = queue_item.get('error_reason', '')
                    error_type = queue_item.get('error_type', '')
                    if error_reason or error_type:
                        print(f"    Error type: {error_type}")
                        print(f"    Error reason: {error_reason}")
                break
                
        except Exception as e:
            print(f"    Error checking status: {e}")
        
        # Adaptive wait interval
        if check_count < 10:
            time.sleep(1)
        elif check_count < 30:
            time.sleep(2)
        else:
            time.sleep(5)
    
    if current_status != 'completed':
        print(f"    Warning: Job did not complete successfully")
        return 1
    
    # Extract results
    print("\n[9] Extracting results...")
    
    # Check session information in queue item
    session_info = queue_item.get('session', {})
    if session_info:
        results = session_info.get('results', {})
        if results:
            print(f"    Found {len(results)} results in session")
            
            # Look for image outputs
            image_count = 0
            for result_id, result_data in results.items():
                if result_data.get('type') == 'image_output':
                    image_count += 1
                    image_info = result_data.get('image', {})
                    image_name = image_info.get('image_name')
                    width = result_data.get('width')
                    height = result_data.get('height')
                    
                    print(f"\n    Generated Image #{image_count}:")
                    print(f"      Name: {image_name}")
                    print(f"      Size: {width}x{height}")
                    print(f"      URL: {client.base_url}/images/i/{image_name}/full")
        else:
            print(f"    No results found in session data")
    else:
        print(f"    No session information in queue item")
    
    # Summary
    print_section("TEST SUMMARY")
    print(f"  Workflow: {workflow_def.name}")
    print(f"  Submission method: WorkflowHandle.submit_sync()")
    print(f"  Batch ID: {batch_id}")
    print(f"  Session ID: {session_id}")
    print(f"  Execution time: {time.time() - submission_start:.1f}s")
    print(f"  Final status: {current_status}")
    
    print("\n[SUCCESS] Test completed successfully!")
    print("\nKey findings for workflow-image correspondence:")
    print("- WorkflowHandle internally converts UI format to API format")
    print("- DNN models are set as normal inputs using Protocol conversion")
    print("- submit_sync() returns IvkJob with all tracking information")
    print("- Queue item contains session results with image outputs")
    print("- Images referenced by image_name in results")
    
    return 0


if __name__ == "__main__":
    exit_code = test_workflow_submission_sync()
    sys.exit(exit_code)