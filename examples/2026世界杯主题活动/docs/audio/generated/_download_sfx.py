#!/usr/bin/env python3
"""Poll Meowa elevenlabs jobs and download SFX variants."""
import json
import re
import subprocess
import time
from pathlib import Path

API_KEY = "ma_live_ARONAwrVTCwIvRFbQq3kYZFSaLIHRVAQ"
BASE = "https://api.meowa.ai"
OUT = Path(r"C:\Project\MindToDoc\docs\audio\generated\sfx")
OUT.mkdir(parents=True, exist_ok=True)

PROMPT_TO_ID = {
    "Generic mobile game UI button tap click": "SFX_UI_CLICK",
    "UI selection highlight blip": "SFX_UI_SELECT",
    "Modal popup window appear": "SFX_UI_POPUP_OPEN",
    "Modal popup window close": "SFX_UI_POPUP_CLOSE",
    "UI toggle switch on": "SFX_UI_TOGGLE_ON",
    "UI toggle switch off": "SFX_UI_TOGGLE_OFF",
    "Soft error buzz, action denied": "SFX_UI_NEGATIVE",
    "Game pause menu open": "SFX_UI_PAUSE_OPEN",
    "Game resume, pause menu close": "SFX_UI_PAUSE_CLOSE",
    "Coin reward pop, bright chime": "SFX_REWARD_POP",
    "Soft whoosh transition into soccer kickoff": "SFX_SLICE_ENTER",
    "Mode locked confirm thunk": "SFX_MODE_LOCK",
    "Snappy rubber band release pop": "SFX_BALL_RELEASE",
    "Soccer ball kick impact on grass": "SFX_KICK",
    "Soccer ball hits goal net rustle swish": "SFX_SLICE_SUCCESS",
}


def api_get(path: str) -> dict:
    proc = subprocess.run(
        [
            "curl.exe", "--ssl-no-revoke", "-s",
            f"{BASE}{path}",
            "-H", f"Authorization: Bearer {API_KEY}",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return json.loads(proc.stdout)


def download(url: str, dest: Path) -> None:
    subprocess.run(
        ["curl.exe", "--ssl-no-revoke", "-sL", url, "-o", str(dest)],
        check=True,
    )


def guess_id(job: dict) -> str | None:
    result = job.get("result") or {}
    meta = result.get("metadata") or {}
    prompt = meta.get("raw_prompt") or meta.get("prompt") or ""
    for key, sfx_id in PROMPT_TO_ID.items():
        if key in prompt:
            return sfx_id
    name = result.get("job_name") or ""
    for key, sfx_id in PROMPT_TO_ID.items():
        slug = re.sub(r"[^a-z0-9]+", "_", key.lower())[:30]
        if slug.replace("_", "") in name.lower().replace("_", ""):
            return sfx_id
    return None


def main() -> None:
    target_ids = set(PROMPT_TO_ID.values())
    done: dict[str, dict] = {}
    pending: set[str] = set()

    for round_i in range(1, 91):
        data = api_get("/api/jobs?limit=25")
        items = [j for j in data.get("items", []) if j.get("job_id", "").startswith("workflow-elevenlabs_generator-")]
        for job in items:
            sfx_id = guess_id(job)
            if not sfx_id or sfx_id not in target_ids:
                continue
            status = job.get("status")
            if status in ("success", "failure", "cancelled"):
                done[sfx_id] = job
            else:
                pending.add(sfx_id)
        print(f"[poll {round_i}] done={len(done)}/{len(target_ids)} pending={len(pending)}")
        if len(done) >= len(target_ids):
            break
        pending = {i for i in target_ids if i not in done}
        if not pending:
            break
        time.sleep(10)

    manifest = []
    for sfx_id in sorted(target_ids):
        job = done.get(sfx_id)
        if not job:
            manifest.append({"id": sfx_id, "status": "missing"})
            print(f"MISSING: {sfx_id}")
            continue
        if job.get("status") != "success":
            manifest.append({"id": sfx_id, "status": job.get("status"), "job_id": job.get("job_id")})
            print(f"FAIL: {sfx_id} -> {job.get('status')}")
            continue
        result = job.get("result") or {}
        paths = result.get("audio_paths") or []
        if not paths and result.get("audio_path"):
            paths = [result["audio_path"]]
        files = []
        for idx, url in enumerate(paths, start=1):
            mp3 = OUT / f"{sfx_id}_v{idx:02d}.mp3"
            download(url, mp3)
            files.append(str(mp3))
            print(f"OK: {mp3.name}")
        manifest.append({"id": sfx_id, "status": "success", "job_id": job.get("job_id"), "files": files})

    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nManifest: {manifest_path}")
    ok = sum(1 for m in manifest if m.get("status") == "success")
    print(f"Downloaded: {ok}/{len(target_ids)} SFX groups")


if __name__ == "__main__":
    main()
