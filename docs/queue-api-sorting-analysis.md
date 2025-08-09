# InvokeAI Queue API Sorting Analysis

## Investigation Summary

This document summarizes our deep dive into the InvokeAI source code to determine if there are hidden ways to sort job queue records or get the latest finished job efficiently.

## Key Findings

### 1. **No Hidden Sorting Parameters**

After examining the source code in:
- `invokeai/app/api/routers/session_queue.py` (API router)
- `invokeai/app/services/session_queue/session_queue_sqlite.py` (SQLite implementation)
- `invokeai/app/services/session_queue/session_queue_base.py` (Abstract base class)

**The queue API does NOT provide any sorting parameters.** The API endpoints are:

#### `/api/v1/queue/{queue_id}/list`
Parameters: `limit`, `status`, `cursor`, `priority`, `destination`

#### `/api/v1/queue/{queue_id}/list_all`  
Parameters: `destination`

**No `order`, `sort`, `order_by`, or `order_dir` parameters exist.**

### 2. **Fixed Sorting Logic**

Both endpoints use the same hardcoded SQL ORDER BY clause:

```sql
ORDER BY
    priority DESC,
    item_id ASC
```

This means:
1. **Higher priority jobs come first** (priority DESC)
2. **Within same priority, older jobs come first** (item_id ASC)
3. **Since most jobs have priority=0, they're sorted chronologically oldest-first**

### 3. **No "Latest Job" Endpoint**

There are no specialized endpoints for getting:
- Latest completed job
- Most recent job
- Maximum item_id
- Reverse chronological order

### 4. **Cursor Pagination Limitations**

The cursor pagination only supports forward navigation:
- Has `next_cursor` but no `previous_cursor`
- Cannot start from the end and paginate backwards
- Cursor is based on `(priority, item_id)` and only moves forward

## Available Approaches to Get Latest Job

### Option 1: `list_all` Endpoint (Recommended)
```python
# Most efficient for current API - single call
response = requests.get(f"{BASE_URL}/api/v1/queue/default/list_all")
all_jobs = response.json()
completed_jobs = [job for job in all_jobs if job.get('status') == 'completed']
latest_job = completed_jobs[-1] if completed_jobs else None
```

**Pros:**
- Single API call
- Gets all jobs at once
- Simpler logic

**Cons:**
- Loads all jobs (currently ~165 total)
- Client-side filtering needed
- Memory usage scales with queue size

### Option 2: `list` with High Limit
```python
# Alternative approach using status filtering
response = requests.get(f"{BASE_URL}/api/v1/queue/default/list", 
                       params={"status": "completed", "limit": 1000})
items = response.json().get('items', [])
latest_job = items[-1] if items else None
```

**Pros:**
- Server-side status filtering
- Limit parameter prevents excessive data

**Cons:**
- Still needs high limit to get all completed jobs
- Risk of missing latest if more jobs than limit

### Option 3: Pagination from End (Complex)
```python
# Theoretical approach - would require multiple API calls
# Not practical given the forward-only cursor navigation
```

**Cons:**
- Would require many API calls
- Complex logic to determine total count
- No reverse pagination support

## Performance Analysis

### Current Queue Size: 165 total jobs (163 completed)
- **Option 1 (list_all)**: ~1 API call, ~165 jobs loaded
- **Option 2 (list with limit=1000)**: ~1 API call, ~163 jobs loaded
- **Option 3 (pagination)**: ~4 API calls minimum

### Scaling Considerations
- With 1000+ jobs: list_all becomes less efficient
- Pagination approach would become more attractive at scale
- But API doesn't support reverse pagination

## Recommendations

### For Current Use (< 1000 jobs)
**Use `list_all` endpoint** as demonstrated in our updated code:

```python
def get_latest_completed_job():
    response = requests.get(f"{BASE_URL}/api/v1/queue/default/list_all")
    all_jobs = response.json()
    completed_jobs = [job for job in all_jobs if job.get('status') == 'completed']
    return completed_jobs[-1] if completed_jobs else None
```

### For Future Improvements
This analysis reveals a clear feature gap in the InvokeAI API. Potential improvements:

1. **Add sorting parameters** to queue endpoints:
   - `order_by` (created_at, updated_at, item_id)
   - `order_dir` (asc, desc)

2. **Add "latest job" endpoint**:
   - `GET /api/v1/queue/{queue_id}/latest?status=completed`

3. **Add reverse cursor pagination**:
   - Support starting from the end
   - `previous_cursor` support

## Implementation Notes

The current implementation is hardcoded in `SqliteSessionQueue.list_queue_items()` and `SqliteSessionQueue.list_all_queue_items()` methods. Adding sorting would require:

1. Modifying the abstract base class method signatures
2. Updating the SQLite implementation
3. Adding parameters to the API router
4. Updating the OpenAPI specification

## Conclusion

**There are no hidden sorting parameters in the InvokeAI queue API.** The sorting is hardcoded and cannot be changed through API parameters. To get the latest finished job efficiently, use the `list_all` endpoint and take the last completed job from the chronologically-sorted list.
