# InvokeAI API Endpoint List

This document provides a list of all available API endpoints for InvokeAI, along with their summaries and descriptions.

For detailed information about all endpoints (the openapi json), refer to `context\hints\invokeai-kb\invokeai-openapi-v6.8.json`.

## API Endpoints

*   **Endpoint:** `/api/v1/utilities/dynamicprompts`
    *   **Summary:** Parse Dynamicprompts
    *   **Description:** Creates a batch process
*   **Endpoint:** `/api/v2/models/`
    *   **Summary:** List Model Records
    *   **Description:** Get a list of models.
*   **Endpoint:** `/api/v2/models/get_by_attrs`
    *   **Summary:** Get Model Records By Attrs
    *   **Description:** Gets a model by its attributes. The main use of this route is to provide backwards compatibility with the old model manager, which identified models by a combination of name, base and type.
*   **Endpoint:** `/api/v2/models/i/{key}`
    *   **Summary:** Get Model Record
    *   **Description:** Get a model record
*   **Endpoint:** `/api/v2/models/scan_folder`
    *   **Summary:** Scan For Models
    *   **Description:** null
*   **Endpoint:** `/api/v2/models/hugging_face`
    *   **Summary:** Get Hugging Face Models
    *   **Description:** null
*   **Endpoint:** `/api/v2/models/i/{key}/image`
    *   **Summary:** Get Model Image
    *   **Description:** Gets an image file that previews the model
*   **Endpoint:** `/api/v2/models/install`
    *   **Summary:** Install Model
    *   **Description:** Install a model using a string identifier. `source` can be any of the following. 1. A path on the local filesystem ('C:\\users\\fred\\model.safetensors') 2. A Url pointing to a single downloadable model file 3. A HuggingFace repo_id with any of the following formats: - model/name - model/name:fp16:vae - model/name::vae -- use default precision - model/name:fp16:path/to/model.safetensors - model/name::path/to/model.safetensors `config` is a ModelRecordChanges object. Fields in this object will override the ones that are probed automatically. Pass an empty object to accept all the defaults. `access_token` is an optional access token for use with Urls that require authentication. Models will be downloaded, probed, configured and installed in a series of background threads. The return object has `status` attribute that can be used to monitor progress. See the documentation for `import_model_record` for more information on interpreting the job information returned by this route.
*   **Endpoint:** `/api/v2/models/install/huggingface`
    *   **Summary:** Install Hugging Face Model
    *   **Description:** Install a Hugging Face model using a string identifier.
*   **Endpoint:** `/api/v2/models/install/{id}`
    *   **Summary:** Get Model Install Job
    *   **Description:** Return model install job corresponding to the given source. See the documentation for 'List Model Install Jobs' for information on the format of the return value.
*   **Endpoint:** `/api/v2/models/convert/{key}`
    *   **Summary:** Convert Model
    *   **Description:** Permanently convert a model into diffusers format, replacing the safetensors version. Note that during the conversion process the key and model hash will change. The return value is the model configuration for the converted model.
*   **Endpoint:** `/api/v2/models/starter_models`
    *   **Summary:** Get Starter Models
    *   **Description:** null
*   **Endpoint:** `/api/v2/models/stats`
    *   **Summary:** Get model manager RAM cache performance statistics.
    *   **Description:** Return performance statistics on the model manager's RAM cache. Will return null if no models have been loaded.
*   **Endpoint:** `/api/v2/models/empty_model_cache`
    *   **Summary:** Empty Model Cache
    *   **Description:** Drop all models from the model cache to free RAM/VRAM. 'Locked' models that are in active use will not be dropped.
*   **Endpoint:** `/api/v2/models/hf_login`
    *   **Summary:** Get Hf Login Status
    *   **Description:** null
*   **Endpoint:** `/api/v1/download_queue/`
    *   **Summary:** List Downloads
    *   **Description:** Get a list of active and inactive jobs.
*   **Endpoint:** `/api/v1/download_queue/i/`
    *   **Summary:** Download
    *   **Description:** Download the source URL to the file or directory indicted in dest.
*   **Endpoint:** `/api/v1/download_queue/i/{id}`
    *   **Summary:** Get Download Job
    *   **Description:** Get a download job using its ID.
*   **Endpoint:** `/api/v1/download_queue/i`
    *   **Summary:** Cancel All Download Jobs
    *   **Description:** Cancel all download jobs.
*   **Endpoint:** `/api/v1/images/upload`
    *   **Summary:** Upload Image
    *   **Description:** Uploads an image
*   **Endpoint:** `/api/v1/images/`
    *   **Summary:** Create Image Upload Entry
    *   **Description:** Uploads an image from a URL, not implemented
*   **Endpoint:** `/api/v1/images/i/{image_name}`
    *   **Summary:** Delete Image
    *   **Description:** Deletes an image
*   **Endpoint:** `/api/v1/images/intermediates`
    *   **Summary:** Get Intermediates Count
    *   **Description:** Gets the count of intermediate images
*   **Endpoint:** `/api/v1/images/i/{image_name}/metadata`
    *   **Summary:** Get Image Metadata
    *   **Description:** Gets an image's metadata
*   **Endpoint:** `/api/v1/images/i/{image_name}/workflow`
    *   **Summary:** Get Image Workflow
    *   **Description:** null
*   **Endpoint:** `/api/v1/images/i/{image_name}/full`
    *   **Summary:** Get Image Full
    *   **Description:** Gets a full-resolution image file
*   **Endpoint:** `/api/v1/images/i/{image_name}/thumbnail`
    *   **Summary:** Get Image Thumbnail
    *   **Description:** Gets a thumbnail image file
*   **Endpoint:** `/api/v1/images/i/{image_name}/urls`
    *   **Summary:** Get Image Urls
    *   **Description:** Gets an image and thumbnail URL
*   **Endpoint:** `/api/v1/images/delete`
    *   **Summary:** Delete Images From List
    *   **Description:** null
*   **Endpoint:** `/api/v1/images/uncategorized`
    *   **Summary:** Delete Uncategorized Images
    *   **Description:** Deletes all images that are uncategorized
*   **Endpoint:** `/api/v1/images/star`
    *   **Summary:** Star Images In List
    *   **Description:** null
*   **Endpoint:** `/api/v1/images/unstar`
    *   **Summary:** Unstar Images In List
    *   **Description:** null
*   **Endpoint:** `/api/v1/images/download`
    *   **Summary:** Download Images From List
    *   **Description:** null
*   **Endpoint:** `/api/v1/images/download/{bulk_download_item_name}`
    *   **Summary:** Get Bulk Download Item
    *   **Description:** Gets a bulk download zip file
*   **Endpoint:** `/api/v1/images/names`
    *   **Summary:** Get Image Names
    *   **Description:** Gets ordered list of image names with metadata for optimistic updates
*   **Endpoint:** `/api/v1/images/images_by_names`
    *   **Summary:** Get Images By Names
    *   **Description:** Gets image DTOs for the specified image names. Maintains order of input names.
*   **Endpoint:** `/api/v1/videos/`
    *   **Summary:** List Video Dtos
    *   **Description:** Lists video DTOs
*   **Endpoint:** `/api/v1/videos/ids`
    *   **Summary:** Get Video Ids
    *   **Description:** Gets ordered list of video ids with metadata for optimistic updates
*   **Endpoint:** `/api/v1/videos/videos_by_ids`
    *   **Summary:** Get Videos By Ids
    *   **Description:** Gets video DTOs for the specified video ids. Maintains order of input ids.
*   **Endpoint:** `/api/v1/videos/i/{video_id}`
    *   **Summary:** Get Video Dto
    *   **Description:** Gets a video's DTO
*   **Endpoint:** `/api/v1/videos/i/{video_id}`
    *   **Summary:** Update Video
    *   **Description:** Updates a video
*   **Endpoint:** `/api/v1/videos/delete`
    *   **Summary:** Delete Videos From List
    *   **Description:** 
*   **Endpoint:** `/api/v1/videos/star`
    *   **Summary:** Star Videos In List
    *   **Description:** 
*   **Endpoint:** `/api/v1/videos/unstar`
    *   **Summary:** Unstar Videos In List
    *   **Description:** 
*   **Endpoint:** `/api/v1/videos/uncategorized`
    *   **Summary:** Delete Uncategorized Videos
    *   **Description:** Deletes all videos that are uncategorized
*   **Endpoint:** `/api/v1/boards/`
    *   **Summary:** Create Board
    *   **Description:** Creates a board
*   **Endpoint:** `/api/v1/boards/{board_id}`
    *   **Summary:** Get Board
    *   **Description:** Gets a board
*   **Endpoint:** `/api/v1/boards/{board_id}/image_names`
    *   **Summary:** List All Board Image Names
    *   **Description:** Gets a list of images for a board
*   **Endpoint:** `/api/v1/board_images/`
    *   **Summary:** Add Image To Board
    *   **Description:** Creates a board_image
*   **Endpoint:** `/api/v1/board_images/batch`
    *   **Summary:** Add Images To Board
    *   **Description:** Adds a list of images to a board
*   **Endpoint:** `/api/v1/board_images/batch/delete`
    *   **Summary:** Remove Images From Board
    *   **Description:** Removes a list of images from their board, if they had one
*   **Endpoint:** `/api/v1/board_videos/batch`
    *   **Summary:** Add Videos To Board
    *   **Description:** Adds a list of videos to a board
*   **Endpoint:** `/api/v1/board_videos/batch/delete`
    *   **Summary:** Remove Videos From Board
    *   **Description:** Removes a list of videos from their board, if they had one
*   **Endpoint:** `/api/v1/model_relationships/i/{model_key}`
    *   **Summary:** Get Related Models
    *   **Description:** Get a list of model keys related to a given model.
*   **Endpoint:** `/api/v1/model_relationships/`
    *   **Summary:** Add Model Relationship
    *   **Description:** Creates a **bidirectional** relationship between two models, allowing each to reference the other as related.
*   **Endpoint:** `/api/v1/model_relationships/batch`
    *   **Summary:** Get Related Model Keys (Batch)
    *   **Description:** Retrieves all **unique related model keys** for a list of given models. This is useful for contextual suggestions or filtering.
*   **Endpoint:** `/api/v1/app/version`
    *   **Summary:** Get Version
    *   **Description:** null
*   **Endpoint:** `/api/v1/app/app_deps`
    *   **Summary:** Get App Deps
    *   **Description:** null
*   **Endpoint:** `/api/v1/app/config`
    *   **Summary:** Get Config 
    *   **Description:** null
*   **Endpoint:** `/api/v1/app/runtime_config`
    *   **Summary:** Get Runtime Config
    *   **Description:** null
*   **Endpoint:** `/api/v1/app/logging`
    *   **Summary:** Get Log Level
    *   **Description:** Returns the log level
*   **Endpoint:** `/api/v1/app/invocation_cache`
    *   **Summary:** Clear Invocation Cache
    *   **Description:** Clears the invocation cache
*   **Endpoint:** `/api/v1/app/invocation_cache/enable`
    *   **Summary:** Enable Invocation Cache
    *   **Description:** Clears the invocation cache
*   **Endpoint:** `/api/v1/app/invocation_cache/disable`
    *   **Summary:** Disable Invocation Cache
    *   **Description:** Clears the invocation cache
*   **Endpoint:** `/api/v1/app/invocation_cache/status`
    *   **Summary:** Get Invocation Cache Status
    *   **Description:** Clears the invocation cache
*   **Endpoint:** `/api/v1/queue/{queue_id}/enqueue_batch`
    *   **Summary:** Enqueue Batch
    *   **Description:** Processes a batch and enqueues the output graphs for execution.
*   **Endpoint:** `/api/v1/queue/{queue_id}/item_ids`
    *   **Summary:** Get Queue Item Ids
    *   **Description:** Gets all queue item ids that match the given parameters
*   **Endpoint:** `/api/v1/queue/{queue_id}/items_by_ids`
    *   **Summary:** Get Queue Items By Item Ids
    *   **Description:** Gets queue items for the specified queue item ids. Maintains order of item ids.
*   **Endpoint:** `/api/v1/queue/{queue_id}/list_all`
    *   **Summary:** List All Queue Items
    *   **Description:** Gets all queue items
*   **Endpoint:** `/api/v1/queue/{queue_id}/processor/resume`
    *   **Summary:** Resume
    *   **Description:** Resumes session processor
*   **Endpoint:** `/api/v1/queue/{queue_id}/processor/pause`
    *   **Summary:** Pause
    *   **Description:** Pauses session processor
*   **Endpoint:** `/api/v1/queue/{queue_id}/cancel_all_except_current`
    *   **Summary:** Cancel All Except Current
    *   **Description:** Immediately cancels all queue items except in-processing items
*   **Endpoint:** `/api/v1/queue/{queue_id}/delete_all_except_current`
    *   **Summary:** Delete All Except Current
    *   **Description:** Immediately deletes all queue items except in-processing items
*   **Endpoint:** `/api/v1/queue/{queue_id}/cancel_by_batch_ids`
    *   **Summary:** Cancel By Batch Ids
    *   **Description:** Immediately cancels all queue items from the given batch ids
*   **Endpoint:** `/api/v1/queue/{queue_id}/cancel_by_destination`
    *   **Summary:** Cancel By Destination
    *   **Description:** Immediately cancels all queue items with the given origin
*   **Endpoint:** `/api/v1/queue/{queue_id}/retry_items_by_id`
    *   **Summary:** Retry Items By Id
    *   **Description:** Immediately cancels all queue items with the given origin
*   **Endpoint:** `/api/v1/queue/{queue_id}/clear`
    *   **Summary:** Clear
    *   **Description:** Clears the queue entirely, immediately canceling the currently-executing session
*   **Endpoint:** `/api/v1/queue/{queue_id}/prune`
    *   **Summary:** Prune
    *   **Description:** Prunes all completed or errored queue items
*   **Endpoint:** `/api/v1/queue/{queue_id}/current`
    *   **Summary:** Get Current Queue Item
    *   **Description:** Gets the currently execution queue item
*   **Endpoint:** `/api/v1/queue/{queue_id}/next`
    *   **Summary:** Get Next Queue Item
    *   **Description:** Gets the next queue item, without executing it
*   **Endpoint:** `/api/v1/queue/{queue_id}/status`
    *   **Summary:** Get Queue Status
    *   **Description:** Gets the status of the session queue
*   **Endpoint:** `/api/v1/queue/{queue_id}/b/{batch_id}/status`
    *   **Summary:** Get Batch Status
    *   **Description:** Gets the status of the session queue
*   **Endpoint:** `/api/v1/queue/{queue_id}/i/{item_id}`
    *   **Summary:** Get Queue Item
    *   **Description:** Gets a queue item
*   **Endpoint:** `/api/v1/queue/{queue_id}/i/{item_id}/cancel`
    *   **Summary:** Cancel Queue Item
    *   **Description:** Deletes a queue item
*   **Endpoint:** `/api/v1/queue/{queue_id}/counts_by_destination`
    *   **Summary:** Counts By Destination
    *   **Description:** Gets the counts of queue items by destination
*   **Endpoint:** `/api/v1/queue/{queue_id}/d/{destination}`
    *   **Summary:** Delete By Destination
    *   **Description:** Deletes all items with the given destination
*   **Endpoint:** `/api/v1/workflows/i/{workflow_id}`
    *   **Summary:** Get Workflow
    *   **Description:** Gets a workflow
*   **Endpoint:** `/api/v1/workflows/`
    *   **Summary:** Create Workflow
    *   **Description:** Creates a workflow
*   **Endpoint:** `/api/v1/workflows/i/{workflow_id}/thumbnail`
    *   **Summary:** Set Workflow Thumbnail
    *   **Description:** Sets a workflow's thumbnail image
*   **Endpoint:** `/api/v1/workflows/counts_by_tag`
    *   **Summary:** Get Counts By Tag
    *   **Description:** Counts workflows by tag
*   **Endpoint:** `/api/v1/workflows/counts_by_category`
    *   **Summary:** Counts By Category
    *   **Description:** Counts workflows by category
*   **Endpoint:** `/api/v1/workflows/i/{workflow_id}/opened_at`
    *   **Summary:** Update Opened At
    *   **Description:** Updates the opened_at field of a workflow
*   **Endpoint:** `/api/v1/style_presets/i/{style_preset_id}`
    *   **Summary:** Get Style Preset
    *   **Description:** Gets a style preset
*   **Endpoint:** `/api/v1/style_presets/`
    *   **Summary:** List Style Presets
    *   **Description:** Gets a page of style presets
*   **Endpoint:** `/api/v1/style_presets/i/{style_preset_id}/image`
    *   **Summary:** Get Style Preset Image
    *   **Description:** Gets an image file that previews the model
*   **Endpoint:** `/api/v1/style_presets/export`
    *   **Summary:** Export Style Presets
    *   **Description:** null
*   **Endpoint:** `/api/v1/style_presets/import`
    *   **Summary:** Import Style Presets
    *   **Description:** null
*   **Endpoint:** `/api/v1/client_state/{queue_id}/get_by_key`
    *   **Summary:** Get Client State By Key
    *   **Description:** Gets the client state
*   **Endpoint:** `/api/v1/client_state/{queue_id}/set_by_key`
    *   **Summary:** Set Client State
    *   **Description:** Sets the client state
*   **Endpoint:** `/api/v1/client_state/{queue_id}/delete`
    *   **Summary:** Delete Client State
    *   **Description:** Deletes the client state
