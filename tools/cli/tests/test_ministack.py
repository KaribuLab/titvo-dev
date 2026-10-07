"""Opt-in SDK/Docker integration tests against the real MiniStack container."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from titvo_cli.snapshot import collect, package
from titvo_cli.storage import BUCKET, bootstrap, clients, upload

pytestmark = pytest.mark.skipif(
    os.getenv("TITVO_MINISTACK_TESTS") != "1",
    reason="Requires MiniStack and built Docker worker",
)
COMPOSE = Path(__file__).resolve().parents[3] / "docker-compose.ministack.yaml"


def execute(task_id):
    """Run an actual worker container rather than trust a Batch emulator status."""
    return subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE),
            "run",
            "--rm",
            "--no-deps",
            "worker",
            "--task-id",
            task_id,
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_multibatch_snapshot_and_corruption(tmp_path):
    """Verify bounded execution and an incomplete result for a tampered package."""
    for index in range(60):
        (tmp_path / f"file_{index}.py").write_text("# fixture\n" + "x = 1\n" * 2000)
    (tmp_path / "api.py").write_text("eval(input())  # TITVO_TEST_VULNERABILITY\n")
    files, manifest = collect(tmp_path)
    s3, dynamodb = clients()
    bootstrap(s3, dynamodb)
    archive = package(files, manifest)
    task_id = upload(s3, dynamodb, archive, manifest, "mock")
    process = execute(task_id)
    assert process.returncode == 0, process.stdout + process.stderr
    result = json.loads(
        s3.get_object(Bucket=BUCKET, Key=f"reports/{task_id}.json")["Body"].read()
    )
    assert result["scaned_files"] == 61
    assert (
        result["metrics"]["task_duration_seconds"]
        >= result["metrics"]["duration_seconds"]
    )
    assert result["metrics"]["total_batches"] == result["metrics"]["completed_batches"]
    assert result["usage"]["cost_usd"] == 0
    assert result["usage"]["cost_status"] == "mock"
    assert result["coverage"]["complete"]
    assert result["coverage"]["experts"]["code_vulnerabilities"]["batches_total"] > 1
    assert len(result["issues"]) == 1
    bad_task = upload(s3, dynamodb, archive, manifest, "mock")
    changed = dict(files)
    changed["api.py"] = b"changed after manifest"
    s3.put_object(
        Bucket=BUCKET,
        Key=f"temp/{bad_task}/snapshot.tar.gz",
        Body=package(changed, manifest),
    )
    process = execute(bad_task)
    assert process.returncode == 2, process.stdout + process.stderr
    result = json.loads(
        s3.get_object(Bucket=BUCKET, Key=f"reports/{bad_task}.json")["Body"].read()
    )
    assert result["status"] == "FAILED"
    assert not result["coverage"]["complete"]
    assert result["scaned_files"] == 0
    assert "integrity mismatch" in result["error"]
