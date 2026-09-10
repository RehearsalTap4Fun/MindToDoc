#!/usr/bin/env python3
"""Resolve the portable X15 workspace layout used by audio pipeline scripts."""

from __future__ import annotations

from pathlib import Path


def looks_like_workspace_root(path: Path) -> bool:
    return (
        (path / ".gdconfig_tmp").is_dir()
        and (path / "audio").exists()
        and (path / "client").exists()
    )


def find_workspace_root(start: Path | None = None) -> Path:
    origins = [Path(__file__).resolve(), Path.cwd()]
    if start is not None:
        origins.insert(1, start)

    checked: set[Path] = set()
    for origin in origins:
        current = origin.resolve()
        if current.is_file():
            current = current.parent
        for candidate in [current, *current.parents]:
            if candidate in checked:
                continue
            checked.add(candidate)
            if looks_like_workspace_root(candidate):
                return candidate

    raise RuntimeError(
        "workspace root not found: expected .gdconfig_tmp, audio, and client under the same folder"
    )


def production_root(workspace: Path, sheet_name: str) -> Path:
    return workspace / ".gdconfig_tmp" / "output" / "audio" / "production" / sheet_name


def skill_root(workspace: Path) -> Path:
    return workspace / ".gdconfig_tmp" / ".agents" / "skills" / "audio-production-pipeline"
