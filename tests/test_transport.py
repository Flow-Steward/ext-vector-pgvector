import json
from unittest.mock import patch
import pytest
import toolbox
from validation import Failure, connection_values


def test_policy_pin_and_public_tls(monkeypatch):
    config = {"host": "db.example", "port": 5432, "tls": False}
    monkeypatch.delenv("FS_ALLOW_PRIVATE_REMOTE_URLS", raising=False)
    with patch.object(toolbox, "resolve_pinned_ips", return_value=["127.0.0.1"]):
        with pytest.raises(Failure):
            toolbox._endpoint(config)
    monkeypatch.setenv("FS_ALLOW_PRIVATE_REMOTE_URLS", "true")
    with patch.object(toolbox, "resolve_pinned_ips", return_value=["8.8.8.8"]):
        with pytest.raises(Failure):
            toolbox._endpoint(config)
        assert toolbox._endpoint({**config, "tls": True}) == ("8.8.8.8",)


def test_managed_config_pins_address_preserves_tls_hostname_and_no_env_expansion():
    config, secrets = connection_values(
        {"config": {"host": "db.example"}, "secrets": {"username": "user", "password": "$secret"}}
    )
    raw = toolbox.managed_config(
        config,
        secrets,
        {"type": "postgres-sql", "statement": "SELECT $1", "parameters": [], "readOnly": True},
        {},
        ("8.8.8.8",),
    )
    source, command = [json.loads(d) for d in raw.split("\n---\n")]
    assert "$" not in raw and source["password"] == "$secret"
    assert source["host"] == "db.example" and source["queryParams"]["sslmode"] == "verify-full"
    assert source["queryParams"]["fs_pinned_ips"] == "8.8.8.8"
    assert command["statement"] == "SELECT $1" and "readOnly" not in command
