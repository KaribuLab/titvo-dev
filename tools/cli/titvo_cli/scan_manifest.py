"""Build the scan-manifest.json sidecar uploaded next to snapshot.tar.gz.

Contract (version 1)
--------------------
``scan-manifest.json`` is a sibling object under ``temp/{batch_id}/``, not inside
the tar and not listed in the analysis inventory as source code.

JSON shape::

    {
      "version": 1,
      "scope": "commit" | "staged" | "full",
      "commit": "<sha>",
      "branch": "<branch>",
      "focus_files": ["..."],   # lexicographically sorted; empty for full
      "files": [{"path", "sha256", "size"}]  # tar inventory, sorted by path
    }

``focus_files`` semantics (local Git only, no network):

- ``commit``: paths from ``git diff`` vs the first parent (includes deletions).
  For a root commit, every path in ``HEAD``'s tree.
- ``staged``: paths from ``git diff --cached``.
- ``full``: ``[]`` (analyze the whole analyzable snapshot).

``files`` inventorizes the snapshot tar contents (from collect/package), not
the focus set. A deleted path may appear in ``focus_files`` and be absent from
``files``.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Iterable, Mapping, Sequence

SCOPES = frozenset({"commit", "staged", "full"})


def _git(project: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    """Run a local Git command without network; never mutate the repository."""
    return subprocess.run(
        ["git", "-C", str(project), *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=check,
    )


def resolve_commit_sha(project: Path) -> str:
    """Return the current HEAD commit SHA for the project working tree."""
    result = _git(project, "rev-parse", "HEAD")
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError(
            "No se pudo resolver el commit HEAD; el proyecto debe ser un repositorio Git."
        )
    return result.stdout.strip()


def resolve_focus_files(project: Path, scope: str) -> list[str]:
    """Resolve analysis focus paths for the given scan scope (lexicographically sorted)."""
    if scope not in SCOPES:
        raise ValueError(f"scope inválido: {scope!r}; use commit, staged o full")
    if scope == "full":
        return []
    if scope == "staged":
        result = _git(project, "diff", "--cached", "--name-only", "-z")
        if result.returncode != 0:
            raise ValueError("No se pudo listar cambios staged con git diff --cached.")
        return _sorted_paths(result.stdout.split("\0"))
    # scope == "commit"
    parent = _git(project, "rev-parse", "--verify", "HEAD^")
    if parent.returncode != 0:
        tree = _git(project, "ls-tree", "-r", "--name-only", "-z", "HEAD")
        if tree.returncode != 0:
            raise ValueError("No se pudo listar el árbol del commit raíz.")
        return _sorted_paths(tree.stdout.split("\0"))
    diff = _git(project, "diff", "--name-only", "-z", "HEAD^", "HEAD")
    if diff.returncode != 0:
        raise ValueError("No se pudo listar el diff del commit contra su padre.")
    return _sorted_paths(diff.stdout.split("\0"))


def _sorted_paths(parts: Iterable[str]) -> list[str]:
    """Drop empty git -z segments and return unique paths in lexical order."""
    return sorted({path for path in parts if path})


def _inventory_from_bytes(files_bytes: Mapping[str, bytes]) -> list[dict]:
    """Build sorted path/sha256/size entries from collected file bytes."""
    return [
        {
            "path": path,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        }
        for path, data in sorted(files_bytes.items())
    ]


def _inventory_from_entries(entries: Sequence[Mapping]) -> list[dict]:
    """Normalize and sort precomputed inventory entries by path."""
    normalized = []
    for item in entries:
        path = item["path"]
        sha256 = item["sha256"]
        size = item["size"]
        if not isinstance(path, str) or not isinstance(sha256, str):
            raise ValueError("Cada entrada de files requiere path y sha256 string.")
        if not isinstance(size, int) or size < 0:
            raise ValueError("Cada entrada de files requiere size entero no negativo.")
        normalized.append({"path": path, "sha256": sha256, "size": size})
    return sorted(normalized, key=lambda item: item["path"])


def build_scan_manifest(
    *,
    scope: str,
    commit: str,
    branch: str,
    files_bytes: Mapping[str, bytes] | None = None,
    files: Sequence[Mapping] | None = None,
    focus_files: Sequence[str] | None = None,
) -> dict:
    """Assemble a version-1 scan-manifest dict ready to serialize as JSON.

    Pass either ``files_bytes`` (collect() output) or ``files`` (path/sha256/size
    entries). ``focus_files`` defaults to ``[]``; callers should pass the result
    of ``resolve_focus_files`` for commit/staged scopes.
    """
    if scope not in SCOPES:
        raise ValueError(f"scope inválido: {scope!r}; use commit, staged o full")
    if not commit or not isinstance(commit, str):
        raise ValueError("commit debe ser un SHA no vacío.")
    if not branch or not isinstance(branch, str):
        raise ValueError("branch debe ser un nombre de rama no vacío.")
    if files_bytes is not None and files is not None:
        raise ValueError("Pasa files_bytes o files, no ambos.")
    if files_bytes is None and files is None:
        raise ValueError("Se requiere files_bytes o files para el inventory.")
    inventory = (
        _inventory_from_bytes(files_bytes)
        if files_bytes is not None
        else _inventory_from_entries(files)
    )
    focus = _sorted_paths(focus_files or ())
    if scope == "full" and focus:
        raise ValueError("scope full exige focus_files vacío.")
    return {
        "version": 1,
        "scope": scope,
        "commit": commit,
        "branch": branch,
        "focus_files": focus,
        "files": inventory,
    }


def encode_scan_manifest(manifest: dict | bytes) -> bytes:
    """Serialize a scan-manifest dict to UTF-8 JSON bytes, or pass bytes through."""
    if isinstance(manifest, bytes):
        return manifest
    if not isinstance(manifest, dict):
        raise ValueError("scan_manifest debe ser dict o bytes.")
    return json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode()
