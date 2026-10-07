"""Select immutable working-tree bytes without executing project code."""

import hashlib
import io
import json
import os
import subprocess
import tarfile
from pathlib import Path

EXCLUDED_DIRS = {
    ".titvo",
    ".tmp",
    ".agents",
    ".codex",
    ".claude",
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".venv",
    "venv",
    ".cache",
    "coverage",
    "__pycache__",
    ".terraform",
    ".terragrunt-cache",
}
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 90 * 1024 * 1024


def collect(
    root: Path, include: list[str] | None = None
) -> tuple[dict[str, bytes], dict]:
    """Honor each initialized Git repository's ignores, including submodules."""
    root = root.resolve()
    scopes = [Path(part) for part in (include or [])]
    if any(part.is_absolute() or ".." in part.parts for part in scopes):
        raise ValueError("Include paths must be relative to the project")
    if not root.is_dir():
        raise ValueError(f"Project directory does not exist: {root}")
    candidates: dict[Path, list[Path]] = {}
    git_root = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    owner_root = Path(git_root.stdout.strip()) if git_root.returncode == 0 else root
    owners = {root: owner_root}
    excluded = []
    missing_submodules = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        current = Path(directory)
        owner = owners.get(current, root)
        if (current / ".git").exists():
            owner = current
            result = subprocess.run(
                ["git", "-C", str(current), "ls-files", "--stage", "-z"],
                capture_output=True,
                check=True,
            )
            for record in result.stdout.split(b"\0"):
                if record.startswith(b"160000 "):
                    subpath = os.fsdecode(record.split(b"\t", 1)[1])
                    if not (current / subpath / ".git").exists():
                        missing_submodules.append(
                            (current / subpath).relative_to(root).as_posix()
                        )
        for name in list(dirs):
            child = current / name
            if name in EXCLUDED_DIRS or name.startswith(".venv") or child.is_symlink():
                dirs.remove(name)
                excluded.append(
                    {
                        "path": child.relative_to(root).as_posix() + "/",
                        "reason": "dependency/build/link",
                    }
                )
            else:
                owners[child] = owner
        for name in names:
            path = current / name
            relative = path.relative_to(root).as_posix()
            if (
                name == ".git"
                or name.startswith(".env")
                or name == ".titvo-manifest.json"
                or name
                in {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock"}
            ):
                excluded.append(
                    {"path": relative, "reason": "metadata/environment/lockfile"}
                )
            elif path.is_symlink() or not path.is_file():
                excluded.append({"path": relative, "reason": "link/non-regular"})
            else:
                candidates.setdefault(owner, []).append(path)
    selected = {}
    for owner, paths in candidates.items():
        ignored = set()
        if (owner / ".git").exists():
            names = [path.relative_to(owner).as_posix() for path in paths]
            result = subprocess.run(
                ["git", "-C", str(owner), "check-ignore", "-z", "--stdin"],
                input=("\0".join(names) + "\0").encode(),
                capture_output=True,
            )
            if result.returncode not in (0, 1):
                raise ValueError(f"Unable to evaluate Git ignore rules in {owner}")
            ignored = {os.fsdecode(name) for name in result.stdout.split(b"\0") if name}
        for path in paths:
            relative = path.relative_to(root).as_posix()
            if scopes and not any(
                Path(relative) == part or part in Path(relative).parents
                for part in scopes
            ):
                excluded.append({"path": relative, "reason": "outside selected scope"})
                continue
            if path.relative_to(owner).as_posix() in ignored:
                excluded.append({"path": relative, "reason": "gitignore"})
                continue
            if path.stat().st_size > MAX_FILE_BYTES:
                excluded.append({"path": relative, "reason": "larger than 2 MiB"})
                continue
            data = path.read_bytes()
            try:
                if b"\0" in data:
                    raise UnicodeError()
                data.decode("utf-8")
            except UnicodeError:
                excluded.append({"path": relative, "reason": "binary/non-UTF-8"})
                continue
            selected[relative] = data
    if sum(map(len, selected.values())) > MAX_TOTAL_BYTES:
        raise ValueError("Selected snapshot exceeds 90 MiB")
    manifest = {
        "version": 1,
        "scope": [part.as_posix() for part in scopes],
        "project": root.name,
        "project_id": hashlib.sha256(str(root).encode()).hexdigest(),
        "files": [
            {
                "path": path,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for path, data in sorted(selected.items())
        ],
        "excluded": sorted(excluded, key=lambda item: item["path"]),
        "missing_submodules": sorted(set(missing_submodules)),
    }
    return selected, manifest


def package(files: dict[str, bytes], manifest: dict) -> bytes:
    """Create the existing CLI tar.gz format with an integrity manifest."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        entries = {
            **files,
            ".titvo-manifest.json": json.dumps(manifest, ensure_ascii=False).encode(),
        }
        for path, data in sorted(entries.items()):
            member = tarfile.TarInfo(path)
            member.size = len(data)
            member.mode = 0o600
            archive.addfile(member, io.BytesIO(data))
    return buffer.getvalue()
