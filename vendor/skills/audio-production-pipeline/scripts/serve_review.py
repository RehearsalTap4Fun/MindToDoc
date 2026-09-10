#!/usr/bin/env python3
"""Serve review pages and build validated audio-production handoff packages."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from audio_sheet_workbook import validate_sheet_name
from company_audio_api import DEFAULT_BASE_URL, generate_sound, load_token, missing_token_message
from workspace_paths import find_workspace_root


class ReviewHandler(SimpleHTTPRequestHandler):
    workspace: Path

    def __init__(self, *args, workspace: Path, **kwargs) -> None:
        self.workspace = workspace
        super().__init__(*args, **kwargs)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 5 * 1024 * 1024:
            raise ValueError("request body must be between 1 byte and 5 MB")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def run_script(self, script: str, *arguments: str) -> dict[str, object]:
        path = Path(__file__).with_name(script)
        result = subprocess.run(
            [sys.executable, str(path), *arguments],
            cwd=self.workspace,
            capture_output=True,
            text=True,
        )
        return {
            "script": script,
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }

    @staticmethod
    def safe_component(value: object, fallback: str = "audio") -> str:
        text = str(value or "").strip() or fallback
        return "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in text)[:120]

    def ai_status_url(self, job_id: str) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/api/ai-gap/status/{job_id}"

    def generate_ai_job(self, job_id: str, row: dict[str, object]) -> None:
        jobs = self.server.ai_jobs
        jobs[job_id] = {"status": "running", "message": "生成中", "ai_candidates": []}
        try:
            sheet_name = validate_sheet_name(str(row.get("sheet_name") or "").strip())
            asset = self.safe_component(row.get("asset_name") or row.get("event_name"), "audio")
            prompt = str(row.get("prompt_en") or "").strip()
            if not prompt:
                raise ValueError("missing prompt_en")
            variants = int(row.get("variants_needed") or 3)
            variants = max(1, min(variants, 8))
            duration = float(row.get("duration") or 0)
            prod = self.workspace / ".gdconfig_tmp" / "output" / "audio" / "production" / sheet_name
            if not prod.is_dir():
                raise FileNotFoundError(f"production directory not found: {prod}")
            if shutil.which(self.server.args.ffmpeg) is None:
                raise FileNotFoundError(f"ffmpeg not found: {self.server.args.ffmpeg}")
            token = load_token(self.server.args.config_dir)
            if not token:
                raise RuntimeError(missing_token_message())

            outputs: list[dict[str, object]] = []
            asset_dir = prod / "ai_candidates" / asset
            for variant in range(1, variants + 1):
                jobs[job_id] = {
                    **jobs[job_id],
                    "status": "running",
                    "message": f"生成中 {variant}/{variants}",
                    "ai_candidates": outputs,
                }
                source = asset_dir / f"{asset}_ai_{job_id}_{variant:02d}.source.mp3"
                target = asset_dir / f"{asset}_ai_{job_id}_{variant:02d}.wav"
                generate_sound(
                    prompt,
                    base_url=self.server.args.base_url,
                    token=token,
                    output_path=source,
                    duration_seconds=duration,
                    prompt_influence=self.server.args.prompt_influence,
                )
                target.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run([
                    self.server.args.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(source), "-vn", "-acodec", "pcm_s16le", str(target),
                ], check=True)
                rel = target.relative_to(prod).as_posix()
                outputs.append({
                    "candidate_id": f"ai:{asset}:{job_id}:{variant:02d}",
                    "candidate_type": "ai",
                    "provider": "company_api",
                    "asset_name": asset,
                    "filename": target.name,
                    "variant": variant,
                    "output_path": rel,
                    "local_preview_url": rel,
                    "status": "generated",
                    "match_score": 70,
                    "final_score": 70,
                    "match_reasons": "公司 API 实时生成；待正式评分脚本复核。",
                })
                if self.server.args.delay:
                    time.sleep(self.server.args.delay)

            manifest_path = prod / "ai_candidate_manifest.json"
            existing: dict[str, object] = {"sheetName": sheet_name, "candidates": []}
            if manifest_path.exists():
                try:
                    loaded = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
                    if isinstance(loaded, dict):
                        existing = loaded
                except Exception:
                    pass
            candidates = existing.get("candidates")
            if not isinstance(candidates, list):
                candidates = []
            candidates.extend(outputs)
            existing["sheetName"] = sheet_name
            existing["candidates"] = candidates
            manifest_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            jobs[job_id] = {"status": "done", "message": "完成", "ai_candidates": outputs, "outputs": outputs}
        except Exception as exc:
            jobs[job_id] = {"status": "failed", "message": "失败", "error": str(exc), "ai_candidates": []}

    def start_ai_generation(self, payload: dict[str, object]) -> None:
        job_id = uuid.uuid4().hex[:12]
        self.server.ai_jobs[job_id] = {"status": "queued", "message": "已入队", "ai_candidates": []}
        thread = threading.Thread(target=self.generate_ai_job, args=(job_id, payload), daemon=True)
        thread.start()
        self.send_json(202, {
            "ok": True,
            "status": "queued",
            "job_id": job_id,
            "status_url": self.ai_status_url(job_id),
        })

    @staticmethod
    def incomplete_decisions(
        decisions: list[dict[str, object]],
        required_rows: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        incomplete: list[dict[str, str]] = []
        provided_events = {
            str(row.get("event_name") or row.get("eventName") or "").strip()
            for row in decisions
        }
        for required in required_rows:
            event = required.get("event_name", "").strip()
            if required.get("demand_tag") == "新增" and event not in provided_events:
                incomplete.append({
                    "event": event,
                    "asset": required.get("asset_name", "").strip(),
                    "reason": "页面未提交该新增事件的判断",
                })
        for row in decisions:
            event = str(row.get("event_name") or row.get("eventName") or "").strip()
            asset = str(row.get("asset_name") or row.get("assetName") or "").strip()
            tag = str(row.get("demand_tag") or "").strip()
            decision = str(row.get("event_decision") or row.get("decision") or "").strip()
            selected = str(row.get("selected_candidate_id") or "").strip()
            if tag in {"复用", "沿用X1"}:
                continue
            reason = ""
            if decision == "modify_use":
                reason = "已标记改后用，需先完成修改"
            elif decision in {"reject", "ai_needed", "auto_ai", ""}:
                reason = "尚未选定最终可用候选"
            elif decision != "direct_use":
                reason = f"不支持的最终决策: {decision}"
            elif not selected:
                reason = "已标记直接用，但未选中候选"
            if reason:
                incomplete.append({"event": event, "asset": asset, "reason": reason})
        return incomplete

    def build_production_package(self, payload: dict[str, object]) -> None:
        sheet_name = validate_sheet_name(str(payload.get("sheet_name") or "").strip())
        decisions = payload.get("decisions")
        if not isinstance(decisions, list) or not decisions:
            raise ValueError("decisions must be a non-empty array")
        if not all(isinstance(row, dict) for row in decisions):
            raise ValueError("every decision must be an object")

        prod = self.workspace / ".gdconfig_tmp" / "output" / "audio" / "production" / sheet_name
        if not prod.is_dir():
            raise FileNotFoundError(f"production directory not found: {prod}")
        decisions_path = prod / "planner_decisions.json"
        decisions_path.write_text(
            json.dumps({"decisions": decisions}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        master_path = prod / "audio_demand_master.csv"
        with master_path.open(encoding="utf-8-sig", newline="") as handle:
            required_rows = list(csv.DictReader(handle))
        incomplete = self.incomplete_decisions(decisions, required_rows)
        if incomplete:
            self.send_json(422, {
                "ok": False,
                "status": "decisions_saved_but_incomplete",
                "message": "已保存策划判断，但还不能生成最终交付包。",
                "decisions": str(decisions_path.relative_to(self.workspace)),
                "incomplete": incomplete,
            })
            return

        common = ["--sheet-name", sheet_name, "--workspace-root", str(self.workspace)]
        steps = [
            self.run_script("apply_planner_decisions.py", *common, "--decisions", str(decisions_path)),
            self.run_script("convert_wav_to_ogg.py", "--sheet-name", sheet_name),
            self.run_script("validate_production_package.py", *common, "--stage", "handoff-ready"),
        ]
        ok = all(bool(step["ok"]) for step in steps)
        manifest_path = prod / "final_package_manifest.json"
        manifest = {
            "sheetName": sheet_name,
            "status": "handoff_ready" if ok else "blocked",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "plannerDecisions": str(decisions_path.relative_to(self.workspace)),
            "audioSheet": ".gdconfig_tmp/output/audio/audio_sheet.xlsx",
            "audioRoot": "audio",
            "steps": steps,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.send_json(200 if ok else 422, {
            "ok": ok,
            "status": manifest["status"],
            "message": "音频交付包已生成并通过校验。" if ok else "决策已应用，但交付校验未通过。",
            "artifacts": {
                "decisions": str(decisions_path.relative_to(self.workspace)),
                "audio_sheet": ".gdconfig_tmp/output/audio/audio_sheet.xlsx",
                "final_manifest": str(manifest_path.relative_to(self.workspace)),
                "audio_root": "audio/",
            },
            "steps": steps,
        })

    def do_POST(self) -> None:
        if self.path == "/api/ai-gap/generate":
            try:
                self.start_ai_generation(self.read_json())
            except Exception as exc:
                self.send_json(400, {"ok": False, "status": "request_error", "error": str(exc)})
            return
        if self.path != "/api/production-package/build":
            self.send_json(404, {"ok": False, "error": "not found"})
            return
        try:
            self.build_production_package(self.read_json())
        except Exception as exc:
            self.send_json(400, {"ok": False, "status": "request_error", "error": str(exc)})

    def do_GET(self) -> None:
        if self.path == "/api/ai-gap/generate":
            self.send_json(405, {
                "ok": False,
                "status": "method_not_allowed",
                "message": "This endpoint only accepts POST requests from the review page. Open the company_library_review.html page and click AI生成.",
            })
            return
        if self.path.startswith("/api/ai-gap/status/"):
            job_id = self.path.rsplit("/", 1)[-1]
            payload = self.server.ai_jobs.get(job_id)
            if not payload:
                self.send_json(404, {"ok": False, "status": "missing", "error": "Job not found."})
                return
            self.send_json(200, {"ok": True, **payload})
            return
        super().do_GET()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8791)
    parser.add_argument("--config-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--prompt-influence", type=float, default=0.3)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()
    workspace = args.workspace_root.resolve() if args.workspace_root else find_workspace_root()
    handler = partial(ReviewHandler, directory=str(workspace), workspace=workspace)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    server.args = args
    server.ai_jobs = {}
    print(f"Serving {workspace} at http://{args.host}:{args.port}")
    print(f"AI API: http://{args.host}:{args.port}/api/ai-gap/generate")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
