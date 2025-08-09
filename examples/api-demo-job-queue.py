#!/usr/bin/env python3
"""
InvokeAI Job Queue Demo

This script demonstrates how to get the latest finished job from InvokeAI's job queue system.
InvokeAI uses a job queue to process different submissions (called "invokes").

Key concepts:
- Jobs have statuses: pending, in_progress, completed, failed, canceled
- Each job contains a complete workflow graph and execution results
- Completed jobs include the generated image information
- Jobs are ordered by creation time (oldest first - need to get last item for latest job)

API Endpoints demonstrated:
- GET /api/v1/queue/{queue_id}/list - Get queue items with filtering
- The default queue_id is "default"
"""

import requests
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

INVOKEAI_URL = "http://localhost:9090"
DEFAULT_QUEUE_ID = "default"

def get_latest_completed_job() -> Optional[Dict[str, Any]]:
    """Get the most recent completed job from the default queue.
    
    NOTE: InvokeAI's queue API does not provide sorting parameters.
    The queue is always sorted by: priority DESC, item_id ASC
    To get the latest job, we must fetch all jobs and take the last one.
    """
    try:
        # Use list_all endpoint for efficiency (single API call vs pagination)
        url = f"{INVOKEAI_URL}/api/v1/queue/{DEFAULT_QUEUE_ID}/list_all"
        
        print(f"Fetching all queue items to find latest completed job...")
        response = requests.get(url)
        response.raise_for_status()
        
        # Filter to completed jobs only (API doesn't support status filter on list_all)
        all_jobs = response.json()
        completed_jobs = [job for job in all_jobs if job.get('status') == 'completed']
        
        if not completed_jobs:
            print("No completed jobs found in the queue")
            return None
        
        # Jobs are sorted by: priority DESC, item_id ASC
        # Since most jobs have priority=0, they're essentially sorted by item_id ASC (oldest first)
        # Therefore, the LAST job in the list is the most recent
        latest_job = completed_jobs[-1]
        print(f"Found latest completed job (out of {len(completed_jobs)} total completed jobs)")
        return latest_job
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching latest job: {e}")
        return None

def get_completed_jobs(limit: int = 5) -> List[Dict[str, Any]]:
    """Get recent completed jobs from the queue."""
    try:
        url = f"{INVOKEAI_URL}/api/v1/queue/{DEFAULT_QUEUE_ID}/list"
        params = {
            "status": "completed",
            "limit": 1000  # Get all jobs since they're sorted oldest first
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        result = response.json()
        all_jobs = result.get('items', [])
        
        # Jobs are sorted oldest first, so take the last N jobs for most recent
        return all_jobs[-limit:] if len(all_jobs) >= limit else all_jobs
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching completed jobs: {e}")
        return []

def extract_generated_image(job: Dict[str, Any]) -> Optional[str]:
    """Extract the generated image name from a completed job."""
    try:
        session = job.get('session', {})
        results = session.get('results', {})
        
        # Look for image output in the results
        for node_id, result in results.items():
            if result.get('type') == 'image_output':
                image_data = result.get('image', {})
                return image_data.get('image_name')
        
        return None
        
    except Exception as e:
        print(f"Error extracting image from job: {e}")
        return None

def get_job_metadata(job: Dict[str, Any]) -> Dict[str, Any]:
    """Extract useful metadata from a job."""
    try:
        session = job.get('session', {})
        results = session.get('results', {})
        
        # Look for metadata in the results
        metadata = {}
        for node_id, result in results.items():
            if result.get('type') == 'metadata_output':
                metadata = result.get('metadata', {})
                break
        
        return metadata
        
    except Exception as e:
        print(f"Error extracting metadata from job: {e}")
        return {}

def display_job_summary(job: Dict[str, Any]):
    """Display a summary of a job."""
    print(f"\n{'='*60}")
    print(f"Job ID: {job.get('item_id')}")
    print(f"Status: {job.get('status')}")
    print(f"Origin: {job.get('origin')}")
    print(f"Destination: {job.get('destination')}")
    
    # Parse timestamps
    created_at = job.get('created_at')
    completed_at = job.get('completed_at')
    created_time = None
    
    if created_at:
        created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        print(f"Created: {created_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if completed_at:
        completed_time = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
        print(f"Completed: {completed_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if created_time:
            duration = completed_time - created_time
            print(f"Duration: {duration.total_seconds():.2f} seconds")
    
    # Extract generated image
    image_name = extract_generated_image(job)
    if image_name:
        print(f"Generated Image: {image_name}")
    
    # Extract generation metadata
    metadata = get_job_metadata(job)
    if metadata:
        print(f"Generation Mode: {metadata.get('generation_mode', 'Unknown')}")
        print(f"Model: {metadata.get('model', {}).get('name', 'Unknown') if isinstance(metadata.get('model'), dict) else metadata.get('model', 'Unknown')}")
        print(f"Positive Prompt: {metadata.get('positive_prompt', 'Unknown')}")
        print(f"Negative Prompt: {metadata.get('negative_prompt', 'Unknown')}")
        print(f"Seed: {metadata.get('seed', 'Unknown')}")
        print(f"Dimensions: {metadata.get('width', 'Unknown')}x{metadata.get('height', 'Unknown')}")
        print(f"Steps: {metadata.get('steps', 'Unknown')}")
        print(f"CFG Scale: {metadata.get('cfg_scale', 'Unknown')}")
        print(f"Scheduler: {metadata.get('scheduler', 'Unknown')}")

def download_job_image(job: Dict[str, Any], download_dir: str = "./tmp/downloads/") -> bool:
    """Download the image generated by a job."""
    image_name = extract_generated_image(job)
    if not image_name:
        print("No image found in this job")
        return False
    
    try:
        from pathlib import Path
        import os
        
        # Create download directory
        Path(download_dir).mkdir(parents=True, exist_ok=True)
        
        # Download the image
        image_url = f"{INVOKEAI_URL}/api/v1/images/i/{image_name}/full"
        response = requests.get(image_url)
        response.raise_for_status()
        
        # Save the image
        file_path = os.path.join(download_dir, image_name)
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        file_size = os.path.getsize(file_path)
        print(f"Downloaded: {file_path} ({file_size:,} bytes)")
        return True
        
    except Exception as e:
        print(f"Error downloading image: {e}")
        return False

def demo_latest_finished_job():
    """Demonstrate getting the latest finished job from the queue."""
    print("InvokeAI Job Queue Demo")
    print("=" * 50)
    
    # Get the latest completed job
    latest_job = get_latest_completed_job()
    
    if not latest_job:
        print("No completed jobs found in the queue")
        return
    
    print("Latest Completed Job:")
    display_job_summary(latest_job)
    
    # Download the generated image
    print(f"\nDownloading generated image...")
    success = download_job_image(latest_job)
    
    if success:
        print(f"\n✅ Successfully retrieved and downloaded the latest finished job!")
    else:
        print(f"\n⚠️ Job retrieved but image download failed")

def demo_recent_jobs():
    """Show recent completed jobs for comparison."""
    print(f"\n{'='*60}")
    print("Recent Completed Jobs (showing 3 most recent):")
    print("=" * 45)
    
    jobs = get_completed_jobs(limit=3)
    
    # Reverse the order to show newest first for better readability
    for i, job in enumerate(reversed(jobs), 1):
        print(f"\n--- Job #{i} (ID: {job.get('item_id')}) ---")
        print(f"Created: {job.get('created_at')}")
        
        image_name = extract_generated_image(job)
        if image_name:
            print(f"Image: {image_name}")
        
        metadata = get_job_metadata(job)
        if metadata:
            prompt = metadata.get('positive_prompt', 'Unknown')
            # Truncate very long prompts for readability
            if len(prompt) > 80:
                prompt = prompt[:77] + "..."
            print(f"Prompt: {prompt}")

if __name__ == "__main__":
    try:
        demo_latest_finished_job()
        demo_recent_jobs()
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to InvokeAI: {e}")
        print("Make sure InvokeAI is running on localhost:9090")
