"""Verify real accounting and local read-only dashboard contracts without credits."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from titvo_cli.dashboard import LabAPI, repository_id
from titvo_cli.usage import UsageModel, summary_rows


def response():
    """Return normalized provider telemetry with discounted cached input."""
    return SimpleNamespace(
        usage_metadata={
            "input_tokens": 1000,
            "output_tokens": 200,
            "input_token_details": {"cache_read": 500},
        }
    )


class Model:
    """Offline fake exercises both graph invocation paths."""

    def invoke(self, *args):
        return response()

    async def ainvoke(self, *args):
        return response()


def test_counts_sync_async_and_cached_pricing(monkeypatch):
    monkeypatch.delenv("TITVO_AI_BASE_URL", raising=False)
    model = UsageModel(Model(), "real", "openai", "gpt-4.1-mini")
    asyncio.run(model.ainvoke([]))
    model.invoke([])
    result = model.summary()
    assert result["calls"] == result["measured_calls"] == 2
    assert result["input_tokens"] == 2000
    assert result["cached_input_tokens"] == 1000
    assert result["total_tokens"] == 2400
    assert result["cost_usd"] == pytest.approx(0.00114)
    assert result["cost_status"] == "estimated"


def test_partial_and_failed_calls_never_claim_total(monkeypatch):
    monkeypatch.delenv("TITVO_AI_BASE_URL", raising=False)
    model = UsageModel(Model(), "real", "openai", "gpt-4.1-mini")
    model.invoke([])
    model.model = Mock()
    model.model.invoke.return_value = SimpleNamespace(content="no usage")
    model.invoke([])
    model.model.invoke.side_effect = TimeoutError()
    with pytest.raises(TimeoutError):
        model.invoke([])
    assert model.summary()["cost_status"] == "partial"
    assert model.summary()["failed_calls"] == 1
    assert not model.summary()["complete"]


def test_unknown_tariff_and_mock_and_historical(monkeypatch):
    monkeypatch.setenv("TITVO_AI_BASE_URL", "http://localhost:9000")
    model = UsageModel(Model(), "real", "openai", "gpt-4.1-mini")
    model.invoke([])
    assert model.summary()["cost_usd"] is None
    assert UsageModel(Model(), "mock").summary()["cost_usd"] == 0
    assert dict(summary_rows({}))["Costo IA"] == "No registrado"


def test_custom_rates_and_metadata_fallback(monkeypatch):
    for kind, rate in [("INPUT", "2"), ("CACHED", "1"), ("OUTPUT", "3")]:
        monkeypatch.setenv(f"TITVO_PRICE_{kind}_PER_MILLION", rate)
    fake = Mock()
    fake.invoke.return_value = SimpleNamespace(
        response_metadata={
            "token_usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 200,
                "prompt_tokens_details": {"cached_tokens": 500},
            }
        }
    )
    tracked = UsageModel(fake, "real", "other", "custom")
    tracked.invoke([])
    assert tracked.summary()["cost_usd"] == pytest.approx(0.0021)
    assert tracked.summary()["pricing_source"] == "configured"
    monkeypatch.setenv("TITVO_PRICE_INPUT_PER_MILLION", "NaN")
    with pytest.raises(ValueError):
        UsageModel(fake, "real")


def test_dashboard_reads_paginated_tasks_and_exact_s3_report():
    dynamodb, s3 = Mock(), Mock()
    item = {
        "scan_id": {"S": "one"},
        "project": {"S": "/project/src"},
        "status": {"S": "FAILED"},
        "model": {"S": "real"},
        "created_at": {"S": "2026-10-06"},
        "report_key": {"S": "reports/one.json"},
    }
    dynamodb.scan.side_effect = lambda **options: (
        {"Items": [item]}
        if "ExclusiveStartKey" in options
        else {"Items": [], "LastEvaluatedKey": {"scan_id": {"S": "older"}}}
    )
    report = {"coverage": {"complete": True}, "usage": {"cost_usd": 1.2}, "issues": []}
    s3.get_object.return_value = {
        "Body": SimpleNamespace(read=lambda: json.dumps(report).encode())
    }
    api = LabAPI(s3, dynamodb)
    assert api.get("/api/admin/auth/me")[1]["role"] == "member"
    assert api.get("/api/admin/repos")[1]["items"][0]["last_scan"]["status"] == "FAILED"
    assert api.get("/api/admin/repos")[1]["items"][0]["last_scan"]["execution_status"] == "COMPLETED"
    identity = repository_id("/project/src")
    assert len(api.get(f"/api/admin/repos/{identity}/scans")[1]["items"]) == 1
    assert api.get("/api/admin/scans/one")[1]["result"] == report
    assert api.get("/api/admin/scans/one")[1]["execution_status"] == "COMPLETED"
    assert api.get("/api/admin/scans/absent")[0] == 404
    assert dynamodb.scan.call_args_list[1].kwargs["ExclusiveStartKey"]


def test_lab_handler_denies_external_reads_and_all_writes():
    """Test the actual HTTP dispatch guard without opening a network socket."""
    from titvo_cli.dashboard import handler_for

    api = Mock()
    Handler = handler_for(api)
    handler = object.__new__(Handler)
    handler.respond = Mock()
    handler.headers = {"Host": "127.0.0.1:8787", "Origin": "https://outside.example"}
    handler.path = "/api/admin/scans/one"
    handler.do_GET()
    assert handler.respond.call_args.args[0] == 403
    api.get.assert_not_called()
    handler.headers = {"Host": "outside.example:8787"}
    handler.do_GET()
    assert handler.respond.call_args.args[0] == 403
    handler.do_POST()
    assert handler.respond.call_args.args[0] == 405
    api.get.assert_not_called()


def test_dashboard_does_not_merge_projects_with_same_name():
    """Local path identities distinguish unrelated repos sharing a basename."""
    s3, dynamodb = Mock(), Mock()
    base = {
        "project": {"S": "frontend"},
        "status": {"S": "PENDING"},
        "model": {"S": "mock"},
    }
    dynamodb.scan.return_value = {
        "Items": [
            {**base, "scan_id": {"S": "a"}, "project_id": {"S": "path-one"}},
            {**base, "scan_id": {"S": "b"}, "project_id": {"S": "path-two"}},
        ]
    }
    repos = LabAPI(s3, dynamodb).get("/api/admin/repos")[1]["items"]
    assert len(repos) == 2
    assert repos[0]["repository_id"] != repos[1]["repository_id"]
