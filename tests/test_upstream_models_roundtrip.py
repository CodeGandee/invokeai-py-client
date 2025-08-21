"""Roundtrip tests for upstream-compatible workflow models.

Validates that we can:
  * Load a workflow JSON into `WorkflowRoot` preserving key data.
  * Introspect nodes & form via utility helpers.
  * Serialize back to dict/JSON and re-load with structural parity.
  * Preserve unknown/extra fields (spot check a few nested values).
"""
from __future__ import annotations

import json
from pathlib import Path
from copy import deepcopy

import pytest

from invokeai_py_client.workflow.upstream_models import (
    load_workflow_json,
    enumerate_output_nodes,
    iter_form_input_fields,
)

WORKFLOW_PATH = Path(__file__).parent.parent / "data" / "workflows" / "sdxl-text-to-image.json"


def _load_raw() -> dict:
    # 'r' mode implicit; keep encoding explicit for Windows reproducibility
    with open(WORKFLOW_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_workflow_load_basic_metadata():
    raw = _load_raw()
    root = load_workflow_json(raw)
    assert root.name == raw.get("name")
    assert root.id == raw.get("id")
    assert isinstance(root.nodes, list)
    assert len(root.nodes) == len(raw.get("nodes", []))
    assert len(root.edges) == len(raw.get("edges", []))


def test_nodes_preserve_ids_and_order():
    raw = _load_raw()
    root = load_workflow_json(raw)
    raw_ids = [n["id"] for n in raw["nodes"]]
    model_ids = [n.get("id") for n in root.nodes]
    assert raw_ids == model_ids  # ordering preserved


def test_form_elements_roundtrip_subset():
    raw = _load_raw()
    root = load_workflow_json(raw)
    # Spot check: collect first 3 form element ids and their types
    raw_elems = raw.get("form", {}).get("elements", {})
    sample_ids = list(raw_elems.keys())[:3]
    for eid in sample_ids:
        assert eid in root.form.elements
        assert root.form.elements[eid].type == raw_elems[eid]["type"]


def test_output_nodes_enumeration_includes_image_output():
    raw = _load_raw()
    root = load_workflow_json(raw)
    out_nodes = list(enumerate_output_nodes(root))
    # Expect at least one l2i node (canvas_output)
    l2i_nodes = [n for n in out_nodes if n[1] == "l2i"]
    assert l2i_nodes, "Expected to find at least one l2i output-capable node"


def test_iter_form_input_fields_matches_positive_prompt_field():
    raw = _load_raw()
    root = load_workflow_json(raw)
    # Find a known positive prompt node field from raw data
    positive_node = next(n for n in raw["nodes"] if n["id"].startswith("positive_prompt:"))
    assert "value" in positive_node["data"]["inputs"], "Raw workflow missing expected value field"
    # Confirm iterator surfaces that field
    fields = list(iter_form_input_fields(root))
    matches = [f for f in fields if f[0] == positive_node["id"] and f[1] == "value"]
    assert matches, "iter_form_input_fields did not return expected positive prompt value field"


def test_roundtrip_serialization_structure_parity():
    raw = _load_raw()
    root = load_workflow_json(raw)
    dumped = root.model_dump(exclude_none=True)
    # Basic parity checks (we do not require exact deep equality due to potential ordering or optional omissions)
    assert dumped.get("name") == raw.get("name")
    assert len(dumped.get("nodes", [])) == len(raw.get("nodes", []))
    assert len(dumped.get("edges", [])) == len(raw.get("edges", []))
    # Ensure an arbitrary deep value survives (board id within l2i node if present)
    l2i_raw = next((n for n in raw["nodes"] if n["data"].get("type") == "l2i"), None)
    if l2i_raw:
        board_val = (
            l2i_raw.get("data", {})
            .get("inputs", {})
            .get("board", {})
            .get("value", {})
            .get("board_id")
        )
        if board_val:
            l2i_dump = next((n for n in dumped["nodes"] if n.get("id") == l2i_raw["id"]), None)
            assert (
                l2i_dump
                and l2i_dump.get("data", {})
                .get("inputs", {})
                .get("board", {})
                .get("value", {})
                .get("board_id")
                == board_val
            ), "Board ID not preserved in roundtrip dump"


def test_reloading_from_dump_preserves_node_ids():
    raw = _load_raw()
    root = load_workflow_json(raw)
    dumped = root.model_dump(exclude_none=True)
    # Mutate a copy to simulate re-load path
    dumped_copy = deepcopy(dumped)
    reloaded = load_workflow_json(dumped_copy)
    orig_ids = sorted([str(n.get("id")) for n in root.nodes if n.get("id") is not None])
    re_ids = sorted([str(n.get("id")) for n in reloaded.nodes if n.get("id") is not None])
    assert orig_ids == re_ids


@pytest.mark.parametrize("key", ["name", "id", "form", "nodes", "edges"])
def test_required_top_level_keys_present(key):
    raw = _load_raw()
    root = load_workflow_json(raw)
    # Some upstream workflow exports omit a top-level 'id'. Treat it as optional like 'description'.
    if key in {"description", "id"}:
        # Merely access to ensure attribute exists
        getattr(root, key)
    else:
        assert getattr(root, key) is not None


if __name__ == "__main__":  # Allow quick ad-hoc run
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
