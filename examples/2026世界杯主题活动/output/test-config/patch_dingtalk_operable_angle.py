# -*- coding: utf-8 -*-
"""Insert operable-angle rules into DingTalk doc section 3.2."""
import json
import subprocess
import sys

DWS = r"C:\Users\jiangzhenyu\.local\bin\dws.exe"
NODE = "amweZ92PV6vDZdmDCKwo2Ev4VxEKBD6p"

RULE_BULLETS = [
    "**操作夹角约束**（非守门切片）：",
    "    **总则**：进入可操作态前，系统生成可操作夹角扇形 [θ_min, θ_max]（水平面，以控球球员为顶点）。扇形**以接球方向为锚**，宽度在 angle_span_min ~ angle_span_max 内调整；玩家划线/弹弓方向超出扇形时 clamp 到边界（MVP 建议 clamp）。",
    "    **合法目标**：本切片内可作为出脚方向的合法目标包括——**球门**（有效得分区中心或配置 scoring 点）、**我方其他球员**（players_init 中同队且非当前控球者）。对方球员、场外点、纯 UI 装饰箭头不算合法目标。",
    "    **覆盖判定**：扇形内须**至少存在一个合法目标**（不要求包含全部合法目标）。多个合法目标时，只要任意一个落在扇形内即满足进入可操作态的前置条件。",
    "    **接球方向 receive_dir**：上一脚为队友传球时 = 传球者→接球者水平方向；否则取 ball_vector 或控球球员初始 facing。",
    "    **扇形生成**：以 receive_dir 为初始中心，在 [receive_dir ± angle_max_center_shift] 内搜索中心角；对每个候选中心取满足「扇形内 ∃ 合法目标」的**最小** span，再 clamp 到 [angle_span_min, angle_span_max]；若有多个可行解，取 span 最小者。",
    "    **带球调整 dribble_realign**：若在 span = angle_span_max 且中心已扫完允许偏移范围后，扇形内仍不存在任何合法目标，则不进入可操作态，自动执行带球：控球球员转向**最近的合法目标**，更新 facing_dir 后重新生成扇形；重复直至扇形内存在合法目标，再进入可操作态。**带球调整无次数上限**；调整期间不可操作；不改变 objective、不额外消耗切片。",
    "    **与 objective 的关系**：扇形覆盖保证「有路可走」；切片成功/失败仍由当前 objectives 独立判定。",
    "    **回溯**：回溯重置后，面向、扇形与 realign_count 一并回到切片 players_init 初始状态。",
    "    **守门切片**：不适用本规则。",
]

FLOWCHART_HEADING = "操作夹角与带球调整流程（非守门切片，进入可操作态前）"
FLOWCHART = """flowchart TD
    A[接球完成] --> B[计算 receive_dir 与 legal_targets]
    B --> C{在 span_min~max 内<br/>扇形内 ∃ 合法目标?}
    C -->|是| D[进入可操作态·显示扇形]
    C -->|否| E[选最近合法目标 T_nearest]
    E --> F[带球转向面向 T_nearest]
    F --> G[更新 facing_dir]
    G --> C
    D --> H[玩家划线/弹弓·方向 clamp 在扇形内]"""

PRESET_NOTE = (
    "**slice_preset 补充字段**（operable_angle 保留为兼容字段，默认等于 angle_span_max）："
    "angle_span_min、angle_span_max、angle_max_center_shift、angle_margin。"
)

RUNTIME_NOTE = (
    "**slice_runtime 补充字段**：receive_dir、operable_angle_center、operable_angle_min/max、"
    "realign_count（≥0，无上限）、legal_targets_resolved。"
)


def run(args):
    r = subprocess.run(
        [DWS, *args, "-y", "--timeout", "120000"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if r.returncode != 0:
        print("FAIL:", " ".join(args[:4]), file=sys.stderr)
        print(r.stdout or r.stderr, file=sys.stderr)
        sys.exit(r.returncode)
    return r.stdout


def insert_list(index, text):
    run(
        [
            "doc",
            "block",
            "insert",
            "--node",
            NODE,
            "--index",
            str(index),
            "--type",
            "unorderedList",
            "--text",
            text,
        ]
    )


def insert_heading(index, text, level=4):
    run(
        [
            "doc",
            "block",
            "insert",
            "--node",
            NODE,
            "--index",
            str(index),
            "--type",
            "heading",
            "--heading",
            text,
            "--level",
            str(level),
        ]
    )


def insert_paragraph(index, text):
    run(
        [
            "doc",
            "block",
            "insert",
            "--node",
            NODE,
            "--index",
            str(index),
            "--type",
            "paragraph",
            "--text",
            text,
        ]
    )


def find_index(sub):
    r = subprocess.run(
        [DWS, "doc", "block", "list", "--node", NODE, "--timeout", "120000", "-f", "json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    blocks = json.loads(r.stdout).get("blocks", [])
    for i, b in enumerate(blocks):
        el = b.get("element") or b
        text = json.dumps(el, ensure_ascii=False)
        ul = (el.get("unorderedList") or {}).get("text", "")
        para = (el.get("paragraph") or {}).get("text", "")
        if sub in text or sub in ul or sub in para:
            return i
    raise SystemExit(f"block not found: {sub!r}")


def main():
    aim_idx = find_index("瞄准辅助线")
    print(f"Insert rules after block {aim_idx} (瞄准辅助线)")
    insert_at = aim_idx + 1
    for text in reversed(RULE_BULLETS):
        insert_list(insert_at, text)
        print("  + list")

    # Re-find flowchart heading after inserts shifted indices
    flow_idx = find_index('"text": "流程图"')
    # first 流程图 under 3.2 — pick heading block then insert after unknown mermaid (index+2)
    r = subprocess.run(
        [DWS, "doc", "block", "list", "--node", NODE, "--timeout", "120000", "-f", "json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    blocks = json.loads(r.stdout).get("blocks", [])
    flow_insert = None
    seen_32_flow = False
    for i, b in enumerate(blocks):
        el = b.get("element") or b
        if el.get("blockType") == "heading" and (el.get("heading") or {}).get("text") == "流程图":
            if not seen_32_flow:
                # first flowchart in 3.2 area: after slice rules (~block 80 originally)
                if i > 50:
                    flow_insert = i + 2  # after mermaid unknown block
                    break
    if flow_insert is None:
        flow_insert = find_index("数据结构 / 配置表")
    print(f"Insert flowchart note at {flow_insert}")
    insert_heading(flow_insert, FLOWCHART_HEADING, level=4)
    insert_paragraph(flow_insert + 1, f"```mermaid\n{FLOWCHART}\n```")

    runtime_idx = find_index("slice_runtime")
    print(f"Insert runtime fields note at {runtime_idx + 2}")
    insert_paragraph(runtime_idx + 2, RUNTIME_NOTE)

    preset_idx = find_index("operable_angle")
    print(f"Insert preset fields note at {preset_idx}")
    insert_paragraph(preset_idx, PRESET_NOTE)

    # Verify
    verify = run(["doc", "read", "--node", NODE, "-f", "json"])
    data = json.loads(verify)
    md = data.get("markdown", "")
    for key in ["操作夹角约束", "dribble_realign", "带球调整无次数上限", "angle_span_min"]:
        ok = key in md
        print(f"verify {key}: {'OK' if ok else 'MISSING'}")
    print("Done.")


if __name__ == "__main__":
    main()
