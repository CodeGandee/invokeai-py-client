# Code Review: Image field unexpectedly typed as IvkStringField (builder coercion bug)

Context
- User observed at runtime that IDX_IMAGE resolves to invokeai_py_client.ivk_fields.primitives.IvkStringField in the FLUX image-to-image example, while it should be IvkImageField.
- The workflow JSON’s form element for the image input references the image node’s "image" field whose value shape is {"image_name": "..."}.

Expectation
- The field-plugin system should detect field_name == "image" and build an IvkImageField so callers can set image_name neatly.

What the system currently does
- Detection:
  - There is a first-class detection rule for the "image" name: [src/invokeai_py_client/workflow/field_plugins.py](src/invokeai_py_client/workflow/field_plugins.py:429-432).
  - If a field_info contains an explicit type key (e.g. type: "string"), it wins at priority 0: [src/invokeai_py_client/workflow/field_plugins.py](src/invokeai_py_client/workflow/field_plugins.py:419-425).

- Building:
  - The image builder is implemented here: [src/invokeai_py_client/workflow/field_plugins.py](src/invokeai_py_client/workflow/field_plugins.py:561-566).
    - It currently returns IvkImageField(value=value) verbatim.
    - When value is a dict like {"image_name": "..."} (as in typical workflow JSON), this attempts to stuff a dict into a field defined as value: Optional[str] (see [IvkImageField](src/invokeai_py_client/ivk_fields/resources.py:21-43)).
    - Pydantic validation rejects the dict for a str-typed field, causing a ValidationError in the builder.

- Fallback behavior on builder failure:
  - build_field() catches builder exceptions, and when not in strict mode (INVOKEAI_STRICT_FIELDS unset), returns None and falls back to an IvkStringField: [build_field()](src/invokeai_py_client/workflow/field_plugins.py:656-684), fallback at [src/invokeai_py_client/workflow/field_plugins.py](src/invokeai_py_client/workflow/field_plugins.py:689-702).
  - Result: The input field becomes IvkStringField in practice, exactly matching the observed runtime type.

Root cause
- _builder_image() does not extract "image_name" from dict values before constructing the field. It passes the dict directly to IvkImageField(value=...), violating the field’s value type (Optional[str]).
- The subsequent builder exception triggers the non-strict fallback to IvkStringField.

Reproduction (from provided workflow)
- The form element "node-field-QuO8FhTq6c" targets the image node’s "image" field and its value is a dict with "image_name":
  - data/workflows/flux-image-to-image.json: [form element](data/workflows/flux-image-to-image.json:119-127), [node value shape](data/workflows/flux-image-to-image.json:361-369).
- Detection: rule matches "image" → image type.
- Builder: returns IvkImageField(value={"image_name": "..."}) → ValidationError → fallback IvkStringField.

Impact
- All workflows where field_info.value for image is a dict {"image_name": "..."} will degrade to IvkStringField under default non-strict settings.
- Examples and typed assertions will be misleading, and ergonomics of image fields are reduced.

Proposed fix (minimal and safe)
- Extract image_name when builder receives a dict; otherwise pass through string or None. Example patch (for discussion):

  - File: [src/invokeai_py_client/workflow/field_plugins.py](src/invokeai_py_client/workflow/field_plugins.py:561)
  - Suggested replacement for _builder_image():

    ```python
    def _builder_image(value: Any, field_info: dict[str, Any]) -> IvkField[Any]:
        """Core image field builder with proper dict handling."""
        # Accept dict {"image_name": "..."} or a bare string, or None
        if isinstance(value, dict):
            image_name = value.get("image_name")
            return IvkImageField(value=image_name)
        if value is None or isinstance(value, str):
            return IvkImageField(value=value)
        # Last‑resort coercion: keep behavior predictable and explicit
        return IvkImageField(value=str(value) if value is not None else None)
    ```

- Rationale:
  - Aligns with IvkImageField.value: Optional[str].
  - Avoids Pydantic coercion errors and eliminates fallback to string.
  - Keeps detection/builder plugin architecture unchanged.
  - Maintains API graph normalization which already ensures {"image": {"image_name": "..."}}, see [WorkflowHandle._convert_to_api_format()](src/invokeai_py_client/workflow/workflow_handle.py:1484).

Example update in docs/examples (secondary)
- The FLUX example currently asserts the image field as IvkStringField and thus hides the underlying bug. It should assert IvkImageField:

  - Replace:
    - [examples/pipelines/flux-image-to-image.py](examples/pipelines/flux-image-to-image.py:315-319)
  - With:
    ```python
    field_image: IvkImageField = workflow_handle.get_input_value(IDX_IMAGE)
    assert isinstance(field_image, IvkImageField)
    field_image.value = uploaded_name
    ```

Diagnostics and hardening suggestions
- Enable strict mode in CI to surface builder failures early:
  - Set INVOKEAI_STRICT_FIELDS=1 when running unit tests. This will raise instead of silently falling back to IvkStringField, catching contract breaks in builders.
- Add debug logging for builder failures (already present under INVOKEAI_FIELD_DEBUG=1, see [FIELD_DEBUG usage](src/invokeai_py_client/workflow/field_plugins.py:362-374)).
- Unit tests to add:
  1) Builder unit tests
     - Given field_info.value={"image_name": "foo.png"}, _builder_image should return IvkImageField(value="foo.png").
     - Given field_info.value="foo.png", returns IvkImageField(value="foo.png").
     - Given field_info.value=None, returns IvkImageField(value=None).
  2) Integration test on discovery:
     - Using the provided flux-image-to-image.json, WorkflowHandle.list_inputs()[IDX_IMAGE].field is IvkImageField.
  3) Negative test under strict mode:
     - Temporarily revert builder to the current faulty form in test to assert that strict mode raises instead of falling back.

Why not coerce everything in WorkflowHandle?
- [WorkflowHandle._convert_to_api_format()](src/invokeai_py_client/workflow/workflow_handle.py:1484) already normalizes outgoing image strings to {"image_name": "..."} as a safety net; however, correcting the builder ensures typed ergonomics during discovery and avoids reliance on late normalization plus string fallbacks.

Non-goals
- Do not convert the field to store an IvkImage object. The submission contract is image_name; representing the input as a string-bearing IvkImageField is idiomatic and avoids discovery-time client/server coupling.

Conclusion
- The root bug is in _builder_image passing dicts directly to IvkImageField(value=...), causing validation failure and fallback to IvkStringField.
- Extract image_name within the builder to produce a valid IvkImageField. Harden with strict mode in tests and add coverage for both dict and string inputs.