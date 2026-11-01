"""Pinned source provenance and native architecture integrity."""

import hashlib
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_native_provenance_matches_patch_and_minimal_packages():
    p = json.loads((ROOT / "toolbox-provenance.json").read_text())
    assert p["tag"] == "v1.3.0" and p["commit"] == "b0010060a939455d91e4f8ba62dc3e72b1892469"
    assert "@sha256:" in p["go_image"]
    assert hashlib.sha256((ROOT / p["patch"]).read_bytes()).hexdigest() == p["patch_sha256"]
    assert set(p["packages"]) == {
        "github.com/googleapis/mcp-toolbox/internal/sources/postgres",
        "github.com/googleapis/mcp-toolbox/internal/tools/postgres/postgressql",
    }


@pytest.mark.parametrize("target,machine", [("linux-amd64", 62), ("linux-arm64", 183)])
def test_native_binary_integrity(target, machine):
    p = json.loads((ROOT / "toolbox-provenance.json").read_text())
    binary = ROOT / "bin" / target / "toolbox"
    payload = binary.read_bytes()
    assert payload[:6] == b"\x7fELF\x02\x01" and int.from_bytes(payload[18:20], "little") == machine
    assert len(payload) == p["binaries"][target]["size"]
    assert hashlib.sha256(payload).hexdigest() == p["binaries"][target]["sha256"]
