#!/usr/bin/env python3
"""
InvokeAI API Demo: Job Exception Handling and Cancellation
===========================================================

Task 4: Job exception handling with cancellation capabilities.

This script demonstrates:
1. How to cancel running jobs (individual and batch cancellation)
2. Various exception types that can occur during job submission/execution
3. Comprehensive error handling for job failures
4. Proper cleanup and error reporting

Features:
- Individual job cancellation by item_id
- Batch job cancellation by batch_id
- Queue-wide cancellation operations
- Exception type identification and handling
- Error message extraction and reporting
- Job state monitoring for failure detection
- Comprehensive error recovery mechanisms

Dependencies:
- InvokeAI running on localhost:9090
- Previous job submission implementation for testing
"""

import requests
import json
import time
import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from enum import Enum


class JobException(Exception):
    """Custom exception for InvokeAI job-related errors."""
    def __init__(self, message: str, job_id: Optional[str] = None, error_type: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.job_id = job_id
        self.error_type = error_type
        self.details = details or {}


class JobErrorType(Enum):
    """Enumeration of different job error types."""
    SUBMISSION_FAILED = "submission_failed"
    VALIDATION_ERROR = "validation_error"
    EXECUTION_FAILED = "execution_failed"
    TIMEOUT_ERROR = "timeout_error"
    NETWORK_ERROR = "network_error"
    RESOURCE_ERROR = "resource_error"
    CANCELLATION_FAILED = "cancellation_failed"
    UNKNOWN_ERROR = "unknown_error"


class InvokeAIJobExceptionHandler:
    """
    Comprehensive job exception handling and cancellation system for InvokeAI API.
    
    Features:
    - Job cancellation (individual, batch, queue-wide)
    - Exception type classification and handling
    - Error reporting and recovery mechanisms
    - Job state monitoring for failure detection
    - Comprehensive logging and debugging support
    """
    
    def __init__(self, base_url: str = "http://localhost:9090"):
        self.base_url = base_url
        self.session = requests.Session()
        
        # Error tracking
        self.error_log = []
        self.cancelled_jobs = []
        
        # Database path for direct queue access
        self.db_path = r"F:\invoke-ai-app\databases\invokeai.db"
        
        print(f"InvokeAI Job Exception Handler initialized")
        print(f"   API Base URL: {base_url}")
        print(f"   Direct DB: {'Available' if os.path.exists(self.db_path) else 'Not found'}")
    
    def cancel_job_by_item_id(self, item_id: int, queue_id: str = "default") -> bool:
        """Cancel a specific job by its item ID."""
        try:
            print(f"🚫 Cancelling job with item ID: {item_id}")
            
            url = f"{self.base_url}/api/v1/queue/{queue_id}/i/{item_id}/cancel"
            response = self.session.put(url)  # Correct HTTP method is PUT
            response.raise_for_status()
            
            self.cancelled_jobs.append({
                'item_id': item_id,
                'queue_id': queue_id,
                'cancelled_at': datetime.now().isoformat(),
                'method': 'individual'
            })
            
            print(f"   ✅ Successfully cancelled job {item_id}")
            return True
            
        except requests.RequestException as e:
            error_msg = f"Failed to cancel job {item_id}: {e}"
            print(f"   ❌ {error_msg}")
            self._log_error(JobErrorType.CANCELLATION_FAILED, error_msg, {'item_id': item_id})
            return False
        except Exception as e:
            error_msg = f"Unexpected error cancelling job {item_id}: {e}"
            print(f"   ❌ {error_msg}")
            self._log_error(JobErrorType.UNKNOWN_ERROR, error_msg, {'item_id': item_id})
            return False
    
    def cancel_jobs_by_batch_id(self, batch_id: str, queue_id: str = "default") -> bool:
        """Cancel all jobs in a specific batch."""
        try:
            print(f"🚫 Cancelling all jobs in batch: {batch_id}")
            
            url = f"{self.base_url}/api/v1/queue/{queue_id}/cancel_by_batch_ids"
            data = {"batch_ids": [batch_id]}
            
            response = self.session.put(url, json=data)  # Correct HTTP method is PUT
            response.raise_for_status()
            
            result = response.json()
            
            self.cancelled_jobs.append({
                'batch_id': batch_id,
                'queue_id': queue_id,
                'cancelled_at': datetime.now().isoformat(),
                'method': 'batch',
                'result': result
            })
            
            print(f"   ✅ Successfully cancelled batch {batch_id}")
            print(f"   📊 Result: {result}")
            return True
            
        except requests.RequestException as e:
            error_msg = f"Failed to cancel batch {batch_id}: {e}"
            print(f"   ❌ {error_msg}")
            self._log_error(JobErrorType.CANCELLATION_FAILED, error_msg, {'batch_id': batch_id})
            return False
        except Exception as e:
            error_msg = f"Unexpected error cancelling batch {batch_id}: {e}"
            print(f"   ❌ {error_msg}")
            self._log_error(JobErrorType.UNKNOWN_ERROR, error_msg, {'batch_id': batch_id})
            return False
    
    def cancel_all_pending_jobs(self, queue_id: str = "default") -> bool:
        """Cancel all pending jobs except currently executing ones."""
        try:
            print(f"🚫 Cancelling all pending jobs in queue: {queue_id}")
            
            url = f"{self.base_url}/api/v1/queue/{queue_id}/cancel_all_except_current"
            response = self.session.post(url)
            response.raise_for_status()
            
            result = response.json()
            
            self.cancelled_jobs.append({
                'queue_id': queue_id,
                'cancelled_at': datetime.now().isoformat(),
                'method': 'all_pending',
                'result': result
            })
            
            print(f"   ✅ Successfully cancelled all pending jobs")
            print(f"   📊 Result: {result}")
            return True
            
        except requests.RequestException as e:
            error_msg = f"Failed to cancel all pending jobs: {e}"
            print(f"   ❌ {error_msg}")
            self._log_error(JobErrorType.CANCELLATION_FAILED, error_msg, {'queue_id': queue_id})
            return False
        except Exception as e:
            error_msg = f"Unexpected error cancelling all pending jobs: {e}"
            print(f"   ❌ {error_msg}")
            self._log_error(JobErrorType.UNKNOWN_ERROR, error_msg, {'queue_id': queue_id})
            return False
    
    def clear_entire_queue(self, queue_id: str = "default") -> bool:
        """Clear the entire queue, cancelling all jobs including currently executing ones."""
        try:
            print(f"🚫 Clearing entire queue: {queue_id}")
            print(f"   ⚠️ WARNING: This will cancel ALL jobs including currently executing ones!")
            
            url = f"{self.base_url}/api/v1/queue/{queue_id}/clear"
            response = self.session.post(url)
            response.raise_for_status()
            
            result = response.json()
            
            self.cancelled_jobs.append({
                'queue_id': queue_id,
                'cancelled_at': datetime.now().isoformat(),
                'method': 'clear_all',
                'result': result
            })
            
            print(f"   ✅ Successfully cleared entire queue")
            print(f"   📊 Result: {result}")
            return True
            
        except requests.RequestException as e:
            error_msg = f"Failed to clear queue: {e}"
            print(f"   ❌ {error_msg}")
            self._log_error(JobErrorType.CANCELLATION_FAILED, error_msg, {'queue_id': queue_id})
            return False
        except Exception as e:
            error_msg = f"Unexpected error clearing queue: {e}"
            print(f"   ❌ {error_msg}")
            self._log_error(JobErrorType.UNKNOWN_ERROR, error_msg, {'queue_id': queue_id})
            return False
    
    def submit_job_with_error_handling(self, workflow_data: Dict[str, Any], queue_id: str = "default") -> Optional[Dict[str, Any]]:
        """Submit a job with comprehensive error handling."""
        try:
            print(f"🔄 Submitting job with error handling...")
            
            url = f"{self.base_url}/api/v1/queue/{queue_id}/enqueue_batch"
            batch_data = {
                "prepend": False,
                "batch": {
                    "graph": workflow_data,
                    "runs": 1
                }
            }
            
            response = self.session.post(url, json=batch_data)
            response.raise_for_status()
            
            result = response.json()
            
            # Extract job information
            batch_id = result.get('batch', {}).get('batch_id')
            item_ids = result.get('item_ids', [])
            
            if not batch_id or not item_ids:
                raise JobException(
                    "Job submission succeeded but no valid job IDs returned",
                    error_type=JobErrorType.SUBMISSION_FAILED.value,
                    details=result
                )
            
            job_info = {
                'batch_id': batch_id,
                'item_ids': item_ids,
                'submitted_at': datetime.now().isoformat(),
                'status': 'submitted'
            }
            
            print(f"   ✅ Job submitted successfully")
            print(f"      Batch ID: {batch_id}")
            print(f"      Item IDs: {item_ids}")
            
            return job_info
            
        except requests.HTTPError as e:
            # Handle HTTP errors (4xx, 5xx status codes)
            error_type = self._classify_http_error(e.response.status_code)
            error_details = self._extract_error_details(e.response)
            
            error_msg = f"HTTP {e.response.status_code}: {error_details.get('message', str(e))}"
            print(f"   ❌ Job submission failed: {error_msg}")
            
            self._log_error(error_type, error_msg, error_details)
            return None
            
        except requests.ConnectionError as e:
            error_msg = f"Connection error: {e}"
            print(f"   ❌ Job submission failed: {error_msg}")
            self._log_error(JobErrorType.NETWORK_ERROR, error_msg, {'exception': str(e)})
            return None
            
        except requests.Timeout as e:
            error_msg = f"Request timeout: {e}"
            print(f"   ❌ Job submission failed: {error_msg}")
            self._log_error(JobErrorType.TIMEOUT_ERROR, error_msg, {'exception': str(e)})
            return None
            
        except JobException as e:
            print(f"   ❌ Job submission failed: {e}")
            self._log_error(JobErrorType(e.error_type), str(e), e.details)
            return None
            
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"   ❌ Job submission failed: {error_msg}")
            self._log_error(JobErrorType.UNKNOWN_ERROR, error_msg, {'exception': str(e)})
            return None
    
    def monitor_job_with_failure_handling(self, item_id: int, max_wait_time: int = 300) -> Dict[str, Any]:
        """Monitor a job with failure detection and handling."""
        print(f"👀 Monitoring job {item_id} with failure handling...")
        
        start_time = time.time()
        last_status = None
        check_count = 0
        
        try:
            while time.time() - start_time < max_wait_time:
                check_count += 1
                
                # Get job status
                job_item = self._get_job_item(item_id)
                
                if not job_item:
                    # Job not found - might have been cancelled or deleted
                    error_msg = f"Job {item_id} not found - may have been cancelled or deleted"
                    print(f"   ⚠️ {error_msg}")
                    return {
                        'status': 'not_found',
                        'item_id': item_id,
                        'error': error_msg,
                        'check_count': check_count
                    }
                
                current_status = job_item.get('status')
                
                if current_status != last_status:
                    elapsed = time.time() - start_time
                    print(f"   [{elapsed:.1f}s] Status: {current_status} (check #{check_count})")
                    last_status = current_status
                
                # Check for completion
                if current_status == 'completed':
                    print(f"   ✅ Job completed successfully")
                    return {
                        'status': 'completed',
                        'item_id': item_id,
                        'job_data': job_item,
                        'check_count': check_count
                    }
                
                # Check for failure
                elif current_status == 'failed':
                    error_msg = f"Job {item_id} failed during execution"
                    print(f"   ❌ {error_msg}")
                    
                    # Extract error details from job
                    error_details = self._extract_job_error_details(job_item)
                    
                    self._log_error(
                        JobErrorType.EXECUTION_FAILED,
                        error_msg,
                        {'item_id': item_id, 'job_data': job_item, **error_details}
                    )
                    
                    return {
                        'status': 'failed',
                        'item_id': item_id,
                        'error': error_msg,
                        'error_details': error_details,
                        'job_data': job_item,
                        'check_count': check_count
                    }
                
                # Check for cancellation
                elif current_status == 'canceled':
                    print(f"   🚫 Job {item_id} was cancelled")
                    return {
                        'status': 'canceled',
                        'item_id': item_id,
                        'job_data': job_item,
                        'check_count': check_count
                    }
                
                # Wait before next check
                time.sleep(2)
            
            # Timeout reached
            error_msg = f"Job {item_id} monitoring timeout ({max_wait_time}s)"
            print(f"   ⏰ {error_msg}")
            self._log_error(JobErrorType.TIMEOUT_ERROR, error_msg, {'item_id': item_id})
            
            return {
                'status': 'timeout',
                'item_id': item_id,
                'error': error_msg,
                'check_count': check_count
            }
            
        except Exception as e:
            error_msg = f"Error monitoring job {item_id}: {e}"
            print(f"   ❌ {error_msg}")
            self._log_error(JobErrorType.UNKNOWN_ERROR, error_msg, {'item_id': item_id})
            
            return {
                'status': 'monitor_error',
                'item_id': item_id,
                'error': error_msg,
                'check_count': check_count
            }
    
    def _get_job_item(self, item_id: int, queue_id: str = "default") -> Optional[Dict[str, Any]]:
        """Get job item details from the queue."""
        try:
            url = f"{self.base_url}/api/v1/queue/{queue_id}/i/{item_id}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None
    
    def _classify_http_error(self, status_code: int) -> JobErrorType:
        """Classify HTTP errors into job error types."""
        if status_code == 400:
            return JobErrorType.VALIDATION_ERROR
        elif status_code == 422:
            return JobErrorType.VALIDATION_ERROR
        elif status_code == 500:
            return JobErrorType.EXECUTION_FAILED
        elif status_code == 503:
            return JobErrorType.RESOURCE_ERROR
        else:
            return JobErrorType.NETWORK_ERROR
    
    def _extract_error_details(self, response) -> Dict[str, Any]:
        """Extract detailed error information from HTTP response."""
        details = {
            'status_code': response.status_code,
            'reason': response.reason
        }
        
        try:
            error_data = response.json()
            details['message'] = error_data.get('detail', 'Unknown error')
            details['response_data'] = error_data
        except:
            details['message'] = response.text
            details['response_text'] = response.text
        
        return details
    
    def _extract_job_error_details(self, job_item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract error details from a failed job item."""
        details = {}
        
        # Look for error information in the job session
        session = job_item.get('session', {})
        if session:
            errors = session.get('errors', {})
            if errors:
                details['session_errors'] = errors
                
                # Extract first error message
                for error_id, error_data in errors.items():
                    details['first_error'] = {
                        'error_id': error_id,
                        'error_data': error_data
                    }
                    break
        
        return details
    
    def _log_error(self, error_type: JobErrorType, message: str, details: Dict[str, Any]):
        """Log an error with timestamp and details."""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type.value,
            'message': message,
            'details': details
        }
        self.error_log.append(error_entry)
    
    def demonstrate_job_cancellation(self) -> None:
        """Demonstrate various job cancellation techniques."""
        print(f"\n🎯 Demonstrating Job Cancellation Techniques")
        print(f"=" * 50)
        
        # First, let's see what's currently in the queue
        self._show_queue_status()
        
        # Method 1: Cancel by item ID (if there are any pending jobs)
        print(f"\n1️⃣ Individual Job Cancellation Test")
        pending_items = self._get_pending_items()
        
        if pending_items:
            test_item_id = pending_items[0]['item_id']
            print(f"   Testing cancellation of item {test_item_id}")
            self.cancel_job_by_item_id(test_item_id)
        else:
            print(f"   No pending jobs to cancel individually")
        
        # Method 2: Submit a test job and then cancel it
        print(f"\n2️⃣ Submit Test Job and Cancel")
        test_workflow = self._create_minimal_test_workflow()
        
        if test_workflow:
            job_info = self.submit_job_with_error_handling(test_workflow)
            
            if job_info:
                # Wait a moment, then cancel
                time.sleep(2)
                batch_id = job_info['batch_id']
                item_id = job_info['item_ids'][0]
                
                print(f"   Cancelling test job {item_id} in batch {batch_id}")
                self.cancel_job_by_item_id(item_id)
        
        # Method 3: Demonstrate batch cancellation (create test batch first)
        print(f"\n3️⃣ Batch Cancellation Test")
        print(f"   Creating test batch with multiple jobs...")
        
        test_batch_info = self._create_test_batch()
        if test_batch_info:
            time.sleep(1)  # Let jobs start
            batch_id = test_batch_info['batch_id']
            print(f"   Cancelling entire test batch {batch_id}")
            self.cancel_jobs_by_batch_id(batch_id)
        
        # Show final queue status
        print(f"\n📊 Final Queue Status:")
        self._show_queue_status()
    
    def demonstrate_error_handling(self) -> None:
        """Demonstrate various error handling scenarios."""
        print(f"\n🎯 Demonstrating Error Handling Scenarios")
        print(f"=" * 50)
        
        # Error 1: Invalid workflow submission
        print(f"\n1️⃣ Testing Invalid Workflow Submission")
        invalid_workflow = {"invalid": "workflow", "missing": "required_fields"}
        self.submit_job_with_error_handling(invalid_workflow)
        
        # Error 2: Malformed JSON
        print(f"\n2️⃣ Testing Malformed Workflow Data")
        malformed_workflow = {"nodes": "should_be_dict_not_string", "edges": []}
        self.submit_job_with_error_handling(malformed_workflow)
        
        # Error 3: Network error simulation (invalid endpoint)
        print(f"\n3️⃣ Testing Network Error Handling")
        try:
            # Temporarily modify base URL to simulate network error
            original_url = self.base_url
            self.base_url = "http://invalid-url:9999"
            
            test_workflow = self._create_minimal_test_workflow()
            if test_workflow:
                self.submit_job_with_error_handling(test_workflow)
            
            # Restore original URL
            self.base_url = original_url
            
        except Exception as e:
            print(f"   Expected network error: {e}")
        
        # Error 4: Submit valid job but simulate monitoring failure
        print(f"\n4️⃣ Testing Job Execution Monitoring")
        test_workflow = self._create_minimal_test_workflow()
        
        if test_workflow:
            job_info = self.submit_job_with_error_handling(test_workflow)
            
            if job_info:
                item_id = job_info['item_ids'][0]
                
                # Monitor the job and handle any failures
                result = self.monitor_job_with_failure_handling(item_id, max_wait_time=30)
                
                print(f"   Monitoring result: {result['status']}")
                
                # If job is still running, cancel it for cleanup
                if result['status'] in ['in_progress', 'pending']:
                    print(f"   Cleaning up running job...")
                    self.cancel_job_by_item_id(item_id)
    
    def _show_queue_status(self):
        """Display current queue status."""
        try:
            url = f"{self.base_url}/api/v1/queue/default/status"
            response = self.session.get(url)
            response.raise_for_status()
            
            status = response.json()
            queue_info = status.get('queue', {})
            
            print(f"   📋 Queue Status:")
            print(f"      Pending: {queue_info.get('pending', 0)}")
            print(f"      In Progress: {queue_info.get('in_progress', 0)}")
            print(f"      Completed: {queue_info.get('completed', 0)}")
            print(f"      Failed: {queue_info.get('failed', 0)}")
            print(f"      Canceled: {queue_info.get('canceled', 0)}")
            
        except Exception as e:
            print(f"   ❌ Could not get queue status: {e}")
    
    def _get_pending_items(self) -> List[Dict[str, Any]]:
        """Get list of pending queue items."""
        try:
            url = f"{self.base_url}/api/v1/queue/default/list"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            
            # Filter for pending items
            pending_items = [item for item in items if item.get('status') == 'pending']
            return pending_items
            
        except Exception as e:
            print(f"   ⚠️ Could not get pending items: {e}")
            return []
    
    def _create_minimal_test_workflow(self) -> Optional[Dict[str, Any]]:
        """Create a minimal test workflow for demonstration purposes."""
        # This is a simplified workflow that should work for testing
        workflow = {
            "id": "test_workflow",
            "nodes": {
                "test_node": {
                    "id": "test_node",
                    "type": "string",
                    "is_intermediate": False,
                    "use_cache": True,
                    "value": "test_value"
                }
            },
            "edges": []
        }
        return workflow
    
    def _create_test_batch(self) -> Optional[Dict[str, Any]]:
        """Create a test batch with multiple jobs."""
        try:
            test_workflow = self._create_minimal_test_workflow()
            if not test_workflow:
                return None
            
            url = f"{self.base_url}/api/v1/queue/default/enqueue_batch"
            batch_data = {
                "prepend": False,
                "batch": {
                    "graph": test_workflow,
                    "runs": 3  # Create 3 test jobs
                }
            }
            
            response = self.session.post(url, json=batch_data)
            response.raise_for_status()
            
            result = response.json()
            batch_id = result.get('batch', {}).get('batch_id')
            item_ids = result.get('item_ids', [])
            
            print(f"   Created test batch {batch_id} with {len(item_ids)} jobs")
            
            return {
                'batch_id': batch_id,
                'item_ids': item_ids
            }
            
        except Exception as e:
            print(f"   ❌ Could not create test batch: {e}")
            return None
    
    def print_error_summary(self):
        """Print a summary of all errors encountered."""
        print(f"\n📊 Error Summary")
        print(f"=" * 30)
        
        if not self.error_log:
            print(f"   ✅ No errors encountered")
            return
        
        # Group errors by type
        error_types = {}
        for error in self.error_log:
            error_type = error['error_type']
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(error)
        
        print(f"   Total errors: {len(self.error_log)}")
        print(f"   Error types:")
        
        for error_type, errors in error_types.items():
            print(f"      {error_type}: {len(errors)} error(s)")
            
            # Show latest error of each type
            latest_error = errors[-1]
            print(f"         Latest: {latest_error['message']}")
    
    def print_cancellation_summary(self):
        """Print a summary of all job cancellations."""
        print(f"\n📊 Cancellation Summary")
        print(f"=" * 30)
        
        if not self.cancelled_jobs:
            print(f"   No jobs were cancelled")
            return
        
        print(f"   Total cancellations: {len(self.cancelled_jobs)}")
        
        for i, cancellation in enumerate(self.cancelled_jobs, 1):
            method = cancellation['method']
            
            if method == 'individual':
                print(f"   {i}. Individual job {cancellation['item_id']} at {cancellation['cancelled_at']}")
            elif method == 'batch':
                print(f"   {i}. Batch {cancellation['batch_id']} at {cancellation['cancelled_at']}")
            elif method == 'all_pending':
                print(f"   {i}. All pending jobs at {cancellation['cancelled_at']}")
            elif method == 'clear_all':
                print(f"   {i}. Cleared entire queue at {cancellation['cancelled_at']}")


def main():
    """Main execution function demonstrating Task 4 implementation."""
    print("InvokeAI API Demo: Job Exception Handling & Cancellation")
    print("=" * 65)
    
    # Initialize the exception handler
    handler = InvokeAIJobExceptionHandler()
    
    # Demonstrate job cancellation capabilities
    handler.demonstrate_job_cancellation()
    
    # Demonstrate error handling scenarios
    handler.demonstrate_error_handling()
    
    # Print summaries
    handler.print_error_summary()
    handler.print_cancellation_summary()
    
    print("\nTask 4 Complete - Job Exception Handling & Cancellation Demo")


if __name__ == "__main__":
    main()
