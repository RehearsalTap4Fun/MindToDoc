#!/usr/bin/env python3
"""Batch generate 15 core SFX via Meowa elevenlabs_generator with per-ID duration."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = "https://api.meowa.ai"
OUT = Path(__file__).resolve().parent / "sfx_v2"

# (id, api_duration, prompt) — duration per Meowa API: 0.5 or int 1-10
SFX_LIST: list[tuple[str, float, str]] = [
    ("SFX_UI_CLICK", 0.5, "Generic mobile game UI button tap click, soft plastic button, neutral positive feedback, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix"),
    ("SFX_UI_SELECT", 0.5, "UI selection highlight blip, light tick pitch up, character picker feedback, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix"),
    ("SFX_UI_POPUP_OPEN", 0.5, "Modal popup window appear, soft whoosh upward, mobile game UI, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix"),
    ("SFX_UI_POPUP_CLOSE", 0.5, "Modal popup window close, soft whoosh downward, mobile game UI, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix"),
    ("SFX_UI_TOGGLE_ON", 0.5, "UI toggle switch on, high pitch blip, targeting enabled, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix"),
    ("SFX_UI_TOGGLE_OFF", 0.5, "UI toggle switch off, low pitch blip, targeting disabled, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix"),
    ("SFX_UI_NEGATIVE", 0.5, "Soft error buzz, action denied, insufficient resources, mobile game UI, not harsh alarm, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix"),
    ("SFX_UI_PAUSE_OPEN", 0.5, "Game pause menu open, soft pop, game paused state, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix"),
    ("SFX_UI_PAUSE_CLOSE", 0.5, "Game resume, pause menu close, soft pop, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix"),
    ("SFX_REWARD_POP", 0.5, "Coin reward pop, bright chime sparkle, loot item appear, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix"),
    ("SFX_SLICE_ENTER", 0.5, "Soft whoosh transition into soccer kickoff moment, subtle referee whistle hint in distance, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix"),
    ("SFX_MODE_LOCK", 0.5, "Mode locked confirm thunk, firm mechanical latch click with short positive tail, decisive UI commit, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix"),
    ("SFX_BALL_RELEASE", 0.5, "Snappy rubber band release pop with light whoosh, cartoon elastic snap, soccer mini game, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix"),
    ("SFX_KICK", 1, "Soccer ball kick impact on grass, crisp thump, outdoor stadium foley, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix"),
    ("SFX_SLICE_SUCCESS", 1, "Soccer ball hits goal net rustle swish plus short victory sting, brief crowd cheer burst, satisfying mobile soccer success, no vocals, no full music bed, clean mix"),
]

COUNT = 1  # 无变体，每条仅 1 份


def credits(duration: float, count: int = COUNT) -> float:
    return duration * count * 5


def curl_json(args: list[str]) -> dict:
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "curl failed")
    return json.loads(proc.stdout)


def submit(api_key: str, item: tuple[str, float, str]) -> str:
    sfx_id, duration, prompt = item
    dur = str(int(duration)) if duration == int(duration) and duration >= 1 else str(duration)
    args = [
        "curl.exe", "--ssl-no-revoke", "-s", "-X", "POST",
        f"{BASE}/api/workflows/elevenlabs_generator/run",
        "-H", f"Authorization: Bearer {api_key}",
        "-F", f"prompt={prompt}",
        "-F", f"duration={dur}",
        "-F", "variants=false",
        "-F", f"count={COUNT}",
        "-F", "normalize_volume=true",
        "-F", "temperature=0.3",
    ]
    data = curl_json(args)
    job_id = data.get("job_id")
    if not job_id:
        raise RuntimeError(f"Submit failed for {sfx_id}: {data}")
    return job_id


def poll_job(api_key: str, job_id: str, timeout_s: int = 600) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        data = curl_json([
            "curl.exe", "--ssl-no-revoke", "-s",
            f"{BASE}/api/jobs?id={job_id}",
            "-H", f"Authorization: Bearer {api_key}",
        ])
        status = data.get("status")
        if status in ("success", "failure", "cancelled"):
            return data
        time.sleep(8)
    raise TimeoutError(f"Job timeout: {job_id}")


def download_urls(urls: list[str], sfx_id: str) -> list[str]:
    files: list[str] = []
    for idx, url in enumerate(urls, start=1):
        dest = OUT / (f"{sfx_id}.mp3" if COUNT == 1 else f"{sfx_id}_v{idx:02d}.mp3")
        subprocess.run(["curl.exe", "--ssl-no-revoke", "-sL", url, "-o", str(dest)], check=True)
        files.append(str(dest))
        print(f"  saved {dest.name}")
    return files


def extract_urls(job: dict) -> list[str]:
    result = job.get("result") or {}
    urls = list(result.get("audio_paths") or [])
    if not urls and result.get("audio_path"):
        urls = [result["audio_path"]]
    return urls


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python batch_sfx_v2.py <API_KEY>")
        sys.exit(1)
    api_key = sys.argv[1].strip()
    OUT.mkdir(parents=True, exist_ok=True)

    total = sum(credits(d) for _, d, _ in SFX_LIST)
    print(f"Planned: {len(SFX_LIST)} SFX, 1 file each (no variants), ~{total:.0f} credits\n")

    jobs: list[dict] = []
    for item in SFX_LIST:
        sfx_id, duration, _ = item
        print(f"Submit {sfx_id} (duration={duration}, ~{credits(duration):.0f} cr)")
        job_id = submit(api_key, item)
        jobs.append({"id": sfx_id, "duration": duration, "job_id": job_id})
        time.sleep(1)

    (OUT / "jobs_submitted.json").write_text(json.dumps(jobs, indent=2), encoding="utf-8")

    manifest: list[dict] = []
    for entry in jobs:
        sfx_id = entry["id"]
        print(f"\nPoll {sfx_id} ...")
        job = poll_job(api_key, entry["job_id"])
        status = job.get("status")
        if status != "success":
            manifest.append({"id": sfx_id, "status": status, "job_id": entry["job_id"], "error": job.get("error")})
            print(f"  FAILED: {status} {job.get('error')}")
            continue
        urls = extract_urls(job)
        print(f"  download {len(urls)} files")
        files = download_urls(urls, sfx_id)
        manifest.append({"id": sfx_id, "status": "success", "duration": entry["duration"], "job_id": entry["job_id"], "files": files})

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    ok = sum(1 for m in manifest if m.get("status") == "success")
    print(f"\nDone: {ok}/{len(SFX_LIST)} -> {OUT}")


if __name__ == "__main__":
    main()
