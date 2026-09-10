#!/usr/bin/env python3
"""Build a planner review page for company library candidates."""

from __future__ import annotations

import csv
import json
import argparse
import os
from collections import defaultdict
from html import escape
from pathlib import Path
from urllib.parse import urlparse, urlunparse


API_BASE = os.environ.get("TAPPER_AUDIO_BASE_URL", "http://172.20.90.54:8001")
REVIEW_PAGE_CONTRACT_VERSION = "x15-planner-review-v1"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def normalize_download_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        base = urlparse(API_BASE)
        return urlunparse((base.scheme, base.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
    return url


def duration_float(value: str) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0


def load_preview_map(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def page_relative_preview_url(relative_path: str) -> str:
    if not relative_path:
        return ""
    clean = relative_path.lstrip("/")
    marker = "company_library_previews/"
    if marker in clean:
        return clean[clean.index(marker):]
    return clean


SCORING_RULES = [
    {
        "needs": ["水", "水箭", "海浪", "浪", "water", "wave", "surge", "splash"],
        "positive": ["water", "wave", "waves", "ocean", "sea", "surge", "splash", "stream", "river", "liquid", "foam", "tidal", "swirl", "whoosh", "impact", "hit", "boom", "low"],
        "negative": ["fire", "flame", "lava", "metal", "sword", "blade", "pixie", "electric", "ice", "wood", "stone", "ui", "click", "button", "creature", "roar"],
        "duration_min": 0.9,
        "duration_max": 4.5,
    },
    {
        "needs": ["火", "火焰", "熔岩", "fire", "flame", "lava"],
        "positive": ["fire", "flame", "lava", "burn", "ignite", "ember", "explosion", "impact", "whoosh", "burst"],
        "negative": ["water", "wave", "ice", "metal", "ui", "click", "button"],
        "duration_min": 0.4,
        "duration_max": 3.5,
    },
    {
        "needs": ["冰", "frost", "ice"],
        "positive": ["ice", "frost", "freeze", "crystal", "shard", "snow", "impact", "break"],
        "negative": ["fire", "flame", "lava", "water", "ui", "click"],
        "duration_min": 0.4,
        "duration_max": 3.5,
    },
    {
        "needs": ["雷", "电", "electric", "thunder", "lightning"],
        "positive": ["electric", "lightning", "thunder", "zap", "spark", "shock", "impact"],
        "negative": ["water", "fire", "ice", "ui", "click"],
        "duration_min": 0.3,
        "duration_max": 3.0,
    },
    {
        "needs": ["ui", "界面", "按钮", "点击", "弹窗", "click", "button", "popup"],
        "positive": ["ui", "click", "button", "tap", "popup", "open", "close", "select", "locked", "scroll", "chime"],
        "negative": ["battle", "war", "hero", "creature", "roar", "explosion", "cinematic"],
        "duration_min": 0.05,
        "duration_max": 1.5,
    },
]


def tokens(text: str) -> set[str]:
    lowered = text.lower().replace("_", " ").replace("-", " ")
    return {part for part in lowered.replace("/", " ").replace(".", " ").split() if part}


def keyword_matches(keyword: str, text: str, text_tokens: set[str]) -> bool:
    keyword = keyword.lower()
    if keyword.isascii():
        return keyword in text_tokens
    return keyword in text


def semantic_score(row: dict[str, str], item: dict[str, str], duration: float) -> dict[str, object]:
    demand_text = " ".join(
        [
            row.get("event_name", ""),
            row.get("asset_name", ""),
            row.get("description_cn", ""),
            row.get("trigger_timing", ""),
            row.get("prompt_en", ""),
        ]
    ).lower()
    demand_tokens = tokens(demand_text)
    candidate_text = " ".join(
        [
            item.get("filename", ""),
            item.get("category_path", ""),
            item.get("tags_clean", ""),
        ]
    ).lower()
    candidate_tokens = tokens(candidate_text)
    rules = [rule for rule in SCORING_RULES if any(keyword_matches(need, demand_text, demand_tokens) for need in rule["needs"])]
    if not rules:
        rules = [
            {
                "positive": [part for part in tokens(row.get("library_search_queries", "")) if len(part) > 2],
                "negative": [],
                "duration_min": 0.1,
                "duration_max": 3.0,
            }
        ]

    score = 45
    positive_hits: list[str] = []
    negative_hits: list[str] = []
    for rule in rules:
        for word in rule["positive"]:
            if word in candidate_tokens or word in candidate_text:
                if word not in positive_hits:
                    positive_hits.append(word)
                    score += 8
        for word in rule["negative"]:
            if word in candidate_tokens or word in candidate_text:
                if word not in negative_hits:
                    negative_hits.append(word)
                    score -= 22
        if duration:
            if rule["duration_min"] <= duration <= rule["duration_max"]:
                score += 10
            elif duration < rule["duration_min"]:
                score -= 10
            elif duration > rule["duration_max"]:
                score -= 8

    if "impact" in demand_text and ("impact" in candidate_text or "hit" in candidate_tokens):
        score += 8
    if any(word in demand_text for word in ["低频", "low", "boom", "rumble"]) and any(word in candidate_text for word in ["low", "boom", "rumble", "heavy"]):
        score += 8
    sad_dismiss_demand = any(word in demand_text for word in ["放弃", "失落", "黯哑", "消散", "giveup", "give up", "sad", "failure", "dissipate", "fade"])
    if sad_dismiss_demand:
        sad_core = ["remove", "fade", "dissipate", "dark", "sad", "soft", "low", "muted", "negative", "fail", "failure"]
        bright_wrong = ["metal", "metl", "clang", "chime", "bell", "bright", "sparkle", "fight", "battle", "start", "reward", "success"]
        if any(word in candidate_text for word in sad_core):
            score += 14
        if any(word in candidate_text for word in bright_wrong):
            score = min(score - 24, 42)
            if "放弃/失落不应是高亮金属或成功反馈" not in negative_hits:
                negative_hits.append("放弃/失落不应是高亮金属或成功反馈")
    premium_card_demand = any(word in demand_text for word in ["ssr", "sr card", "card reveal", "品质卡片", "专属特效", "金光", "银紫"])
    if premium_card_demand:
        soft_reward_core = ["card", "reveal", "reward", "chime", "glow", "bloom", "magic", "ui"]
        harsh_metal = ["metal", "metl", "clang", "clangy", "rattle", "scrape", "junk", "sheet", "container"]
        if any(word in candidate_text for word in soft_reward_core):
            score += 12
        if any(word in candidate_text for word in harsh_metal):
            score = min(score - 24, 48)
            if "品质卡片不应是尖锐金属/杂物撞击" not in negative_hits:
                negative_hits.append("品质卡片不应是尖锐金属/杂物撞击")
    if any(word in demand_text for word in ["水", "水箭", "海浪", "浪", "water", "wave", "surge", "splash"]):
        water_core = ["water", "wave", "waves", "ocean", "sea", "surge", "splash", "stream", "river", "liquid", "tidal"]
        hard_conflict = ["fire", "flame", "lava", "metal", "sword", "blade", "pixie", "electric"]
        if not any(word in candidate_text for word in water_core):
            score = min(score, 40)
            if "缺少水浪核心词" not in negative_hits:
                negative_hits.append("缺少水浪核心词")
        if any(word in candidate_text for word in hard_conflict):
            score = min(score, 44)

    fire_demand = any(keyword_matches(word, demand_text, demand_tokens) for word in ["火", "火焰", "燃火", "熔岩", "迸发", "爆发", "fire", "flame", "lava", "burst", "ignite"])
    if fire_demand:
        fire_core = ["fire", "flame", "flames", "lava", "burn", "burning", "ignite", "ignition", "ember", "blaze"]
        burst_core = ["burst", "explosion", "explode", "detonation", "blast", "boom"]
        irrelevant_fire = ["fire department", "fire extinguisher", "hydrant"]
        blade_core = ["sword", "blade", "metal", "weapon", "weap", "slash", "swing"]
        has_fire_core = any(keyword_matches(word, candidate_text, candidate_tokens) for word in fire_core)
        needs_burst = any(word in demand_text for word in ["迸发", "爆发"]) or any(word in demand_tokens for word in ["burst", "explosion", "blast"])
        has_burst_core = any(keyword_matches(word, candidate_text, candidate_tokens) for word in burst_core)
        needs_blade = any(word in demand_text for word in ["剑", "大剑", "金属"]) or any(word in demand_tokens for word in ["sword", "blade", "metal"])
        has_blade_core = any(keyword_matches(word, candidate_text, candidate_tokens) for word in blade_core)

        if not has_fire_core:
            score = min(score, 44)
            if "缺少火焰核心词" not in negative_hits:
                negative_hits.append("缺少火焰核心词")
        if needs_burst and not has_burst_core:
            score = min(score, 50)
            if "缺少火焰迸发/爆裂" not in negative_hits:
                negative_hits.append("缺少火焰迸发/爆裂")
        if any(phrase in candidate_text for phrase in irrelevant_fire):
            score = min(score, 25)
            if "火焰语义无关" not in negative_hits:
                negative_hits.append("火焰语义无关")
        if needs_blade and not has_blade_core:
            score = min(score, 48)
            if "缺少金属/剑动作层" not in negative_hits:
                negative_hits.append("缺少金属/剑动作层")
        if needs_blade and any(keyword_matches(word, candidate_text, candidate_tokens) for word in ["gore", "fist", "punch"]):
            score = min(score, 42)
            if "动作材质不符" not in negative_hits:
                negative_hits.append("动作材质不符")
    if score < 0:
        score = 0
    if score > 100:
        score = 100
    if score >= 70:
        tier = "高"
    elif score >= 45:
        tier = "中"
    else:
        tier = "低"
    return {
        "match_score": score,
        "match_tier": tier,
        "match_reasons": "加分: " + (", ".join(positive_hits) or "无明显命中"),
        "mismatch_reasons": "扣分: " + (", ".join(negative_hits) or "无明显冲突"),
    }


def build_manifest(master_path: Path, candidates_path: Path, preview_map_path: Path) -> list[dict[str, object]]:
    master_rows = read_csv(master_path)
    candidate_rows = [row for row in read_csv(candidates_path) if row.get("candidate_id")]
    preview_map = load_preview_map(preview_map_path)
    by_event: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidate_rows:
        by_event[row["request_id"]].append(row)

    manifest: list[dict[str, object]] = []
    for row in master_rows:
        candidates = []
        seen = set()
        for item in by_event.get(row["request_id"], []):
            candidate_id = item.get("candidate_id", "")
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            duration = duration_float(item.get("duration_sec", ""))
            if 0 < duration <= 3:
                length_label = "短"
            elif duration <= 8:
                length_label = "中"
            elif duration:
                length_label = "长"
            else:
                length_label = "未知"
            scored = semantic_score(row, item, duration)
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "filename": item.get("filename", ""),
                    "duration_sec": duration,
                    "length_label": length_label,
                    "project_code": item.get("project_code", ""),
                    "category_path": item.get("category_path", ""),
                    "tags_clean": item.get("tags_clean", ""),
                    "download_url": normalize_download_url(item.get("download_url", "")),
                    "local_preview_url": page_relative_preview_url(preview_map.get(candidate_id, {}).get("relative_path", "")),
                    "query_rank": item.get("query_rank", ""),
                    "library_query": item.get("library_query", ""),
                    **scored,
                }
            )
        candidates.sort(key=lambda item: (-int(item["match_score"]), int(item.get("query_rank") or 99), item["duration_sec"] or 999999))
        qualified_count = sum(1 for item in candidates if int(item["match_score"]) >= 60)
        manifest.append(
            {
                "request_id": row["request_id"],
                "event_name": row["event_name"],
                "asset_name": row["asset_name"],
                "source_sheet": row["source_sheet"],
                "section": row["section"],
                "demand_tag": row["demand_tag"],
                "description_cn": row["description_cn"],
                "resource_bank": row["resource_bank"],
                "trigger_timing": row["trigger_timing"],
                "priority": row["priority"],
                "loop": row["loop"],
                "stop_event_needed": row["stop_event_needed"],
                "company_library_first": row.get("company_library_first", ""),
                "reuse_strategy": row.get("reuse_strategy", ""),
                "ai_needed_after_library_review": row.get("ai_needed_after_library_review", ""),
                "prompt_en": row["prompt_en"],
                "candidate_count": len(candidates),
                "short_candidate_count": sum(1 for item in candidates if item["length_label"] == "短"),
                "qualified_candidate_count": qualified_count,
                "candidates": candidates,
            }
        )
    return manifest


def merge_scored_manifest(manifest: list[dict[str, object]], scored_manifest_path: Path | None) -> list[dict[str, object]]:
    if not scored_manifest_path or not scored_manifest_path.exists():
        return manifest
    scored_manifest = json.loads(scored_manifest_path.read_text(encoding="utf-8"))
    scored_by_key: dict[tuple[str, str], dict[str, object]] = {}
    for item in scored_manifest:
        request_id = str(item.get("request_id", ""))
        for candidate in item.get("candidates", []):
            candidate_id = str(candidate.get("candidate_id", ""))
            if request_id and candidate_id:
                scored_by_key[(request_id, candidate_id)] = candidate
    score_fields = [
        "semantic_score",
        "rule_match_score",
        "quality_score",
        "feedback_score",
        "final_score",
        "feedback_profile_best_count",
        "feedback_profile_miss_count",
    ]
    for item in manifest:
        request_id = str(item.get("request_id", ""))
        for candidate in item.get("candidates", []):
            scored = scored_by_key.get((request_id, str(candidate.get("candidate_id", ""))))
            if not scored:
                continue
            for field in score_fields:
                if field in scored:
                    candidate[field] = scored[field]
    return manifest


def merge_ai_manifest(manifest: list[dict[str, object]], ai_manifest_path: Path | None) -> list[dict[str, object]]:
    if not ai_manifest_path or not ai_manifest_path.exists():
        return manifest
    raw = json.loads(ai_manifest_path.read_text(encoding="utf-8"))
    by_asset: dict[str, list[dict[str, object]]] = defaultdict(list)
    if isinstance(raw, dict):
        for candidate in raw.get("candidates", []):
            asset = str(candidate.get("assetName") or candidate.get("asset_name") or "")
            if asset:
                by_asset[asset].append(candidate)
    elif isinstance(raw, list):
        for event in raw:
            asset = str(event.get("asset_name") or event.get("assetName") or "")
            if asset:
                by_asset[asset].extend(event.get("candidates", []))
    for item in manifest:
        normalized = []
        for index, candidate in enumerate(by_asset.get(str(item.get("asset_name", "")), []), 1):
            path = str(
                candidate.get("wavPath")
                or candidate.get("output_path")
                or candidate.get("local_preview_url")
                or candidate.get("sourcePath")
                or ""
            )
            if not path:
                continue
            normalized.append({
                **candidate,
                "candidate_id": candidate.get("candidate_id") or f"ai:{path}",
                "candidate_type": "ai",
                "output_path": path,
                "local_preview_url": candidate.get("local_preview_url") or path,
                "filename": candidate.get("filename") or Path(path).name,
                "variant": candidate.get("variant") or index,
            })
        item["ai_candidates"] = normalized
    return manifest


def write_page(
    output: Path,
    manifest: list[dict[str, object]],
    manifest_path: Path,
    title: str = "X15 公司资产库候选筛选",
    subtitle: str = "先听公司库候选，标记直接用、改后用、不合适；如果整个事件没有合适候选，再在事件级标记需要 AI。短候选已缓存到本地试听，不走 Wwise。",
    state_key: str = "x15-company-library-review-state-v1",
    auto_start_ai: bool = False,
    enable_ai_api: bool = False,
) -> None:
    data_json = json.dumps(manifest, ensure_ascii=False, indent=2)
    state_key_json = json.dumps(state_key, ensure_ascii=False)
    page_title = escape(title)
    page_subtitle = escape(subtitle)
    contract_version = REVIEW_PAGE_CONTRACT_VERSION
    auto_ai_bootstrap = "autoStartAiForLibraryGaps();" if auto_start_ai else ""
    enable_ai_api_json = "true" if enable_ai_api else "false"
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="x15-review-page-contract" content="{contract_version}">
  <title>{page_title}</title>
  <style>
    :root {{
      --bg: #f6f7f4;
      --panel: #fff;
      --ink: #20231f;
      --muted: #667069;
      --line: #dfe3dc;
      --soft: #e8f1ee;
      --accent: #1b6f60;
      --warn: #95651e;
      --bad: #9b3a34;
      --blue: #2c6d92;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif;
      color: var(--ink);
      background: var(--bg);
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 3;
      background: rgba(246,247,244,0.96);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(12px);
    }}
    .bar {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 16px 20px 12px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 14px;
      align-items: center;
    }}
    h1 {{
      margin: 0;
      font-size: 22px;
      letter-spacing: 0;
    }}
    .sub {{
      color: var(--muted);
      font-size: 13px;
      margin-top: 5px;
    }}
    .contract {{
      display: inline-flex;
      align-items: center;
      width: fit-content;
      margin-top: 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px 8px;
      color: var(--muted);
      background: rgba(255,255,255,.72);
      font-size: 11px;
    }}
    .stats {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
      color: var(--muted);
      font-size: 12px;
    }}
    .pill {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 5px 9px;
      background: var(--panel);
    }}
    .pill.strong {{
      border-color: var(--accent);
      color: var(--accent);
      font-weight: 750;
    }}
    .progress {{
      flex-basis: 100%;
      height: 7px;
      background: #e4e8e2;
      border-radius: 999px;
      overflow: hidden;
    }}
    .progress span {{
      display: block;
      height: 100%;
      width: var(--progress, 0%);
      background: var(--accent);
    }}
    .controls {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 0 20px 14px;
      display: grid;
      grid-template-columns: minmax(220px, 1fr) 140px 140px 150px 150px 150px auto;
      gap: 10px;
    }}
    input, select, button, textarea {{
      font: inherit;
    }}
    input, select {{
      min-height: 38px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 6px;
      padding: 0 10px;
      min-width: 0;
    }}
    button {{
      min-height: 34px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      border-radius: 6px;
      padding: 0 10px;
      cursor: pointer;
    }}
    button.primary {{
      background: var(--accent);
      color: white;
      border-color: var(--accent);
    }}
    main {{
      max-width: 1440px;
      margin: 18px auto 44px;
      padding: 0 20px;
      display: grid;
      grid-template-columns: 340px minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }}
    .list, .detail {{
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      min-height: 74vh;
      max-height: calc(100vh - 170px);
      overflow: auto;
    }}
    .list {{
      overscroll-behavior: contain;
    }}
    .event-item {{
      width: 100%;
      border: 0;
      border-bottom: 1px solid var(--line);
      border-radius: 0;
      background: transparent;
      text-align: left;
      padding: 11px 12px;
      display: block;
    }}
    .event-item.active {{
      background: var(--soft);
    }}
    .event-title {{
      font-size: 13px;
      font-weight: 750;
      overflow-wrap: anywhere;
    }}
    .event-sub {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
      margin-top: 4px;
    }}
    .badge {{
      display: inline-block;
      border-radius: 999px;
      padding: 3px 7px;
      background: #edf1ef;
      color: var(--muted);
      font-size: 11px;
      margin-right: 5px;
      margin-top: 6px;
    }}
    .badge.good {{ color: var(--accent); background: #e3f1ed; }}
    .badge.warn {{ color: var(--warn); background: #fbf1df; }}
    .badge.bad {{ color: var(--bad); background: #f7e7e5; }}
    .badge.blue {{ color: var(--blue); background: #e8f1f6; }}
    .detail {{
      padding: 18px;
      scroll-behavior: smooth;
      overscroll-behavior: contain;
    }}
    .empty {{
      color: var(--muted);
      padding: 26px;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin: 12px 0 16px;
    }}
    .meta div {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      min-height: 58px;
    }}
    .label {{
      display: block;
      color: var(--muted);
      font-size: 11px;
      margin-bottom: 4px;
    }}
    .desc {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fbfcfb;
      margin-bottom: 14px;
      color: #37403b;
      line-height: 1.5;
    }}
    .candidate-summary {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin: -4px 0 14px;
    }}
    .candidates {{
      display: grid;
      gap: 12px;
    }}
    .candidate {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      display: grid;
      grid-template-columns: minmax(240px, 1fr) minmax(260px, 1.2fr) 250px;
      gap: 12px;
      align-items: center;
    }}
    .candidate.selected {{
      border-color: var(--accent);
      background: #f1f8f5;
    }}
    .candidate.best {{
      border-color: #b68a22;
      background: #fff8e4;
      box-shadow: inset 3px 0 0 #d9a62e;
    }}
    .candidate.modify {{
      border-color: var(--blue);
      background: #eef6fa;
    }}
    .candidate.reject {{
      opacity: 0.62;
    }}
    .candidate.low-match {{
      opacity: .72;
      border-color: #e6b6a8;
      background: #fff8f5;
    }}
    .candidate.best-short {{
      border-color: #77a7bd;
      box-shadow: inset 3px 0 0 #77a7bd;
    }}
    .file {{
      font-weight: 700;
      overflow-wrap: anywhere;
      font-size: 13px;
    }}
    .file-meta {{
      color: var(--muted);
      font-size: 12px;
      margin-top: 5px;
      line-height: 1.4;
    }}
    .quick-line {{
      color: #3d4741;
      font-size: 12px;
      margin-top: 7px;
      line-height: 1.45;
    }}
    audio {{
      width: 100%;
      height: 36px;
    }}
    .actions {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 7px;
      margin-top: 8px;
    }}
    .actions button.on {{
      color: white;
      background: var(--accent);
      border-color: var(--accent);
    }}
    .actions button.best.on {{
      background: #b27912;
      border-color: #b27912;
    }}
    .actions button.modify.on {{
      background: var(--blue);
      border-color: var(--blue);
    }}
    .actions button.reject.on {{
      background: var(--bad);
      border-color: var(--bad);
    }}
    .event-actions {{
      display: grid;
      grid-template-columns: repeat(4, auto) 1fr;
      gap: 8px;
      align-items: center;
      margin: 14px 0;
      position: sticky;
      top: -18px;
      z-index: 2;
      background: rgba(255,255,255,.96);
      border-bottom: 1px solid var(--line);
      padding: 10px 0;
    }}
    .event-actions button.on {{
      color: #fff;
      background: var(--accent);
      border-color: var(--accent);
    }}
    .event-actions .ai-generate,
    .candidate-ai-retry {{
      background: #fbf1df;
      border-color: #e1be80;
      color: var(--warn);
      font-weight: 750;
    }}
    .event-actions .ai-generate.on {{
      background: var(--warn);
      border-color: var(--warn);
      color: #fff;
    }}
    textarea {{
      width: 100%;
      min-height: 80px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      resize: vertical;
      margin-top: 10px;
    }}
    .candidate-note {{
      min-height: 58px;
      font-size: 13px;
      line-height: 1.35;
      color: #38423d;
      background: #fbfcfb;
    }}
    .candidate-ai-retry {{
      width: 100%;
      margin-top: 8px;
    }}
    .ai-score {{
      display: inline-block;
      margin-top: 7px;
    }}
    .export-panel {{
      position: fixed;
      right: 18px;
      bottom: 18px;
      width: min(620px, calc(100vw - 36px));
      max-height: 70vh;
      overflow: auto;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 18px 50px rgba(34, 37, 31, .18);
      padding: 14px;
      z-index: 20;
    }}
    .export-panel[hidden] {{
      display: none;
    }}
    .export-head {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: flex-start;
      margin-bottom: 10px;
    }}
    .export-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 10px 0;
    }}
    .export-panel textarea {{
      min-height: 220px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      white-space: pre;
    }}
    .advanced-export {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      background: rgba(255, 255, 255, .58);
    }}
    .advanced-export summary {{
      cursor: pointer;
      color: var(--muted);
      font-weight: 700;
      user-select: none;
    }}
    .advanced-export .advanced-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }}
    .inline-option {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--muted);
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, .7);
    }}
    @media (max-width: 1100px) {{
      main, .bar, .controls, .candidate, .meta {{
        grid-template-columns: 1fr;
      }}
      .list, .detail {{
        max-height: none;
        overflow: visible;
      }}
      .stats {{
        justify-content: flex-start;
      }}
    }}
  </style>
</head>
<body data-review-page-contract="{contract_version}">
  <!-- review-page-contract: {contract_version}; generated by build_company_library_review_page.py -->
  <header>
    <div class="bar">
      <div>
        <h1>{page_title}</h1>
        <div class="sub">{page_subtitle}</div>
        <div class="contract">Review Page Contract: {contract_version}</div>
      </div>
      <div class="stats" id="stats"></div>
    </div>
    <div class="controls">
      <input id="search" type="search" placeholder="搜索事件、资源名、中文描述、候选文件">
      <select id="bank"></select>
      <select id="decision">
        <option value="">全部状态</option>
        <option value="undecided">未判断</option>
        <option value="best">最佳</option>
        <option value="direct_use">直接用</option>
        <option value="modify_use">改后用</option>
        <option value="reject">不合适</option>
        <option value="ai_needed">AI生成</option>
      </select>
      <select id="candidateFilter">
        <option value="">全部候选</option>
        <option value="has_qualified">有合格候选</option>
        <option value="has_short">有短候选</option>
        <option value="needs_triage">需重点听</option>
        <option value="no_candidate">无候选</option>
      </select>
      <select id="reuseFilter" title="复用项默认不进入听审工作量">
        <option value="hide_reuse">隐藏复用项</option>
        <option value="show_all">显示复用项</option>
        <option value="reuse_only">只看复用项</option>
      </select>
      <select id="scoreFilter">
        <option value="45">中高分+最佳短</option>
        <option value="60">只看60分以上</option>
        <option value="0">显示全部分数</option>
      </select>
      <select id="candidateSort">
        <option value="short_first">短候选优先</option>
        <option value="final_first">综合分优先</option>
        <option value="score_first">匹配分优先</option>
        <option value="rank_first">搜索排名优先</option>
      </select>
      <label class="inline-option" title="正式模式默认按优先级生成：P0=6个，P1=5个，P2=4个。也可以临时手动改数量。">
        AI数量
        <select id="aiVariantCount">
          <option value="auto">按优先级</option>
          <option value="1">1个</option>
          <option value="2">2个</option>
          <option value="3">3个</option>
          <option value="4">4个</option>
          <option value="6">6个</option>
        </select>
      </label>
      <label class="inline-option" title="默认关闭。combined 是本地把多个 AI stem 混在一起，容易放大尖锐高频；只有需要试混合版时再勾选。">
        <input id="generateCombined" type="checkbox">
        生成 combined 混合版
      </label>
      <button class="primary" id="submitPackageBtn">提交判断并生成交付包</button>
      <details class="advanced-export">
        <summary>高级导出</summary>
        <div class="advanced-actions">
          <button class="primary" id="exportBtn">导出判断</button>
          <button class="primary" id="exportFeedbackBtn">导出反馈CSV</button>
          <button class="primary" id="exportAiBtn">导出AI队列</button>
          <button id="exportStateJsonBtn" title="下载当前 localStorage 状态 JSON，作为手动保险。">导出状态JSON</button>
        </div>
      </details>
    </div>
  </header>
  <main>
    <section class="list" id="eventList"></section>
    <section class="detail" id="detail"></section>
  </main>
  <section class="export-panel" id="exportPanel" hidden>
    <div class="export-head">
      <div>
        <h3 id="exportTitle">导出结果</h3>
        <div class="file-meta" id="exportMeta"></div>
      </div>
      <button id="closeExport">关闭</button>
    </div>
    <div class="export-actions">
      <a class="primary button-like" id="exportDownload" download>下载文件</a>
      <button id="copyExport">复制内容</button>
    </div>
    <textarea id="exportContent" readonly></textarea>
  </section>
  <script>
    const manifest = {data_json};
    const stateKey = {state_key_json};
    const enableAiApi = {enable_ai_api_json};
    const state = JSON.parse(localStorage.getItem(stateKey) || "{{}}");
    Object.values(state).forEach(s => {{
      if (s?.ai_generation_status === "已标记AI缺口；导出决策后命令行生成") {{
        s.ai_generation_status = "";
        s.ai_generation_error = "";
      }}
    }});
    localStorage.setItem(stateKey, JSON.stringify(state));
    let activeId = manifest[0]?.request_id || "";
    let lastRenderedActiveId = activeId;
    let shouldScrollDetailTop = false;

    function saveState() {{
      localStorage.setItem(stateKey, JSON.stringify(state));
      render();
    }}

    function eventState(id) {{
      const item = manifest.find(event => event.request_id === id);
      state[id] ||= {{ event_decision: "", selected_candidate_id: "", candidate_decisions: {{}}, candidate_notes: {{}}, notes: "", ai_generation_status: "", ai_generation_job_id: "", ai_generation_outputs: [] }};
      if ((item?.ai_candidates || []).length && !(state[id].ai_generation_outputs || []).length) {{
        state[id].ai_generation_outputs = item.ai_candidates;
        state[id].ai_generation_status ||= "AI补位候选已生成";
        state[id].event_decision ||= "auto_ai";
      }}
      state[id].candidate_notes ||= {{}};
      return state[id];
    }}

    function setEventDecision(id, decision) {{
      const s = eventState(id);
      if (decision === "ai_needed") {{
        const item = manifest.find(event => event.request_id === id);
        if (item && !aiAllowed(item)) {{
          showMessage("复用项不生成AI", `${{id}} 是复用/沿用类需求，应优先使用目标资源名：${{item.asset_name}}。如公司库候选不合适，请先标记具体候选“不合适”并写备注。`);
          return;
        }}
        const hasExistingOutputs = (s.ai_generation_outputs || []).length > 0;
        s.event_decision = "ai_needed";
        s.selected_candidate_id = "";
        if (!s.ai_generation_status) s.ai_generation_status = "等待生成服务";
        saveState();
        startAiGeneration(id, {{ append: hasExistingOutputs }});
        return;
      }}
      s.event_decision = s.event_decision === decision ? "" : decision;
      saveState();
    }}

    function isReuseItem(item) {{
      return ["复用", "沿用X1"].includes(item.demand_tag || "")
        || (item.reuse_strategy || "").startsWith("reuse_")
        || (item.ai_needed_after_library_review || "").toUpperCase() === "FALSE";
    }}

    function aiAllowed(item) {{
      return !isReuseItem(item) && Boolean(item.prompt_en);
    }}

    function companyLibraryNeedsAi(item) {{
      return aiAllowed(item) && ((item.candidate_count || 0) <= 0 || (item.qualified_candidate_count || 0) <= 0);
    }}

    function firstCandidateIdByDecision(s, decisions) {{
      const wanted = Array.isArray(decisions) ? decisions : [decisions];
      const found = Object.entries(s.candidate_decisions || {{}})
        .find(([, value]) => wanted.includes(value));
      return found ? found[0] : "";
    }}

    function recomputeFinalSelection(s) {{
      const best = firstCandidateIdByDecision(s, "best");
      if (best) {{
        s.selected_candidate_id = best;
        s.event_decision = "direct_use";
        return;
      }}
      const modify = firstCandidateIdByDecision(s, "modify_use");
      if (modify) {{
        s.selected_candidate_id = modify;
        s.event_decision = "modify_use";
        return;
      }}
      const direct = firstCandidateIdByDecision(s, "direct_use");
      if (direct) {{
        s.selected_candidate_id = direct;
        s.event_decision = "direct_use";
        return;
      }}
      s.selected_candidate_id = "";
      if (s.event_decision === "direct_use" || s.event_decision === "modify_use") {{
        s.event_decision = "";
      }}
    }}

    function setCandidateDecision(eventId, candidateId, decision) {{
      const s = eventState(eventId);
      const current = s.candidate_decisions[candidateId] || "";
      if (current === decision) {{
        delete s.candidate_decisions[candidateId];
      }} else {{
        if (decision === "best") {{
          Object.entries(s.candidate_decisions || {{}}).forEach(([id, value]) => {{
            if (id !== candidateId && value === "best") {{
              delete s.candidate_decisions[id];
            }}
          }});
        }} else if (decision === "modify_use") {{
          Object.entries(s.candidate_decisions || {{}}).forEach(([id, value]) => {{
            if (id !== candidateId && value === "modify_use") delete s.candidate_decisions[id];
          }});
        }}
        s.candidate_decisions[candidateId] = decision;
      }}
      recomputeFinalSelection(s);
      saveState();
    }}

    function outputUrl(path) {{
      if (!path) return "";
      if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("file:")) return path;
      const clean = path.replace(/^[/]+/, "");
      if (clean.startsWith("company_library_previews/") || clean.startsWith("ai_candidates/")) return clean;
      return location.protocol === "file:" ? clean : `/${{clean}}`;
    }}

    function aiOutputPath(output) {{
      if (!output) return "";
      if (typeof output === "string") return output;
      return output.output_path || output.local_preview_url || output.source_path || output.download_url || "";
    }}

    function normalizeAiCandidate(item, output, index) {{
      const path = aiOutputPath(output);
      if (!path) return null;
      if (typeof output === "object" && output.candidate_id) {{
        return {{
          ...output,
          candidate_id: output.candidate_id || `ai:${{path}}`,
          candidate_type: "ai",
          output_path: path,
          local_preview_url: output.local_preview_url || path,
          filename: output.filename || path.split("/").pop(),
          match_score: output.match_score || output.rule_match_score || output.final_score || aiCandidateScore(item, path, index),
          final_score: output.final_score || output.match_score || aiCandidateScore(item, path, index)
        }};
      }}
      const score = aiCandidateScore(item, path, index);
      return {{
        candidate_id: `ai:${{path}}`,
        candidate_type: "ai",
        output_path: path,
        local_preview_url: path,
        filename: path.split("/").pop(),
        provider: "company_api",
        match_score: score,
        rule_match_score: score,
        final_score: score,
        semantic_score: "",
        quality_score: "",
        feedback_score: "",
        duration_sec: "",
        length_label: "",
        match_reasons: "旧状态中的AI输出路径，重新同步或再生成后会补齐正式评分。"
      }};
    }}

    function visibleAiOutputs(outputs, item = null) {{
      const list = (outputs || [])
        .map((output, index) => item ? normalizeAiCandidate(item, output, index) : output)
        .filter(Boolean);
      const pathOf = output => aiOutputPath(output);
      const nonStem = list.filter(output => !/_stem\\d+_/i.test(pathOf(output)));
      const plain = nonStem.filter(output => !/_full_\\d+\\./i.test(pathOf(output)) && !/_combined_\\d+\\./i.test(pathOf(output)));
      const full = nonStem.filter(output => /_full_\\d+\\./i.test(pathOf(output)));
      const combined = shouldGenerateCombined() ? nonStem.filter(output => /_combined_\\d+\\./i.test(pathOf(output))) : [];
      return [...plain, ...full, ...combined];
    }}

    function shouldGenerateCombined() {{
      return Boolean(document.getElementById("generateCombined")?.checked);
    }}

    function candidateThreshold() {{
      return Number(document.getElementById("scoreFilter")?.value || 45);
    }}

    function candidateSortMode() {{
      return document.getElementById("candidateSort")?.value || "short_first";
    }}

    function candidatePriority(candidate) {{
      const duration = Number(candidate.duration_sec || 0);
      const isShort = candidate.length_label === "短" || (duration > 0 && duration <= 3);
      const playable = candidate.local_preview_url ? 0 : 1;
      const score = Number(candidate.match_score || 0);
      const finalScore = Number(candidate.final_score || candidate.match_score || 0);
      const rank = Number(candidate.query_rank || 99);
      if (candidateSortMode() === "final_first") return [playable, -finalScore, isShort ? 0 : 1, -score, rank, duration || 999999];
      if (candidateSortMode() === "score_first") return [playable, -score, isShort ? 0 : 1, rank, duration || 999999];
      if (candidateSortMode() === "rank_first") return [playable, rank, isShort ? 0 : 1, -score, duration || 999999];
      return [playable, isShort ? 0 : 1, -score, rank, duration || 999999];
    }}

    function comparePriority(a, b) {{
      const pa = candidatePriority(a);
      const pb = candidatePriority(b);
      for (let i = 0; i < pa.length; i += 1) {{
        if (pa[i] < pb[i]) return -1;
        if (pa[i] > pb[i]) return 1;
      }}
      return String(a.filename || "").localeCompare(String(b.filename || ""));
    }}

    function visibleCompanyCandidates(item) {{
      const threshold = candidateThreshold();
      const topShort = bestShortCandidate(item);
      const playable = bestPlayableCandidate(item);
      const hasPlayable = Boolean(playable);
      return [...(item.candidates || [])]
        .filter(candidate => {{
          if (threshold <= 0) return true;
          if (candidate.local_preview_url) return true;
          if (hasPlayable) return false;
          return Number(candidate.match_score || 0) >= threshold || candidate.candidate_id === topShort?.candidate_id;
        }})
        .sort(comparePriority);
    }}

    function bestShortCandidate(item) {{
      const shortCandidates = [...(item.candidates || [])]
        .filter(candidate => candidate.length_label === "短" || Number(candidate.duration_sec || 0) <= 3)
        .sort((a, b) => {{
          const playableDiff = (b.local_preview_url ? 1 : 0) - (a.local_preview_url ? 1 : 0);
          if (playableDiff) return playableDiff;
          return Number(b.match_score || 0) - Number(a.match_score || 0);
        }});
      return shortCandidates.find(candidate => candidate.local_preview_url) || bestPlayableCandidate(item) || shortCandidates[0];
    }}

    function bestPlayableCandidate(item) {{
      return [...(item.candidates || [])]
        .filter(candidate => candidate.local_preview_url)
        .sort(comparePriority)[0];
    }}

    function finalDecisionState(item) {{
      const d = eventState(item.request_id).event_decision || "";
      return ["best", "direct_use", "modify_use", "reject"].includes(d) ? d : "undecided";
    }}

    function setNotes(id, value) {{
      eventState(id).notes = value;
      localStorage.setItem(stateKey, JSON.stringify(state));
    }}

    function setCandidateNote(eventId, candidateId, value) {{
      eventState(eventId).candidate_notes[candidateId] = value;
      localStorage.setItem(stateKey, JSON.stringify(state));
    }}

    function noteForGeneration(item) {{
      const s = eventState(item.request_id);
      if (s.selected_candidate_id && s.candidate_notes?.[s.selected_candidate_id]) return s.candidate_notes[s.selected_candidate_id];
      return s.notes || "";
    }}

    function textFor(item) {{
      return [
        item.event_name, item.asset_name, item.description_cn, item.trigger_timing,
        item.resource_bank, item.section,
        ...item.candidates.map(c => [c.filename, c.tags_clean, c.category_path, c.library_query].join(" "))
      ].join(" ").toLowerCase();
    }}

    function filteredEvents() {{
      const q = document.getElementById("search").value.trim().toLowerCase();
      const bank = document.getElementById("bank").value;
      const decision = document.getElementById("decision").value;
      const candidateFilter = document.getElementById("candidateFilter").value;
      const reuseFilter = document.getElementById("reuseFilter")?.value || "hide_reuse";
      return manifest.filter(item => {{
        const s = eventState(item.request_id);
        const d = s.event_decision || "undecided";
        const finalD = finalDecisionState(item);
        if (reuseFilter === "hide_reuse" && isReuseItem(item)) return false;
        if (reuseFilter === "reuse_only" && !isReuseItem(item)) return false;
        if (q && !textFor(item).includes(q)) return false;
        if (bank && item.resource_bank !== bank) return false;
        if (decision === "undecided" && finalD !== "undecided") return false;
        if (decision === "best" && finalD !== "best") return false;
        if (decision === "direct_use" && !["best", "direct_use"].includes(finalD)) return false;
        if (["modify_use", "reject"].includes(decision) && finalD !== decision) return false;
        if (decision === "ai_needed" && !["ai_needed", "auto_ai"].includes(d)) return false;
        if (candidateFilter === "has_qualified" && item.qualified_candidate_count <= 0) return false;
        if (candidateFilter === "has_short" && item.short_candidate_count <= 0) return false;
        if (candidateFilter === "needs_triage" && !companyLibraryNeedsAi(item)) return false;
        if (candidateFilter === "no_candidate" && item.candidate_count > 0) return false;
        return true;
      }});
    }}

    function decisionLabel(value) {{
      return {{
        direct_use: "直接用",
        best: "最佳",
        modify_use: "改后用",
        reject: "不合适",
        ai_needed: "AI生成",
        auto_ai: "AI补位",
        undecided: "未判断",
        "": "未判断"
      }}[value] || value;
    }}

    function renderStats() {{
      const total = manifest.length;
      const reuse = manifest.filter(item => isReuseItem(item)).length;
      const decided = manifest.filter(item => finalDecisionState(item) !== "undecided").length;
      const best = manifest.filter(item => finalDecisionState(item) === "best").length;
      const direct = manifest.filter(item => ["best", "direct_use"].includes(finalDecisionState(item))).length;
      const modify = manifest.filter(item => finalDecisionState(item) === "modify_use").length;
      const ai = manifest.filter(item => ["ai_needed", "auto_ai"].includes(eventState(item.request_id).event_decision)).length;
      const pct = total ? Math.round((decided / total) * 100) : 0;
      document.getElementById("stats").innerHTML = [
        `进度 ${{pct}}%`,
        `事件 ${{total}}`,
        `复用 ${{reuse}}`,
        `已判断 ${{decided}}`,
        `最佳 ${{best}}`,
        `直接用 ${{direct}}`,
        `改后用 ${{modify}}`,
        `AI生成 ${{ai}}`
      ].map((v, index) => `<span class="pill ${{index === 0 ? "strong" : ""}}">${{v}}</span>`).join("") + `<div class="progress" style="--progress:${{pct}}%"><span></span></div>`;
    }}

    function renderFilters() {{
      const bankSelect = document.getElementById("bank");
      const previous = bankSelect.value;
      const banks = [...new Set(manifest.map(item => item.resource_bank).filter(Boolean))].sort();
      bankSelect.innerHTML = `<option value="">全部资源包</option>` + banks.map(bank => `<option value="${{bank}}">${{bank}}</option>`).join("");
      bankSelect.value = previous;
    }}

    function renderList() {{
      const list = document.getElementById("eventList");
      const items = filteredEvents();
      if (!items.find(item => item.request_id === activeId) && items[0]) {{
        activeId = items[0].request_id;
        shouldScrollDetailTop = true;
      }}
      list.innerHTML = items.map(item => {{
        const s = eventState(item.request_id);
        const d = s.event_decision || "undecided";
        const badgeClass = d === "direct_use" ? "good" : d === "modify_use" ? "good" : ["ai_needed", "auto_ai"].includes(d) ? "warn" : d === "reject" ? "bad" : "";
        const reuseBadge = isReuseItem(item) ? `<span class="badge good">复用：${{item.asset_name}}</span>` : "";
        const aiBadge = s.ai_generation_status ? `<span class="badge warn">AI ${{s.ai_generation_status}}</span>` : "";
        const visibleCandidateCount = visibleCompanyCandidates(item).length;
        const bestShort = bestShortCandidate(item);
        const quickLine = bestShort
          ? `最佳短候选：${{bestShort.filename}} · ${{Number(bestShort.match_score || 0)}}分 · ${{Number(bestShort.duration_sec || 0).toFixed(2)}}s`
          : item.candidate_count
            ? (isReuseItem(item) ? "复用项：优先确认目标资源是否可直接用" : (item.qualified_candidate_count <= 0 ? "公司库分低：已进入AI补位队列" : "无短候选：建议只听高分/合格项"))
            : "公司库无候选：已进入AI补位队列";
        return `<button class="event-item ${{item.request_id === activeId ? "active" : ""}}" data-id="${{item.request_id}}">
          <div class="event-title">${{item.event_name}}</div>
          <div class="event-sub">${{item.description_cn || item.asset_name}}</div>
          <div class="quick-line">${{quickLine}}</div>
          <span class="badge ${{badgeClass}}">${{decisionLabel(d)}}</span>
          ${{reuseBadge}}
          ${{aiBadge}}
          <span class="badge">${{item.resource_bank}}</span>
          <span class="badge blue">短 ${{item.short_candidate_count || 0}}</span>
          <span class="badge ${{item.qualified_candidate_count > 0 ? "good" : visibleCandidateCount ? "warn" : "bad"}}">合格 ${{item.qualified_candidate_count || 0}} / 展示 ${{visibleCandidateCount}}</span>
        </button>`;
      }}).join("") || `<div class="empty">没有符合筛选条件的事件。</div>`;
      list.querySelectorAll(".event-item").forEach(button => {{
        button.addEventListener("click", () => {{
          if (activeId !== button.dataset.id) {{
            activeId = button.dataset.id;
            shouldScrollDetailTop = true;
          }}
          render();
        }});
      }});
    }}

    function renderDetail() {{
      const detail = document.getElementById("detail");
      const item = manifest.find(event => event.request_id === activeId);
      if (!item) {{
        detail.innerHTML = `<div class="empty">选择左侧事件开始筛选。</div>`;
        return;
      }}
      const s = eventState(item.request_id);
      const eventButtons = ["direct_use", "modify_use", "reject"].map(d =>
        `<button class="${{s.event_decision === d ? "on" : ""}}" data-event-decision="${{d}}">${{decisionLabel(d)}}</button>`
      ).join("");
      const visibleOutputs = visibleAiOutputs(s.ai_generation_outputs, item);
      const aiActionLabel = visibleOutputs.length ? "再生成一版AI" : "AI生成候选";
      const aiGenerateButton = isReuseItem(item)
        ? `<button class="ai-generate" disabled title="复用项默认不生成AI">复用项不生成AI</button>`
        : item.prompt_en
        ? `<button class="ai-generate ${{s.event_decision === "ai_needed" || s.event_decision === "auto_ai" ? "on" : ""}}" data-event-decision="ai_needed">${{aiActionLabel}}</button>`
        : `<button class="ai-generate" disabled title="这条需求缺少AI prompt">暂无AI prompt</button>`;
      const reusePanel = isReuseItem(item) ? `
        <div class="desc">
          <strong>复用策略：</strong>${{item.demand_tag || "复用"}} / ${{item.reuse_strategy || "reuse_existing_or_company_library_asset"}}<br>
          <span class="label">目标复用资源名</span>${{item.asset_name}}<br>
          这条需求表标记为复用，默认不进入 AI 生成；请优先在公司库候选里确认可直接用或改后用。
        </div>
      ` : "";
      const generationPanel = s.ai_generation_status ? `
        <div class="desc">
          <strong>AI生成状态：</strong>${{s.ai_generation_status || "未开始"}}
          ${{s.ai_generation_job_id ? `<br><span class="label">Job</span>${{s.ai_generation_job_id}}` : ""}}
          ${{s.ai_generation_job_id ? `<br><button data-sync-ai-status="${{item.request_id}}">同步AI状态</button>` : ""}}
          ${{visibleOutputs.length ? `<br><span class="label">输出</span>${{visibleOutputs.map(aiOutputPath).join("<br>")}}` : ""}}
        </div>
      ` : "";
      const visibleCompany = visibleCompanyCandidates(item);
      const hiddenLowScoreCount = (item.candidates || []).length - visibleCompany.length;
      const hiddenLowScoreHint = hiddenLowScoreCount > 0 ? `<div class="empty">已隐藏 ${{hiddenLowScoreCount}} 条低分公司库候选（当前阈值：匹配分 &gt;= ${{candidateThreshold()}}）。可在顶部切到“显示全部分数”。</div>` : "";
      const topShort = bestShortCandidate(item);
      const summaryBadges = [
        `<span class="badge">公司库候选 ${{item.candidate_count || 0}}</span>`,
        `<span class="badge blue">短候选 ${{item.short_candidate_count || 0}}</span>`,
        `<span class="badge ${{item.qualified_candidate_count > 0 ? "good" : "warn"}}">合格候选 ${{item.qualified_candidate_count || 0}}</span>`,
        topShort ? `<span class="badge blue">先听：${{topShort.filename}} · ${{Number(topShort.match_score || 0)}}分</span>` : `<span class="badge warn">无短候选可优先听</span>`
      ].join("");
      const candidates = visibleCompany.map(c => {{
        const cd = s.candidate_decisions[c.candidate_id] || "";
        const cn = s.candidate_notes?.[c.candidate_id] || "";
        const selectedClass = cd === "best" ? "best" : cd === "direct_use" ? "selected" : cd === "modify_use" ? "modify" : cd === "reject" ? "reject" : "";
        const scoreClass = c.candidate_id === topShort?.candidate_id ? "best-short" : Number(c.match_score || 0) < 45 ? "low-match" : "";
        const scoreBadge = c.match_score >= 70 ? "good" : c.match_score >= 45 ? "warn" : "bad";
        const listenBadge = c.candidate_id === topShort?.candidate_id ? `<span class="badge blue">建议先听</span>` : "";
        const finalScoreBlock = c.final_score
          ? `<div><span class="badge good">综合分 ${{c.final_score}}</span><span class="badge">语义 ${{c.semantic_score || "-"}}</span><span class="badge">质量 ${{c.quality_score || "-"}}</span><span class="badge">偏好 ${{c.feedback_score || "-"}}</span></div>`
          : "";
        const audioBlock = c.local_preview_url
          ? `<audio controls preload="none" src="${{c.local_preview_url}}"></audio><div class="file-meta">本地缓存试听</div>`
          : `<div class="empty">未缓存，暂不可在本页播放</div><div class="file-meta">可稍后重跑缓存下载，或用下方公司库链接定位原素材。</div>`;
        return `<article class="candidate ${{selectedClass}} ${{scoreClass}}">
          <div>
            <div class="file">${{c.filename}}</div>
            <div class="file-meta">ID ${{c.candidate_id}} · ${{c.duration_sec ? c.duration_sec.toFixed(2) + "s" : "时长未知"}} · ${{c.length_label}} · ${{c.project_code || ""}}</div>
            <div><span class="badge ${{scoreBadge}}">匹配分 ${{c.match_score}} / ${{c.match_tier}}</span>${{listenBadge}}</div>
            ${{finalScoreBlock}}
            <div class="file-meta">${{c.match_reasons || ""}}</div>
            <div class="file-meta">${{c.mismatch_reasons || ""}}</div>
            <div class="file-meta">${{c.category_path || "无分类路径"}}</div>
            <div class="file-meta">Query: ${{c.library_query}}</div>
          </div>
          <div>
            ${{audioBlock}}
            <div class="file-meta"><a href="${{c.download_url}}" target="_blank" rel="noreferrer">打开公司库下载链接</a></div>
            <div class="file-meta">${{c.tags_clean || "无标签"}}</div>
          </div>
          <div>
            <div class="actions">
              <button class="best ${{cd === "best" ? "on" : ""}}" data-candidate="${{c.candidate_id}}" data-decision="best" title="本条需求最终交付只取最佳；最佳单选">最佳</button>
              <button class="${{cd === "direct_use" ? "on" : ""}}" data-candidate="${{c.candidate_id}}" data-decision="direct_use" title="可直接使用的备选，可多选；最终交付仍优先取最佳">直接用</button>
              <button class="modify ${{cd === "modify_use" ? "on" : ""}}" data-candidate="${{c.candidate_id}}" data-decision="modify_use">改后用</button>
              <button class="reject ${{cd === "reject" ? "on" : ""}}" data-candidate="${{c.candidate_id}}" data-decision="reject">不合适</button>
            </div>
            <textarea class="candidate-note" data-candidate-note="${{c.candidate_id}}" placeholder="这条候选哪里不对？如果改后用，需要怎么改？">${{cn}}</textarea>
            ${{isReuseItem(item)
              ? `<button class="candidate-ai-retry" disabled title="复用项默认不生成AI">复用项不生成AI</button>`
              : `<button class="candidate-ai-retry" data-regenerate-candidate="${{c.candidate_id}}">按这条反馈再生成AI</button>`}}
          </div>
        </article>`;
      }}).join("");
      const aiCandidates = visibleOutputs.map((candidate, index) => {{
        const path = aiOutputPath(candidate);
        const candidateId = candidate.candidate_id || `ai:${{path}}`;
        const cd = s.candidate_decisions[candidateId] || "";
        const cn = s.candidate_notes?.[candidateId] || "";
        const selectedClass = cd === "best" ? "best" : cd === "direct_use" ? "selected" : cd === "modify_use" ? "modify" : cd === "reject" ? "reject" : "";
        const scoreBlock = candidate.quality_score || candidate.feedback_score || candidate.semantic_score
          ? `<div><span class="badge good">综合分 ${{candidate.final_score || "-"}}</span><span class="badge">语义 ${{candidate.semantic_score || "-"}}</span><span class="badge">质量 ${{candidate.quality_score || "-"}}</span><span class="badge">偏好 ${{candidate.feedback_score || "-"}}</span></div>`
          : `<div><span class="badge ai-score">AI待试听评分</span></div>`;
        const durationText = candidate.duration_sec ? ` · ${{Number(candidate.duration_sec).toFixed(2)}}s` : "";
        return `<article class="candidate ${{selectedClass}}">
          <div>
            <div class="file">AI候选 ${{index + 1}} · ${{candidate.filename || path.split("/").pop()}}</div>
            <div class="file-meta">来源：公司API生成 · 已纳入正式候选评分${{durationText}}</div>
            ${{scoreBlock}}
            <div class="file-meta">${{candidate.match_reasons || ""}}</div>
            <div class="file-meta">${{path}}</div>
          </div>
          <div>
            <audio controls preload="none" src="${{outputUrl(path)}}"></audio>
            <div class="file-meta">本地AI生成试听</div>
          </div>
          <div>
            <div class="actions">
              <button class="best ${{cd === "best" ? "on" : ""}}" data-candidate="${{candidateId}}" data-decision="best" title="本条需求最终交付只取最佳；最佳单选">最佳</button>
              <button class="${{cd === "direct_use" ? "on" : ""}}" data-candidate="${{candidateId}}" data-decision="direct_use" title="可直接使用的备选，可多选；最终交付仍优先取最佳">直接用</button>
              <button class="modify ${{cd === "modify_use" ? "on" : ""}}" data-candidate="${{candidateId}}" data-decision="modify_use">改后用</button>
              <button class="reject ${{cd === "reject" ? "on" : ""}}" data-candidate="${{candidateId}}" data-decision="reject">不合适</button>
            </div>
            <textarea class="candidate-note" data-candidate-note="${{candidateId}}" placeholder="这条AI候选哪里不对？下一版需要怎么改？">${{cn}}</textarea>
            ${{isReuseItem(item)
              ? `<button class="candidate-ai-retry" disabled title="复用项默认不生成AI">复用项不生成AI</button>`
              : `<button class="candidate-ai-retry" data-regenerate-candidate="${{candidateId}}">按这条反馈再生成AI</button>`}}
          </div>
        </article>`;
      }}).join("");
      const candidateContent = hiddenLowScoreHint + candidates + aiCandidates || `<div class="empty">公司库没有可展示候选。需要 AI 补位时，请点击上方“AI生成候选”。</div>`;
      detail.innerHTML = `
        <h2>${{item.event_name}}</h2>
        <div class="meta">
          <div><span class="label">资源名</span>${{item.asset_name}}</div>
          <div><span class="label">资源包</span>${{item.resource_bank}}</div>
          <div><span class="label">优先级</span>${{item.priority}}</div>
          <div><span class="label">Loop / Stop</span>${{item.loop}} / ${{item.stop_event_needed}}</div>
        </div>
        <div class="desc"><strong>${{item.description_cn || item.asset_name}}</strong><br>${{item.trigger_timing}}<br><span class="label">Section</span>${{item.section}}</div>
        ${{reusePanel}}
        <div class="candidate-summary">${{summaryBadges}}</div>
        <div class="event-actions">
          ${{eventButtons}}
          ${{aiGenerateButton}}
          <span class="file-meta">事件级判断：${{decisionLabel(s.event_decision || "undecided")}}</span>
        </div>
        ${{generationPanel}}
        <div class="candidates">${{candidateContent}}</div>
        <textarea id="notes" placeholder="策划备注：为什么选它、需要怎么改、AI要补什么">${{s.notes || ""}}</textarea>
      `;
      detail.querySelectorAll("[data-event-decision]").forEach(button => {{
        button.addEventListener("click", () => setEventDecision(item.request_id, button.dataset.eventDecision));
      }});
      detail.querySelectorAll("[data-regenerate-ai]").forEach(button => {{
        button.addEventListener("click", () => startAiGeneration(item.request_id, {{ append: true }}));
      }});
      detail.querySelectorAll("[data-sync-ai-status]").forEach(button => {{
        button.addEventListener("click", () => syncAiGenerationStatus(button.dataset.syncAiStatus));
      }});
      detail.querySelectorAll("[data-candidate]").forEach(button => {{
        button.addEventListener("click", () => setCandidateDecision(item.request_id, button.dataset.candidate, button.dataset.decision));
      }});
      detail.querySelectorAll("[data-candidate-note]").forEach(input => {{
        input.addEventListener("input", event => setCandidateNote(item.request_id, input.dataset.candidateNote, event.target.value));
      }});
      detail.querySelectorAll("[data-regenerate-candidate]").forEach(button => {{
        button.addEventListener("click", () => regenerateFromCandidate(item.request_id, button.dataset.regenerateCandidate));
      }});
      detail.querySelector("#notes").addEventListener("input", event => setNotes(item.request_id, event.target.value));
      if (shouldScrollDetailTop || lastRenderedActiveId !== item.request_id) {{
        detail.scrollTop = 0;
        lastRenderedActiveId = item.request_id;
        shouldScrollDetailTop = false;
      }}
    }}

    function reviewRows() {{
      return manifest.map(item => {{
        const s = eventState(item.request_id);
        recomputeFinalSelection(s);
        const selectedId = s.selected_candidate_id || "";
        const selected = item.candidates.find(c => c.candidate_id === selectedId);
        const aiSelectedCandidate = visibleAiOutputs(s.ai_generation_outputs || [], item)
          .find(candidate => (candidate.candidate_id || `ai:${{aiOutputPath(candidate)}}`) === selectedId);
        const aiSelected = aiSelectedCandidate ? aiOutputPath(aiSelectedCandidate) : "";
        return {{
          request_id: item.request_id,
          event_name: item.event_name,
          asset_name: item.asset_name,
          source_sheet: item.source_sheet,
          section: item.section,
          demand_tag: item.demand_tag,
          description_cn: item.description_cn,
          resource_bank: item.resource_bank,
          trigger_timing: item.trigger_timing,
          priority: item.priority,
          loop: item.loop,
          stop_event_needed: item.stop_event_needed,
          event_decision: s.event_decision || "",
          selected_candidate_id: selectedId,
          selected_filename: selected?.filename || aiSelectedCandidate?.filename || "",
          selected_download_url: selected?.download_url || "",
          selected_local_preview_url: selected?.local_preview_url || aiSelectedCandidate?.local_preview_url || "",
          selected_source_path: aiSelected,
          candidate_decisions: s.candidate_decisions || {{}},
          candidate_notes: s.candidate_notes || {{}},
          notes: s.notes || "",
          prompt_en: item.prompt_en || ""
        }};
      }});
    }}

    function feedbackLabel(decision) {{
      return {{
        best: "best",
        direct_use: "usable",
        modify_use: "edit",
        reject: "miss"
      }}[decision] || "";
    }}

    function cleanSourcePath(path) {{
      if (!path) return "";
      return path.replace(/^\\.\\.\\//, "").replace(/^\\//, "");
    }}

    function profileLabels(item) {{
      const text = `${{item.section || ""}} ${{item.event_name || ""}} ${{item.asset_name || ""}} ${{item.description_cn || ""}} ${{item.prompt_en || ""}}`.toLowerCase();
      const labels = ["ui"];
      const checks = [
        ["card", ["card", "卡片", "choice"]],
        ["ssr", ["ssr", "金光", "gold", "premium"]],
        ["sr", ["sr", "银紫", "silver", "purple"]],
        ["magic", ["magic", "魔法", "aura"]],
        ["fire", ["fire", "火"]],
        ["water", ["water", "水"]],
        ["metal", ["metal", "金属"]],
        ["impact", ["impact", "冲击", "boom", "thud"]],
        ["button", ["button", "btn", "按钮", "click"]],
        ["slot", ["slotmachine", "老虎机"]]
      ];
      checks.forEach(([label, tokens]) => {{
        if (tokens.some(token => text.includes(token)) && !labels.includes(label)) labels.push(label);
      }});
      return labels.join("|");
    }}

    function feedbackRows() {{
      const rows = [];
      manifest.forEach(item => {{
        const s = eventState(item.request_id);
        (item.candidates || []).forEach(candidate => {{
          const decision = s.candidate_decisions?.[candidate.candidate_id] || "";
          const feedback = feedbackLabel(decision);
          if (!feedback) return;
          rows.push({{
            request_id: item.request_id,
            asset_name: item.asset_name,
            event_name: item.event_name,
            candidate_id: candidate.candidate_id,
            candidate_type: "company_library",
            source_path: cleanSourcePath(candidate.local_preview_url || candidate.download_url || ""),
            feedback,
            decision,
            note: s.candidate_notes?.[candidate.candidate_id] || "",
            semantic_score: candidate.semantic_score || "",
            rule_match_score: candidate.match_score || "",
            quality_score: candidate.quality_score || "",
            feedback_score: candidate.feedback_score || "",
            final_score: candidate.final_score || candidate.match_score || "",
            duration_sec: candidate.duration_sec || "",
            profile_labels: profileLabels(item),
            description_cn: item.description_cn,
            prompt_en: item.prompt_en
          }});
        }});
        visibleAiOutputs(s.ai_generation_outputs || [], item).forEach((candidate, index) => {{
          const path = aiOutputPath(candidate);
          const candidateId = candidate.candidate_id || `ai:${{path}}`;
          const decision = s.candidate_decisions?.[candidateId] || "";
          const feedback = feedbackLabel(decision);
          if (!feedback) return;
          const score = Number(candidate.final_score || candidate.match_score || aiCandidateScore(item, path, index));
          rows.push({{
            request_id: item.request_id,
            asset_name: item.asset_name,
            event_name: item.event_name,
            candidate_id: candidateId,
            candidate_type: "ai",
            source_path: cleanSourcePath(path),
            feedback,
            decision,
            note: s.candidate_notes?.[candidateId] || "",
            semantic_score: candidate.semantic_score || "",
            rule_match_score: candidate.rule_match_score || candidate.match_score || score,
            quality_score: candidate.quality_score || "",
            feedback_score: candidate.feedback_score || "",
            final_score: score,
            duration_sec: candidate.duration_sec || "",
            profile_labels: profileLabels(item),
            description_cn: item.description_cn,
            prompt_en: item.prompt_en
          }});
        }});
      }});
      return rows;
    }}

    function aiCandidateScore(item, path, index) {{
      let score = 72;
      const prompt = (item.prompt_en || "").toLowerCase();
      if (path.endsWith(".wav")) score += 8;
      if (path.toLowerCase().includes("combined")) score -= 8;
      if (prompt.includes("required layers")) score += 5;
      if ((eventState(item.request_id).notes || "").trim()) score += 3;
      score -= Math.min(index * 3, 9);
      return Math.max(50, Math.min(95, score));
    }}

    function showExport(filename, text, type, rowCount, metaText = "") {{
      const panel = document.getElementById("exportPanel");
      const download = document.getElementById("exportDownload");
      const content = document.getElementById("exportContent");
      const blob = new Blob([text], {{ type }});
      const url = URL.createObjectURL(blob);
      if (download.dataset.url) URL.revokeObjectURL(download.dataset.url);
      download.href = url;
      download.dataset.url = url;
      download.download = filename;
      document.getElementById("exportTitle").textContent = filename;
      document.getElementById("exportMeta").textContent = metaText || `已生成 ${{rowCount}} 行。点“下载文件”会保存到浏览器默认下载目录；如果没弹出下载，就复制下面内容。`;
      content.value = text;
      panel.hidden = false;
    }}

    function downloadText(filename, text, type, rowCount) {{
      showExport(filename, text, type, rowCount);
      const blob = new Blob([text], {{ type }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    }}

    function stateStats(value = state) {{
      const rows = Object.values(value || {{}});
      const decided = rows.filter(row => row && row.event_decision).length;
      const selected = rows.filter(row => row && row.selected_candidate_id).length;
      const ai = rows.filter(row => row && Array.isArray(row.ai_generation_outputs) && row.ai_generation_outputs.length).length;
      return {{ total: rows.length, decided, selected, ai }};
    }}

    function hasMeaningfulState(value = state) {{
      const stats = stateStats(value);
      return stats.decided > 0 || stats.selected > 0 || stats.ai > 0;
    }}

    async function backupReviewState() {{
      try {{
        const response = await fetch("http://127.0.0.1:8791/api/review-state/backup", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            state_key: stateKey,
            source_url: location.href,
            state
          }})
        }});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${{response.status}}`);
        const stats = stateStats();
        const currentReviewUrl = `${{location.origin}}${{location.pathname}}`;
        showMessage(
          "已备份当前选择",
          `已备份到 ${{data.path}}\\n事件状态 ${{stats.total}} 条，已判断 ${{stats.decided}} 条，已选候选 ${{stats.selected}} 条。\\n现在可以回到 ${{currentReviewUrl}} 并点“恢复备份选择”。`
        );
      }} catch (error) {{
        showMessage(
          "备份失败",
          `当前评审服务不提供状态备份 API。请先导出策划决策 JSON。\\n\\n错误：${{error.message}}`
        );
      }}
    }}

    async function restoreReviewState() {{
      try {{
        const response = await fetch("http://127.0.0.1:8791/api/review-state/backup");
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${{response.status}}`);
        if (!data.state || typeof data.state !== "object") throw new Error("备份文件里没有 state。");
        Object.entries(data.state).forEach(([id, value]) => {{
          state[id] = {{ ...(state[id] || {{}}), ...(value || {{}}) }};
        }});
        localStorage.setItem(stateKey, JSON.stringify(state));
        const stats = stateStats(data.state);
        showMessage(
          "已恢复备份选择",
          `来源：${{data.source_url || "unknown"}}\\n备份时间：${{data.saved_at || "unknown"}}\\n恢复事件状态 ${{stats.total}} 条，已判断 ${{stats.decided}} 条，已选候选 ${{stats.selected}} 条。`
        );
        render();
      }} catch (error) {{
        showMessage("恢复失败", `没有找到可恢复的备份，或服务未启动。\\n\\n错误：${{error.message}}`);
      }}
    }}

    function exportStateJson() {{
      const stats = stateStats();
      downloadText(
        "x15_review_state_backup.json",
        JSON.stringify({{ state_key: stateKey, source_url: location.href, exported_at: new Date().toISOString(), state }}, null, 2),
        "application/json",
        stats.total
      );
    }}

    function installStateMigrationGuard() {{
      if (location.protocol === "file:" && hasMeaningfulState()) {{
        window.setTimeout(() => {{
          backupReviewState();
        }}, 800);
        return;
      }}
      if (location.protocol.startsWith("http") && !hasMeaningfulState()) {{
        window.setTimeout(async () => {{
          try {{
            const response = await fetch("http://127.0.0.1:8791/api/review-state/backup");
            if (!response.ok) return;
            const data = await response.json();
            if (data.state && hasMeaningfulState(data.state)) {{
              Object.entries(data.state).forEach(([id, value]) => {{
                state[id] = {{ ...(state[id] || {{}}), ...(value || {{}}) }};
              }});
              localStorage.setItem(stateKey, JSON.stringify(state));
              render();
              const stats = stateStats(data.state);
              showMessage(
                "已自动恢复旧页面选择",
                `从备份恢复 ${{stats.total}} 条状态，已判断 ${{stats.decided}} 条，已选候选 ${{stats.selected}} 条。`
              );
            }}
          }} catch (error) {{
            // 静默失败，避免影响正常审核。
          }}
        }}, 1000);
      }}
    }}

    function csvCell(value) {{
      const text = value === undefined || value === null ? "" : String(value);
      return /[",\\n\\r]/.test(text) ? `"${{text.replaceAll('"', '""')}}"` : text;
    }}

    function jsonCell(value) {{
      return JSON.stringify(value || {{}});
    }}

    function generationVariantCount(item) {{
      const selected = document.getElementById("aiVariantCount")?.value || "auto";
      if (selected !== "auto") return selected;
      if ((item.priority || "").toUpperCase() === "P0") return "6";
      if ((item.priority || "").toUpperCase() === "P1") return "5";
      return "4";
    }}

    function toCsv(rows, fields) {{
      return [
        fields.join(","),
        ...rows.map(row => fields.map(field => csvCell(row[field])).join(","))
      ].join("\\n") + "\\n";
    }}

    function aiGapRows() {{
      return reviewRows()
        .filter(row => row.event_decision === "ai_needed" || row.event_decision === "auto_ai")
        .filter(row => aiAllowed(manifest.find(item => item.request_id === row.request_id) || {{}}))
        .map(row => ({{
          request_id: row.request_id,
          event_name: row.event_name,
          asset_name: row.asset_name,
          resource_bank: row.resource_bank,
          priority: row.priority,
          loop: row.loop,
          prompt_en: row.prompt_en,
          ai_generation_status: "queued_by_planner",
          variants_needed: generationVariantCount(manifest.find(item => item.request_id === row.request_id) || {{ priority: row.priority }}),
          generate_combined: shouldGenerateCombined() ? "TRUE" : "FALSE",
          planner_notes: row.notes,
          candidate_notes: jsonCell(row.candidate_notes),
          selected_candidate_note: row.candidate_notes?.[row.selected_candidate_id] || row.notes || "",
          description_cn: row.description_cn,
          trigger_timing: row.trigger_timing
        }}));
    }}

    const aiGenerationEndpoint = "http://127.0.0.1:8791/api/ai-gap/generate";

    function rowForAiGeneration(item) {{
      const s = eventState(item.request_id);
      return {{
        request_id: item.request_id,
        sheet_name: item.source_sheet || manifest[0]?.source_sheet || "",
        event_name: item.event_name,
        asset_name: item.asset_name,
        resource_bank: item.resource_bank,
        priority: item.priority,
        loop: item.loop,
        prompt_en: item.prompt_en,
        ai_generation_status: "queued_by_planner",
        variants_needed: generationVariantCount(item),
        generate_combined: shouldGenerateCombined() ? "TRUE" : "FALSE",
        planner_notes: s.notes || "",
        candidate_notes: s.candidate_notes || {{}},
        selected_candidate_note: noteForGeneration(item),
        description_cn: item.description_cn,
        trigger_timing: item.trigger_timing
      }};
    }}

    function updateAiStatus(id, patch) {{
      Object.assign(eventState(id), patch);
      localStorage.setItem(stateKey, JSON.stringify(state));
      render();
    }}

    function regenerateFromCandidate(id, candidateId) {{
      const s = eventState(id);
      s.selected_candidate_id = candidateId;
      s.event_decision = "ai_needed";
      localStorage.setItem(stateKey, JSON.stringify(state));
      startAiGeneration(id, {{ append: true }});
    }}

    function mergeOutputs(existing, incoming) {{
      const merged = [...(existing || [])];
      const seen = new Set(merged.map(aiOutputPath));
      (incoming || []).forEach(output => {{
        const path = aiOutputPath(output);
        if (path && !seen.has(path)) {{
          merged.push(output);
          seen.add(path);
        }}
      }});
      return merged;
    }}

    function showMessage(title, message) {{
      showExport(title, message, "text/plain", 1);
    }}

    function aiStatusUrl(jobId) {{
      return `http://127.0.0.1:8791/api/ai-gap/status/${{jobId}}`;
    }}

    function isPendingAiStatus(status) {{
      return ["请求生成服务中", "请求新增AI候选中", "排队等待生成", "已入队"].includes(status || "")
        || (status || "").startsWith("生成中");
    }}

    async function applyAiGenerationStatus(id, jobId, statusUrl) {{
        const response = await fetch(statusUrl);
        const data = await response.json();
        if (data.status === "missing") {{
          updateAiStatus(id, {{
            ai_generation_status: "任务已失效，请重新生成",
            ai_generation_error: data.error || "Job not found."
          }});
          return true;
        }}
        if (data.status === "done") {{
          const incomingOutputs = data.ai_candidates || data.outputs || [];
          const mergedOutputs = mergeOutputs(eventState(id).ai_generation_outputs, incomingOutputs);
          updateAiStatus(id, {{
            ai_generation_status: "完成",
            ai_generation_outputs: mergedOutputs,
            ai_generation_error: "",
            event_decision: eventState(id).event_decision || "auto_ai"
          }});
          showMessage("AI生成完成", `${{id}} 已生成并完成正式评分：\\n${{incomingOutputs.map(aiOutputPath).join("\\n")}}`);
          return true;
        }}
        if (data.status === "failed") {{
          updateAiStatus(id, {{
            ai_generation_status: "失败",
            ai_generation_error: data.error || "unknown error"
          }});
          showMessage("AI生成失败", `${{id}} 生成失败：\\n${{data.error || "unknown error"}}`);
          return true;
        }}
        updateAiStatus(id, {{
          ai_generation_status: data.message || "生成中",
          ai_generation_job_id: jobId,
          event_decision: eventState(id).event_decision || "auto_ai",
          ai_generation_outputs: mergeOutputs(eventState(id).ai_generation_outputs, data.ai_candidates || data.outputs || [])
        }});
        return false;
    }}

    async function pollAiGeneration(id, jobId, statusUrl) {{
      for (let attempt = 0; attempt < 360; attempt += 1) {{
        const finished = await applyAiGenerationStatus(id, jobId, statusUrl);
        if (finished) return;
        await new Promise(resolve => setTimeout(resolve, 2000));
      }}
      updateAiStatus(id, {{ ai_generation_status: "生成中，稍后点同步状态" }});
    }}

    async function syncAiGenerationStatus(id) {{
      const s = eventState(id);
      if (!s.ai_generation_job_id) {{
        showMessage("暂无AI任务", `${{id}} 还没有可同步的AI生成任务。`);
        return;
      }}
      try {{
        await applyAiGenerationStatus(id, s.ai_generation_job_id, aiStatusUrl(s.ai_generation_job_id));
      }} catch (error) {{
        updateAiStatus(id, {{ ai_generation_status: "同步失败", ai_generation_error: error.message }});
        showMessage("AI状态同步失败", `${{id}} 同步失败：\\n${{error.message}}`);
      }}
    }}

    function resumePendingAiJobs() {{
      manifest.forEach(item => {{
        const s = eventState(item.request_id);
        if (s.ai_generation_job_id && isPendingAiStatus(s.ai_generation_status)) {{
          pollAiGeneration(item.request_id, s.ai_generation_job_id, aiStatusUrl(s.ai_generation_job_id));
        }}
      }});
    }}

    function autoStartAiForLibraryGaps() {{
      manifest.forEach(item => {{
        if (!companyLibraryNeedsAi(item)) return;
        const s = eventState(item.request_id);
        const hasOutputs = (s.ai_generation_outputs || []).length > 0;
        const hasPendingJob = s.ai_generation_job_id && isPendingAiStatus(s.ai_generation_status);
        const alreadyMarkedAi = ["ai_needed", "auto_ai"].includes(s.event_decision || "");
        if (hasOutputs || hasPendingJob || s.event_decision === "direct_use" || s.event_decision === "modify_use" || s.event_decision === "reject") return;
        s.event_decision = alreadyMarkedAi ? s.event_decision : "auto_ai";
        if (!s.ai_generation_status) {{
          s.ai_generation_status = (item.candidate_count || 0) <= 0 ? "公司库无候选，自动AI补位" : "公司库候选分低，自动AI补位";
        }}
        startAiGeneration(item.request_id, {{ auto: true, silent: true }});
      }});
      localStorage.setItem(stateKey, JSON.stringify(state));
    }}

    async function startAiGeneration(id, options = {{}}) {{
      const item = manifest.find(event => event.request_id === id);
      if (!item) return;
      if (!aiAllowed(item)) {{
        showMessage("复用项不生成AI", `${{id}} 是复用/沿用类需求，应优先使用目标资源名：${{item.asset_name}}。`);
        return;
      }}
      const current = eventState(id);
      if (!enableAiApi) {{
        updateAiStatus(id, {{
          ai_generation_status: "当前页面是离线模式，不能直接生成",
          ai_generation_outputs: current.ai_generation_outputs || [],
          ai_generation_error: "请用 --enable-ai-api 重建页面，并启动 serve_review.py",
          event_decision: "ai_needed"
        }});
        showMessage("AI生成未启用", `${{id}} 当前页面未启用实时 AI 生成接口。请重建页面时加 --enable-ai-api，并启动本地 review 服务。`);
        return;
      }}
      if (["请求生成服务中", "请求新增AI候选中"].includes(current.ai_generation_status) || (current.ai_generation_status || "").startsWith("生成中")) return;
      updateAiStatus(id, {{ ai_generation_status: options.append ? "请求新增AI候选中" : "请求生成服务中", ai_generation_outputs: current.ai_generation_outputs || [], ai_generation_error: "", event_decision: current.event_decision || "auto_ai" }});
      try {{
        const response = await fetch(aiGenerationEndpoint, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(rowForAiGeneration(item))
        }});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${{response.status}}`);
        updateAiStatus(id, {{
          ai_generation_status: "生成中",
          ai_generation_job_id: data.job_id,
          ai_generation_outputs: eventState(id).ai_generation_outputs || []
        }});
        pollAiGeneration(id, data.job_id, data.status_url);
      }} catch (error) {{
        updateAiStatus(id, {{
          ai_generation_status: "未连接生成服务",
          ai_generation_error: error.message
        }});
        if (options.silent) return;
        showMessage(
          "AI生成服务未启动",
          `${{id}} 没有生成成功，因为本地 AI 生成服务没有连上。\\n\\n请启动 dev-235 的 serve_review.py 后再点 AI生成。\\n\\n错误：${{error.message}}`
        );
      }}
    }}

    function exportState() {{
      const rows = reviewRows();
      downloadText(
        "x15_company_library_planner_decisions.json",
        JSON.stringify(rows, null, 2),
        "application/json",
        rows.length
      );
    }}

    async function submitProductionPackage() {{
      const button = document.getElementById("submitPackageBtn");
      const originalText = button.textContent;
      button.disabled = true;
      button.textContent = "正在生成交付包...";
      try {{
        const response = await fetch("/api/production-package/build", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            sheet_name: manifest[0]?.source_sheet || "",
            decisions: reviewRows()
          }})
        }});
        const data = await response.json();
        if (!response.ok || !data.ok) {{
          const incomplete = (data.incomplete || [])
            .map(row => `${{row.event || row.asset}}: ${{row.reason}}`)
            .join("\\n");
          const failedSteps = (data.steps || [])
            .filter(step => !step.ok)
            .map(step => `${{step.script}}:\\n${{step.stderr || step.stdout || "未通过"}}`)
            .join("\\n\\n");
          throw new Error(incomplete || failedSteps || data.error || data.message || `HTTP ${{response.status}}`);
        }}
        const artifacts = data.artifacts || {{}};
        showMessage(
          "交付包已生成",
          `${{data.message}}\\n\\n配置意图表：${{artifacts.audio_sheet}}\\n最终音频：${{artifacts.audio_root}}\\n交付清单：${{artifacts.final_manifest}}`
        );
      }} catch (error) {{
        showMessage("暂不能生成最终交付包", `判断已尝试保存。请完成以下项目：\\n\\n${{error.message}}`);
      }} finally {{
        button.disabled = false;
        button.textContent = originalText;
      }}
    }}

    function exportFeedback() {{
      const rows = feedbackRows();
      const fields = [
        "request_id",
        "asset_name",
        "event_name",
        "candidate_id",
        "candidate_type",
        "source_path",
        "feedback",
        "decision",
        "note",
        "semantic_score",
        "rule_match_score",
        "quality_score",
        "feedback_score",
        "final_score",
        "duration_sec",
        "profile_labels",
        "description_cn",
        "prompt_en"
      ];
      downloadText(
        "x15_sfx_feedback.csv",
        toCsv(rows, fields),
        "text/csv;charset=utf-8",
        rows.length
      );
    }}

    async function buildProgramPackage() {{
      try {{
        const response = await fetch("http://127.0.0.1:8791/api/program-package/build", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            package_name: "X15_Program_Audio_Package",
            simulate: true,
            review_rows: reviewRows()
          }})
        }});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${{response.status}}`);
        const manifestResponse = await fetch(`/${{data.manifest}}`);
        const manifestCsv = await manifestResponse.text();
        showExport(
          "Program_Integration_Manifest.csv",
          manifestCsv,
          "text/csv;charset=utf-8",
          data.final_count,
          [
            `程序表：${{data.manifest}}`,
            `AudioEvent配置：${{data.audio_event_config}}`,
            `DisplayKey流水线表：${{data.displaykey_sheet}}`,
            `最终音频目录：${{data.audio_root}}`,
            `未完成检查：${{data.incomplete}}`,
            `改后用清单：${{data.needs_edit}}`,
            `最终音频 ${{data.final_count}} 条，未完成 ${{data.incomplete_count}} 条，需修改 ${{data.needs_edit_count}} 条。`
          ].join("  ")
        );
      }} catch (error) {{
        showMessage(
          "程序接入包生成失败",
          `当前评审服务不生成程序接入包。请在 handoff-ready 验证通过后使用 audio-config-pipeline。\\n\\n错误：${{error.message}}`
        );
      }}
    }}

    function exportAiQueue() {{
      const rows = aiGapRows();
      const fields = [
        "request_id",
        "event_name",
        "asset_name",
        "resource_bank",
        "priority",
        "loop",
        "prompt_en",
        "ai_generation_status",
        "variants_needed",
        "planner_notes",
        "candidate_notes",
        "selected_candidate_note",
        "description_cn",
        "trigger_timing"
      ];
      downloadText(
        "x15_ai_gap_queue_from_planner.csv",
        toCsv(rows, fields),
        "text/csv;charset=utf-8",
        rows.length
      );
    }}

    function render() {{
      renderStats();
      renderList();
      renderDetail();
    }}

    renderFilters();
    render();
    resumePendingAiJobs();
    {auto_ai_bootstrap}
    installStateMigrationGuard();
    ["search", "bank", "decision", "candidateFilter", "reuseFilter", "scoreFilter", "candidateSort"].forEach(id => document.getElementById(id).addEventListener("input", render));
    document.getElementById("exportBtn").addEventListener("click", exportState);
    document.getElementById("exportFeedbackBtn").addEventListener("click", exportFeedback);
    document.getElementById("exportAiBtn").addEventListener("click", exportAiQueue);
    document.getElementById("exportStateJsonBtn").addEventListener("click", exportStateJson);
    document.getElementById("submitPackageBtn").addEventListener("click", submitProductionPackage);
    document.getElementById("closeExport").addEventListener("click", () => document.getElementById("exportPanel").hidden = true);
    document.getElementById("copyExport").addEventListener("click", async () => {{
      const content = document.getElementById("exportContent");
      content.select();
      try {{
        await navigator.clipboard.writeText(content.value);
        document.getElementById("exportMeta").textContent += " 已复制。";
      }} catch (error) {{
        document.execCommand("copy");
        document.getElementById("exportMeta").textContent += " 已尝试复制。";
      }}
    }});
  </script>
</body>
</html>
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    manifest_path.write_text(data_json + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--preview-map", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title", default="X15 公司资产库候选筛选")
    parser.add_argument("--subtitle", default="先听公司库候选，标记直接用、改后用、不合适；如果整个事件没有合适候选，再在事件级标记需要 AI。短候选已缓存到本地试听，不走 Wwise。")
    parser.add_argument("--state-key", default="x15-company-library-review-state-v1")
    parser.add_argument("--scored-manifest", type=Path)
    parser.add_argument("--ai-manifest", type=Path)
    parser.add_argument("--auto-start-ai", action="store_true")
    parser.add_argument("--enable-ai-api", action="store_true")
    args = parser.parse_args()
    master = args.master
    candidates = args.candidates
    preview_map = args.preview_map
    manifest_path = args.manifest
    output = args.output
    manifest = build_manifest(master, candidates, preview_map)
    manifest = merge_scored_manifest(manifest, args.scored_manifest)
    manifest = merge_ai_manifest(manifest, args.ai_manifest)
    write_page(
        output,
        manifest,
        manifest_path,
        args.title,
        args.subtitle,
        args.state_key,
        auto_start_ai=args.auto_start_ai,
        enable_ai_api=args.enable_ai_api,
    )
    print(f"Wrote {output}")
    print(f"Wrote {manifest_path}")
    print(f"Events: {len(manifest)}")
    print(f"Candidates: {sum(len(item['candidates']) for item in manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
