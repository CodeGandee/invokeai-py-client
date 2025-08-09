#!/usr/bin/env python3
"""
InvokeAI Job Queue Hybrid Approach

This script combines the direct database hack with API fallback for maximum
performance and reliability. It tries the fast direct database approach first,
then falls back to the API if the database is unavailable.

Performance:
- Direct DB: ~0.002 seconds (1600x faster)
- API fallback: ~3 seconds (when DB unavailable)
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
import requests

# Configuration
INVOKEAI_URL = "http://localhost:9090"
DEFAULT_QUEUE_ID = "default"

# Database configuration - make this configurable
DEFAULT_DATABASE_PATHS = [
    r"F:\invoke-ai-app\databases\invokeai.db",
    r"C:\Users\{}\AppData\Local\InvokeAI\databases\invokeai.db".format(os.getenv('USERNAME', '')),
    r"~\invokeai\databases\invokeai.db",
    r".\invokeai.db"
]

def find_database_path() -> Optional[str]:
    """Find the InvokeAI database by checking common locations."""
    for path in DEFAULT_DATABASE_PATHS:
        expanded_path = os.path.expanduser(path)
        if os.path.exists(expanded_path):
            return expanded_path
    return None

def get_latest_completed_job_direct(db_path: str) -> Optional[Dict[str, Any]]:
    """Get the latest completed job by directly querying the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Ultra-fast query using MAX(item_id) with primary key index
        query = """
        SELECT *
        FROM session_queue
        WHERE status = 'completed'
        AND item_id = (
            SELECT MAX(item_id)
            FROM session_queue
            WHERE status = 'completed'
        )
        """
        
        cursor.execute(query)
        result = cursor.fetchone()
        
        if result is None:
            return None
        
        job_data = dict(result)
        
        # Parse session JSON for additional metadata
        if job_data.get('session'):
            try:
                session_data = json.loads(job_data['session'])
                job_data['parsed_session'] = session_data
            except json.JSONDecodeError:
                pass  # Session parsing is optional
        
        return job_data
        
    except (sqlite3.Error, OSError) as e:
        raise Exception(f"Database access failed: {e}")
    finally:
        if conn is not None:
            conn.close()

def get_latest_completed_job_api() -> Optional[Dict[str, Any]]:
    """Get the latest completed job using the API (fallback approach)."""
    try:
        url = f"{INVOKEAI_URL}/api/v1/queue/{DEFAULT_QUEUE_ID}/list_all"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        all_jobs = response.json()
        completed_jobs = [job for job in all_jobs if job.get('status') == 'completed']
        
        return completed_jobs[-1] if completed_jobs else None
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"API access failed: {e}")

def get_latest_completed_job_hybrid() -> tuple[Optional[Dict[str, Any]], str]:
    """
    Hybrid approach: try direct database first, fallback to API.
    
    Returns:
        tuple: (job_data, method_used)
        method_used: "direct_db", "api_fallback", or "failed"
    """
    # Try direct database approach first
    db_path = find_database_path()
    if db_path:
        try:
            job_data = get_latest_completed_job_direct(db_path)
            return job_data, "direct_db"
        except Exception as e:
            print(f"⚠️  Direct database failed: {e}")
    else:
        print("⚠️  Database not found at common locations")
    
    # Fallback to API approach
    try:
        job_data = get_latest_completed_job_api()
        return job_data, "api_fallback"
    except Exception as e:
        print(f"❌ API fallback failed: {e}")
        return None, "failed"

def extract_generated_image(job_data: Dict[str, Any]) -> Optional[str]:
    """Extract generated image name from job data (works with both DB and API formats)."""
    # Try parsed session first (direct DB format)
    session_data = job_data.get('parsed_session')
    if session_data:
        results = session_data.get('results', {})
        for node_id, result in results.items():
            if result.get('type') == 'image_output':
                image_data = result.get('image', {})
                return image_data.get('image_name')
    
    # Try API format (session as dict)
    session = job_data.get('session')
    if isinstance(session, dict):
        results = session.get('results', {})
        for node_id, result in results.items():
            if result.get('type') == 'image_output':
                image_data = result.get('image', {})
                return image_data.get('image_name')
    
    return None

def download_image(image_name: str, download_dir: str = "./tmp/downloads/") -> bool:
    """Download the generated image."""
    if not image_name:
        return False
    
    try:
        from pathlib import Path
        Path(download_dir).mkdir(parents=True, exist_ok=True)
        
        image_url = f"{INVOKEAI_URL}/api/v1/images/i/{image_name}/full"
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        file_path = os.path.join(download_dir, image_name)
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        file_size = os.path.getsize(file_path)
        print(f"📥 Downloaded: {file_path} ({file_size:,} bytes)")
        return True
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

def display_job_summary(job_data: Dict[str, Any], method_used: str):
    """Display job summary with method indicator."""
    method_icons = {
        "direct_db": "⚡",
        "api_fallback": "📡", 
        "failed": "❌"
    }
    
    print(f"\n{'='*60}")
    print(f"{method_icons.get(method_used, '?')} LATEST COMPLETED JOB ({method_used.upper()})")
    print(f"{'='*60}")
    
    print(f"Job ID: {job_data.get('item_id')}")
    print(f"Status: {job_data.get('status')}")
    
    # Handle timestamp formats (DB vs API)
    created_at = job_data.get('created_at')
    completed_at = job_data.get('completed_at')
    
    print(f"Created: {created_at}")
    print(f"Completed: {completed_at}")
    
    # Calculate duration if possible
    if created_at and completed_at:
        try:
            if method_used == "direct_db":
                # SQLite format
                created_time = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S.%f')
                completed_time = datetime.strptime(completed_at, '%Y-%m-%d %H:%M:%S.%f')
            else:
                # API format (ISO)
                created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                completed_time = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
            
            duration = completed_time - created_time
            print(f"⏱️  Duration: {duration.total_seconds():.2f} seconds")
        except (ValueError, AttributeError):
            pass  # Duration calculation is optional
    
    # Extract and display image
    image_name = extract_generated_image(job_data)
    if image_name:
        print(f"🖼️  Generated Image: {image_name}")
    
    return image_name

def performance_benchmark():
    """Benchmark both approaches to show performance difference."""
    import time
    
    print(f"\n{'='*60}")
    print("⚡ PERFORMANCE BENCHMARK")
    print(f"{'='*60}")
    
    # Test direct database
    db_path = find_database_path()
    if db_path:
        try:
            start_time = time.time()
            job_db = get_latest_completed_job_direct(db_path)
            db_time = time.time() - start_time
            
            if job_db:
                print(f"⚡ Direct DB: {db_time:.4f} seconds (Job ID: {job_db['item_id']})")
            else:
                print("❌ Direct DB: No jobs found")
                return
        except Exception as e:
            print(f"❌ Direct DB failed: {e}")
            return
    else:
        print("⚠️  Database not found for benchmark")
        return
    
    # Test API approach
    try:
        start_time = time.time()
        job_api = get_latest_completed_job_api()
        api_time = time.time() - start_time
        
        if job_api:
            print(f"📡 API: {api_time:.4f} seconds (Job ID: {job_api['item_id']})")
            
            # Compare results
            if job_db['item_id'] == job_api['item_id']:
                speedup = api_time / db_time
                print(f"✅ Results match! Direct DB is {speedup:.1f}x faster")
            else:
                print(f"⚠️  Different results: DB={job_db['item_id']}, API={job_api['item_id']}")
        else:
            print("❌ API: No jobs found")
            
    except Exception as e:
        print(f"❌ API benchmark failed: {e}")

def demo_hybrid_approach():
    """Main demo showing the hybrid approach."""
    print("🎯 InvokeAI Job Queue Hybrid Approach")
    print("=" * 50)
    print("⚡ Trying direct database first, API fallback if needed")
    
    # Get latest job using hybrid approach
    start_time = time.time()
    latest_job, method_used = get_latest_completed_job_hybrid()
    total_time = time.time() - start_time
    
    if latest_job is None:
        print("❌ No completed jobs found using any method")
        return
    
    print(f"\n✅ Retrieved latest job in {total_time:.4f} seconds using {method_used}")
    
    # Display job details
    image_name = display_job_summary(latest_job, method_used)
    
    # Download image if available
    if image_name:
        print(f"\n📥 Downloading generated image...")
        success = download_image(image_name)
        
        if success:
            print(f"\n🎉 Successfully retrieved and downloaded the latest finished job!")
        else:
            print(f"\n⚠️  Job retrieved but image download failed")
    
    # Show performance comparison
    if method_used == "direct_db":
        performance_benchmark()

if __name__ == "__main__":
    try:
        import time
        demo_hybrid_approach()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Make sure InvokeAI is running on localhost:9090")
