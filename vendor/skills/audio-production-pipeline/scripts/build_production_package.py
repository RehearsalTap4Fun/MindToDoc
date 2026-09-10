#!/usr/bin/env python3
"""Build deterministic production artifacts from an approved audio demand JSON."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from audio_sheet_workbook import ensure_sheet, upsert_rows, validate_sheet_name
from workspace_paths import find_workspace_root, production_root


VALID_TAGS = {"新增", "复用", "沿用X1"}
VALID_SOUND_TYPES = {"UI一次性", "2D音效", "3D音效", "Sfx循环", "3D循环", "环境循环", "音乐循环", "语音"}
MASTER_FIELDS = [
    "request_id", "project", "source_file", "source_sheet", "section",
    "event_name", "asset_name", "demand_tag", "description_cn", "resource_bank",
    "trigger_timing", "priority", "loop", "stop_event_needed", "company_library_first",
    "library_search_queries", "reuse_strategy", "ai_needed_after_library_review",
    "prompt_en", "review_status", "program_integration_target", "notes",
]
REVIEW_COLUMNS = [
    "序号", "事件名", "音效资源名", "生产状态", "功能模块", "描述", "触发时机", "优先级",
    "是否循环", "需StopEvent", "触发点是否合理", "命名/资源是否合理",
    "新增/复用是否合理", "Loop/StopEvent是否合理", "策划审核结论", "策划审核意见",
]


def write_planner_review_workbook(path: Path, sheet_name: str, rows: list[dict[str, Any]]) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "策划逐行审核"

    header_fill = PatternFill("solid", fgColor="4472C4")
    pass_fill = PatternFill("solid", fgColor="E2F0D9")
    pending_fill = PatternFill("solid", fgColor="FFF2CC")
    side = Side(style="thin", color="BBBBBB")
    border = Border(left=side, right=side, top=side, bottom=side)

    title = ws.cell(row=1, column=1, value=f"{sheet_name} 策划音效需求逐行审核")
    title.font = Font(name="微软雅黑", size=13, bold=True, color="1F3864")
    title.alignment = Alignment(vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(REVIEW_COLUMNS))
    ws.row_dimensions[1].height = 24

    widths = [8, 34, 30, 10, 18, 42, 42, 8, 10, 12, 16, 18, 18, 20, 14, 42]
    for ci, (name, width) in enumerate(zip(REVIEW_COLUMNS, widths), 1):
        ws.column_dimensions[get_column_letter(ci)].width = width
        cell = ws.cell(row=2, column=ci, value=name)
        cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    for index, row in enumerate(rows, 1):
        loop = str(row.get("loop") or "").upper()
        stop = str(row.get("stop_event_needed") or "").upper()
        tag = str(row.get("demand_tag") or "")
        loop_check = "通过" if loop != "TRUE" or stop == "TRUE" else "需修改"
        reuse_check = "通过" if row.get("reuse_strategy") != "reuse_unverified" else "需确认"
        values = [
            index,
            row.get("event_name", ""),
            row.get("asset_name", ""),
            tag,
            row.get("resource_bank", ""),
            row.get("description_cn", ""),
            row.get("trigger_timing", ""),
            row.get("priority", ""),
            row.get("loop", ""),
            row.get("stop_event_needed", ""),
            "待审核",
            "待审核",
            reuse_check,
            loop_check,
            "待审核",
            "",
        ]
        excel_row = index + 2
        for ci, value in enumerate(values, 1):
            cell = ws.cell(row=excel_row, column=ci, value=value)
            cell.font = Font(name="微软雅黑", size=10)
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            cell.border = border
            if ci in {11, 12, 13, 14, 15}:
                cell.fill = pass_fill if value == "通过" else pending_fill
        ws.row_dimensions[excel_row].height = 42

    ws.freeze_panes = "B3"

    summary = wb.create_sheet("审核说明")
    summary.column_dimensions["A"].width = 26
    summary.column_dimensions["B"].width = 80
    summary_rows = [
        ("状态", "pending_planner_review"),
        ("审核对象", "音效需求是否拆得准确,不是试听候选是否合适。"),
        ("通过标准", "触发点合理、命名/资源合理、新增/复用判断合理、Loop/StopEvent 合理。"),
        ("通过后", "再把 planner_demand_review.json.status 改为 approved,进入公司库检索和后续 AI 缺口流程。"),
    ]
    for ri, (key, value) in enumerate(summary_rows, 1):
        summary.cell(row=ri, column=1, value=key).font = Font(name="微软雅黑", bold=True)
        summary.cell(row=ri, column=2, value=value).font = Font(name="微软雅黑")
        for ci in (1, 2):
            summary.cell(row=ri, column=ci).alignment = Alignment(wrap_text=True, vertical="center")
            summary.cell(row=ri, column=ci).border = border

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def demand_rows(data: dict[str, Any], sheet_name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    matches = [sheet for sheet in data.get("sheets", []) if sheet.get("name") == sheet_name]
    if len(matches) != 1:
        raise ValueError(f"demand JSON must contain exactly one sheet named {sheet_name}")
    sheet = matches[0]
    rows = [row for row in sheet.get("rows", []) if row.get("type") not in {"module", "submod"}]
    if not rows:
        raise ValueError(f"demand sheet is empty: {sheet_name}")
    return sheet, rows


def normalize_bool(value: Any) -> str:
    return "TRUE" if str(value).strip().upper() in {"1", "TRUE", "YES", "Y"} else "FALSE"


def sound_type(row: dict[str, Any]) -> str:
    explicit = str(row.get("sound_type") or row.get("声音类型") or "").strip()
    if explicit:
        if explicit not in VALID_SOUND_TYPES:
            raise ValueError(f"invalid sound type for {row.get('event')}: {explicit}")
        return explicit
    if normalize_bool(row.get("loop")) == "TRUE":
        return "3D循环" if row.get("t") == "3D" else "Sfx循环"
    return "3D音效" if row.get("t") == "3D" else "UI一次性"


def library_queries(row: dict[str, Any]) -> list[str]:
    raw = row.get("library_queries") or row.get("library_search_queries") or []
    if isinstance(raw, str):
        values = [part.strip() for part in raw.split("|") if part.strip()]
    else:
        values = [str(part).strip() for part in raw if str(part).strip()]
    if values:
        return values
    prompt = str(row.get("prompt") or row.get("prompt_en") or "").strip()
    asset = str(row.get("asset") or "").replace("_", " ")
    return [prompt or asset]


def reuse_verified(row: dict[str, Any], workspace: Path, asset: str) -> bool:
    """A reuse tag is valid only when the final X15 OGG already exists."""
    return (workspace / "audio" / f"{asset}.ogg").exists()


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demand-json", type=Path, required=True)
    parser.add_argument("--sheet-name", required=True)
    parser.add_argument("--source", default="")
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--skip-demand-xlsx", action="store_true")
    args = parser.parse_args()

    workspace = args.workspace_root.resolve() if args.workspace_root else find_workspace_root()
    sheet_name = validate_sheet_name(args.sheet_name.strip())
    data = json.loads(args.demand_json.read_text(encoding="utf-8-sig"))
    sheet, rows = demand_rows(data, sheet_name)
    prod = production_root(workspace, sheet_name)
    (prod / "wav").mkdir(parents=True, exist_ok=True)
    (prod / "company_library_previews").mkdir(parents=True, exist_ok=True)
    (prod / "ai_candidates").mkdir(parents=True, exist_ok=True)

    seen_events: set[str] = set()
    asset_tags: dict[str, str] = {}
    event_tags: dict[str, str] = {}
    verified_reuse_events: set[str] = set()
    config_rows: list[dict[str, Any]] = []
    master_rows: list[dict[str, Any]] = []
    search_rows: list[dict[str, Any]] = []
    sound_rows: list[dict[str, Any]] = []
    ai_rows: list[dict[str, Any]] = []

    for index, row in enumerate(rows, 1):
        event = str(row.get("event") or "").strip()
        asset = str(row.get("asset") or "").strip()
        tag = str(row.get("tag") or "").strip()
        if not event or not asset:
            raise ValueError(f"row {index} requires event and asset")
        if event in seen_events:
            raise ValueError(f"duplicated event: {event}")
        if tag not in VALID_TAGS:
            raise ValueError(f"invalid tag for {event}: {tag}")
        if tag == "新增":
            asset_tags[asset] = "新增"
        else:
            asset_tags.setdefault(asset, tag)
            if reuse_verified(row, workspace, asset):
                verified_reuse_events.add(event)
        event_tags[event] = tag
        seen_events.add(event)

        loop = normalize_bool(row.get("loop"))
        stop = normalize_bool(row.get("stop_event_needed"))
        if loop == "TRUE" and stop != "TRUE":
            raise ValueError(f"loop row must require StopEvent: {event}")
        request_id = str(row.get("request_id") or f"{sheet_name}-{index:03d}")
        queries = library_queries(row)
        config_row = {
            "事件名": event,
            "音效资源名": asset,
            "功能模块": str(row.get("module") or row.get("bank") or "").strip(),
            "声音类型": sound_type(row),
            "描述": str(row.get("desc") or "").strip(),
            "触发时机": str(row.get("trigger") or "").strip(),
            "生产状态": tag,
            "优先级": str(row.get("priority") or "P1"),
            "是否循环": loop,
            "需StopEvent": stop,
            "资源状态": "pending_company_library" if tag == "新增" else "reuse_verified" if event in verified_reuse_events else "reuse_unverified",
        }
        for key in ("淡入秒数", "淡出秒数", "音量", "最大实例数", "空间混合", "最小距离", "最大距离"):
            if key in row:
                config_row[key] = row[key]
        config_rows.append(config_row)

        master_rows.append({
            "request_id": request_id, "project": data.get("project", "X15"),
            "source_file": args.source, "source_sheet": sheet_name,
            "section": str(row.get("section") or row.get("bank") or ""),
            "event_name": event, "asset_name": asset, "demand_tag": tag,
            "description_cn": config_row["描述"], "resource_bank": config_row["功能模块"],
            "trigger_timing": config_row["触发时机"], "priority": config_row["优先级"],
            "loop": loop, "stop_event_needed": stop, "company_library_first": "TRUE",
            "library_search_queries": " | ".join(queries),
            "reuse_strategy": "company_library_first_then_ai_gap" if tag == "新增" else "reuse_verified" if event in verified_reuse_events else "reuse_unverified",
            "ai_needed_after_library_review": "PENDING_AFTER_LIBRARY_REVIEW" if tag == "新增" else "FALSE",
            "prompt_en": str(row.get("prompt") or row.get("prompt_en") or ""),
            "review_status": "not_reviewed", "program_integration_target": config_row["功能模块"],
            "notes": str(row.get("notes") or ""),
        })

    for config_row in config_rows:
        asset = str(config_row.get("音效资源名") or "")
        event = str(config_row.get("事件名") or "")
        if event_tags.get(event) != "新增" and asset_tags.get(asset) == "新增":
            config_row["资源状态"] = "reuse_generated_in_current_sheet"
    for master in master_rows:
        asset = str(master.get("asset_name") or "")
        event = str(master.get("event_name") or "")
        if event_tags.get(event) != "新增" and asset_tags.get(asset) == "新增":
            master["reuse_strategy"] = "reuse_generated_in_current_sheet"

    unique_assets: dict[str, dict[str, Any]] = {}
    for master in master_rows:
        asset = master["asset_name"]
        current = unique_assets.get(asset)
        if current is None:
            unique_assets[asset] = master
            continue
        if master["demand_tag"] == "新增" and current["demand_tag"] != "新增":
            unique_assets[asset] = master
            continue
        if master["demand_tag"] == "新增" and current["demand_tag"] == "新增":
            current_has_prompt = bool(str(current.get("prompt_en") or "").strip())
            master_has_prompt = bool(str(master.get("prompt_en") or "").strip())
            current_has_queries = bool(str(current.get("library_search_queries") or "").strip())
            master_has_queries = bool(str(master.get("library_search_queries") or "").strip())
            if (master_has_prompt and not current_has_prompt) or (master_has_queries and not current_has_queries):
                unique_assets[asset] = master

    for asset, master in unique_assets.items():
        tag = asset_tags[asset]
        queries = [q.strip() for q in master["library_search_queries"].split("|") if q.strip()]
        sound_rows.append({
            "assetName": asset, "tag": tag, "reuse": tag != "新增",
            "reuseVerified": False if tag != "新增" else None,
            "promptProfile": "", "acoustic": master["description_cn"],
            "avoid": [], "duration": "loop" if master["loop"] == "TRUE" else "short",
        })
        if tag != "新增":
            continue
        for rank, query in enumerate(queries, 1):
            search_rows.append({
                "request_id": master["request_id"], "event_name": master["event_name"],
                "asset_name": asset, "query_rank": rank, "library_query": query,
                "search_status": "pending", "top_candidates_json": "", "planner_decision": "",
            })
        ai_rows.append({
            "音效资源名": asset, "prompt": master["prompt_en"], "avoid": "",
            "duration": "loop" if master["loop"] == "TRUE" else "short",
            "status": "blocked_pending_company_library_review", "priority": master["priority"],
        })

    demand_xlsx = prod / "audio_demand.xlsx"
    if not args.skip_demand_xlsx:
        generator = Path(__file__).with_name("generate_audio_demand_workbook.py")
        subprocess.run([sys.executable, str(generator), str(demand_xlsx), str(args.demand_json)], check=True)

    rows_json = prod / "audio_sheet_rows.json"
    rows_json.write_text(json.dumps(config_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    workbook = workspace / ".gdconfig_tmp" / "output" / "audio" / "audio_sheet.xlsx"
    ensure_sheet(workbook, sheet_name)
    upsert_rows(workbook, sheet_name, rows_json, "事件名")

    write_csv(prod / "audio_demand_master.csv", master_rows, MASTER_FIELDS)
    write_csv(prod / "company_library_search_plan.csv", search_rows, [
        "request_id", "event_name", "asset_name", "query_rank", "library_query",
        "search_status", "top_candidates_json", "planner_decision",
    ])
    write_csv(prod / "ai_gap_queue.csv", ai_rows, ["音效资源名", "prompt", "avoid", "duration", "status", "priority"])
    review_status = {
        "sheetName": sheet_name,
        "status": "pending_planner_review",
        "reviewer": "",
        "approvedAt": "",
        "notes": "",
        "mustReviewBefore": [
            "company_library_search",
            "company_library_preview_download",
            "ai_generation",
            "candidate_review_page",
            "handoff",
        ],
        "checklist": [
            "是否漏拆玩家能听到的关键触发点",
            "普通 UI 反馈是否正确复用,有没有过度新增或模拟复用",
            "新增/复用/沿用X1 判断是否符合本期制作范围",
            "复用/沿用X1 是否已有真实 X15/公司资源来源,没有则改为新增通用资产",
            "Event/Asset 命名是否能给程序和音频端直接使用",
            "Loop 行是否标了 StopEvent",
            "Prompt/描述是否符合策划想要的表现方向",
            "优先级是否合理",
        ],
    }
    (prod / "planner_demand_review.json").write_text(
        json.dumps(review_status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (prod / "planner_demand_review.md").write_text(
        f"# {sheet_name} 策划音效需求审核\n\n"
        "状态: pending_planner_review\n\n"
        "请先审核 `planner_demand_review.xlsx` 或 `audio_demand.xlsx` 的逐行内容,"
        "确认需求拆分准确后再进入公司库检索、AI 生成和候选试听。\n\n"
        "## 必查项\n\n"
        "- 是否漏拆玩家能听到的关键触发点。\n"
        "- 普通 UI 反馈是否正确复用,有没有过度新增。\n"
        "- `复用/沿用X1` 是否已有真实 X15/公司资源来源;没有则改为 `新增` 通用资产。\n"
        "- `新增/复用/沿用X1` 判断是否符合本期制作范围。\n"
        "- Event/Asset 命名是否能给程序和音频端直接使用。\n"
        "- Loop 行是否标了 StopEvent。\n"
        "- Prompt/描述是否符合策划想要的表现方向。\n"
        "- 优先级是否合理。\n\n"
        "## 确认方式\n\n"
        "确认后把 `planner_demand_review.json` 里的 `status` 改为 `approved`,"
        "并填写 `reviewer`、`approvedAt`、`notes`。\n",
        encoding="utf-8",
    )
    write_planner_review_workbook(prod / "planner_demand_review.xlsx", sheet_name, master_rows)
    (prod / "sheet.meta.json").write_text(json.dumps({
        "sheetName": sheet_name, "safeDirName": sheet_name,
        "generatedAt": datetime.now(timezone.utc).isoformat(), "source": args.source,
        "rowCount": len(config_rows), "assetCount": len(unique_assets),
        "demandReviewStatus": "pending_planner_review",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (prod / "sound_design.json").write_text(json.dumps({"resources": sound_rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (prod / "planner_decisions.json").write_text('{"decisions": []}\n', encoding="utf-8")
    (prod / "company_library_review_manifest.json").write_text(json.dumps({
        "sheetName": sheet_name, "status": "pending_company_library_search", "events": [],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (prod / "company_library_preview_map.json").write_text("{}\n", encoding="utf-8")
    (prod / "company_library_search_results.json").write_text("[]\n", encoding="utf-8")
    write_csv(prod / "company_library_candidates.csv", [], [
        "request_id", "event_name", "asset_name", "query_rank", "library_query",
        "candidate_id", "filename", "duration_sec", "source_path",
    ])
    write_csv(prod / "planner_feedback.csv", [], [
        "request_id", "asset_name", "event_name", "candidate_id", "candidate_type",
        "source_path", "feedback", "decision", "note",
    ])
    (prod / "audio_preference_profiles.json").write_text("{}\n", encoding="utf-8")
    (prod / "decision_application_manifest.json").write_text(json.dumps({
        "sheetName": sheet_name, "status": "pending", "applied": [],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (prod / "ai_candidate_manifest.json").write_text(json.dumps({
        "sheetName": sheet_name, "status": "pending", "candidates": [],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (prod / "company_library_review.html").write_text(
        "<!doctype html><meta charset=\"utf-8\"><title>Pending company library search</title>"
        "<h1>Pending company library search</h1><p>Run the bundled search/download/review scripts.</p>",
        encoding="utf-8",
    )
    (prod / "final_package_manifest.json").write_text(json.dumps({
        "sheetName": sheet_name, "status": "prepared",
        "newAssets": [a for a, tag in asset_tags.items() if tag == "新增"],
        "reuseAssets": [a for a, tag in asset_tags.items() if tag != "新增"],
        "pendingWav": [f"wav/{a}.wav" for a, tag in asset_tags.items() if tag == "新增"],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (prod / "summary.md").write_text(
        f"# {sheet_name}\n\n已拆分 {len(config_rows)} 个事件 / {len(unique_assets)} 个资源。\n\n"
        f"新增资源: {sum(tag == '新增' for tag in asset_tags.values())}\n\n"
        f"复用/沿用资源: {sum(tag != '新增' for tag in asset_tags.values())}\n\n"
        "当前阶段: prepared; 等待公司库检索与策划评审。\n",
        encoding="utf-8",
    )
    print(f"prepared {sheet_name}: events={len(config_rows)} assets={len(unique_assets)} searches={len(search_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
