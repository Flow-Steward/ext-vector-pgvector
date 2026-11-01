"""Standalone pgvector public contracts."""

from pathlib import Path
import yaml

from commands import FIELDS, WRITES

ROOT = Path(__file__).resolve().parents[1]

READS = set(FIELDS) - WRITES


def load(f):
    return yaml.safe_load((ROOT / f).read_text())


def test_identity_and_operation_parity():
    m = load("extension.yaml")
    assert (
        m["extension_id"]
        == load("extension-descriptor.yaml")["extension_id"]
        == "flowsteward.pgvector"
    )
    assert m["features"] == ["tool", "action"]
    ops = load("contracts/operation_manifest.yaml")["operations"]
    actions = load("ui/actions/actions.yaml")["actions"]
    forms = load("contracts/step_ui_manifest.yaml")["forms"]
    assert {o["operation_id"] for o in ops} == READS | WRITES
    assert {a["action_id"] for a in actions} == READS | WRITES
    assert {f["operation_id"] for f in forms} == READS | WRITES
    assert {e["operation_id"] for e in m["external_effects"]} == WRITES
    assert m["egress"] == {"connection_fields": ["pgvector.host"]}
    for o in ops:
        assert o["connection_type_ids"] == ["pgvector"]
        a = next(a for a in actions if a["action_id"] == o["operation_id"])
        f = next(f for f in forms if f["operation_id"] == o["operation_id"])
        assert {i["name"] for i in o["inputs"]} == {i["name"] for i in a["parameters"]}
        assert {i["name"] for i in f["fields"]} == {i["name"] for i in o["inputs"]} - {
            "connection_ref"
        }
        assert o["outputs"] == [
            {"name": "records", "value_type": "json"},
            {"name": "count", "value_type": "integer"},
            {"name": "applied", "value_type": "boolean"},
        ]


def test_connection_is_own_and_secret_safe():
    c = load("contracts/connection_types.yaml")["connection_types"]
    assert len(c) == 1 and c[0]["connection_type_id"] == "pgvector"
    assert c[0]["capabilities"]["workflow_trigger"] is False
    assert c[0]["config_schema"]["additionalProperties"] is False
    assert set(c[0]["config_schema"]["properties"]) == {
        "host",
        "port",
        "tls",
        "database",
        "schema",
        "request_timeout_seconds",
    }
    assert c[0]["secret_schema"]["required"] == ["username", "password"]
