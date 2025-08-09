# InvokeAI Direct Database Hack - Performance Analysis

## Summary

Our "hack" approach of directly querying the InvokeAI SQLite database provides **incredible performance improvements** over the official API.

## Performance Results

| Method | Time | Performance | Notes |
|--------|------|-------------|-------|
| **Direct DB Query** | **0.0019 seconds** | **1643.9x faster** | Uses `MAX(item_id)` SQL query |
| API `list_all` | 3.0719 seconds | Baseline | Loads all 165 jobs, client-side filtering |
| API `list` (limit=1000) | ~3+ seconds | Similar to list_all | Still needs to load many jobs |

## Technical Details

### Direct Database Approach
```sql
SELECT *
FROM session_queue
WHERE status = 'completed'
AND item_id = (
    SELECT MAX(item_id)
    FROM session_queue
    WHERE status = 'completed'
)
```

**Why it's so fast:**
1. **MAX(item_id)** is extremely efficient - uses the primary key index
2. **Single record return** - no need to load all jobs
3. **No JSON serialization/deserialization** overhead
4. **No HTTP network calls**
5. **Direct SQLite access** - minimal overhead

### API Approach
```python
# Must load all jobs to find the latest
response = requests.get("/api/v1/queue/default/list_all")
all_jobs = response.json()  # ~165 jobs
completed_jobs = [job for job in all_jobs if job.get('status') == 'completed']
latest_job = completed_jobs[-1]  # Get last one
```

**Why it's slow:**
1. **HTTP round trip** - network latency
2. **JSON serialization** - server converts all 165 jobs to JSON
3. **JSON deserialization** - client parses large JSON response
4. **Client-side filtering** - filter 165 jobs to 163 completed
5. **Memory overhead** - load all jobs into memory

## Database Schema

From InvokeAI's `migration_1.py`, the `session_queue` table structure:

```sql
CREATE TABLE session_queue (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Key for our MAX() query
    batch_id TEXT NOT NULL,
    queue_id TEXT NOT NULL,
    session_id TEXT NOT NULL UNIQUE,
    field_values TEXT,
    session TEXT NOT NULL,                       -- JSON session data
    status TEXT NOT NULL DEFAULT 'pending',     -- 'completed', 'pending', etc.
    priority INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    started_at DATETIME,
    completed_at DATETIME
);
```

## Security & Risks

### Risks of Direct Database Access
1. **Schema Changes**: InvokeAI updates could change the database schema
2. **Database Locking**: Concurrent access might cause locks
3. **Data Integrity**: Direct writes could corrupt data (we only read)
4. **Support**: Not officially supported by InvokeAI
5. **Path Dependencies**: Database location might change

### Mitigation Strategies
1. **Read-only Access**: Only SELECT queries, never INSERT/UPDATE/DELETE
2. **Error Handling**: Graceful fallback to API on database errors
3. **Schema Validation**: Check table structure before queries
4. **Configuration**: Make database path configurable

## Recommendations

### For Development/Testing
✅ **Use the direct database hack** for maximum performance

### For Production
⚠️ **Consider hybrid approach:**
1. Try direct database access first
2. Fall back to API if database unavailable
3. Add monitoring for schema changes

### Feature Request for InvokeAI
Based on this analysis, InvokeAI could easily add a `/api/v1/queue/{queue_id}/latest?status=completed` endpoint that uses similar SQL for 1000x+ performance improvement.

## Code Example

```python
def get_latest_job_hybrid():
    """Hybrid approach: try direct DB, fallback to API"""
    try:
        # Try direct database first (1600x faster)
        return get_latest_completed_job_direct()
    except Exception as e:
        print(f"Database access failed, falling back to API: {e}")
        # Fall back to API approach
        return get_latest_completed_job_api()
```

## Conclusion

The direct database hack provides **extraordinary performance benefits** with minimal risk when used properly (read-only access). This demonstrates a significant opportunity for InvokeAI to optimize their queue API endpoints.
