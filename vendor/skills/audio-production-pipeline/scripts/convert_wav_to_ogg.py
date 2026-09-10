#!/usr/bin/env python3
"""Convert production WAV files referenced by audio_sheet.xlsx into audio repo OGG files."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from audio_sheet_workbook import read_workbook


ASSET_NAME_FIELD = "音效资源名"
SAFE_NAME_EXTRA_CHARS = {"_", "-"}


def looks_like_workspace_root(path: Path) -> bool:
    return (
        (path / ".gdconfig_tmp").is_dir()
        and (path / "client").is_dir()
        and (path / "audio").exists()
    )


def find_workspace_root(start: Path | None = None) -> Path:
    starts = [Path(__file__).resolve()]
    if start is not None:
        starts.append(start)
    starts.append(Path.cwd())

    checked: set[Path] = set()
    for origin in starts:
        current = origin.resolve()
        if current.is_file():
            current = current.parent

        for candidate in [current, *current.parents]:
            if candidate in checked:
                continue
            checked.add(candidate)
            if looks_like_workspace_root(candidate):
                return candidate

    raise RuntimeError("workspace root not found: expected .gdconfig_tmp, audio, and client under the same folder")


def default_workbook_path() -> Path:
    return find_workspace_root() / ".gdconfig_tmp" / "output" / "audio" / "audio_sheet.xlsx"


def default_audio_repo_root() -> Path:
    return find_workspace_root() / "audio"


def safe_dir_name(value: str) -> str:
    result = []
    for char in value.strip():
        if char in '\\/:*?"<>|':
            result.append("_")
        else:
            result.append(char)
    return "".join(result).strip(" .") or "sheet"


def default_wav_root(sheet_name: str) -> Path:
    return (
        find_workspace_root()
        / ".gdconfig_tmp"
        / "output"
        / "audio"
        / "production"
        / safe_dir_name(sheet_name)
        / "wav"
    )


def is_safe_asset_name(value: str) -> bool:
    if not value:
        return False

    for char in value:
        if char.isalnum() or char in SAFE_NAME_EXTRA_CHARS or "\u4e00" <= char <= "\u9fff":
            continue
        return False

    return True


def collect_asset_names(workbook: Path, sheet_name: str) -> list[str]:
    sheets = read_workbook(workbook)
    if sheet_name not in sheets:
        raise ValueError(f"sheet not found: {sheet_name}")

    rows = sheets[sheet_name]
    if not rows:
        raise ValueError(f"sheet is empty: {sheet_name}")

    headers = {name.strip(): index for index, name in enumerate(rows[0]) if name.strip()}
    if ASSET_NAME_FIELD not in headers:
        raise ValueError(f"sheet missing required column: {ASSET_NAME_FIELD}")

    asset_index = headers[ASSET_NAME_FIELD]
    result: list[str] = []
    seen: set[str] = set()
    for row in rows[1:]:
        asset_name = row[asset_index].strip() if asset_index < len(row) else ""
        if not asset_name:
            continue
        if asset_name in seen:
            continue
        if not is_safe_asset_name(asset_name):
            raise ValueError(f"unsafe asset name: {asset_name}")

        seen.add(asset_name)
        result.append(asset_name)

    return result


def find_source_wav(wav_root: Path, asset_name: str) -> Path | None:
    candidates = [
        wav_root / f"{asset_name}.wav",
        wav_root / f"{asset_name}.WAV",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    matches = [
        path
        for path in wav_root.rglob("*")
        if path.is_file() and path.suffix.lower() == ".wav" and path.stem == asset_name
    ]
    if len(matches) > 1:
        names = ", ".join(str(path) for path in matches)
        raise ValueError(f"multiple wav files found for {asset_name}: {names}")

    return matches[0] if matches else None


def convert_wav_to_ogg(ffmpeg: str, source: Path, target: Path, overwrite: bool) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.stem}.tmp.ogg")
    temporary.unlink(missing_ok=True)
    probe = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"],
        capture_output=True,
        text=True,
        check=False,
    )
    encoder_text = f"{probe.stdout}\n{probe.stderr}"
    encoders = []
    if " libvorbis " in encoder_text:
        encoders.append(["-c:a", "libvorbis", "-q:a", "5"])
    if " vorbis " in encoder_text:
        encoders.append(["-c:a", "vorbis", "-strict", "experimental", "-q:a", "5"])
    if not encoders:
        encoders = [
            ["-c:a", "libvorbis", "-q:a", "5"],
            ["-c:a", "vorbis", "-strict", "experimental", "-q:a", "5"],
        ]
    last_error: subprocess.CalledProcessError | None = None
    for encoder in encoders:
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(source), "-vn", *encoder, str(temporary),
        ]
        try:
            subprocess.run(command, check=True)
            temporary.replace(target)
            return
        except subprocess.CalledProcessError as exc:
            last_error = exc
            temporary.unlink(missing_ok=True)
    if last_error:
        raise last_error
    raise RuntimeError(f"no OGG encoder attempted for {source}")


def run(args: argparse.Namespace) -> int:
    sheet_name = args.sheet_name.strip()
    workbook = Path(args.workbook).resolve() if args.workbook else default_workbook_path()
    wav_root = Path(args.wav_root).resolve() if args.wav_root else default_wav_root(sheet_name)
    audio_repo_root = (
        Path(args.audio_repo_root).resolve()
        if args.audio_repo_root
        else default_audio_repo_root()
    )
    ffmpeg = args.ffmpeg

    if not sheet_name:
        raise ValueError("sheetName is required")
    if not workbook.exists():
        raise FileNotFoundError(f"workbook not found: {workbook}")
    if not wav_root.exists():
        raise FileNotFoundError(f"wav root not found: {wav_root}")
    if not audio_repo_root.exists():
        raise FileNotFoundError(f"audio repo root not found: {audio_repo_root}")
    if not args.dry_run and shutil.which(ffmpeg) is None:
        raise FileNotFoundError(f"ffmpeg not found: {ffmpeg}")

    asset_names = collect_asset_names(workbook, sheet_name)
    converted = 0
    skipped = 0
    missing = 0

    for asset_name in asset_names:
        target = audio_repo_root / f"{asset_name}.ogg"

        if target.exists() and not args.overwrite:
            print(f"skip existing: {target}")
            skipped += 1
            continue

        source = find_source_wav(wav_root, asset_name)
        if source is None:
            print(f"missing wav: {asset_name} ({wav_root})")
            missing += 1
            continue

        if args.dry_run:
            print(f"dry run: {source} -> {target}")
            converted += 1
            continue

        try:
            convert_wav_to_ogg(ffmpeg, source, target, args.overwrite)
            print(f"converted: {source} -> {target}")
            converted += 1
        except subprocess.CalledProcessError as exc:
            print(f"convert failed: {source} -> {target} ({exc})", file=sys.stderr)
            missing += 1

    print(f"summary: converted={converted}, skipped={skipped}, missingOrFailed={missing}")
    return 1 if missing else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert audio production WAV files to audio repo OGG files.")
    parser.add_argument("--sheet-name", required=True, help="audio_sheet.xlsx sheet name.")
    parser.add_argument("--workbook", default="", help="Path to audio_sheet.xlsx.")
    parser.add_argument("--wav-root", default="", help="Folder containing <音效资源名>.wav. Defaults to production/<sheetName>/wav.")
    parser.add_argument("--audio-repo-root", default="", help="Path to audio source repo.")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="ffmpeg executable.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing ogg files.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned conversions without running ffmpeg.")
    args = parser.parse_args()

    try:
        return run(args)
    except Exception as exc:
        print(f"convert wav to ogg failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
