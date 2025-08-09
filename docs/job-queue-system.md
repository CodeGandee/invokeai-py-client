# InvokeAI Job Queue System

InvokeAI uses a sophisticated job queue system to process image generation requests (called "invokes"). This document explains how to interact with the queue system via the REST API.

## Queue Overview

### Job States
- **pending**: Job is waiting in the queue to run
- **in_progress**: Job is currently being processed
- **completed**: Job finished successfully
- **failed**: Job encountered an error
- **canceled**: Job was manually canceled

### Queue Structure
- Default queue ID: `"default"`
- **Jobs are ordered chronologically (oldest first) - to get the latest job, use the LAST item in the list**
- Each job contains complete workflow graphs and execution results

## Key Endpoints

### Get Queue Status
```bash
GET /api/v1/queue/{queue_id}/status
```

Example response:
```json
{
  "queue": {
    "queue_id": "default",
    "pending": 0,
    "in_progress": 0,
    "completed": 163,
    "failed": 0,
    "canceled": 2,
    "total": 165
  },
  "processor": {
    "is_started": true,
    "is_processing": false
  }
}
```

### List Queue Items
```bash
GET /api/v1/queue/{queue_id}/list?status={status}&limit={limit}
```

**⚠️ IMPORTANT: Jobs are sorted chronologically (oldest first). To get the latest finished job, you need the LAST item in the list, not the first!**

Parameters:
- `status`: Filter by job status (pending, in_progress, completed, failed, canceled)
- `limit`: Maximum number of jobs to return (default: 50, use 1000+ to get all jobs)
- `offset`: Number of jobs to skip (for pagination)
- `limit`: Maximum number of items to return (default: 50)
- `cursor`: Pagination cursor for large result sets

### Get Current Job
```bash
GET /api/v1/queue/{queue_id}/current
```
Returns the currently processing job, or `null` if none.

### Get Specific Job
```bash
GET /api/v1/queue/{queue_id}/i/{item_id}
```

## Job Structure

### Basic Job Information
```json
{
  "item_id": 563,
  "status": "completed",
  "priority": 0,
  "batch_id": "e3270230-fc4e-4c3b-92a8-fa6d3f3e1807",
  "origin": "canvas",
  "destination": "generate",
  "session_id": "042552fd-8dc5-42e8-b1c4-54975731923f",
  "queue_id": "default"
}
```

### Timestamps
```json
{
  "created_at": "2025-08-09 16:11:26.998",
  "updated_at": "2025-08-09 16:11:35.625", 
  "started_at": "2025-08-09 16:11:27.004",
  "completed_at": "2025-08-09 16:11:35.625"
}
```

### Error Information (if failed)
```json
{
  "error_type": "string",
  "error_message": "string", 
  "error_traceback": "string"
}
```

### Session Data
Each job contains a complete `session` object with:
- **graph**: Original workflow graph definition
- **execution_graph**: Actual executed graph with resolved parameters
- **results**: Complete execution results including generated images
- **executed**: List of executed nodes
- **errors**: Any execution errors

## Extracting Results

### Generated Images
Look for nodes with `"type": "image_output"` in the session results:
```python
def extract_generated_image(job):
    session = job.get('session', {})
    results = session.get('results', {})
    
    for node_id, result in results.items():
        if result.get('type') == 'image_output':
            image_data = result.get('image', {})
            return image_data.get('image_name')
    return None
```

### Generation Metadata
Look for nodes with `"type": "metadata_output"`:
```python
def get_job_metadata(job):
    session = job.get('session', {})
    results = session.get('results', {})
    
    for node_id, result in results.items():
        if result.get('type') == 'metadata_output':
            return result.get('metadata', {})
    return {}
```

## Python Examples

### Get Latest Completed Job
```python
import requests

def get_latest_completed_job():
    url = "http://localhost:9090/api/v1/queue/default/list"
    params = {
        "status": "completed",
        "limit": 1000  # Get all jobs since they're sorted oldest first
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    result = response.json()
    items = result.get('items', [])
    
    # Jobs are sorted chronologically (oldest first), so take the LAST job for latest
    return items[-1] if items else None
```

### Monitor Queue in Real-time
```python
import time

def monitor_queue():
    while True:
        # Check current job
        current_response = requests.get("http://localhost:9090/api/v1/queue/default/current")
        current_job = current_response.json()
        
        if current_job:
            print(f"Currently processing job {current_job['item_id']}")
        else:
            print("No job currently processing")
        
        # Check queue status
        status_response = requests.get("http://localhost:9090/api/v1/queue/default/status")
        status = status_response.json()
        
        queue_info = status['queue']
        print(f"Queue status: {queue_info['pending']} pending, {queue_info['completed']} completed")
        
        time.sleep(5)  # Check every 5 seconds
```

### Download Job Results
```python
def download_job_image(job, download_dir="./downloads/"):
    # Extract image name from job results
    image_name = extract_generated_image(job)
    if not image_name:
        return False
    
    # Download the image
    image_url = f"http://localhost:9090/api/v1/images/i/{image_name}/full"
    response = requests.get(image_url)
    response.raise_for_status()
    
    # Save to file
    import os
    from pathlib import Path
    
    Path(download_dir).mkdir(parents=True, exist_ok=True)
    file_path = os.path.join(download_dir, image_name)
    
    with open(file_path, 'wb') as f:
        f.write(response.content)
    
    return file_path
```

## Job vs Session vs Image Relationship

1. **Job**: Queue entry representing a generation request
2. **Session**: Complete workflow execution with all node results
3. **Image**: Final output saved to InvokeAI's image database

The job contains the session, and the session results contain references to generated images.

## Best Practices

1. **Pagination**: Use cursor-based pagination for large job lists
2. **Status Filtering**: Always filter by status to get only the jobs you need
3. **Error Handling**: Check for failed jobs and extract error information
4. **Image Downloads**: Extract image names from job results, then download via image API
5. **Real-time Monitoring**: Poll the `/current` endpoint to track active jobs

## Queue Management Operations

The API also provides endpoints for:
- Canceling jobs: `POST /api/v1/queue/{queue_id}/i/{item_id}/cancel`
- Clearing queue: `DELETE /api/v1/queue/{queue_id}/clear`
- Pruning completed jobs: `DELETE /api/v1/queue/{queue_id}/prune`
- Pausing/resuming processor: `POST /api/v1/queue/{queue_id}/processor/pause|resume`

This comprehensive queue system allows for full monitoring and control of InvokeAI's image generation pipeline.
