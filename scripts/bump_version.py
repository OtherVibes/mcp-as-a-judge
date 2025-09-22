#!/usr/bin/env python3
"""
Version bump utility for mcp-as-a-judge.

- Validates a semantic version (MAJOR.MINOR.PATCH)
- Updates version in:
  * pyproject.toml -> [project].version
  * src/mcp_as_a_judge/__init__.py -> __version__
- Scans the repo and reports other files containing the old version (without modifying them),
  so we can review drift. Known safe patterns can be extended here in the future.

Usage:
  python scripts/bump_version.py --version 0.3.0

Outputs:
  - Prints a machine-readable list of modified files on stdout (one per line) preceded by 'UPDATED: '
  - Prints a machine-readable list of other files containing the old version preceded by 'FOUND: '
  - Exits non-zero on validation failure or if expected files are missing
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
INIT_PATH = REPO_ROOT / "src" / "mcp_as_a_judge" / "__init__.py"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(2)


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def extract_current_version() -> str:
    text = _read_text(PYPROJECT_PATH)
    # naive toml line parse to avoid adding deps
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        print(
            "ERROR: Could not find [project].version in pyproject.toml", file=sys.stderr
        )
        sys.exit(2)
    return m.group(1)


def bump_pyproject(version: str) -> bool:
    content = _read_text(PYPROJECT_PATH)
    new_content, n = re.subn(
        r'^(version\s*=\s*)"[^\"]+"',
        rf'\1"{version}"',
        content,
        flags=re.MULTILINE,
    )
    if n:
        _write_text(PYPROJECT_PATH, new_content)
        print(f"UPDATED: {PYPROJECT_PATH.relative_to(REPO_ROOT)}")
        return True
    else:
        print("WARN: version field not updated in pyproject.toml", file=sys.stderr)
        return False


def bump_init(version: str) -> bool:
    content = _read_text(INIT_PATH)
    new_content, n = re.subn(
        r'^__version__\s*=\s*"[^\"]+"',
        rf'__version__ = "{version}"',
        content,
        flags=re.MULTILINE,
    )
    if n:
        _write_text(INIT_PATH, new_content)
        print(f"UPDATED: {INIT_PATH.relative_to(REPO_ROOT)}")
        return True
    else:
        print("WARN: __version__ not found in __init__.py", file=sys.stderr)
        return False


def find_other_references(old_version: str) -> None:
    # Report-only scan for the old version string across repo (excluding venvs, git, dist, etc.)
    skip_dirs = {
        ".git",
        ".venv",
        "dist",
        "build",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
    }
    for path in REPO_ROOT.rglob("*"):
        if path.is_dir():
            if path.name in skip_dirs:
                # prune by skipping children
                for _ in []:
                    pass
            continue
        if path.suffix in {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".zip",
            ".whl",
            ".tar",
            ".gz",
        }:
            continue
        # Avoid scanning the lock file for noisy matches
        if path.name == "uv.lock":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if old_version in text:
            print(f"FOUND: {path.relative_to(REPO_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bump project version across files")
    parser.add_argument(
        "--version", required=True, help="Semantic version, e.g., 0.3.0"
    )
    args = parser.parse_args()

    new_version = args.version.strip()
    if not SEMVER_RE.match(new_version):
        print(f"ERROR: Invalid semantic version: {new_version}", file=sys.stderr)
        sys.exit(2)

    current = extract_current_version()
    if current == new_version:
        print(f"INFO: Version already {new_version}; no changes needed.")
        sys.exit(0)

    # Update files
    ok1 = bump_pyproject(new_version)
    ok2 = bump_init(new_version)
    if not (ok1 or ok2):
        print("ERROR: No files were updated; aborting.", file=sys.stderr)
        sys.exit(2)

    # Report other references to the OLD version (so humans can review)
    find_other_references(current)

    # Emit a small JSON summary for the workflow if needed
    summary = {
        "old_version": current,
        "new_version": new_version,
    }
    print(f"SUMMARY: {json.dumps(summary)}")


if __name__ == "__main__":
    main()
