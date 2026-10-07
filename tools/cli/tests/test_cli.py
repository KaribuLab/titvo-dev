"""Check working-tree selection, escaped reports and real graph integration."""

import asyncio
import json
import subprocess

import boto3
import pytest
from moto import mock_aws
from typer.testing import CliRunner

from titvo_cli.app import app
from titvo_cli.report import render
from titvo_cli.snapshot import collect, package
from titvo_cli.storage import BUCKET, bootstrap, upload
from titvo_cli.worker import run


def test_selection_respects_ignores_and_local_changes(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("ignored/\n")
    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored" / "x.py").write_text("ignored")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("dependency")
    (tmp_path / "app.py").write_text("first")
    subprocess.run(["git", "-C", str(tmp_path), "add", "app.py"], check=True)
    (tmp_path / "app.py").write_text("working-tree change")
    (tmp_path / "binary").write_bytes(b"\x00abc")
    (tmp_path / "escape").symlink_to(tmp_path / "app.py")
    (tmp_path / ".env").write_text("SECRET=example")
    selected, manifest = collect(tmp_path)
    assert selected["app.py"] == b"working-tree change"
    assert not {
        "binary",
        "escape",
        ".env",
        "ignored/x.py",
        "node_modules/x.js",
    }.intersection(selected)
    assert any(item["reason"] == "gitignore" for item in manifest["excluded"])


def test_initialized_nested_git_honors_its_own_ignore(tmp_path):
    nested = tmp_path / "frontend"
    nested.mkdir()
    subprocess.run(["git", "init", "-q", str(nested)], check=True)
    (nested / ".gitignore").write_text("generated.ts\n")
    (nested / "generated.ts").write_text("ignored")
    (nested / "app.ts").write_text("code")
    selected, _ = collect(tmp_path)
    assert "frontend/app.ts" in selected
    assert "frontend/generated.ts" not in selected


def test_preview_json_and_real_mode_guard(tmp_path):
    (tmp_path / "app.py").write_text("code")
    runner = CliRunner()
    result = runner.invoke(app, ["preview", str(tmp_path), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["files"][0]["path"] == "app.py"
    result = runner.invoke(app, ["scan", str(tmp_path), "--model", "real", "--yes"])
    assert result.exit_code != 0
    assert "allow-remote-ai" in result.output


def test_html_escapes_project_and_code():
    output = render(
        {
            "project": "<script>alert(1)</script>",
            "model_mode": "mock",
            "issues": [{"code": "<script>unsafe()</script>"}],
        }
    )
    assert "<script>" not in output
    assert "&lt;script&gt;" in output
    assert "no evalúa la seguridad" in output


@mock_aws
def test_snapshot_to_shared_agent_and_report(tmp_path):
    (tmp_path / "app.py").write_text("eval(input())  # TITVO_TEST_VULNERABILITY\n")
    files, manifest = collect(tmp_path)
    options = dict(
        region_name="us-east-1", aws_access_key_id="test", aws_secret_access_key="test"
    )
    s3 = boto3.client("s3", **options)
    dynamodb = boto3.client("dynamodb", **options)
    bootstrap(s3, dynamodb)
    task_id = upload(s3, dynamodb, package(files, manifest), manifest, "mock")
    s3.put_object(
        Bucket=BUCKET,
        Key=f"manifests/{task_id}.json",
        Body=json.dumps(manifest).encode(),
    )
    # The worker uses SDK clients; moto intercepts calls irrespective of endpoint.
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("titvo_cli.worker.clients", lambda: (s3, dynamodb))
        result = asyncio.run(run(task_id))
    assert result["coverage"]["complete"]
    assert result["model_mode"] == "mock"
    assert result["scaned_files"] == 1
    assert len(result["issues"]) == 1
    assert result["issues"][0]["path"] == "app.py"
    html = (
        s3.get_object(Bucket=BUCKET, Key=f"reports/{task_id}.html")["Body"]
        .read()
        .decode()
    )
    assert "IA SIMULADA" in html


def test_selection_in_git_subdirectory_respects_parent_ignores(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("generated.py\n")
    source = tmp_path / "src"
    source.mkdir()
    (source / "generated.py").write_text("ignored")
    (source / "app.py").write_text("code")
    selected, _ = collect(source)
    assert selected == {"app.py": b"code"}
