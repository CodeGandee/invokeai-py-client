Active test scripts exercising workflow features. Guidelines:

1. Use new index-centric input APIs (`set_many`, `preview`, `list_inputs`) instead of direct field mutation or hard-coded node UUIDs.
2. Avoid committing temporary or ad-hoc debug scripts here (place experiments under `tmp/` or discard).
3. Legacy tests removed in this cleanup:
	- `test_flux_i2i_submission.py` (replaced by `test_flux_i2i_submission_new_api.py`).
	- Deprecated helper/demo scripts purged from `tests/deprecated/`.
4. Prefer dynamic discovery (labels, field names, node types) over static IDs for robustness.
5. Keep runtime reasonable (tune steps, resolutions) so full suite completes quickly.

Refer to history if older direct-mutation examples are needed.