#!/usr/bin/env python3
"""Build a K1 audio reuse reference from AudioListCfg.tsv and audio filenames."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT_HINTS = [
    Path("k1_client/client/Assets/Res/config/AudioListCfg.tsv"),
    Path("client/Assets/Res/config/AudioListCfg.tsv"),
    Path("Assets/Res/config/AudioListCfg.tsv"),
]

AUDIO_DIR_HINTS = [
    Path("k1_client/client/Assets/k1/K1D1/Res/Audios"),
    Path("k1_client/client/Assets/k1/Res/Audio"),
    Path("k1_client/client/Assets/Res/Audio"),
    Path("client/Assets/k1/K1D1/Res/Audios"),
    Path("client/Assets/k1/Res/Audio"),
    Path("client/Assets/Res/Audio"),
    Path("Assets/k1/K1D1/Res/Audios"),
    Path("Assets/k1/Res/Audio"),
    Path("Assets/Res/Audio"),
]

AUDIOCONST_HINTS = [
    Path("k1_client/client/Assets/k1/Script/HotfixScripts/Config/ConstConfig/AudioConst.cs"),
    Path("client/Assets/k1/Script/HotfixScripts/Config/ConstConfig/AudioConst.cs"),
    Path("Assets/k1/Script/HotfixScripts/Config/ConstConfig/AudioConst.cs"),
]

CATEGORY_RULES = [
    ("ui_click", "UI通用点击/按钮", ["generic", "button", "click", "btn", "ui_i_generic", "ui_h_button"]),
    ("ui_close", "UI关闭/返回", ["close", "back", "return", "menu_close"]),
    ("ui_open_popup", "UI打开/弹窗/出现", ["popup", "appear", "open", "show", "menu_open", "envelope_popup"]),
    ("ui_tab_select", "UI切换/选中/列表", ["tab", "switch", "select", "label", "lable", "horizontal", "ruler"]),
    ("reward_claim", "奖励/领取/获得", ["reward", "claim", "collect", "congratulation", "receive", "item", "coin", "diamond"]),
    ("chest_card", "宝箱/卡牌/抽取", ["chest", "card", "draw", "box"]),
    ("upgrade_unlock", "升级/解锁/成长", ["upgrade", "levelup", "lvup", "unlock", "star", "skill_upgrade", "waken"]),
    ("negative_error", "错误/不可用/失败提示", ["error", "negative", "buyerror", "lost", "defeat", "lock"]),
    ("map_world", "地图/行军/世界交互", ["map", "march", "rally", "teleport", "shield", "troop", "world", "unit"]),
    ("city_building", "城市/建筑/生产", ["city", "building", "castle", "alliance", "research", "training"]),
    ("battle_skill", "战斗/技能/命中", ["battle", "fight", "skill", "attack", "hit", "launch", "arrow", "dragon"]),
    ("activity_gameplay", "活动玩法专用", ["kingopoly", "roguelike", "treasure", "slot", "halloween", "valentine", "capybara", "collapse"]),
    ("bgm_amb_loop", "BGM/环境/循环", ["music", "mus_", "bgm", "amb", "loop", "soundtrack"]),
]

COMMON_REUSE_PATTERNS = [
    ("通用按钮点击", ["ui_i_generic", "uigeneric", "generic", "button", "click"]),
    ("关闭/返回按钮", ["ui_close", "ui_back", "close", "back", "return"]),
    ("普通弹窗打开/关闭", ["popup", "menu_open", "menu_close", "open", "close"]),
    ("页签/横向切换/选中", ["switch", "select", "horizontal", "label", "lable"]),
    ("领取/获得奖励", ["claim", "reward", "collect", "receive"]),
    ("宝箱/卡牌表现", ["chest", "card", "draw"]),
    ("升级/解锁/成功反馈", ["upgrade", "levelup", "unlock", "success", "star"]),
    ("错误/不可点击反馈", ["error", "negative", "buyerror", "lock"]),
    ("金币/道具飞入或增长", ["coin", "item", "diamond", "fly", "increase"]),
    ("地图点击/行军/传送", ["map", "march", "teleport", "troop", "rally", "shield"]),
    ("循环环境/BGM", ["amb", "bgm", "music", "loop", "mus_"]),
]


@dataclass
class AudioRow:
    audio_id: str
    asset: str
    time: str
    typ: str
    mode: str
    scene: str
    priority: str
    vol_scale: str
    const_name: str = ""
    remark: str = ""
    exists: bool = False

    @property
    def basename(self) -> str:
        return Path(self.asset).name

    @property
    def stem(self) -> str:
        return Path(self.asset).stem

    @property
    def haystack(self) -> str:
        return f"{self.asset} {self.const_name} {self.remark}".lower()


def find_first(root: Path, hints: list[Path]) -> Path | None:
    for hint in hints:
        candidate = root / hint
        if candidate.exists():
            return candidate
    return None


def normalize_asset_path(path: str) -> str:
    return path.replace("\\", "/").replace("Assets/K1/", "Assets/k1/")


def parse_audio_const(path: Path | None) -> dict[str, tuple[str, str]]:
    if path is None or not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    result: dict[str, tuple[str, str]] = {}
    pending: list[str] = []
    for line in text:
        stripped = line.strip()
        if stripped.startswith("///"):
            content = re.sub(r"^///\s?", "", stripped)
            content = re.sub(r"</?summary>", "", content).strip()
            if content:
                pending.append(content)
            continue
        match = re.search(r"public\s+(?:static\s+)?(?:const\s+)?int\s+(\w+)\s*=\s*(\d+)", stripped)
        if match:
            name, audio_id = match.groups()
            remark = " ".join(pending).strip()
            result[audio_id] = (name, remark)
        pending = []
    return result


def load_rows(tsv_path: Path, const_map: dict[str, tuple[str, str]]) -> list[AudioRow]:
    rows: list[AudioRow] = []
    with tsv_path.open("r", encoding="utf-8", errors="ignore", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for raw in reader:
            audio_id = raw.get("C_INT_id", "").strip()
            const_name, remark = const_map.get(audio_id, ("", ""))
            rows.append(
                AudioRow(
                    audio_id=audio_id,
                    asset=normalize_asset_path(raw.get("C_STR_asset", "").strip()),
                    time=raw.get("C_FLT_time", "").strip(),
                    typ=raw.get("C_INT_typ", "").strip(),
                    mode=raw.get("C_INT_mode", "").strip(),
                    scene=raw.get("C_INT_scene", "").strip(),
                    priority=raw.get("C_INT_priority", "").strip(),
                    vol_scale=raw.get("C_FLT_vol_scale", "").strip(),
                    const_name=const_name,
                    remark=remark,
                )
            )
    return rows


def scan_audio_files(root: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for hint in AUDIO_DIR_HINTS:
        base = root / hint
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix.lower() in {".wav", ".ogg", ".mp3"}:
                rel = path.relative_to(root).as_posix()
                asset_style = rel
                if asset_style.startswith("k1_client/client/"):
                    asset_style = asset_style[len("k1_client/client/") :]
                elif asset_style.startswith("client/"):
                    asset_style = asset_style[len("client/") :]
                found[normalize_asset_path(asset_style).lower()] = path
                found[path.name.lower()] = path
    return found


def categorize(row: AudioRow) -> str:
    for key, _, terms in CATEGORY_RULES:
        if any(term in row.haystack for term in terms):
            return key
    return "other"


def category_title(key: str) -> str:
    for rule_key, title, _ in CATEGORY_RULES:
        if rule_key == key:
            return title
    return "其他/待人工试听"


def score_pattern(row: AudioRow, terms: list[str]) -> int:
    text = row.haystack.replace("_", " ")
    return sum(1 for term in terms if term.lower() in text)


def render_candidates(rows: list[AudioRow], terms: list[str], limit: int = 10) -> list[AudioRow]:
    scored = [(score_pattern(row, terms), row) for row in rows]
    picked = [row for score, row in sorted(scored, key=lambda item: (-item[0], item[1].audio_id)) if score > 0]
    return picked[:limit]


def markdown_table(rows: list[AudioRow]) -> str:
    if not rows:
        return "_未命中，需要回到 `AudioListCfg.tsv` 继续检索或试听。_"
    lines = ["| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |", "|---|---|---|---|---|"]
    for row in rows:
        note = row.remark or row.const_name
        if row.const_name and row.remark:
            note = f"{row.const_name}: {row.remark}"
        lines.append(f"| `{row.audio_id}` | `{row.basename}` | {note or '-'} | `{row.scene}` | `{row.typ}` |")
    return "\n".join(lines)


def render_markdown(root: Path, tsv_path: Path, rows: list[AudioRow], audio_files: dict[str, Path]) -> str:
    asset_lookup = set(audio_files.keys())
    for row in rows:
        row.exists = row.asset.lower() in asset_lookup or row.basename.lower() in asset_lookup

    categories: dict[str, list[AudioRow]] = defaultdict(list)
    for row in rows:
        categories[categorize(row)].append(row)

    type_counts = Counter(row.typ for row in rows)
    scene_counts = Counter(row.scene for row in rows)
    missing = [row for row in rows if not row.exists]

    lines: list[str] = []
    lines.append("# K1 项目组音效复用库")
    lines.append("")
    lines.append("来源：`AudioListCfg.tsv`、`AudioConst.cs` 注释、仓库内 `.wav/.ogg/.mp3` 文件名。")
    lines.append("")
    lines.append("## 使用规则")
    lines.append("")
    lines.append("- K1 项目拆音效需求前，先查本库；命中同类语义时，标注 `复用`，资源名填已有 ID 或文件名。")
    lines.append("- 常规 UI 反馈、奖励领取、宝箱卡牌、升级解锁、错误提示、地图行军、BGM/环境音优先复用。")
    lines.append("- 活动玩法、角色技能、强主题包装音效只有在现有语义不贴合时才标注 `新增`。")
    lines.append("- 表格没有独立备注列时，以 `AudioConst` 注释和文件名语义作为复用判断依据；最终需要人工试听确认。")
    lines.append("")
    lines.append("## 资源概况")
    lines.append("")
    lines.append(f"- 配表：`{tsv_path.relative_to(root).as_posix()}`")
    lines.append(f"- 配表条目：{len(rows)}")
    lines.append(f"- 扫描到音频文件：{len({p for p in audio_files.values()})}")
    lines.append(f"- 配表资源未在本地文件名中直接命中：{len(missing)}")
    lines.append(f"- 类型统计 `C_INT_typ`：{dict(type_counts)}")
    lines.append(f"- 场景统计 `C_INT_scene`：{dict(scene_counts)}")
    lines.append("")
    lines.append("## 常用复用入口")
    lines.append("")
    for label, terms in COMMON_REUSE_PATTERNS:
        lines.append(f"### {label}")
        lines.append("")
        lines.append(markdown_table(render_candidates(rows, terms)))
        lines.append("")
    lines.append("## 分类索引")
    lines.append("")
    for key in [rule[0] for rule in CATEGORY_RULES] + ["other"]:
        group = sorted(categories.get(key, []), key=lambda row: int(row.audio_id) if row.audio_id.isdigit() else 0)
        if not group:
            continue
        lines.append(f"### {category_title(key)}")
        lines.append("")
        lines.append(f"共 {len(group)} 条。优先检索关键词：`{'`, `'.join(next((r[2] for r in CATEGORY_RULES if r[0] == key), []))}`")
        lines.append("")
        lines.append(markdown_table(group[:40]))
        if len(group) > 40:
            lines.append("")
            lines.append(f"_还有 {len(group) - 40} 条同类配置，继续在 `AudioListCfg.tsv` 按关键词/ID 检索。_")
        lines.append("")
    lines.append("## 快速检索命令")
    lines.append("")
    lines.append("```powershell")
    lines.append("rg -n -i \"click|button|close|reward|claim|chest|upgrade|unlock|error|map|march|skill|loop\" k1_client\\client\\Assets\\Res\\config\\AudioListCfg.tsv")
    lines.append("rg --files k1_client\\client\\Assets\\k1\\K1D1\\Res\\Audios k1_client\\client\\Assets\\k1\\Res\\Audio k1_client\\client\\Assets\\Res\\Audio | rg -i \"click|button|close|reward|claim|chest|upgrade|unlock|error|map|march|skill|loop\"")
    lines.append("```")
    lines.append("")
    lines.append("## 维护")
    lines.append("")
    lines.append("K1 音频资源或配表变化后，在 K1 仓库根目录运行：")
    lines.append("")
    lines.append("```powershell")
    lines.append("python scripts/build_k1_audio_library.py --project-root <K1仓库根> --output references/k1-audio-library.md --json-output references/k1-audio-library.json")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build K1 audio reuse library markdown.")
    parser.add_argument("--project-root", default=".", help="K1 repository/workspace root.")
    parser.add_argument("--output", required=True, help="Markdown output path.")
    parser.add_argument("--json-output", help="Optional JSON index output path.")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    tsv_path = find_first(root, ROOT_HINTS)
    if tsv_path is None:
        raise SystemExit("AudioListCfg.tsv not found under project root.")

    const_path = find_first(root, AUDIOCONST_HINTS)
    const_map = parse_audio_const(const_path)
    rows = load_rows(tsv_path, const_map)
    audio_files = scan_audio_files(root)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(root, tsv_path, rows, audio_files), encoding="utf-8")

    if args.json_output:
        data = [
            {
                "id": row.audio_id,
                "asset": row.asset,
                "file": row.basename,
                "category": categorize(row),
                "const": row.const_name,
                "remark": row.remark,
                "time": row.time,
                "typ": row.typ,
                "mode": row.mode,
                "scene": row.scene,
                "priority": row.priority,
                "vol_scale": row.vol_scale,
            }
            for row in rows
        ]
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
