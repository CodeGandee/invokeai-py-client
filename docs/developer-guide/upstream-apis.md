# Upstream APIs

InvokeAI server API reference.

## API Endpoints

### Images
- `GET /api/v1/images/` - List images
- `POST /api/v1/images/upload` - Upload image
- `GET /api/v1/images/i/{name}` - Get image
- `DELETE /api/v1/images/i/{name}` - Delete image

### Boards
- `GET /api/v1/boards/` - List boards
- `POST /api/v1/boards/` - Create board
- `GET /api/v1/boards/{id}` - Get board
- `DELETE /api/v1/boards/{id}` - Delete board

### Models
- `GET /api/v1/models/` - List models
- `GET /api/v1/models/i/{key}` - Get model info
- `POST /api/v1/models/load` - Load model

### Queue
- `POST /api/v1/queue/default/enqueue_batch` - Submit batch
- `GET /api/v1/queue/default/status` - Queue status
- `GET /api/v1/queue/default/session/{id}` - Session status

## WebSocket Events

```javascript
// Connection
ws://localhost:9090/ws

// Events
{
  "event": "invocation_started",
  "data": {...}
}

{
  "event": "invocation_complete",
  "data": {...}
}

{
  "event": "session_complete",
  "data": {...}
}
```

## OpenAPI Specification

Full API spec available at:
- Development: `http://localhost:9090/openapi.json`
- Reference: `context/hints/invokeai-kb/invokeai-openapi.json`

## Rate Limiting

- Default: 100 requests/minute
- Batch operations: 10 requests/minute
- WebSocket: 1 connection per client

See [API Reference](../api-reference/index.md) for client-side APIs.
