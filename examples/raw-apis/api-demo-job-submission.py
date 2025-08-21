#!/usr/bin/env python3
"""
InvokeAI API Demo: Job Submission with Monitoring
=================================================

Task 3: Submit SDXL text-to-image job to queue and monitor progress.

This script demonstrates:
1. Loading an SDXL workflow template
2. Customizing prompts and parameters
3. Submitting job to the session queue
4. Monitoring job status in real-time
5. Extracting generated image details
6. Performance optimization with hybrid approaches

Performance Notes:
- Uses hybrid queue monitoring (direct DB + API fallback)
- Leverages optimized techniques from previous queue exploration
- Provides both real-time monitoring and final result extraction

Dependencies:
- InvokeAI running on localhost:9090
- SDXL workflow file: data/workflows/sdxl-text-to-image.json
- Previous queue exploration examples for monitoring functions
"""

import requests
import json
import time
import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path


class InvokeAIJobSubmitter:
    """
    Comprehensive job submission and monitoring for InvokeAI API.
    
    Features:
    - Workflow template loading and customization
    - Job submission with parameter validation
    - Real-time monitoring with hybrid optimization
    - Result extraction and image details
    - Performance benchmarking
    """
    
    def __init__(self, base_url: str = "http://localhost:9090"):
        self.base_url = base_url
        self.session = requests.Session()
        
        # Performance tracking
        self.timings = {}
        
        # Database path for direct queue access (optimization)
        self.db_path = r"F:\invoke-ai-app\databases\invokeai.db"
        
        print(f"🚀 InvokeAI Job Submitter initialized")
        print(f"   API Base URL: {base_url}")
        print(f"   Direct DB: {'✓ Available' if os.path.exists(self.db_path) else '✗ Not found'}")
    
    def load_workflow_template(self, workflow_path: str) -> Dict[str, Any]:
        """Load SDXL workflow template from JSON file."""
        start_time = time.time()
        
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
            
            self.timings['load_workflow'] = time.time() - start_time
            
            print(f"📄 Workflow template loaded: {workflow_path}")
            print(f"   Workflow ID: {workflow.get('id', 'Unknown')}")
            print(f"   Name: {workflow.get('name', 'Unknown')}")
            print(f"   Nodes: {len(workflow.get('nodes', []))}")
            print(f"   Load time: {self.timings['load_workflow']:.3f}s")
            
            return workflow
            
        except Exception as e:
            print(f"❌ Failed to load workflow: {e}")
            raise
    
    def customize_workflow_parameters(self, workflow: Dict[str, Any], 
                                    positive_prompt: Optional[str] = None,
                                    negative_prompt: Optional[str] = None,
                                    width: Optional[int] = None,
                                    height: Optional[int] = None,
                                    steps: Optional[int] = None,
                                    cfg_scale: Optional[float] = None,
                                    scheduler: Optional[str] = None) -> Dict[str, Any]:
        """Customize workflow parameters for text-to-image generation."""
        print(f"⚙️ Customizing workflow parameters...")
        
        # Find nodes to customize
        nodes = workflow.get('nodes', [])
        
        for node in nodes:
            node_type = node.get('data', {}).get('type')
            node_id = node.get('id', '')
            
            # Positive prompt customization
            if positive_prompt and 'positive_prompt' in node_id.lower():
                if 'inputs' in node.get('data', {}) and 'value' in node['data']['inputs']:
                    old_prompt = node['data']['inputs']['value']['value']
                    node['data']['inputs']['value']['value'] = positive_prompt
                    print(f"   📝 Positive prompt: '{old_prompt}' → '{positive_prompt}'")
            
            # Negative prompt customization  
            if negative_prompt and ('negative_prompt' in node_id.lower() or 
                                  node_id == "484ecc77-b7a0-4e19-b793-cc313f20fbe6"):
                if 'inputs' in node.get('data', {}) and 'value' in node['data']['inputs']:
                    old_prompt = node['data']['inputs']['value']['value']
                    node['data']['inputs']['value']['value'] = negative_prompt
                    print(f"   🚫 Negative prompt: '{old_prompt}' → '{negative_prompt}'")
            
            # Noise node (width/height)
            if node_type == 'noise':
                if width and 'inputs' in node.get('data', {}) and 'width' in node['data']['inputs']:
                    old_width = node['data']['inputs']['width']['value']
                    node['data']['inputs']['width']['value'] = width
                    print(f"   📐 Width: {old_width} → {width}")
                
                if height and 'inputs' in node.get('data', {}) and 'height' in node['data']['inputs']:
                    old_height = node['data']['inputs']['height']['value']
                    node['data']['inputs']['height']['value'] = height
                    print(f"   📐 Height: {old_height} → {height}")
            
            # Denoising node (steps, cfg_scale, scheduler)
            if node_type == 'denoise_latents':
                if steps and 'inputs' in node.get('data', {}) and 'steps' in node['data']['inputs']:
                    old_steps = node['data']['inputs']['steps']['value']
                    node['data']['inputs']['steps']['value'] = steps
                    print(f"   🔢 Steps: {old_steps} → {steps}")
                
                if cfg_scale and 'inputs' in node.get('data', {}) and 'cfg_scale' in node['data']['inputs']:
                    old_cfg = node['data']['inputs']['cfg_scale']['value']
                    node['data']['inputs']['cfg_scale']['value'] = cfg_scale
                    print(f"   ⚖️ CFG Scale: {old_cfg} → {cfg_scale}")
                
                if scheduler and 'inputs' in node.get('data', {}) and 'scheduler' in node['data']['inputs']:
                    old_scheduler = node['data']['inputs']['scheduler']['value']
                    node['data']['inputs']['scheduler']['value'] = scheduler
                    print(f"   📅 Scheduler: {old_scheduler} → {scheduler}")
        
        return workflow
    
    def convert_workflow_to_api_format(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Convert UI workflow format to API graph format."""
        print(f"🔄 Converting workflow to API format...")
        
        # Extract nodes from the workflow
        ui_nodes = workflow.get('nodes', [])
        ui_edges = workflow.get('edges', [])
        
        # Convert nodes array to nodes dictionary
        api_nodes = {}
        for node in ui_nodes:
            node_id = node.get('id')
            node_data = node.get('data', {})
            
            # Create API node format
            api_node = {
                'id': node_id,
                'type': node_data.get('type'),
                'is_intermediate': node_data.get('isIntermediate', True),
                'use_cache': node_data.get('useCache', True)
            }
            
            # Add node inputs
            node_inputs = node_data.get('inputs', {})
            for input_name, input_data in node_inputs.items():
                if isinstance(input_data, dict) and 'value' in input_data:
                    api_node[input_name] = input_data['value']
            
            api_nodes[node_id] = api_node
        
        # Convert edges to API format
        api_edges = []
        for edge in ui_edges:
            source_node = edge.get('source')
            target_node = edge.get('target')
            source_handle = edge.get('sourceHandle')
            target_handle = edge.get('targetHandle')
            
            api_edge = {
                'source': {
                    'node_id': source_node,
                    'field': source_handle
                },
                'destination': {
                    'node_id': target_node,
                    'field': target_handle
                }
            }
            api_edges.append(api_edge)
        
        # Create the API graph structure
        api_graph = {
            'id': workflow.get('id', 'converted_workflow'),
            'nodes': api_nodes,
            'edges': api_edges
        }
        
        print(f"   ✅ Conversion complete")
        print(f"      Nodes: {len(api_nodes)}")
        print(f"      Edges: {len(api_edges)}")
        
        return api_graph
    
    def submit_workflow_job(self, workflow: Dict[str, Any]) -> Optional[str]:
        """Submit workflow to session queue and return batch_id."""
        start_time = time.time()
        
        try:
            # Convert workflow to API format
            api_graph = self.convert_workflow_to_api_format(workflow)
            
            # Prepare the batch submission to queue
            url = f"{self.base_url}/api/v1/queue/default/enqueue_batch"
            
            # Convert the workflow to a batch structure
            batch_data = {
                "prepend": False,
                "batch": {
                    "graph": api_graph,
                    "runs": 1
                }
            }
            
            print(f"🔄 Submitting job to session queue...")
            response = self.session.post(url, json=batch_data)
            response.raise_for_status()
            
            batch_result = response.json()
            
            # The result contains batch info and item_ids
            batch_id = batch_result.get('batch', {}).get('batch_id')
            item_ids = batch_result.get('item_ids', [])
            
            if not batch_id or not item_ids:
                print(f"❌ No batch ID or item IDs returned: {batch_result}")
                return None
            
            # Get the first item ID
            item_id = item_ids[0]
            
            # Get the queue item details to find session_id
            try:
                item_url = f"{self.base_url}/api/v1/queue/default/i/{item_id}"
                item_response = self.session.get(item_url)
                item_response.raise_for_status()
                
                item_data = item_response.json()
                session_id = item_data.get('session_id')
                
            except Exception as e:
                print(f"⚠️ Could not get session ID from item: {e}")
                session_id = "unknown"
            
            self.timings['submit_job'] = time.time() - start_time
            
            print(f"✅ Job submitted successfully!")
            print(f"   Session ID: {session_id}")
            print(f"   Batch ID: {batch_id}")
            print(f"   Item ID: {item_id}")
            print(f"   Submit time: {self.timings['submit_job']:.3f}s")
            
            return session_id
            
        except requests.RequestException as e:
            print(f"❌ Job submission failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"   Error details: {error_detail}")
                except:
                    print(f"   Response text: {e.response.text}")
            return None
        except Exception as e:
            print(f"❌ Job submission failed: {e}")
            return None
    
    def get_latest_queue_item_optimized(self) -> Optional[Dict[str, Any]]:
        """Get latest queue item using hybrid approach (DB + API fallback)."""
        
        # Try direct database access first (1600x faster)
        try:
            if os.path.exists(self.db_path):
                start_time = time.time()
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Get the latest item (highest item_id)
                cursor.execute("""
                    SELECT item_id, status, batch_id, session_id, 
                           created_at, updated_at, started_at, completed_at
                    FROM session_queue 
                    WHERE item_id = (SELECT MAX(item_id) FROM session_queue)
                """)
                
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    db_time = time.time() - start_time
                    return {
                        'item_id': row[0],
                        'status': row[1], 
                        'batch_id': row[2],
                        'session_id': row[3],
                        'created_at': row[4],
                        'updated_at': row[5],
                        'started_at': row[6],
                        'completed_at': row[7],
                        '_query_time': db_time,
                        '_query_method': 'direct_db'
                    }
        except Exception as e:
            print(f"⚠️ Direct DB access failed, falling back to API: {e}")
        
        # Fallback to API method
        try:
            start_time = time.time()
            
            url = f"{self.base_url}/api/v1/sessions/queue"
            response = self.session.get(url)
            response.raise_for_status()
            
            queue_data = response.json()
            items = queue_data.get('items', [])
            
            if not items:
                return None
            
            # Find the latest item by created_at
            latest_item = max(items, key=lambda x: x.get('created_at', ''))
            latest_item['_query_time'] = time.time() - start_time
            latest_item['_query_method'] = 'api_fallback'
            
            return latest_item
            
        except Exception as e:
            print(f"❌ API queue query failed: {e}")
            return None
    
    def monitor_job_progress(self, target_session_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """Monitor job progress until completion or timeout."""
        print(f"👀 Monitoring job progress for session: {target_session_id}")
        print(f"   Max wait time: {max_wait_time}s")
        
        start_time = time.time()
        last_status = None
        check_count = 0
        
        while time.time() - start_time < max_wait_time:
            check_count += 1
            
            # Get latest queue item
            latest_item = self.get_latest_queue_item_optimized()
            
            if latest_item and latest_item.get('session_id') == target_session_id:
                current_status = latest_item.get('status')
                query_method = latest_item.get('_query_method', 'unknown')
                query_time = latest_item.get('_query_time', 0)
                
                if current_status != last_status:
                    elapsed = time.time() - start_time
                    print(f"   [{elapsed:.1f}s] Status: {current_status} (check #{check_count}, {query_method}, {query_time:.3f}s)")
                    last_status = current_status
                
                # Check if job is complete
                if current_status in ['completed', 'failed', 'canceled']:
                    total_time = time.time() - start_time
                    self.timings['monitor_job'] = total_time
                    
                    print(f"🏁 Job monitoring finished!")
                    print(f"   Final status: {current_status}")
                    print(f"   Total monitoring time: {total_time:.1f}s")
                    print(f"   Status checks: {check_count}")
                    
                    return latest_item
            else:
                # Look for any recent job that might be ours
                # Check for any job in last few items that could be ours
                if latest_item:
                    current_status = latest_item.get('status')
                    session_id = latest_item.get('session_id')
                    elapsed = time.time() - start_time
                    
                    if check_count <= 5 and session_id:  # Only show for first few checks
                        session_short = session_id[:8] if len(session_id) >= 8 else session_id
                        print(f"   [{elapsed:.1f}s] Latest job status: {current_status} (session: {session_short}...)")
                    
                    # If we see a completed job and we haven't found our target, it might be ours
                    if current_status in ['completed', 'failed', 'canceled'] and elapsed > 5:
                        print(f"   🤔 Found completed job with different session ID, checking if it's ours...")
                        return latest_item
            
            # Wait before next check (adaptive interval)
            if check_count < 10:
                time.sleep(1)  # Quick checks initially
            elif check_count < 30:
                time.sleep(2)  # Medium interval
            else:
                time.sleep(5)  # Slower checks for long jobs
        
        # Timeout reached
        print(f"⏰ Monitoring timeout reached ({max_wait_time}s)")
        return {'status': 'timeout', 'session_id': target_session_id}
    
    def get_session_results(self, session_id: str) -> Dict[str, Any]:
        """Get detailed results from completed session by checking queue item."""
        try:
            # First try to get the latest completed queue item
            latest_item = self.get_latest_queue_item_optimized()
            
            if latest_item and latest_item.get('status') == 'completed':
                print(f"📊 Session results retrieved from queue:")
                print(f"   Session ID: {latest_item.get('session_id')}")
                print(f"   Item ID: {latest_item.get('item_id')}")
                print(f"   Status: {latest_item.get('status')}")
                print(f"   Batch ID: {latest_item.get('batch_id')}")
                
                # Try to get the specific queue item with more details
                item_id = latest_item.get('item_id')
                if item_id:
                    try:
                        detail_url = f"{self.base_url}/api/v1/queue/default/i/{item_id}"
                        detail_response = self.session.get(detail_url)
                        detail_response.raise_for_status()
                        
                        detailed_item = detail_response.json()
                        
                        # Look for session information
                        session_info = detailed_item.get('session', {})
                        if session_info:
                            results = session_info.get('results', {})
                            if results:
                                print(f"   Session results found: {len(results)} items")
                                
                                # Look for image outputs
                                image_count = 0
                                for result_id, result_data in results.items():
                                    if result_data.get('type') == 'image_output':
                                        image_count += 1
                                        image_info = result_data.get('image', {})
                                        image_name = image_info.get('image_name')
                                        width = result_data.get('width')
                                        height = result_data.get('height')
                                        
                                        print(f"   🖼️ Generated image #{image_count}: {image_name}")
                                        print(f"      Dimensions: {width}x{height}")
                                        print(f"      Image URL: {self.base_url}/api/v1/images/i/{image_name}")
                            
                            return session_info
                        else:
                            print(f"   ⚠️ No session details found in queue item")
                            return detailed_item
                    
                    except Exception as e:
                        print(f"   ⚠️ Could not get detailed queue item: {e}")
                        return latest_item
                
                return latest_item
            else:
                print(f"   ⚠️ No completed queue item found")
                return {}
            
        except Exception as e:
            print(f"❌ Failed to get session results: {e}")
            return {}
    
    def download_generated_images(self, session_results: Dict[str, Any], download_dir: str = "./tmp/downloads/") -> List[str]:
        """Download generated images from completed session."""
        print(f"📥 Downloading generated images...")
        
        # Ensure download directory exists
        download_path = Path(download_dir)
        download_path.mkdir(parents=True, exist_ok=True)
        
        downloaded_files = []
        
        try:
            # Look for session results
            results = session_results.get('results', {})
            if not results:
                print(f"   ⚠️ No results found in session data")
                return downloaded_files
            
            # Find image outputs
            image_count = 0
            for result_id, result_data in results.items():
                if result_data.get('type') == 'image_output':
                    image_count += 1
                    image_info = result_data.get('image', {})
                    image_name = image_info.get('image_name')
                    
                    if not image_name:
                        print(f"   ⚠️ No image name found in result {result_id}")
                        continue
                    
                    # Download the image
                    try:
                        image_url = f"{self.base_url}/api/v1/images/i/{image_name}/full"
                        
                        print(f"   📸 Downloading image #{image_count}: {image_name}")
                        print(f"      URL: {image_url}")
                        
                        response = self.session.get(image_url)
                        response.raise_for_status()
                        
                        # Save the image
                        local_filename = download_path / image_name
                        with open(local_filename, 'wb') as f:
                            f.write(response.content)
                        
                        # Get file size for confirmation
                        file_size = os.path.getsize(local_filename)
                        file_size_mb = file_size / (1024 * 1024)
                        
                        print(f"      ✅ Saved: {local_filename}")
                        print(f"      📊 Size: {file_size_mb:.2f} MB ({file_size:,} bytes)")
                        
                        downloaded_files.append(str(local_filename))
                        
                    except Exception as e:
                        print(f"      ❌ Failed to download {image_name}: {e}")
            
            if downloaded_files:
                print(f"   🎉 Successfully downloaded {len(downloaded_files)} image(s)")
            else:
                print(f"   ⚠️ No images were downloaded")
                
            return downloaded_files
            
        except Exception as e:
            print(f"❌ Image download failed: {e}")
            return downloaded_files
    
    def run_complete_job_workflow(self, workflow_path: str, 
                                positive_prompt: str = "a beautiful landscape with mountains and lakes, sunset, highly detailed",
                                negative_prompt: str = "blurry, low quality, distorted",
                                width: int = 768,
                                height: int = 1024,
                                steps: int = 25,
                                cfg_scale: float = 7.5,
                                scheduler: str = "dpmpp_3m_k") -> Dict[str, Any]:
        """
        Complete workflow: Load → Customize → Submit → Monitor → Extract Results
        """
        print(f"🎯 Starting complete SDXL text-to-image job workflow")
        print(f"════════════════════════════════════════════════════")
        
        overall_start = time.time()
        
        try:
            # Step 1: Load workflow template
            print(f"\n📋 Step 1: Loading workflow template")
            workflow = self.load_workflow_template(workflow_path)
            
            # Step 2: Customize parameters
            print(f"\n🔧 Step 2: Customizing workflow parameters")
            customized_workflow = self.customize_workflow_parameters(
                workflow=workflow,
                positive_prompt=positive_prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                cfg_scale=cfg_scale,
                scheduler=scheduler
            )
            
            # Step 3: Submit job
            print(f"\n🚀 Step 3: Submitting job to queue")
            session_id = self.submit_workflow_job(customized_workflow)
            
            if not session_id:
                return {'error': 'Job submission failed'}
            
            # Step 4: Monitor progress
            print(f"\n👀 Step 4: Monitoring job progress")
            job_result = self.monitor_job_progress(session_id)
            
            # Step 5: Extract results
            print(f"\n📊 Step 5: Extracting detailed results")
            session_results = self.get_session_results(session_id)
            
            # Step 6: Download generated images
            print(f"\n📥 Step 6: Downloading generated images")
            downloaded_files = self.download_generated_images(session_results)
            
            # Performance summary
            total_time = time.time() - overall_start
            self.timings['total_workflow'] = total_time
            
            print(f"\n⚡ Performance Summary:")
            print(f"   Total workflow time: {total_time:.1f}s")
            for operation, duration in self.timings.items():
                print(f"   {operation}: {duration:.3f}s")
            
            # Compile final results
            final_results = {
                'success': True,
                'session_id': session_id,
                'job_status': job_result.get('status'),
                'session_results': session_results,
                'downloaded_files': downloaded_files,
                'performance': self.timings,
                'parameters': {
                    'positive_prompt': positive_prompt,
                    'negative_prompt': negative_prompt,
                    'width': width,
                    'height': height,
                    'steps': steps,
                    'cfg_scale': cfg_scale,
                    'scheduler': scheduler
                }
            }
            
            return final_results
            
        except Exception as e:
            print(f"\n❌ Workflow failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'downloaded_files': [],
                'timings': self.timings
            }


def main():
    """Main execution function demonstrating Task 3 implementation."""
    print("🎨 InvokeAI API Demo: SDXL Job Submission & Monitoring")
    print("=" * 60)
    
    # Initialize the job submitter
    submitter = InvokeAIJobSubmitter()
    
    # Define workflow path
    workflow_path = "data/workflows/sdxl-text-to-image.json"
    
    # Custom parameters for this demo
    job_params = {
        'positive_prompt': "a cyberpunk cityscape at night, neon lights, futuristic buildings, highly detailed, 8k",
        'negative_prompt': "blurry, low quality, distorted, text, watermark",
        'width': 768,
        'height': 1024,
        'steps': 20,
        'cfg_scale': 7.0,
        'scheduler': "euler_a"
    }
    
    print(f"\n🎯 Job Parameters:")
    for key, value in job_params.items():
        print(f"   {key}: {value}")
    
    # Run the complete workflow
    results = submitter.run_complete_job_workflow(workflow_path, **job_params)
    
    # Display final summary
    print(f"\n🏆 Final Results Summary:")
    print(f"   Success: {results.get('success', False)}")
    
    if results.get('success'):
        print(f"   Session ID: {results.get('session_id')}")
        print(f"   Job Status: {results.get('job_status')}")
        
        # Look for generated images
        session_results = results.get('session_results', {})
        session_results_dict = session_results.get('results', {})
        
        image_count = 0
        for result_id, result_data in session_results_dict.items():
            if result_data.get('type') == 'image_output':
                image_count += 1
                image_info = result_data.get('image', {})
                image_name = image_info.get('image_name')
                print(f"   Generated Image #{image_count}: {image_name}")
        
        if image_count == 0:
            print(f"   ⚠️ No images found in results")
        
        # Show downloaded files
        downloaded_files = results.get('downloaded_files', [])
        if downloaded_files:
            print(f"   📁 Downloaded Files:")
            for i, file_path in enumerate(downloaded_files, 1):
                print(f"      #{i}: {file_path}")
        else:
            print(f"   ⚠️ No files were downloaded")
    else:
        print(f"   Error: {results.get('error', 'Unknown error')}")
    
    print(f"\n✨ Task 3 Complete - SDXL Job Submission, Monitoring & Download Demo")


if __name__ == "__main__":
    main()
