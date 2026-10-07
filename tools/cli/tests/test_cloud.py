"""Exercise AWS contracts, credential isolation, bounded polling and menu routing."""

import importlib
import io
import json
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest
import typer
from rich.console import Console
from typer.testing import CliRunner

from titvo_cli import cloud
from titvo_cli import interactive as ui
from titvo_cli.outcome import outcome_rows
from titvo_cli.snapshot import collect, package

cli = importlib.import_module("titvo_cli.app")


class Response(io.BytesIO):
    """Provide the real urllib response context-manager interface."""


class API:
    """Test double for existing HTTP contracts; never contacts a provider or AWS."""

    def __init__(self, failure=None, urls=None):
        self.calls = []
        self.failure = failure
        self.urls = urls

    def open(self, request, timeout):
        """Record actual Request headers and bytes, and serve scripted API responses."""
        self.calls.append(request)
        assert timeout == 30
        if self.failure and request.get_method() == "PUT":
            raise self.failure
        if request.full_url.endswith("/cli-files"):
            return Response(
                json.dumps(
                    {
                        "presigned_urls": self.urls
                        or {
                            "snapshot.tar.gz": "https://bucket.s3.example/temp/snapshot.tar.gz?signature=secret"
                        }
                    }
                ).encode()
            )
        if request.get_method() == "PUT":
            return Response(b"")
        if request.full_url.endswith("/run-scan"):
            return Response(b'{"scan_id":"tvo-scan-test"}')
        return Response(
            b'{"status":"COMPLETED","result":{"coverage":{"complete":true},"issues_count":3}}'
        )


def test_aws_contract_upload_preserves_snapshot_and_scopes_key(tmp_path):
    """Upload exact manifest bytes to S3 without forwarding the API credential."""
    from code_analysis.infra.adapters.cli_snapshot import read_snapshot

    (tmp_path / "app.py").write_text("code = 1\n")
    files, manifest = collect(tmp_path)
    archive = package(files, manifest)
    api = API()
    client = cloud.CloudClient("https://api.example/stage", "tvok-test-secret", api)
    task_id = client.start(archive, "git@github.com:team/repo.git", "dev")
    assert task_id == "tvo-scan-test"
    assert len(api.calls) == 3
    signed, put, start = api.calls
    assert signed.full_url == "https://api.example/stage/cli-files"
    assert signed.get_header("X-api-key") == "tvok-test-secret"
    payload = json.loads(signed.data)
    assert payload["source"] == "cli"
    assert payload["args"]["files"] == [
        {"name": "snapshot.tar.gz", "content_type": "application/gzip"}
    ]
    assert put.get_method() == "PUT"
    assert put.get_header("X-api-key") is None
    assert put.get_header("Content-type") == "application/gzip"
    assert put.data == archive
    assert read_snapshot(put.data) == [{"path": "app.py", "content": "code = 1\n"}]
    trigger = json.loads(start.data)
    assert trigger == {
        "source": "cli",
        "args": {
            "batch_id": payload["args"]["batch_id"],
            "repository_url": "git@github.com:team/repo.git",
            "branch": "dev",
            "scan_mode": "full",
        },
    }
    assert client.status(task_id)["result"]["issues_count"] == 3
    assert json.loads(api.calls[-1].data) == {"scan_id": task_id}


@pytest.mark.parametrize(
    "failure",
    [
        HTTPError("https://signed.example/?secret", 403, "secret", {}, None),
        URLError("tvok-secret: signed secret"),
    ],
)
def test_failed_upload_does_not_trigger_retry_or_change_destination(failure):
    """An unsuccessful PUT must never launch a scan or leak a signed URL."""
    api = API(failure)
    client = cloud.CloudClient("https://api.example", "tvok-secret", api)
    with pytest.raises(ValueError) as exc:
        client.start(b"archive", "https://github.com/team/repo", "main")
    assert len(api.calls) == 2
    assert "secret" not in str(exc.value)
    assert "No se cambió de destino" in str(exc.value)


def test_documented_list_signed_url_shape_is_accepted():
    """Support the older documented API response without changing upload semantics."""
    api = API(urls=[{"name": "snapshot.tar.gz", "url": "https://s3.example/file"}])
    assert (
        cloud.CloudClient("https://api.example", "key", api).start(
            b"tar", "https://github.com/a/b", "main"
        )
        == "tvo-scan-test"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://api.example",
        "https://key@api.example",
        "https://api.example/#secret",
        "file:///tmp/api",
        "https://api.example/?key=secret",
    ],
)
def test_invalid_api_url_rejected_before_network(url):
    """Reject ambiguous or insecure API endpoints before attaching a credential."""
    with pytest.raises(ValueError):
        cloud.CloudClient(url, "key", Mock())


def test_api_redirects_are_not_followed():
    """A redirect cannot carry a credential to another origin."""
    assert (
        cloud.NoRedirect().redirect_request(
            None, None, 302, "", {}, "https://other.example"
        )
        is None
    )


def test_polling_terminal_failed_can_still_mean_completed_with_findings(monkeypatch):
    """Polling follows task completion, while measured execution remains independent."""
    client = cloud.CloudClient("https://api.example", "key", API())
    client.status = Mock(
        side_effect=[
            {"status": "IN_PROGRESS"},
            {
                "status": "FAILED",
                "result": {"coverage": {"complete": True}, "issues_count": 2},
            },
        ]
    )
    monkeypatch.setattr(cloud.time, "sleep", Mock())
    states = []
    response = client.wait(
        "tvo-scan-test", 10, update=lambda data: states.append(data["status"])
    )
    assert states == ["IN_PROGRESS", "FAILED"]
    assert dict(outcome_rows(response["result"]))["Ejecución"] == "Completado"
    assert dict(outcome_rows(response["result"]))["Seguridad"] == "Con hallazgos · 2"


def test_poll_timeout_keeps_task_available_for_later_status(monkeypatch):
    """Timeout does not restart or cancel the task and supplies its consultation command."""
    client = cloud.CloudClient("https://api.example", "key", API())
    client.status = Mock(return_value={"status": "IN_PROGRESS"})
    monkeypatch.setattr(cloud.time, "monotonic", Mock(side_effect=[0, 11]))
    with pytest.raises(ValueError, match="titvo status tvo-scan-test --target aws"):
        client.wait("tvo-scan-test", 10)
    client.status.assert_called_once()


@pytest.mark.parametrize("task_id", ["../escape", "/absolute", "", "a/b"])
def test_invalid_task_ids_cannot_write_reports(task_id, tmp_path):
    """Remote identifiers cannot escape the reports directory."""
    with pytest.raises(ValueError):
        cloud.save_result({"status": "COMPLETED"}, task_id, tmp_path)
    assert not list(tmp_path.iterdir())


def test_aws_report_preserves_counts_cost_and_external_link(tmp_path):
    """Save measured AWS summary without pretending to have inline findings."""
    result = cloud.save_result(
        {
            "status": "FAILED",
            "result": {
                "coverage": {"complete": True},
                "issues_count": 3,
                "report_url": "https://reports.example/full.html",
                "usage": {"cost_usd": 0.2},
            },
        },
        "tvo-scan-test",
        tmp_path,
    )
    assert result["target"] == "aws"
    assert "issues" not in result
    assert (
        json.loads((tmp_path / "tvo-scan-test.json").read_text())["usage"]["cost_usd"]
        == 0.2
    )
    assert "Abrir reporte completo AWS" in (tmp_path / "tvo-scan-test.html").read_text()
    assert dict(outcome_rows({"status": "FAILED"}))["Seguridad"] == "No registrado"


def test_aws_scan_uses_no_docker_or_lab_clients(monkeypatch, tmp_path):
    """CLI dispatch reaches the cloud transport and preserves completed security rejection."""
    (tmp_path / "app.py").write_text("code")
    client = Mock(endpoint="https://api.example")
    client.start.return_value = "tvo-scan-test"
    client.wait.return_value = {
        "status": "FAILED",
        "result": {"coverage": {"complete": True}, "issues_count": 3},
    }
    monkeypatch.setattr(cloud, "CloudClient", Mock(return_value=client))
    lab = Mock(side_effect=AssertionError("must not touch MiniStack"))
    monkeypatch.setattr(cli, "clients", lab)
    original_popen = cli.subprocess.Popen

    def reject_docker(command, *args, **kwargs):
        """Allow local Git reads while rejecting any Docker worker launch."""
        if command[0] == "docker":
            return lab(command, *args, **kwargs)
        return original_popen(command, *args, **kwargs)

    monkeypatch.setattr(cli.subprocess, "Popen", reject_docker)
    result = CliRunner().invoke(
        cli.app,
        [
            "scan",
            str(tmp_path),
            "--target",
            "aws",
            "--repository-url",
            "https://github.com/team/repo",
            "--branch",
            "main",
            "--yes",
            "--output",
            str(tmp_path / "reports"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "AWS · servicio Titvo" in result.output
    assert "Con hallazgos · 3" in result.output
    assert "sin hallazgos reportados" not in result.output
    lab.assert_not_called()


def test_cloud_confirmation_denied_never_uploads(monkeypatch, tmp_path):
    """The final guided confirmation precedes every cloud mutation."""
    (tmp_path / "app.py").write_text("code")
    client = Mock(endpoint="https://api.example")
    monkeypatch.setattr(cloud, "CloudClient", Mock(return_value=client))
    monkeypatch.setattr(
        ui.questionary, "confirm", Mock(return_value=Mock(ask=lambda: False))
    )
    with pytest.raises(typer.Exit):
        cli.guided_scan(
            tmp_path,
            "http://localhost:4566",
            "service",
            False,
            False,
            tmp_path / "reports",
            None,
            target="aws",
            repository_url="https://github.com/a/b",
            branch="main",
        )
    client.start.assert_not_called()


def test_missing_cloud_key_and_model_override_reject_before_upload(
    monkeypatch, tmp_path
):
    """A provider key is not a Titvo credential; AWS cannot silently become mock."""
    monkeypatch.delenv("TITVO_API_KEY", raising=False)
    monkeypatch.setenv("TITVO_AI_API_KEY", "provider-secret")
    monkeypatch.setenv("TITVO_API_ENDPOINT", "https://api.example")
    runner = CliRunner()
    missing = runner.invoke(
        cli.app, ["scan", str(tmp_path), "--target", "aws", "--yes"]
    )
    assert missing.exit_code == 2 and "TITVO_API_KEY" in missing.output
    override = runner.invoke(
        cli.app, ["scan", str(tmp_path), "--target", "aws", "--model", "mock", "--yes"]
    )
    assert override.exit_code != 0 and "omite --model" in override.output
    assert "provider-secret" not in missing.output


def test_target_preferences_survive_without_project_or_secrets(monkeypatch, tmp_path):
    """Destination is remembered independently of project selection."""
    monkeypatch.setenv("TITVO_API_KEY", "tvok-secret")
    terminal = Console(file=io.StringIO())
    session = ui.Session(target="aws", api_url="https://api.example")
    path = tmp_path / "ui.json"
    ui.save_session(terminal, path, session)
    restored = ui.load_session(path, tmp_path, tmp_path)
    assert restored.target == "aws" and restored.api_url == session.api_url
    assert restored.target_ready
    assert "tvok-secret" not in path.read_text()


def test_cloud_menu_routes_scan_status_and_restores_credentials(monkeypatch, tmp_path):
    """Use the chosen destination throughout a menu session without asking for AI keys."""
    session = ui.Session(
        project=tmp_path,
        scope_ready=True,
        target="aws",
        api_url="https://api.example",
        repository_url="https://github.com/a/b",
        branch="main",
    )
    monkeypatch.setattr(ui, "load_session", lambda *args: session)
    choices = iter(["scan", "status", None])
    answers = iter(["tvok-session-secret", "tvo-scan-test"])
    monkeypatch.setattr(ui, "choose", lambda *args: next(choices))
    monkeypatch.setattr(ui, "ask", lambda *args, **kwargs: next(answers))
    monkeypatch.setattr(ui, "pause", lambda: None)
    monkeypatch.delenv("TITVO_API_KEY", raising=False)
    scan, status = Mock(return_value=None), Mock()
    ui.run_session(Console(file=io.StringIO()), tmp_path, Mock(), scan, status, Mock())
    assert scan.call_args.kwargs["target"] == "aws"
    assert scan.call_args.kwargs["model"] == "service"
    assert status.call_args.kwargs["target"] == "aws"
    import os

    assert "TITVO_API_KEY" not in os.environ
    assert "tvok-session-secret" not in (tmp_path / ".titvo/ui.json").read_text()


def test_change_api_endpoint_clears_previous_key(monkeypatch):
    """Changing AWS service accounts does not reuse another endpoint's credential."""
    monkeypatch.setenv("TITVO_API_ENDPOINT", "https://first.example")
    monkeypatch.setenv("TITVO_API_KEY", "first-key")
    monkeypatch.setattr(ui, "choose", lambda *args: "aws")
    answers = iter(["https://second.example", ""])
    monkeypatch.setattr(ui, "ask", lambda *args, **kwargs: next(answers))
    session = ui.Session()
    assert ui.select_target(Console(file=io.StringIO()), session)
    import os

    assert "TITVO_API_KEY" not in os.environ
    assert session.target == "aws"


def test_aws_dashboard_opens_configured_site_without_local_server(monkeypatch):
    """Production dashboard uses its own login and never enables the lab adapter."""
    browser = Mock()
    monkeypatch.setattr(cli.webbrowser, "open", browser)
    result = CliRunner().invoke(
        cli.app,
        [
            "dashboard",
            "--target",
            "aws",
            "--dashboard-url",
            "https://dashboard.example",
        ],
    )
    assert result.exit_code == 0
    browser.assert_called_once_with("https://dashboard.example")


def test_cancel_target_setup_preserves_existing_destination_and_key(monkeypatch):
    """Cancelling the connection form does not partially save another account."""
    monkeypatch.setenv("TITVO_API_ENDPOINT", "https://original.example")
    monkeypatch.setenv("TITVO_API_KEY", "original-key")
    monkeypatch.setattr(ui, "choose", lambda *args: "aws")
    answers = iter(["https://new.example", None])
    monkeypatch.setattr(ui, "ask", lambda *args, **kwargs: next(answers))
    session = ui.Session()
    assert not ui.select_target(Console(file=io.StringIO()), session)
    import os

    assert os.environ["TITVO_API_KEY"] == "original-key"
    assert session.target == "ministack" and session.api_url == ""


def test_cloud_key_can_be_replaced_without_persisting(monkeypatch):
    """Settings can replace an existing service key with a hidden session-only input."""
    monkeypatch.setenv("TITVO_API_KEY", "old-key")
    monkeypatch.setenv("TITVO_API_ENDPOINT", "https://api.example")
    monkeypatch.setattr(ui, "ask", lambda *args, **kwargs: "new-key")
    assert ui.configure(
        Console(file=io.StringIO()),
        ui.Session(target="aws", api_url="https://api.example"),
    )
    import os

    assert os.environ["TITVO_API_KEY"] == "new-key"


def test_unknown_cloud_result_shape_is_rejected_before_saving(tmp_path):
    """Unexpected API responses do not create misleading local reports."""
    with pytest.raises(ValueError, match="resultado inesperado"):
        cloud.save_result(
            {"status": "FAILED", "result": "invalid"}, "task-id", tmp_path
        )
    assert not list(tmp_path.iterdir())


def test_repository_identity_detects_git_and_requires_branch_for_detached_head(
    tmp_path,
):
    """Read cloud identity from local metadata and reject credential-bearing URLs."""
    import subprocess

    subprocess.run(["git", "init", "-q", "-b", "dev", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "remote",
            "add",
            "origin",
            "git@github.com:team/repo.git",
        ],
        check=True,
    )
    assert cloud.repository_identity(tmp_path, None, None) == (
        "git@github.com:team/repo.git",
        "dev",
    )
    with pytest.raises(ValueError, match="credenciales"):
        cloud.repository_identity(tmp_path, "https://token@github.com/team/repo", "dev")
