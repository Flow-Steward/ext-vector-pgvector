from unittest.mock import patch
import json
import main
from test_live import envelope
from validation import Failure
import toolbox
import pytest


@pytest.mark.parametrize(
    "kw,code",
    [
        ({"claim": False}, "effect_claim_required"),
        ({"test_mode": True}, "test_mode_suppressed"),
        ({"reference": "other"}, "invalid_connection"),
    ],
)
def test_write_claim_and_test_mode_block_before_io(kw, code):
    payload = envelope("delete_chunk", {"collection": "docs", "chunk_id": "x"}, **kw)
    with patch.object(toolbox, "invoke", side_effect=AssertionError("must not call")):
        assert main.handle(payload)["error_code"] == code


def test_uncertain_write_is_not_automatically_retryable_or_secret_leaking():
    payload = envelope("delete_chunk", {"collection": "docs", "chunk_id": "x"})
    responses = [
        [[{"dimensions": 3, "metric": "cosine", "valid": True}]],
        Failure("provider_unavailable", "Safe error", dispatched=True),
    ]
    with patch.object(toolbox, "invoke", side_effect=responses):
        result = main.handle(payload)
    assert result["external_effect_status"] == "timeout_unknown" and result["retryable"] is False
    assert "fixture-only-pgvector" not in json.dumps(result)


def test_connection_and_input_budgets_precede_io():
    payload = envelope("query", {"collection": "docs", "vector": [1, 0, 0]})
    payload["action"]["input"]["secret"] = "x" * 270000
    with patch.object(toolbox, "invoke", side_effect=AssertionError("must not call")):
        result = main.handle(payload)
    assert result["ok"] is False and result["definitely_no_external_effect"]
