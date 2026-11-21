"""Unit tests for scan-manifest focus semantics and inventory contract."""

import hashlib
import subprocess
from pathlib import Path

import pytest

from titvo_cli.scan_manifest import (
    build_scan_manifest,
    resolve_commit_sha,
    resolve_focus_files,
)


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    return path


def test_focus_full_is_empty(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    (repo / "a.py").write_text("a\n")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-q", "-m", "init")
    assert resolve_focus_files(repo, "full") == []


def test_focus_staged_lists_cached_paths(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    (repo / "a.py").write_text("a\n")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-q", "-m", "init")
    (repo / "b.py").write_text("b\n")
    (repo / "a.py").write_text("a2\n")
    _git(repo, "add", "a.py", "b.py")
    assert resolve_focus_files(repo, "staged") == ["a.py", "b.py"]


def test_focus_commit_includes_deletions_and_changes(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    (repo / "keep.py").write_text("k\n")
    (repo / "gone.py").write_text("g\n")
    _git(repo, "add", "keep.py", "gone.py")
    _git(repo, "commit", "-q", "-m", "init")
    (repo / "keep.py").write_text("k2\n")
    (repo / "gone.py").unlink()
    (repo / "new.py").write_text("n\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "change")
    assert resolve_focus_files(repo, "commit") == ["gone.py", "keep.py", "new.py"]


def test_focus_root_commit_lists_entire_tree(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    (repo / "z.py").write_text("z\n")
    (repo / "a.py").write_text("a\n")
    _git(repo, "add", "a.py", "z.py")
    _git(repo, "commit", "-q", "-m", "root")
    assert resolve_focus_files(repo, "commit") == ["a.py", "z.py"]


def test_build_scan_manifest_inventory_sorted_and_hashed(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    (repo / "a.py").write_text("hello\n")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-q", "-m", "init")
    data = b"hello\n"
    files = {"b.py": b"b\n", "a.py": data}
    manifest = build_scan_manifest(
        scope="full",
        commit=resolve_commit_sha(repo),
        branch="main",
        files_bytes=files,
        focus_files=[],
    )
    assert manifest["version"] == 1
    assert manifest["scope"] == "full"
    assert manifest["branch"] == "main"
    assert manifest["focus_files"] == []
    assert [item["path"] for item in manifest["files"]] == ["a.py", "b.py"]
    assert manifest["files"][0] == {
        "path": "a.py",
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
    }


def test_build_allows_focus_path_absent_from_files():
    manifest = build_scan_manifest(
        scope="commit",
        commit="abc123",
        branch="dev",
        files=[{"path": "kept.py", "sha256": "0" * 64, "size": 1}],
        focus_files=["deleted.py", "kept.py"],
    )
    assert manifest["focus_files"] == ["deleted.py", "kept.py"]
    assert [item["path"] for item in manifest["files"]] == ["kept.py"]


def test_invalid_scope_rejected(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    with pytest.raises(ValueError, match="scope inválido"):
        resolve_focus_files(repo, "partial")
    with pytest.raises(ValueError, match="scope inválido"):
        build_scan_manifest(
            scope="partial",
            commit="abc",
            branch="main",
            files_bytes={},
        )
