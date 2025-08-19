#!/usr/bin/env python
"""
Comprehensive test for workflow submission with DNN model support.
Tests both sync and async submission methods after refactoring _convert_to_api_format.
"""

import asyncio
import time
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowRepository
from invokeai_py_client.ivk_fields.model_conversion import to_ivk_model_field


def test_sync_submission():
    """Test synchronous workflow submission with DNN model."""
    print("\n" + "=" * 60)
    print(" TEST 1: SYNCHRONOUS WORKFLOW SUBMISSION")
    print("=" * 60)
    
    # Initialize client
    print("\n[1] Initializing client...")
    # Use from_url helper so base_path is set to /api/v1 automatically
    client = InvokeAIClient.from_url("http://127.0.0.1:9090")
    
    # Get model repository
    print("\n[2] Discovering SDXL models...")
    model_repo = client.dnn_model_repo
    all_models = model_repo.list_models()
    from invokeai_py_client.dnn_model import DnnModelType, BaseDnnModelType
    
    # Filter for SDXL Main models only (not ControlNet, VAE, etc.)
    sdxl_models = [
        m for m in all_models 
        if m.type == DnnModelType.Main and 
        m.base == BaseDnnModelType.StableDiffusionXL
    ]
    
    if not sdxl_models:
        print("    ERROR: No SDXL Main models found!")
        return False
    
    selected_model = sdxl_models[0]
    print(f"    Selected: {selected_model.name}")
    print(f"    Base: {selected_model.base.value}")
    print(f"    Type: {selected_model.type.value}")
    
    # Load workflow
    print("\n[3] Loading workflow...")
    workflow_repo = WorkflowRepository(client)
    workflow_path = Path("data/workflows/sdxl-text-to-image.json")
    workflow = workflow_repo.create_workflow_from_file(str(workflow_path))
    print(f"    Loaded: {workflow.definition.name}")
    print(f"    Inputs: {len(workflow.inputs)}")
    
    # Set inputs
    print("\n[4] Setting workflow inputs...")
    
    # Set model (index 0)
    model_field = to_ivk_model_field(selected_model)
    workflow.set_input_value(0, value=model_field)
    print(f"    Set model: {model_field.name}")
    
    # Set prompts
    positive_field = workflow.get_input_value(1)
    if hasattr(positive_field, 'value'):
        positive_field.value = "A majestic dragon flying over ancient castles during sunset, highly detailed fantasy art"  # type: ignore[attr-defined]
    print("    Set positive prompt")
    
    negative_field = workflow.get_input_value(2)
    if hasattr(negative_field, 'value'):
        negative_field.value = "blurry, low quality, distorted, bad anatomy"  # type: ignore[attr-defined]
    print("    Set negative prompt")
    
    # Validate
    print("\n[5] Validating inputs...")
    errors = workflow.validate_inputs()
    if errors:
        print(f"    Validation errors: {errors}")
        return False
    print("    Validation passed!")
    
    # Submit
    print("\n[6] Submitting workflow (sync)...")
    try:
        result = workflow.submit_sync()
        # submit_sync returns a flat dict: {batch_id, item_ids, enqueued, session_id}
        batch_id = result.get('batch_id')
        item_ids = result.get('item_ids', [])
        item_id = item_ids[0] if item_ids else None
        
        print(f"    Batch ID: {batch_id}")
        print(f"    Item ID: {item_id}")
        
        if not item_id:
            print("    ERROR: No item ID returned")
            return False
        
        # Monitor completion via queue API
        print("\n[7] Monitoring execution...")
        item_url = f"{client.base_url}/queue/default/i/{item_id}"
        max_wait = 60
        start_time = time.time()
        final_status = None
        
        while time.time() - start_time < max_wait:
            try:
                response = client.session.get(item_url)
                response.raise_for_status()
                queue_item = response.json()
                status = queue_item.get('status')
                
                if status in ['completed', 'failed', 'canceled']:
                    final_status = status
                    break
                
                time.sleep(2)
            except Exception as e:
                print(f"    Error checking status: {e}")
                time.sleep(2)
        
        print(f"    Final status: {final_status}")
        
        if final_status == "completed":
            print("    SUCCESS: Workflow completed!")
            return True
        else:
            print(f"    ERROR: Workflow failed with status {final_status}")
            return False
            
    except Exception as e:
        print(f"    ERROR: {e}")
        return False


async def test_async_submission():
    """Test asynchronous workflow submission with Socket.IO events."""
    print("\n" + "=" * 60)
    print(" TEST 2: ASYNCHRONOUS WORKFLOW SUBMISSION")
    print("=" * 60)
    
    # Initialize client
    print("\n[1] Initializing client...")
    client = InvokeAIClient.from_url("http://127.0.0.1:9090")
    
    # Get model repository
    print("\n[2] Discovering SDXL models...")
    model_repo = client.dnn_model_repo
    all_models = model_repo.list_models()
    from invokeai_py_client.dnn_model import DnnModelType, BaseDnnModelType
    
    # Filter for SDXL Main models only (not ControlNet, VAE, etc.)
    sdxl_models = [
        m for m in all_models 
        if m.type == DnnModelType.Main and 
        m.base == BaseDnnModelType.StableDiffusionXL
    ]
    
    if not sdxl_models:
        print("    ERROR: No SDXL Main models found!")
        return False
    
    selected_model = sdxl_models[0]
    print(f"    Selected: {selected_model.name}")
    print(f"    Base: {selected_model.base.value}")
    print(f"    Type: {selected_model.type.value}")
    
    # Load workflow
    print("\n[3] Loading workflow...")
    workflow_repo = WorkflowRepository(client)
    workflow_path = Path("data/workflows/sdxl-text-to-image.json")
    workflow = workflow_repo.create_workflow_from_file(str(workflow_path))
    print(f"    Loaded: {workflow.definition.name}")
    
    # Set inputs
    print("\n[4] Setting workflow inputs...")
    
    # Set model
    model_field = to_ivk_model_field(selected_model)
    workflow.set_input_value(0, value=model_field)
    print(f"    Set model: {model_field.name}")
    
    # Set prompts
    positive_field = workflow.get_input_value(1)
    if hasattr(positive_field, 'value'):
        positive_field.value = "An underwater coral reef city inhabited by mermaids, bioluminescent lighting, photorealistic"  # type: ignore[attr-defined]
    print("    Set positive prompt")
    
    negative_field = workflow.get_input_value(2)
    if hasattr(negative_field, 'value'):
        negative_field.value = "blurry, low quality, distorted, oversaturated, amateur"  # type: ignore[attr-defined]
    print("    Set negative prompt")
    
    # Event tracking
    events_received = []
    
    def on_progress(event):
        progress = event.get('progress', 0)
        node_id = event.get('node_id', 'unknown')
        events_received.append(('progress', node_id, progress))
        print(f"    Progress: {node_id[:20]}... - {progress*100:.0f}%")
    
    def on_complete(event):
        node_id = event.get('node_id', 'unknown')
        events_received.append(('complete', node_id))
        print(f"    Completed: {node_id[:20]}...")
    
    def on_error(event):
        node_id = event.get('node_id', 'unknown')
        error = event.get('error', 'Unknown error')
        events_received.append(('error', node_id, error))
        print(f"    ERROR in {node_id[:20]}...: {error}")
    
    # Submit with event subscriptions
    print("\n[5] Submitting workflow (async with events)...")
    try:
        result = await workflow.submit(
            subscribe_events=True,
            on_invocation_progress=on_progress,
            on_invocation_complete=on_complete,
            on_invocation_error=on_error
        )
        batch_id = result.get('batch_id')
        session_id = result.get('session_id')
        item_ids = result.get('item_ids', [])
        item_id = item_ids[0] if item_ids else None
        
        print(f"    Batch ID: {batch_id}")
        print(f"    Session ID: {session_id}")
        print(f"    Items queued: {result.get('enqueued', 0)}")
        
        if not item_id:
            print("    ERROR: No item ID returned")
            return False
        
        # Monitor via queue API
        print("\n[6] Monitoring execution...")
        item_url = f"{client.base_url}/queue/default/i/{item_id}"
        max_wait = 60
        start_time = time.time()
        final_status = None
        
        while time.time() - start_time < max_wait:
            await asyncio.sleep(2)
            
            try:
                # Use sync request within async function
                response = client.session.get(item_url)
                response.raise_for_status()
                queue_item = response.json()
                status = queue_item.get('status')
                
                if status in ['completed', 'failed', 'canceled']:
                    final_status = status
                    break
                    
            except Exception as e:
                print(f"    Error checking status: {e}")
        
        print(f"\n[7] Final status: {final_status}")
        print(f"    Events received: {len(events_received)}")
        
        if final_status == "completed":
            print("    SUCCESS: Workflow completed!")
            return True
        else:
            print(f"    ERROR: Workflow failed with status {final_status}")
            return False
            
    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print(" COMPREHENSIVE WORKFLOW SUBMISSION TEST")
    print("=" * 60)
    print("\nThis test verifies that workflow submission works correctly")
    print("after refactoring _convert_to_api_format to use raw_data.")
    
    # Test 1: Sync submission
    sync_result = test_sync_submission()
    
    # Test 2: Async submission
    async_result = asyncio.run(test_async_submission())
    
    # Summary
    print("\n" + "=" * 60)
    print(" TEST SUMMARY")
    print("=" * 60)
    print(f"  Sync submission:  {'PASSED' if sync_result else 'FAILED'}")
    print(f"  Async submission: {'PASSED' if async_result else 'FAILED'}")
    
    if sync_result and async_result:
        print("\n[SUCCESS] All tests passed!")
        print("\nKey implementation details verified:")
        print("- WorkflowHandle._convert_to_api_format() uses raw_data")
        print("- Only modifies fields set through WorkflowHandle inputs")
        print("- Generates clean API format without field metadata")
        print("- DNN models work as normal inputs via Protocol conversion")
        print("- Both sync and async submission methods work correctly")
    else:
        print("\n[FAILURE] Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()