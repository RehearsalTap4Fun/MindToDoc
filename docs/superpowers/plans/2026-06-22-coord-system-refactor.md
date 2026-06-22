# 坐标系协议 v1 派生重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把主生成器(`generate_activity_soccer_test_config.py`)按协议 v1 重写,实现「文件常量 ↔ 协议 v1 完全一致」+ 落 2 条 lint + 状态机推协议到 v1.1。

**Architecture:** 引入坐标常量层 + helper 函数(B 方案),18 个 preset 改用常量表达;两条 lint(`check_protocol_drift.py` + `check_preset_consistency.py`)做协议 ↔ 代码双向校验;关卡 tag 工具 39 测试做回归网。Lint 框架先行(空壳跑当前代码会 fail),逐步迁数据让 lint 由红转绿。

**Tech Stack:** Python 3.10+ / openpyxl / pytest;不引新依赖。

**Spec:** `docs/superpowers/specs/2026-06-22-coord-system-refactor-design.md`

---

## 文件结构

| 路径 | 责任 |
|---|---|
| `output/test-config/generate_activity_soccer_test_config.py` | 主生成器,顶部加 ~50 行协议 v1 常量段 + 3 helper;18 preset 数据重写;Const + ReceiveDecisionCfg 单位转换;删 WARN 注释段 |
| `scripts/check_protocol_drift.py` | 解析协议 markdown §3-§4 的字段表,与主生成器顶部常量段比对,不一致非零退出 |
| `scripts/check_preset_consistency.py` | 加载 `_build_presets`,对每个 preset 跑摆位合规断言(z 范围 / 点球点 / 角球 / 守门 / 任意球人墙间距) |
| `references/soccer-coordinate-protocol.md` | §12 派生改动清单加状态机 + 状态列;头部状态升 v1.1;commit hash 索引 |

不改:`output/test-config/level-tags/`、`output/test-config/generate_worldcup_test_config.py`、其它 reference。

---
