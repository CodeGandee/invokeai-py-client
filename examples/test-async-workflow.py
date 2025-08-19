#!/usr/bin/env python3
"""
Test script for async workflow submission (use cases 3.2 and 3.3).

This script demonstrates:
- Use case 3.2: Async submission with real-time Socket.IO events
- Use case 3.3: Hybrid approach - sync submission with async monitoring
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client.client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition


async def test_async_submission():
    """
    Use case 3.2: Asynchronous submission with real-time events.
    """
    print("=" * 80)
    print("USE CASE 3.2: Async Submission with Real-time Events")
    print("=" * 80)
    
    # Create client
    client = InvokeAIClient.from_url("http://localhost:9090")
    
    # Load a simple workflow
    workflow_path = Path("data/workflows/flux-image-to-image.json")
    if not workflow_path.exists():
        print(f"Workflow file not found: {workflow_path}")
        return
    
    # Create workflow handle
    workflow_def = WorkflowDefinition.from_file(str(workflow_path))
    workflow = client.workflow_repo.create_workflow(workflow_def)
    
    # Set some inputs (simplified for demo)
    inputs = workflow.list_inputs()
    print(f"Found {len(inputs)} workflow inputs")
    
    # Set required text inputs if any
    for inp in inputs[:3]:  # Just set first few for demo
        if hasattr(inp.field, 'value') and inp.required:
            if inp.field_name == "value" and inp.node_name in ["Positive", "Negative"]:
                if "Positive" in inp.node_name:
                    inp.field.value = "A beautiful mountain landscape"
                else:
                    inp.field.value = "blurry, low quality"
                print(f"Set {inp.label}: {inp.field.value}")
    
    # Define event callbacks
    async def on_started(event):
        print(f"  [STARTED] Node: {event.get('node_type', 'unknown')}")
    
    async def on_progress(event):
        progress = event.get('progress', 0) * 100
        message = event.get('message', '')
        print(f"  [PROGRESS] {progress:.0f}% - {message}")
    
    async def on_complete(event):
        node_type = event.get('node_type', 'unknown')
        print(f"  [COMPLETE] Node: {node_type}")
    
    async def on_error(event):
        error = event.get('error', 'Unknown error')
        print(f"  [ERROR] {error}")
    
    # Submit with events
    print("\nSubmitting workflow with real-time events...")
    try:
        result = await workflow.submit(
            queue_id="default",
            board_id="async-test",
            subscribe_events=True,
            on_invocation_started=on_started,
            on_invocation_progress=on_progress,
            on_invocation_complete=on_complete,
            on_invocation_error=on_error
        )
        
        print(f"Submitted successfully!")
        print(f"  Batch ID: {result['batch_id']}")
        print(f"  Session ID: {result['session_id']}")
        print(f"  Items enqueued: {result['enqueued']}")
        
        # Wait for completion
        print("\nWaiting for completion...")
        completed_item = await workflow.wait_for_completion(timeout=60.0)
        print(f"Workflow completed! Status: {completed_item['status']}")
        
    except asyncio.TimeoutError:
        print("Workflow timed out!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Disconnect Socket.IO
        await client.disconnect_socketio()


async def test_hybrid_approach():
    """
    Use case 3.3: Hybrid approach - submit sync, monitor async.
    """
    print("\n" + "=" * 80)
    print("USE CASE 3.3: Hybrid Approach (Sync Submit + Async Monitor)")
    print("=" * 80)
    
    # Create client
    client = InvokeAIClient.from_url("http://localhost:9090")
    
    # Load workflow
    workflow_path = Path("data/workflows/flux-image-to-image.json")
    if not workflow_path.exists():
        print(f"Workflow file not found: {workflow_path}")
        return
    
    workflow_def = WorkflowDefinition.from_file(str(workflow_path))
    workflow = client.workflow_repo.create_workflow(workflow_def)
    
    # Set some inputs
    inputs = workflow.list_inputs()
    for inp in inputs[:3]:
        if hasattr(inp.field, 'value') and inp.required:
            if inp.field_name == "value" and "Positive" in inp.node_name:
                inp.field.value = "A serene forest path"
            elif inp.field_name == "value" and "Negative" in inp.node_name:
                inp.field.value = "artifacts, noise"
    
    print("\nUsing hybrid approach: sync submission + async monitoring...")
    
    try:
        # Monitor events as they come
        event_count = 0
        async for event in workflow.submit_sync_monitor_async(
            board_id="hybrid-test"
        ):
            event_type = event.get("event_type")
            event_count += 1
            
            if event_type == "submission":
                print(f"[SUBMISSION] Batch: {event['batch_id']}")
                print(f"             Session: {event['session_id']}")
            elif event_type == "invocation_started":
                print(f"[NODE START] {event.get('node_type', 'unknown')}")
            elif event_type == "invocation_progress":
                progress = event.get('progress', 0) * 100
                print(f"[PROGRESS]   {progress:.0f}%")
            elif event_type == "invocation_complete":
                print(f"[NODE DONE]  {event.get('node_type', 'unknown')}")
            elif event_type == "invocation_error":
                print(f"[ERROR]      {event.get('error', 'unknown')}")
            elif event_type == "graph_complete":
                print(f"[COMPLETE]   Workflow finished!")
            elif event_type == "queue_item_status_changed":
                print(f"[STATUS]     {event.get('status', 'unknown')}")
        
        print(f"\nProcessed {event_count} events total")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.disconnect_socketio()


async def test_concurrent_workflows():
    """
    Bonus: Run multiple workflows concurrently using async.
    """
    print("\n" + "=" * 80)
    print("BONUS: Concurrent Workflow Execution")
    print("=" * 80)
    
    client = InvokeAIClient.from_url("http://localhost:9090")
    
    workflow_path = Path("data/workflows/flux-image-to-image.json")
    if not workflow_path.exists():
        print(f"Workflow file not found: {workflow_path}")
        return
    
    workflow_def = WorkflowDefinition.from_file(str(workflow_path))
    
    async def run_workflow(index: int):
        """Run a single workflow instance."""
        workflow = client.workflow_repo.create_workflow(workflow_def)
        
        # Set unique prompts
        for inp in workflow.list_inputs()[:2]:
            if hasattr(inp.field, 'value') and "Positive" in inp.node_name:
                inp.field.value = f"Test workflow {index}: A beautiful scene"
        
        # Submit
        result = await workflow.submit(board_id=f"concurrent-{index}")
        print(f"  Workflow {index}: Submitted (batch: {result['batch_id']})")
        
        # Wait for completion
        try:
            completed = await workflow.wait_for_completion(timeout=60.0)
            print(f"  Workflow {index}: Completed!")
            return completed
        except asyncio.TimeoutError:
            print(f"  Workflow {index}: Timed out")
            return None
    
    print("\nRunning 3 workflows concurrently...")
    
    try:
        # Run workflows in parallel
        tasks = [run_workflow(i) for i in range(1, 4)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        success_count = sum(1 for r in results if r and not isinstance(r, Exception))
        print(f"\nCompleted {success_count}/3 workflows successfully")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.disconnect_socketio()


async def main():
    """Main test runner."""
    print("InvokeAI Async Workflow Test Suite")
    print("Testing use cases 3.2 and 3.3")
    print()
    
    # Run tests
    await test_async_submission()
    await test_hybrid_approach()
    await test_concurrent_workflows()
    
    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())