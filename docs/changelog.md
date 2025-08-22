# Changelog

All notable changes to the InvokeAI Python Client will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive MkDocs Material documentation
- Support for Flux workflows
- Enhanced field type system with Pydantic validation
- Async execution modes
- Progress tracking callbacks

### Changed
- Improved error messages for better debugging
- Optimized output mapping performance
- Updated dependencies to latest versions

### Fixed
- Board handling for uncategorized images
- Model synchronization edge cases
- Index calculation for nested containers

## [0.1.0] - 2024-01-15

### Added
- Initial release of InvokeAI Python Client
- Core workflow execution functionality
- Support for SDXL workflows
- Board and image management
- Model synchronization
- Type-safe field system
- Index-based input access
- Output-to-image mapping
- Synchronous execution mode
- Board upload/download operations
- Comprehensive examples for common use cases

### Documentation
- README with quick start guide
- API documentation
- Example workflows for SDXL
- Developer summaries

## Development Roadmap

### Planned Features
- [ ] GUI workflow validation tool
- [ ] Workflow caching for improved performance
- [ ] Extended model management capabilities
- [ ] Workflow templates library
- [ ] CLI tool for common operations
- [ ] Integration with popular ML frameworks
- [ ] Workflow visualization tools
- [ ] Performance profiling utilities

### Known Issues
- Large batch operations may require memory optimization
- Some edge cases in complex nested workflows
- WebSocket reconnection needs improvement

## Version History

| Version | Release Date | Python Support | InvokeAI Support |
|---------|-------------|----------------|------------------|
| 0.1.0   | 2024-01-15  | 3.9+          | 4.0+            |

## Upgrade Guide

### From Raw API to Client

If you're migrating from raw API calls:

1. Replace REST calls with client methods:
   ```python
   # Before
   response = requests.post(f"{url}/api/v1/queue/enqueue_batch", json=data)
   
   # After
   result = wf.submit_sync()
   ```

2. Use typed fields instead of raw JSON:
   ```python
   # Before
   workflow_json["nodes"]["prompt"]["value"] = "New prompt"
   
   # After
   wf.get_input_value(0).value = "New prompt"
   ```

3. Leverage automatic output mapping:
   ```python
   # Before
   # Manual parsing of session results
   
   # After
   mappings = wf.map_outputs_to_images(result)
   ```

## Support

For questions or issues:
- [GitHub Issues](https://github.com/CodeGandee/invokeai-py-client/issues)
- [GitHub Discussions](https://github.com/CodeGandee/invokeai-py-client/discussions)