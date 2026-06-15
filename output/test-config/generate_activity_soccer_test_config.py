# -*- coding: utf-8 -*-
"""Generate ActivitySoccer.xlsx test config from 2026 World Cup DingTalk doc."""
from __future__ import annotations

import json
import math
from pathlib import Path

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

OUT_DIR = Path(__file__).parent
OUTPUT_FILE = OUT_DIR / "ActivitySoccer.xlsx"
OUTPUT_LC_FILE = OUT_DIR / "ActivitySoccerLanguage.xlsx"
OUTPUT_CONST_FILE = OUT_DIR / "ConstConfig_ActvSoccer.xlsx"
# 追加到 dataconfig/ConstConfig.xlsx 的 CfgID 段（当前线上最大约 10135564）
ACTV_SOCCER_CONST_CFGID_BASE = 10135601
SOURCE_DOCS = [
    "钉钉文档 2026世界杯主题活动-开发文档 (amweZ92PV6vDZdmDCKwo2Ev4VxEKBD6p)",
    "K1Client docs/plans/2026-06-09-worldcup-fsm-bt-enemy-ai-design.md",
]

# 球员 AI 职责枚举（程序侧 PlayerAiDuty）
# 约定：守门员；对方除门将外均为后卫；我方所有球员(含玩家)均为前锋
PLAYER_AI_DUTY_ENUM: dict[str, int] = {
    "Goalkeeper": 1,
    "Defender": 2,
    "Forward": 3,
}
PLAYER_AI_DUTY_ENUM_COMMENT = "1=Goalkeeper,2=Defender,3=Forward"
# CharacterState 场景表现行专用，不属于 PlayerAiDuty 枚举
CHARACTER_STATE_SCENE_DUTY = 0
CHARACTER_STATE_DUTY_COMMENT = (
    "0=场景(仅CharacterState),1=Goalkeeper,2=Defender,3=Forward"
)


# 第1行读取端: c=仅客户端 s=仅服务端 cs=双端; Remark 留空(备注列)
SHEET_DEFAULT_READ: dict[str, str] = {
    "ActvSoccerTutorialCfg": "c",
    "ActvSoccerHapticCfg": "c",
    "ActvSoccerSliceFlowCfg": "c",
    "ActvSoccerCharacterStateCfg": "c",
    "ActvSoccerPlayerAiDutyEnumCfg": "c",
    "ActvSoccerContractCfg": "cs",
    "ActvSoccerContractStarLicCfg": "s",
    "ActvSoccerFameGainRuleCfg": "s",
    "ActvSoccerKnockoutCfg": "s",
    "ActvSoccerKnockoutPhaseCfg": "s",
    "ActvSoccerMatchSimulationCfg": "s",
    "ActvSoccerBetCoinSourceCfg": "s",
    "ActvSoccerRankSectionCfg": "s",
}
READ_OVERRIDES: dict[str, dict[str, str]] = {
    "ActvSoccerCharacterCfg": {"AppearanceKey": "c", "DisplayPower": "c"},
    "ActvSoccerNationalityCfg": {"NameLcKey": "c", "ContractPool": "s"},
    "ActvSoccerTutorialCfg": {"SliceInstanceID": "cs", "DescLcKey": "c"},
    "ActvSoccerSliceTypeDefCfg": {
        "AllowedModes": "c", "PayloadSchema": "c", "DefaultCameraFov": "c",
    },
    "ActvSoccerSlicePresetCfg": {
        "NameLcKey": "c", "Tags": "c", "BallPos": "c", "BallVector": "c", "BallOwner": "c",
        "PlayersInit": "c", "CameraFov": "c", "TargetPoint": "c", "RecommendedModes": "c",
        "AngleSpanMin": "c", "AngleSpanMax": "c", "AngleMaxCenterShift": "c", "AngleMargin": "c",
    },
    "ActvSoccerSliceInstanceCfg": {"OverrideOperableAngle": "c"},
    "ActvSoccerEnemyAiCfg": {"AnimationKey": "c"},
    "ActvSoccerTeamCfg": {"NameLcKey": "c", "KitKey": "c", "BadgeKey": "c"},
    "ActvSoccerFameGrowthLevelCfg": {"TitleLcKey": "c"},
    "ActvSoccerLifeGrowthLevelCfg": {"TitleLcKey": "c"},
    "ActvSoccerSeasonCfg": {"LeagueNameLcKey": "c"},
    "ActvSoccerKnockoutPhaseCfg": {
        "PhaseLcKey": "cs", "PhaseKey": "cs", "DayContentLcKey": "c", "BetOpen": "cs",
    },
    "ActvSoccerBetMatchCfg": {"Status": "s"},
}


def _resolve_read(sheet_name: str, field: str) -> str:
    if field == "Remark" or (sheet_name == "ActvSoccerLanguageCfg" and field == "Source"):
        return ""
    overrides = READ_OVERRIDES.get(sheet_name, {})
    if field in overrides:
        return overrides[field]
    return SHEET_DEFAULT_READ.get(sheet_name, "cs")


def make_sheet(wb: Workbook, name: str, columns: list[dict], rows: list[dict]) -> None:
    ws: Worksheet = wb.create_sheet(name)
    for col_idx, col in enumerate(columns, start=1):
        read_side = col.get("read", _resolve_read(name, col["field"]))
        if read_side:
            ws.cell(1, col_idx, read_side)
        ws.cell(2, col_idx, col["type"])
        ws.cell(3, col_idx, col["field"])
        ws.cell(4, col_idx, col.get("server", ""))
        ws.cell(5, col_idx, col.get("comment1", ""))
        ws.cell(6, col_idx, col.get("comment2", ""))
        ws.cell(7, col_idx, col.get("comment3", ""))
        ws.cell(8, col_idx, col.get("comment4", ""))
    for row_idx, row in enumerate(rows, start=9):
        for col_idx, col in enumerate(columns, start=1):
            val = row.get(col["field"])
            if val is None or (isinstance(val, str) and val.strip() == ""):
                if col["type"] == "ext[]":
                    val = col.get("default", "[]")
                elif col["type"] == "ext":
                    val = col.get("default", "{}")
            if val is not None:
                ws.cell(row_idx, col_idx, val)


# dataconfig/ConstConfig.xlsx → ConstConfigCfg 表头（首列 CfgID，非活动表 ID 约定）
CONST_CONFIG_COLUMNS: list[dict] = [
    {"field": "CfgID", "type": "int", "server": "id", "read": "cs", "comment2": "编号"},
    {"field": "Comment", "type": "string", "server": "comment", "read": "s", "comment2": "备注"},
    {"field": "Constant", "type": "string", "server": "constant", "read": "cs", "comment2": "字符串"},
    {"field": "Val", "type": "double", "server": "val", "read": "cs", "comment2": "值"},
    {"field": "Array", "type": "int[]", "server": "array", "read": "cs", "comment2": "数组", "default": "[]"},
    {
        "field": "Effects", "type": "ext[]", "server": "quintuple", "read": "cs",
        "comment1": "Effect_P", "comment2": "", "default": "[]",
    },
    {"field": "", "type": "map", "server": "requirement", "read": "c", "comment2": "", "default": "{}"},
]


def make_const_format_sheet(wb: Workbook, sheet_name: str, rows: list[dict]) -> None:
    """Write a sheet whose columns match dataconfig/ConstConfig.xlsx → ConstConfigCfg."""
    ws: Worksheet = wb.create_sheet(sheet_name)
    cols = CONST_CONFIG_COLUMNS
    for col_idx, col in enumerate(cols, start=1):
        if col.get("read"):
            ws.cell(1, col_idx, col["read"])
        ws.cell(2, col_idx, col["type"])
        ws.cell(3, col_idx, col["field"] if col["field"] else "")
        ws.cell(4, col_idx, col.get("server", ""))
        ws.cell(5, col_idx, col.get("comment1", ""))
        ws.cell(6, col_idx, col.get("comment2", ""))
    req_field = cols[-1]["server"]
    for row_idx, row in enumerate(rows, start=9):
        for col_idx, col in enumerate(cols, start=1):
            key = col["field"] if col["field"] else req_field
            val = row.get(key)
            if val is None or (isinstance(val, str) and val.strip() == ""):
                if col["type"] == "ext[]":
                    val = col.get("default", "[]")
                elif col["type"] == "map":
                    val = col.get("default", "{}")
            if val is not None:
                ws.cell(row_idx, col_idx, val)


def _const(
    offset: int,
    comment: str,
    constant: str,
    val: str | int | float = "0",
    array: str = "[]",
    effects: str = "[]",
    requirement: str = "{}",
) -> dict:
    return {
        "CfgID": ACTV_SOCCER_CONST_CFGID_BASE + offset,
        "Comment": comment,
        "Constant": constant,
        "Val": val,
        "Array": array,
        "Effects": effects,
        "requirement": requirement,
    }


def _first_sign_contract_rows() -> list[dict]:
    """首签 1 星合同：签约/存档关联 contract_id，展示球队通过 TeamID 反查。"""
    season_goal = '[{"type":"rank","threshold":12,"settle_at":"season_end"}]'
    season_reward = '[{"typ":"vm","id":11151001,"val":84}]'
    pairs = [
        (1, 101, "全局默认"),
        (11, 102, "欧洲默认"),
        (12, 103, "南美默认"),
        (13, 104, "南美默认2"),
        (101, 201, "中国动态池"),
        (102, 202, "中国动态池"),
        (103, 203, "欧洲动态池"),
        (104, 204, "欧洲/南美动态池"),
        (105, 205, "南美动态池"),
        (106, 206, "南美动态池"),
        (107, 207, "南美动态池"),
        (108, 208, "欧洲动态池"),
    ]
    return [
        {
            "ID": cid, "TeamID": tid, "TeamStar": 1,
            "PayFinish": 10, "PayGoal": 5, "PayAssist": 5, "PayFame": 20,
            "SeasonGoal": season_goal,
            "SeasonReward": season_reward,
            "SignReward": "[]",
            "GrantFameLevel": 1, "GrantLifeLevel": 1,
            "GrantScene": "first_sign",
            "Remark": f"首签1星-{note}",
        }
        for cid, tid, note in pairs
    ]


def _contract_star_license_rows() -> list[dict]:
    """合同星级许可表：ID=2~5，allowed_team_stars 与 star_weights 等长按下标对应。"""
    return [
        {"ID": 2, "AllowedTeamStars": "[1,2]", "StarWeights": "[10,30]", "Remark": "2星许可"},
        {"ID": 3, "AllowedTeamStars": "[1,2,3]", "StarWeights": "[10,30,60]", "Remark": "3星许可-文档示例"},
        {"ID": 4, "AllowedTeamStars": "[1,2,3,4]", "StarWeights": "[10,20,40,60]", "Remark": "4星许可"},
        {"ID": 5, "AllowedTeamStars": "[1,2,3,4,5]", "StarWeights": "[10,15,25,35,60]", "Remark": "5星许可"},
    ]


def _league_finish_contract_rows() -> list[dict]:
    """联赛完成换约池：星级由 ContractStarLicenseCfg 权重决定，同星级内均匀抽合同。"""
    season_goal_rank = '[{"type":"rank","threshold":12,"settle_at":"season_end"}]'
    season_goal_slice = '[{"type":"slice_win","threshold":5,"settle_at":"season_end"}]'
    reward_84 = '[{"typ":"vm","id":11151001,"val":84}]'
    reward_120 = '[{"typ":"vm","id":11151001,"val":120}]'
    reward_200 = '[{"typ":"vm","id":11151001,"val":200}]'
    reward_300 = '[{"typ":"vm","id":11151001,"val":300}]'
    reward_500 = '[{"typ":"vm","id":11151001,"val":500}]'
    rows = [
        (2, 204, 2, 20, 8, 6, 30, season_goal_slice, reward_120, 2, 2, "2星-联赛换约"),
        (3, 203, 2, 18, 7, 5, 28, season_goal_rank, reward_84, 1, 2, "2星-联赛换约(低门槛)"),
        (4, 205, 2, 22, 9, 7, 32, season_goal_slice, reward_120, 2, 3, "2星-联赛换约(高门槛)"),
        (5, 208, 3, 35, 12, 9, 45, season_goal_rank, reward_200, 3, 3, "3星-联赛换约"),
        (6, 207, 3, 32, 11, 8, 42, season_goal_slice, reward_200, 3, 2, "3星-联赛换约(生活门槛低)"),
        (7, 206, 1, 12, 4, 4, 18, season_goal_rank, reward_84, 1, 1, "1星-联赛换约(保底)"),
        (8, 201, 4, 45, 15, 10, 55, season_goal_rank, reward_300, 4, 4, "4星-联赛换约"),
        (9, 202, 5, 60, 20, 12, 70, season_goal_slice, reward_500, 5, 5, "5星-联赛换约"),
    ]
    return [
        {
            "ID": cid, "TeamID": tid, "TeamStar": star,
            "PayFinish": pf, "PayGoal": pg, "PayAssist": pa, "PayFame": pfm,
            "SeasonGoal": sg, "SeasonReward": sr, "SignReward": "[]",
            "GrantFameLevel": gfl, "GrantLifeLevel": gll,
            "GrantScene": "league_finish",
            "Remark": note,
        }
        for cid, tid, star, pf, pg, pa, pfm, sg, sr, gfl, gll, note in rows
    ]


def actv_soccer_const_rows() -> list[dict]:
    """ActivitySoccer 玩法常量行（活动表与 ConstConfig 补丁共用同一份数据）。"""
    return [
        _const(0, "主界面门票上限(测试)", "ActvSoccer_ticket_cap_default", "250"),
        _const(1, "门票恢复间隔(分钟)", "ActvSoccer_ticket_recover_minutes", "30"),
        _const(2, "淘汰赛开放关卡(round15起=level141)", "ActvSoccer_knockout_open_level", str(KNOCKOUT_OPEN_LEVEL)),
        _const(3, "可选角色数", "ActvSoccer_default_character_count", "4"),
        _const(4, "首签固定合同星级", "ActvSoccer_first_sign_contract_star", "1"),
        _const(
            5,
            "SeededRng种子组成(attempt_id+slice_id+ai_profile_id+rewind_count)",
            "ActvSoccer_ai_random_seed_formula",
            "0",
        ),
        _const(6, "死角不可扑(策划确认)", "ActvSoccer_dead_corner_can_save", "0"),
        _const(
            7,
            "参数叠加顺序 preset->instance->ai_profile->modifier",
            "ActvSoccer_config_overlay_order",
            "0",
        ),
        _const(8, "待机移动速度(固定值,单位m/s TODO)", "ActvSoccer_move_speed_idle", "0"),
        _const(9, "慢走移动速度(固定值,单位m/s TODO)", "ActvSoccer_move_speed_walk", "2.5"),
        _const(10, "跑动速度下限;run=lerp(能力值,min,max)", "ActvSoccer_move_speed_run_min", "4"),
        _const(11, "跑动速度上限;run=lerp(能力值,min,max)", "ActvSoccer_move_speed_run_max", "8"),
        _const(12, "待机倍率;0=读MoveSpeedIdle,不乘run", "ActvSoccer_move_speed_ratio_idle", "0"),
        _const(13, "慢走倍率;0=读MoveSpeedWalk,不乘run", "ActvSoccer_move_speed_ratio_walk", "0"),
        _const(14, "正常跑倍率;0=读能力值映射run速度", "ActvSoccer_move_speed_ratio_run", "0"),
        _const(15, "慢跑跑位-队友/对手;相对run倍率", "ActvSoccer_move_speed_ratio_jog", "0.75"),
        _const(16, "冲刺-主角/对手;相对run倍率", "ActvSoccer_move_speed_ratio_sprint", "1.25"),
        _const(17, "带球推进-控球者;相对run倍率", "ActvSoccer_move_speed_ratio_dribble", "0.85"),
        _const(18, "逼抢-对手;相对run倍率", "ActvSoccer_move_speed_ratio_press", "1.1"),
        _const(19, "门将横移;相对run倍率,moving_keeper再乘params.speed", "ActvSoccer_move_speed_ratio_keeper_lateral", "0.9"),
        _const(20, "出球力量下限", "ActvSoccer_kick_force_min", "10"),
        _const(21, "出球力量上限", "ActvSoccer_kick_force_max", "25"),
        _const(22, "停球/控球距离(m TODO)", "ActvSoccer_ball_control_distance", "1.2"),
        _const(23, "可操作夹角宽度下限(°)", "ActvSoccer_operable_angle_span_min", "20"),
        _const(24, "可操作夹角宽度上限(°)", "ActvSoccer_operable_angle_span_max", "70"),
        _const(25, "联赛换约候选合同份数", "ActvSoccer_contract_offer_count", "3"),
    ]


def build_const_config_workbook(rows: list[dict]) -> Workbook:
    """ConstConfig 补丁 xlsx，便于合并进 dataconfig/ConstConfig.xlsx。"""
    wb = Workbook()
    wb.remove(wb.active)
    make_const_format_sheet(wb, "ConstConfigCfg", rows)
    return wb


def id_col(col_type: str = "int", desc: str = "编号") -> dict:
    """首列固定 ID / id（K1 测试配置约定）。"""
    return {"field": "ID", "type": col_type, "server": "id", "comment2": desc}


def c(*specs: tuple | dict) -> list[dict]:
    """Column spec: (field, type, desc) or (field, type, desc, proto_row5) or + json_example row7; or id_col dict."""
    cols: list[dict] = []
    for spec in specs:
        if isinstance(spec, dict):
            cols.append(spec)
            continue
        field, col_type, desc = spec[0], spec[1], spec[2]
        col: dict = {"field": field, "type": col_type, "comment2": desc}
        if len(spec) > 3 and spec[3]:
            col["comment1"] = spec[3]
        if len(spec) > 4 and spec[4]:
            col["comment3"] = spec[4]
            if col_type in ("ext", "ext[]"):
                col["default"] = spec[4]
        cols.append(col)
    return cols


# K1 ext 第5行结构标记（见 config-table-editor skill）
P_TYIDVAL = "TypIDVal_P_cspb"
P_VEC3 = "PositionTuple_P"
V_TYPE_PAYLOAD = "SoccerTypePayload_V"
V_OBJECTIVE = "SoccerObjective_V"
V_MODIFIER = "SoccerModifier_V"
V_PLAYER_INIT = "SoccerPlayerInit_V"
V_SEASON_GOAL = "SoccerSeasonGoal_V"
V_SIM_PARAMS = "SoccerSimParams_V"

# SoccerPlayerInit_V: team, idx, duty(→PlayerAiDuty), pos
PLAYER_INIT_DEFAULT = (
    '[{"team":"home","idx":0,"duty":3,'
    '"pos":{"x":0,"y":0,"z":0}}]'
)


def player_init(team: str, idx: int, duty: int, x: float, y: float, z: float) -> dict:
    return {"team": team, "idx": idx, "duty": duty, "pos": {"x": x, "y": y, "z": z}}


def players_init_json(players: list[dict]) -> str:
    return json.dumps(players, ensure_ascii=False)


LC_PREFIX = "ActvSoccer"


def lc_key(*parts: str) -> str:
    """生成本地化唯一 ID，格式: ActvSoccer_{语义}_{序号}。"""
    return f"{LC_PREFIX}_" + "_".join(parts)


class LcRegistry:
    """收集测试配置引用的本地化条目，ID 为英文字符串且全局唯一。"""

    def __init__(self) -> None:
        self._rows: list[dict] = []
        self._keys: dict[str, str] = {}

    def add(self, lc_id: str, cn: str, source: str = "") -> str:
        if lc_id in self._keys:
            return self._keys[lc_id]
        self._keys[lc_id] = lc_id
        self._rows.append({"ID": lc_id, "Cn": cn, "Source": source})
        return lc_id

    @property
    def rows(self) -> list[dict]:
        return self._rows


def build_language_workbook(registry: LcRegistry) -> Workbook:
    wb = Workbook()
    wb.remove(wb.active)
    make_sheet(
        wb,
        "ActvSoccerLanguageCfg",
        c(
            id_col("string", "本地化唯一ID(英文+数字)"),
            ("Cn", "string", "简体中文"),
            ("Source", "string", "引用来源(测试追溯)"),
        ),
        registry.rows,
    )
    return wb


# =====================================================================
# 关卡设计 · 参数化生成（50 轮 × 10 关 = 500 关；分层可复用切片实例库）
# 详见 output/关卡设计方案.md。tier = ceil(round/5)，每档 5 轮。
# =====================================================================

ROUNDS_TOTAL = 50
LEVELS_PER_ROUND = 10
TIERS_TOTAL = 10

# slice_type 编号沿用 ActvSoccerSliceTypeDefCfg
SLICE_TYPE_NAME: dict[int, str] = {
    1: "attack", 2: "free_kick", 3: "penalty",
    4: "corner", 5: "throw_in", 6: "goalkeep",
}
SLICE_TYPE_ORDER = [1, 2, 3, 4, 5, 6]

# 每个 slice_type 的可用 preset 池（按 tier 轮换取用，丰富画面）
PRESET_POOL: dict[int, list[int]] = {
    1: [1, 5, 6, 16],     # attack
    2: [2, 7, 8, 17],     # free_kick
    3: [3, 9],            # penalty
    4: [10, 11, 18],      # corner
    5: [12, 13],          # throw_in
    6: [4, 14, 15],       # goalkeep
}

# tier 主题（联赛名 + 主题对手球队池）
TIER_THEME: dict[int, str] = {
    1: "社区杯", 2: "城市联赛", 3: "省级联赛", 4: "大区联赛", 5: "全国联赛",
    6: "洲际资格赛", 7: "洲际联赛", 8: "国际邀请赛", 9: "世界精英赛", 10: "世界杯总决赛",
}

# 淘汰赛开放：round 15（tier3 末）→ level_id = (15-1)*10 + 1 = 141
KNOCKOUT_OPEN_ROUND = 15
KNOCKOUT_OPEN_LEVEL = (KNOCKOUT_OPEN_ROUND - 1) * LEVELS_PER_ROUND + 1


def _tier_specs() -> dict[int, dict]:
    """10 档单一真源：AiProfile / Level / SliceAi / 角度 override 共用。"""
    gk = [25, 30, 36, 42, 48, 54, 60, 66, 72, 78]
    dfn = [12, 18, 24, 30, 36, 42, 48, 54, 60, 66]
    sht = [30, 36, 42, 48, 54, 60, 66, 72, 78, 84]
    react = [1300, 1200, 1100, 1000, 950, 880, 820, 760, 700, 640]
    span_min = [40, 38, 36, 34, 32, 30, 28, 26, 24, 22]
    span_max = [70, 66, 62, 58, 54, 50, 46, 42, 36, 30]
    center_shift = [0, 0, 3, 3, 5, 5, 7, 7, 9, 10]
    margin = [8, 8, 7, 7, 6, 6, 5, 5, 4, 4]
    specs: dict[int, dict] = {}
    for t in range(1, TIERS_TOTAL + 1):
        i = t - 1
        difficulty = "easy" if t <= 2 else "normal" if t <= 5 else "hard"
        specs[t] = {
            "ai_profile_id": 1000 + t,
            "difficulty": difficulty,
            "gk_save": gk[i],
            "def_success": dfn[i],
            "shooter_success": sht[i],
            "react_ms": react[i],
            "opponent_star": math.ceil(t / 2),
            "span_min": span_min[i],
            "span_max": span_max[i],
            "center_shift": center_shift[i],
            "margin": margin[i],
        }
    return specs


TIER = _tier_specs()


def _tier_primary_modifier(tier: int) -> int:
    """SliceAi.ModifierID 单一主机制（0=无）。"""
    if tier <= 2:
        return 0
    if tier <= 4:
        return 4001
    if tier <= 6:
        return 4002
    if tier <= 8:
        return 4006
    return 4005


def _instance_operable_angle(tier: int, slice_type: int) -> float:
    """点球/守门无扇形(0)；其余按 tier 单调收窄并 clamp 到 [20,70]。"""
    if slice_type in (3, 6):
        return 0.0
    s = TIER[tier]
    val = s["span_max"] - (s["span_max"] - s["span_min"]) * (tier - 1) / 9.0
    return round(min(70.0, max(20.0, val)), 1)


def _instance_modifiers_json(tier: int, slice_type: int, variant: int) -> str:
    """实例 ext[] Modifiers（SoccerModifier_V: {id, params}）。"""
    mods: list[dict] = []
    if 3 <= tier <= 4:
        mods.append({"id": "moving_keeper", "params": {"speed": 1.0}})
    elif 5 <= tier <= 6:
        mods.append({"id": "moving_keeper", "params": {"speed": 1.5}})
    elif 7 <= tier <= 8:
        mods.append({"id": "narrow_angle", "params": {"shrink": 0.7}})
    elif tier >= 9:
        mods.append({"id": "moving_keeper", "params": {"speed": 2.0}})
    if slice_type == 2 and tier >= 6:  # 任意球固定人墙
        mods.append({"id": "fixed_wall", "params": {}})
    if variant == 2 and slice_type in (2, 3):  # 任意球/点球加压：关辅助线
        mods.append({"id": "no_aim_line", "params": {}})
    if variant == 2 and slice_type == 6:  # 守门加压：门将移动
        if not any(m["id"] == "moving_keeper" for m in mods):
            mods.append({"id": "moving_keeper", "params": {"speed": 1.5}})
    if tier == 10:
        mods.append({"id": "random_dive", "params": {"randomness": 0.6}})
    return json.dumps(mods, ensure_ascii=False) if mods else "[]"


def _build_instance_library() -> list[dict]:
    """120 库实例 = 10 tier × 6 type × 2 variant；旧 6 行(101-203)前置保留。"""
    legacy = [
        {"ID": 101, "SliceType": "attack", "PresetID": 1, "ObjectiveType": "score", "Remark": "试训-进攻"},
        {"ID": 102, "SliceType": "free_kick", "PresetID": 2, "ObjectiveType": "score", "Remark": "试训-任意球"},
        {"ID": 103, "SliceType": "penalty", "PresetID": 3, "ObjectiveType": "score", "Remark": "试训-点球"},
        {"ID": 201, "SliceType": "attack", "PresetID": 1, "OverrideOperableAngle": 30, "ObjectiveType": "score", "Remark": "引导关1"},
        {"ID": 202, "SliceType": "attack", "PresetID": 1, "OverrideOperableAngle": 28, "ExtraObjectives": '[{"type":"pass_to","params":{"target":1}},{"type":"score"}]', "Remark": "引导关2-助攻"},
        {"ID": 203, "SliceType": "goalkeep", "PresetID": 4, "ObjectiveType": "survive", "Remark": "引导关3-守门"},
    ]
    lib: list[dict] = []
    for tier in range(1, TIERS_TOTAL + 1):
        for stype in SLICE_TYPE_ORDER:
            pool = PRESET_POOL[stype]
            preset_id = pool[(tier - 1) % len(pool)]
            type_name = SLICE_TYPE_NAME[stype]
            for variant in (1, 2):
                iid = tier * 100 + stype * 10 + variant
                row: dict = {
                    "ID": iid,
                    "SliceType": type_name,
                    "PresetID": preset_id,
                    "OverrideOperableAngle": _instance_operable_angle(tier, stype),
                    "Modifiers": _instance_modifiers_json(tier, stype, variant),
                    "Remark": f"库 tier{tier} {type_name} v{variant}",
                }
                if variant == 1:
                    row["ObjectiveType"] = "survive" if stype == 6 else "score"
                    row["ExtraObjectives"] = "[]"
                else:
                    if stype in (1, 4, 5):  # 进攻/角球/界外球：复合(助攻)
                        row["ObjectiveType"] = ""
                        row["ExtraObjectives"] = (
                            '[{"type":"pass_to","params":{"target":1}},{"type":"score"}]'
                        )
                    elif stype == 6:  # 守门
                        row["ObjectiveType"] = "survive"
                        row["ExtraObjectives"] = "[]"
                    else:  # 任意球/点球加压
                        row["ObjectiveType"] = "score"
                        row["ExtraObjectives"] = "[]"
                lib.append(row)
    return legacy + lib


def _enemy_band(tier: int) -> int:
    return 1 if tier <= 3 else 2 if tier <= 6 else 3 if tier <= 8 else 4


def _enemy_id(tier: int, role: int) -> int:
    """role: 1=keeper 2=defender 3=shooter。band1 复用旧 2001-2003。"""
    band = _enemy_band(tier)
    if band == 1:
        return {1: 2001, 2: 2002, 3: 2003}[role]
    return 2000 + band * 10 + role


def _build_enemy_ai() -> list[dict]:
    """12 行 = 4 难度带 × 3 角色；band1 复用旧 2001-2003(保引导切片引用)。"""
    rows = [
        {"ID": 2001, "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "SaveWeight": 45, "LeftWeight": 40, "RightWeight": 40, "UpWeight": 20, "InterceptWeight": 0, "ClearanceWeight": 0, "KeeperCatchFail": 1, "OutOfBoundsFail": 0, "AnimationKey": "E04_GKDiveLeft", "Remark": "band1门将(tier1-3)"},
        {"ID": 2002, "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "SaveWeight": 0, "LeftWeight": 0, "RightWeight": 0, "UpWeight": 0, "InterceptWeight": 35, "ClearanceWeight": 20, "KeeperCatchFail": 0, "OutOfBoundsFail": 1, "AnimationKey": "F03_Intercept", "Remark": "band1后卫(tier1-3)"},
        {"ID": 2003, "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "SaveWeight": 0, "LeftWeight": 40, "RightWeight": 40, "UpWeight": 20, "InterceptWeight": 0, "ClearanceWeight": 0, "KeeperCatchFail": 0, "OutOfBoundsFail": 0, "AnimationKey": "D01_Shoot", "Remark": "band1守门切片射手(tier1-3)"},
    ]
    # band2/3/4 × keeper/def/shooter，权重随带收紧
    band_keeper = {2: (52, 44), 3: (60, 48), 4: (68, 52)}      # (SaveWeight, dir base)
    band_def = {2: 42, 3: 50, 4: 58}                            # InterceptWeight
    band_shooter = {2: 45, 3: 50, 4: 56}                        # dir base
    for band in (2, 3, 4):
        save_w, dir_w = band_keeper[band]
        rows.append({"ID": 2000 + band * 10 + 1, "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "SaveWeight": save_w, "LeftWeight": dir_w, "RightWeight": dir_w, "UpWeight": 16, "InterceptWeight": 0, "ClearanceWeight": 0, "KeeperCatchFail": 1, "OutOfBoundsFail": 0, "AnimationKey": "E04_GKDiveLeft", "Remark": f"band{band}门将"})
        rows.append({"ID": 2000 + band * 10 + 2, "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "SaveWeight": 0, "LeftWeight": 0, "RightWeight": 0, "UpWeight": 0, "InterceptWeight": band_def[band], "ClearanceWeight": 24, "KeeperCatchFail": 0, "OutOfBoundsFail": 1, "AnimationKey": "F03_Intercept", "Remark": f"band{band}后卫"})
        sw = band_shooter[band]
        rows.append({"ID": 2000 + band * 10 + 3, "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "SaveWeight": 0, "LeftWeight": sw, "RightWeight": sw, "UpWeight": 18, "InterceptWeight": 0, "ClearanceWeight": 0, "KeeperCatchFail": 0, "OutOfBoundsFail": 0, "AnimationKey": "D01_Shoot", "Remark": f"band{band}守门切片射手"})
    return rows


def _build_ai_profiles() -> list[dict]:
    """10 档 AI 难度，单调递增；DeadCornerCanSave 固定 0。"""
    label = {"easy": "简单档", "normal": "普通档", "hard": "困难档"}
    rows = []
    for t in range(1, TIERS_TOTAL + 1):
        s = TIER[t]
        rows.append({
            "ID": s["ai_profile_id"], "Difficulty": s["difficulty"],
            "GoalkeeperSaveRate": s["gk_save"], "DefenderSuccessRate": s["def_success"],
            "ShooterSuccessRate": s["shooter_success"], "DeadCornerCanSave": 0,
            "ReactionTimeMs": s["react_ms"],
            "Remark": f"tier{t} {label[s['difficulty']]}(对手{s['opponent_star']}星)",
        })
    return rows


def _build_ai_modifiers() -> list[dict]:
    """7 行：保留 4001-4004，新增 4005/4006/4007。"""
    return [
        {"ID": 4001, "ModifierType": "moving_keeper", "Param1Key": "speed", "Param1Value": "1.0", "Param2Key": "range", "Param2Value": "2.5", "Param3Key": "start_offset", "Param3Value": "0.0", "Remark": "普通移动门将"},
        {"ID": 4002, "ModifierType": "moving_keeper", "Param1Key": "speed", "Param1Value": "1.5", "Param2Key": "range", "Param2Value": "3.5", "Param3Key": "start_offset", "Param3Value": "0.5", "Remark": "困难移动门将"},
        {"ID": 4003, "ModifierType": "no_aim_line", "Param1Key": "enabled", "Param1Value": "1", "Remark": "关闭辅助线"},
        {"ID": 4004, "ModifierType": "fixed_wall", "Param1Key": "enabled", "Param1Value": "1", "Remark": "任意球固定人墙"},
        {"ID": 4005, "ModifierType": "moving_keeper", "Param1Key": "speed", "Param1Value": "2.0", "Param2Key": "range", "Param2Value": "4.5", "Param3Key": "start_offset", "Param3Value": "0.5", "Remark": "极限移动门将"},
        {"ID": 4006, "ModifierType": "narrow_angle", "Param1Key": "shrink", "Param1Value": "0.7", "Remark": "收窄可操作夹角"},
        {"ID": 4007, "ModifierType": "random_dive", "Param1Key": "randomness", "Param1Value": "0.6", "Remark": "门将随机扑救方向"},
    ]


def _slice_ai_for_library(lib_rows: list[dict]) -> list[dict]:
    """每库实例一行(id 从 3100)；旧 3001-3006(引导/试训)前置保留。"""
    legacy = [
        {"ID": 3001, "SliceID": 101, "AiProfileID": 1001, "GoalkeeperAiID": 2001, "DefenderAiID": 0, "ShooterAiID": 0, "ModifierID": 0, "IsGuideAi": 1, "RewindRandom": 1, "OverrideReactionTimeMs": 1200, "Remark": "试训-进攻"},
        {"ID": 3002, "SliceID": 102, "AiProfileID": 1001, "GoalkeeperAiID": 2001, "DefenderAiID": 0, "ShooterAiID": 0, "ModifierID": 0, "IsGuideAi": 1, "RewindRandom": 1, "OverrideReactionTimeMs": 1200, "Remark": "试训-任意球"},
        {"ID": 3003, "SliceID": 103, "AiProfileID": 1001, "GoalkeeperAiID": 2001, "DefenderAiID": 0, "ShooterAiID": 0, "ModifierID": 0, "IsGuideAi": 1, "RewindRandom": 1, "OverrideReactionTimeMs": 1200, "Remark": "试训-点球"},
        {"ID": 3004, "SliceID": 201, "AiProfileID": 1001, "GoalkeeperAiID": 2001, "DefenderAiID": 0, "ShooterAiID": 0, "ModifierID": 0, "IsGuideAi": 1, "RewindRandom": 1, "OverrideReactionTimeMs": 1200, "Remark": "引导关切片1-进攻"},
        {"ID": 3005, "SliceID": 202, "AiProfileID": 1001, "GoalkeeperAiID": 2001, "DefenderAiID": 2002, "ShooterAiID": 0, "ModifierID": 0, "IsGuideAi": 1, "RewindRandom": 1, "OverrideReactionTimeMs": 1200, "Remark": "引导关切片2-助攻"},
        {"ID": 3006, "SliceID": 203, "AiProfileID": 1002, "GoalkeeperAiID": 0, "DefenderAiID": 0, "ShooterAiID": 2003, "ModifierID": 0, "IsGuideAi": 1, "RewindRandom": 1, "OverrideReactionTimeMs": 900, "Remark": "引导关切片3-守门"},
    ]
    rows = list(legacy)
    sid = 3100
    legacy_ids = {101, 102, 103, 201, 202, 203}
    for inst in lib_rows:
        if inst["ID"] in legacy_ids:
            continue
        tier = inst["ID"] // 100
        stype = (inst["ID"] // 10) % 10
        s = TIER[tier]
        if stype == 6:        # 守门：玩家为门将，对方后卫射门
            gk_ai, def_ai, shooter_ai, mod = 0, 0, _enemy_id(tier, 3), 0
        elif stype == 3:      # 点球：有对方门将，无后卫
            gk_ai, def_ai, shooter_ai, mod = _enemy_id(tier, 1), 0, 0, _tier_primary_modifier(tier)
        else:                 # 进攻/任意球/角球/界外球
            gk_ai, def_ai, shooter_ai, mod = _enemy_id(tier, 1), _enemy_id(tier, 2), 0, _tier_primary_modifier(tier)
        rows.append({
            "ID": sid, "SliceID": inst["ID"], "AiProfileID": s["ai_profile_id"],
            "GoalkeeperAiID": gk_ai, "DefenderAiID": def_ai, "ShooterAiID": shooter_ai,
            "ModifierID": mod, "IsGuideAi": 0, "RewindRandom": 1,
            "OverrideReactionTimeMs": s["react_ms"], "Remark": f"库AI tier{tier}",
        })
        sid += 1
    return rows


def _theme_team_pool(tier: int) -> list[int]:
    """该 tier 的 5 个主题对手球队 id（3001-3050）。"""
    base = 3000 + (tier - 1) * 5
    return [base + k for k in range(1, 6)]


def _build_theme_teams(lc: LcRegistry) -> list[dict]:
    """~50 主题对手展示球队(id 3001-3050)；仅展示，复用美术资源键轮换。"""
    regions = ["asia", "europe", "south_america", "africa", "north_america"]
    suffix = ["联", "FC", "竞技", "联合", "勇士"]
    rows = []
    for tier in range(1, TIERS_TOTAL + 1):
        theme = TIER_THEME[tier]
        for k in range(1, 6):
            tid = 3000 + (tier - 1) * 5 + k
            name = f"{theme}·{suffix[k - 1]}"
            kit_idx = ((tid - 1) % 12) + 1
            rows.append({
                "ID": tid,
                "NameLcKey": lc.add(lc_key("team", "name", str(tid)), name, f"TeamCfg/{tid}"),
                "Region": regions[(tier - 1) % len(regions)],
                "KitKey": f"WC_Kit_{kit_idx:02d}",
                "BadgeKey": f"WC_Badge_{kit_idx:02d}",
                "Remark": f"tier{tier}主题对手{k}",
            })
    return rows


def _slice_count(tier: int) -> int:
    if tier == 1:
        return 2
    if tier <= 3:
        return 3
    if tier <= 7:
        return 4
    return 5


def _compose_slice_list(level_in_round: int, tier: int) -> list[int]:
    """类型错位轮换 + 每 3 关末位用 v2(复合/加压)，引用库实例 id。"""
    n = _slice_count(tier)
    start = (level_in_round - 1) % len(SLICE_TYPE_ORDER)
    out: list[int] = []
    for k in range(n):
        stype = SLICE_TYPE_ORDER[(start + k) % len(SLICE_TYPE_ORDER)]
        variant = 2 if (level_in_round % 3 == 0 and k == n - 1) else 1
        out.append(tier * 100 + stype * 10 + variant)
    return out


def _build_seasons(lc: LcRegistry) -> list[dict]:
    """50 轮联赛(单 group=1)；NextSeason 链推进，最后一轮=0。"""
    rows = []
    for r in range(1, ROUNDS_TOTAL + 1):
        tier = math.ceil(r / 5)
        name = f"{TIER_THEME[tier]} 第{r}/{ROUNDS_TOTAL}轮"
        rows.append({
            "ID": r,
            "LeagueNameLcKey": lc.add(lc_key("season", "league_name", str(r)), name, f"SeasonCfg/{r}"),
            "Group": 1,
            "NextSeason": (r + 1 if r < ROUNDS_TOTAL else 0),
            "ContractOfferCount": 3,
            "Remark": f"第{r}轮 tier{tier}",
        })
    return rows


def _build_levels(lc: LcRegistry) -> list[dict]:
    """500 关：lid 全局递增；第1关=引导关(复用 201/202/203)。"""
    rows = []
    lid = 0
    for r in range(1, ROUNDS_TOTAL + 1):
        tier = math.ceil(r / 5)
        s = TIER[tier]
        pool = _theme_team_pool(tier)
        for j in range(1, LEVELS_PER_ROUND + 1):
            lid += 1
            if lid == 1:
                slices = [201, 202, 203]
                is_tut, profile = 1, 1001
            else:
                slices = _compose_slice_list(j, tier)
                is_tut, profile = 0, s["ai_profile_id"]
            n = len(slices)
            win_threshold = math.ceil(n * 0.6)
            draw_threshold = max(1, win_threshold - 1)  # 保证 lose<draw<win 三态可达
            rows.append({
                "ID": lid,
                "IsTutorial": is_tut,
                "SliceList": json.dumps(slices),
                "AiProfileID": profile,
                "WinThreshold": win_threshold,
                "DrawThreshold": draw_threshold,
                "TicketCost": 1,
                "OpponentTeamID": pool[(r - 1) % len(pool)],
                "OpponentTeamStar": s["opponent_star"],
                "Group": r,
                "Remark": (
                    "第1轮-引导关(含守门切片203)" if lid == 1
                    else f"第{r}轮 tier{tier} 第{j}场"
                ),
            })
    return rows


def _preset_angle_cols(slice_type: int, tier_baseline: int = 1) -> dict:
    """Preset 自身 4 角度列存该类型最宽基线(≈tier1)；逐 tier 收窄由实例 override 实现。
    点球/守门无扇形，span 置 0。"""
    if slice_type in (3, 6):
        return {"AngleSpanMin": 0.0, "AngleSpanMax": 0.0, "AngleMaxCenterShift": 0.0, "AngleMargin": 0.0}
    s = TIER[tier_baseline]
    return {
        "AngleSpanMin": float(s["span_min"]),
        "AngleSpanMax": float(s["span_max"]),
        "AngleMaxCenterShift": float(s["center_shift"]),
        "AngleMargin": float(s["margin"]),
    }


def _build_presets(lc: LcRegistry) -> list[dict]:
    """~18 摆位预设，跨 tier 复用。1/2/3/4 沿用原测试预设，新增侧别/难度变体。
    四角度列存最宽基线(tier1)，逐 tier 收窄由实例 OverrideOperableAngle 实现。"""

    def gk_attack(home_x: float) -> list[dict]:
        return [
            player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], home_x, 0, 35),
            player_init("home", 1, PLAYER_AI_DUTY_ENUM["Forward"], home_x - 2, 0, 30),
            player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 55),
            player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], home_x - 4, 0, 48),
        ]

    def free_kick_wall(ball_x: float) -> list[dict]:
        return [
            player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], ball_x, 0, 42),
            player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 58),
            player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], -2, 0, 50),
            player_init("away", 2, PLAYER_AI_DUTY_ENUM["Defender"], 2, 0, 50),
            player_init("away", 3, PLAYER_AI_DUTY_ENUM["Defender"], -1, 0, 50),
            player_init("away", 4, PLAYER_AI_DUTY_ENUM["Defender"], 1, 0, 50),
        ]

    def corner_players(side_x: float) -> list[dict]:
        return [
            player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], side_x, 0, 56),
            player_init("home", 1, PLAYER_AI_DUTY_ENUM["Forward"], 2, 0, 52),
            player_init("home", 2, PLAYER_AI_DUTY_ENUM["Forward"], -2, 0, 52),
            player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 58),
            player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], 0, 0, 53),
        ]

    def throw_in_players(side_x: float) -> list[dict]:
        return [
            player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], side_x, 0, 40),
            player_init("home", 1, PLAYER_AI_DUTY_ENUM["Forward"], side_x - 3, 0, 44),
            player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 58),
            player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], side_x - 2, 0, 46),
        ]

    def penalty_players() -> list[dict]:
        return [
            player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], 0, 0, 50),
            player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 58),
        ]

    def goalkeep_players() -> list[dict]:
        return [
            player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], 0, 0, 58),
            player_init("away", 0, PLAYER_AI_DUTY_ENUM["Defender"], 0, 0, 56),
        ]

    # (id, slice_type, name, tags, ball_pos, ball_vector, ball_owner, players, fov, target, op_angle, type_payload, rec_modes)
    specs = [
        (1, "attack", "右路单刀", '["side","easy"]', '{"x":12,"y":0,"z":35}', '{"x":0,"y":0,"z":1}', 0, gk_attack(12), 45, '{"x":12,"y":0,"z":58}', 35.0, '{"keeper_weight":5000,"angle":35}', '["draw_line","slingshot"]'),
        (5, "attack", "左路单刀", '["side"]', '{"x":-12,"y":0,"z":35}', '{"x":0,"y":0,"z":1}', 0, gk_attack(-12), 45, '{"x":-12,"y":0,"z":58}', 35.0, '{"keeper_weight":5000,"angle":35}', '["draw_line","slingshot"]'),
        (6, "attack", "中路突破", '["center"]', '{"x":0,"y":0,"z":36}', '{"x":0,"y":0,"z":1}', 0, gk_attack(0), 44, '{"x":0,"y":0,"z":58}', 35.0, '{"keeper_weight":5200,"angle":35}', '["draw_line","slingshot"]'),
        (16, "attack", "中路吊射", '["center","lob"]', '{"x":0,"y":0,"z":30}', '{"x":0,"y":0,"z":1}', 0, gk_attack(0), 46, '{"x":0,"y":1.5,"z":58}', 32.0, '{"keeper_weight":5400,"angle":32}', '["draw_line","slingshot"]'),
        (2, "free_kick", "中路任意球", '["center"]', '{"x":0,"y":0,"z":42}', '{"x":0,"y":0,"z":1}', 0, free_kick_wall(0), 42, '{"x":0,"y":1.8,"z":58}', 28.0, '{"wall_count":4,"keeper_weight":4500}', '["draw_line","slingshot"]'),
        (7, "free_kick", "左侧任意球", '["side"]', '{"x":-10,"y":0,"z":44}', '{"x":0,"y":0,"z":1}', 0, free_kick_wall(-10), 42, '{"x":-2,"y":1.8,"z":58}', 28.0, '{"wall_count":4,"keeper_weight":4500}', '["draw_line","slingshot"]'),
        (8, "free_kick", "右侧任意球", '["side"]', '{"x":10,"y":0,"z":44}', '{"x":0,"y":0,"z":1}', 0, free_kick_wall(10), 42, '{"x":2,"y":1.8,"z":58}', 28.0, '{"wall_count":4,"keeper_weight":4500}', '["draw_line","slingshot"]'),
        (17, "free_kick", "弧线任意球", '["center","curve"]', '{"x":4,"y":0,"z":40}', '{"x":0,"y":0,"z":1}', 0, free_kick_wall(4), 41, '{"x":-3,"y":2.0,"z":58}', 26.0, '{"wall_count":5,"keeper_weight":4800}', '["draw_line"]'),
        (3, "penalty", "标准点球", '["penalty"]', '{"x":0,"y":0,"z":50}', '{"x":0,"y":0,"z":1}', 0, penalty_players(), 40, '{"x":0,"y":0.5,"z":58}', 0.0, '{"keeper_dirs":[2500,2500,2500,2500]}', '["draw_line","slingshot"]'),
        (9, "penalty", "加压点球", '["penalty","hard"]', '{"x":0,"y":0,"z":50}', '{"x":0,"y":0,"z":1}', 0, penalty_players(), 40, '{"x":0,"y":0.5,"z":58}', 0.0, '{"keeper_dirs":[2000,3000,3000,2000]}', '["draw_line","slingshot"]'),
        (10, "corner", "左角球", '["corner","left"]', '{"x":-20,"y":0,"z":58}', '{"x":1,"y":0,"z":-1}', 0, corner_players(-20), 48, '{"x":0,"y":2.0,"z":55}', 30.0, '{"first_point_weight":5000}', '["draw_line"]'),
        (11, "corner", "右角球", '["corner","right"]', '{"x":20,"y":0,"z":58}', '{"x":-1,"y":0,"z":-1}', 0, corner_players(20), 48, '{"x":0,"y":2.0,"z":55}', 30.0, '{"first_point_weight":5000}', '["draw_line"]'),
        (18, "corner", "后点包抄", '["corner","far"]', '{"x":20,"y":0,"z":58}', '{"x":-1,"y":0,"z":-1}', 0, corner_players(20), 48, '{"x":-6,"y":2.0,"z":54}', 28.0, '{"first_point_weight":4500,"far_post":1}', '["draw_line"]'),
        (12, "throw_in", "左界外球", '["throw_in","left"]', '{"x":-22,"y":0,"z":40}', '{"x":1,"y":0,"z":0}', 0, throw_in_players(-22), 44, '{"x":-10,"y":0,"z":44}', 34.0, '{"second_attack":1}', '["draw_line"]'),
        (13, "throw_in", "右界外球", '["throw_in","right"]', '{"x":22,"y":0,"z":40}', '{"x":-1,"y":0,"z":0}', 0, throw_in_players(22), 44, '{"x":10,"y":0,"z":44}', 34.0, '{"second_attack":1}', '["draw_line"]'),
        (4, "goalkeep", "基础守门", '["gk"]', '{"x":0,"y":0,"z":56}', '{"x":0,"y":0,"z":-1}', None, goalkeep_players(), 50, None, 0.0, '{"shot_dirs":[3000,3000,4000],"reaction_ms":2500}', '["draw_line"]'),
        (14, "goalkeep", "大范围守门", '["gk","wide"]', '{"x":0,"y":0,"z":56}', '{"x":0,"y":0,"z":-1}', None, goalkeep_players(), 52, None, 0.0, '{"shot_dirs":[3500,3500,3000],"reaction_ms":2200}', '["draw_line"]'),
        (15, "goalkeep", "近距扑点", '["gk","penalty"]', '{"x":0,"y":0,"z":54}', '{"x":0,"y":0,"z":-1}', None, goalkeep_players(), 50, None, 0.0, '{"shot_dirs":[4000,4000,2000],"reaction_ms":1800}', '["draw_line"]'),
    ]

    rows = []
    type_id = {v: k for k, v in SLICE_TYPE_NAME.items()}
    for (pid, stype, name, tags, ball_pos, ball_vec, owner, players, fov, target, op_angle, payload, rec) in specs:
        row = {
            "ID": pid, "SliceType": stype,
            "NameLcKey": lc.add(lc_key("preset", "name", str(pid)), name, f"SlicePresetCfg/{pid}"),
            "Tags": tags, "BallPos": ball_pos, "BallVector": ball_vec, "BallOwner": owner,
            "PlayersInit": players_init_json(players), "CameraFov": fov, "TargetPoint": target,
            "OperableAngle": op_angle, "TypePayload": payload, "RecommendedModes": rec,
        }
        row.update(_preset_angle_cols(type_id[stype]))
        rows.append(row)
    return rows


def build_workbook(lc: LcRegistry, const_rows: list[dict]) -> Workbook:
    wb = Workbook()
    wb.remove(wb.active)

    # --- 3.1 创角 ---
    make_sheet(
        wb,
        "ActvSoccerCharacterCfg",
        c(
            id_col("int", "角色ID character_id"),
            ("AppearanceKey", "string", "外观资源键"),
            ("DisplayPower", "int", "展示战力(仅表现)"),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 1, "AppearanceKey": "WC_Char_01", "DisplayPower": 10, "Remark": "角色A"},
            {"ID": 2, "AppearanceKey": "WC_Char_02", "DisplayPower": 10, "Remark": "角色B"},
            {"ID": 3, "AppearanceKey": "WC_Char_03", "DisplayPower": 10, "Remark": "角色C"},
            {"ID": 4, "AppearanceKey": "WC_Char_04", "DisplayPower": 10, "Remark": "角色D"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerNationalityCfg",
        c(
            id_col("int", "国籍ID"),
            ("NameLcKey", "string", "国籍名称→ActvSoccerLanguageCfg"),
            ("Region", "string", "所属地区"),
            ("ContractPool", "int[]", "首签合同池(关联contract_id)"),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 1, "NameLcKey": lc.add(lc_key("nationality", "name", "1"), "中国", "NationalityCfg/1"), "Region": "asia", "ContractPool": "[1,101,102]", "Remark": "默认合同1+地区合同101/102"},
            {"ID": 2, "NameLcKey": lc.add(lc_key("nationality", "name", "2"), "德国", "NationalityCfg/2"), "Region": "europe", "ContractPool": "[11,103,104]", "Remark": ""},
            {"ID": 3, "NameLcKey": lc.add(lc_key("nationality", "name", "3"), "巴西", "NationalityCfg/3"), "Region": "south_america", "ContractPool": "[12,105,106]", "Remark": ""},
            {"ID": 4, "NameLcKey": lc.add(lc_key("nationality", "name", "4"), "阿根廷", "NationalityCfg/4"), "Region": "south_america", "ContractPool": "[13,105,107]", "Remark": ""},
            {"ID": 5, "NameLcKey": lc.add(lc_key("nationality", "name", "5"), "法国", "NationalityCfg/5"), "Region": "europe", "ContractPool": "[11,103,108]", "Remark": ""},
            {"ID": 6, "NameLcKey": lc.add(lc_key("nationality", "name", "6"), "西班牙", "NationalityCfg/6"), "Region": "europe", "ContractPool": "[11,103,108]", "Remark": ""},
            {"ID": 7, "NameLcKey": lc.add(lc_key("nationality", "name", "7"), "葡萄牙", "NationalityCfg/7"), "Region": "europe", "ContractPool": "[11,103,108]", "Remark": ""},
            {"ID": 8, "NameLcKey": lc.add(lc_key("nationality", "name", "8"), "比利时", "NationalityCfg/8"), "Region": "europe", "ContractPool": "[11,103,108]", "Remark": ""},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerTutorialCfg",
        c(
            id_col("int", "试训步骤序号"),
            ("SliceType", "string", "切片类型"),
            ("SliceInstanceID", "int", "关联切片实例(测试用)"),
            ("ForcedOrder", "bool", "强制顺序"),
            ("DescLcKey", "string", "步骤描述→ActvSoccerLanguageCfg"),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 1, "SliceType": "attack", "SliceInstanceID": 101, "ForcedOrder": 1, "DescLcKey": lc.add(lc_key("tutorial", "desc", "1"), "进攻教学", "TutorialCfg/1")},
            {"ID": 2, "SliceType": "free_kick", "SliceInstanceID": 102, "ForcedOrder": 1, "DescLcKey": lc.add(lc_key("tutorial", "desc", "2"), "任意球教学", "TutorialCfg/2")},
            {"ID": 3, "SliceType": "penalty", "SliceInstanceID": 103, "ForcedOrder": 1, "DescLcKey": lc.add(lc_key("tutorial", "desc", "3"), "点球教学", "TutorialCfg/3")},
        ],
    )

    # --- 3.2 切片 ---
    make_sheet(
        wb,
        "ActvSoccerSliceTypeDefCfg",
        c(
            id_col("int", "编号"),
            ("SliceType", "string", "切片类型"),
            ("AllowedModes", "string[]", "允许操作模式"),
            ("JudgeFn", "string", "判定函数"),
            ("PayloadSchema", "string", "type_payload schema"),
            ("DefaultCameraFov", "float", "默认相机FOV(0=用预设)"),
            ("Remark", "string", "L1只读"),
        ),
        [
            {"ID": 1, "SliceType": "attack", "AllowedModes": '["draw_line","slingshot"]', "JudgeFn": "judge_attack", "PayloadSchema": "dest,keeper_weight,angle", "DefaultCameraFov": 0, "Remark": ""},
            {"ID": 2, "SliceType": "free_kick", "AllowedModes": '["draw_line","slingshot"]', "JudgeFn": "judge_free_kick", "PayloadSchema": "spot,wall,angle,keeper_weight", "DefaultCameraFov": 0, "Remark": ""},
            {"ID": 3, "SliceType": "penalty", "AllowedModes": '["draw_line","slingshot"]', "JudgeFn": "judge_penalty", "PayloadSchema": "spot,keeper_dirs,reaction_ms", "DefaultCameraFov": 0, "Remark": ""},
            {"ID": 4, "SliceType": "corner", "AllowedModes": '["draw_line","slingshot"]', "JudgeFn": "judge_corner", "PayloadSchema": "corner_spot,runs,first_touch", "DefaultCameraFov": 0, "Remark": ""},
            {"ID": 5, "SliceType": "throw_in", "AllowedModes": '["draw_line","slingshot"]', "JudgeFn": "judge_throw_in", "PayloadSchema": "throw_spot,runs,second_attack", "DefaultCameraFov": 0, "Remark": ""},
            {"ID": 6, "SliceType": "goalkeep", "AllowedModes": '["draw_line"]', "JudgeFn": "judge_goalkeep", "PayloadSchema": "shot_dirs,reaction_ms", "DefaultCameraFov": 0, "Remark": "仅划线"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerSlicePresetCfg",
        c(
            id_col("int", "preset_id"),
            ("SliceType", "string", "切片类型"),
            ("NameLcKey", "string", "预设名→ActvSoccerLanguageCfg"),
            ("Tags", "string[]", "标签"),
            ("BallPos", "ext", "球位置", P_VEC3, '{"x":0,"y":0,"z":0}'),
            ("BallVector", "ext", "球方向", P_VEC3, '{"x":0,"y":0,"z":1}'),
            ("BallOwner", "int", "控球球员索引"),
            ("PlayersInit", "ext[]", f"球员站位+duty({PLAYER_AI_DUTY_ENUM_COMMENT})", V_PLAYER_INIT, PLAYER_INIT_DEFAULT),
            ("CameraFov", "float", "相机FOV"),
            ("TargetPoint", "ext", "目标点", P_VEC3, '{"x":0,"y":0,"z":58}'),
            ("OperableAngle", "float", "可操作夹角(兼容字段=AngleSpanMax默认)"),
            ("AngleSpanMin", "float", "可操作夹角宽度下限(°)"),
            ("AngleSpanMax", "float", "可操作夹角宽度上限(°)"),
            ("AngleMaxCenterShift", "float", "扇形中心相对接球方向最大偏移(°)"),
            ("AngleMargin", "float", "合法目标贴边余量(°)"),
            ("TypePayload", "ext", "type_payload默认", V_TYPE_PAYLOAD, '{"keeper_weight":5000,"angle":35}'),
            ("RecommendedModes", "string[]", "建议模式"),
            ("Remark", "string", "备注"),
        ),
        _build_presets(lc),
    )

    make_sheet(
        wb,
        "ActvSoccerSliceInstanceCfg",
        c(
            id_col("int", "slice_instance_id"),
            ("SliceType", "string", "切片类型"),
            ("PresetID", "int", "preset_id"),
            ("OverrideOperableAngle", "float", "覆盖可操作夹角(0=不覆盖)"),
            ("ObjectiveType", "string", "单一胜利目标(score/survive等)"),
            ("ExtraObjectives", "ext[]", "复合胜利目标", V_OBJECTIVE, '[{"type":"pass_to","params":{"target":1}},{"type":"score"}]'),
            ("Modifiers", "ext[]", "切片机制", V_MODIFIER, '[{"id":"moving_keeper","params":{"speed":1.0}}]'),
            ("Remark", "string", "备注"),
        ),
        _build_instance_library(),
    )

    make_sheet(
        wb,
        "ActvSoccerInMatchItemCfg",
        c(
            id_col("int", "item_id"),
            ("ItemKey", "string", "道具键"),
            ("Effect", "string", "效果"),
            ("DefaultActive", "bool", "默认生效"),
            ("FreeCount", "int", "免费次数"),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 1, "ItemKey": "whistle", "Effect": "add_non_gk_slice", "DefaultActive": 1, "FreeCount": 0, "Remark": "哨子"},
            {"ID": 2, "ItemKey": "rewind", "Effect": "reset_slice", "DefaultActive": 0, "FreeCount": 1, "Remark": "回溯"},
            {"ID": 3, "ItemKey": "aim", "Effect": "aim_line", "DefaultActive": 1, "FreeCount": 0, "Remark": "瞄准"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerHapticCfg",
        c(
            id_col("int", "编号"),
            ("EventID", "string", "事件"),
            ("Category", "string", "core_operation/key_result"),
            ("Intensity", "string", "light/medium/heavy"),
            ("Pattern", "string", "tick/double/continuous"),
            ("DurationMs", "int", "时长ms"),
            ("MinIntervalMs", "int", "节流ms"),
            ("EnabledDefault", "bool", "默认开启"),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 1, "EventID": "charge_locked", "Category": "core_operation", "Intensity": "light", "Pattern": "tick", "DurationMs": 30, "MinIntervalMs": 200, "EnabledDefault": 1},
            {"ID": 2, "EventID": "ball_released", "Category": "core_operation", "Intensity": "medium", "Pattern": "tick", "DurationMs": 40, "MinIntervalMs": 200, "EnabledDefault": 1},
            {"ID": 3, "EventID": "slice_success", "Category": "key_result", "Intensity": "heavy", "Pattern": "double", "DurationMs": 80, "MinIntervalMs": 300, "EnabledDefault": 1, "Remark": "进球"},
            {"ID": 4, "EventID": "saved", "Category": "key_result", "Intensity": "medium", "Pattern": "tick", "DurationMs": 50, "MinIntervalMs": 300, "EnabledDefault": 1},
            {"ID": 5, "EventID": "out_of_bounds", "Category": "key_result", "Intensity": "medium", "Pattern": "tick", "DurationMs": 50, "MinIntervalMs": 300, "EnabledDefault": 1},
            {"ID": 6, "EventID": "gk_timeout", "Category": "key_result", "Intensity": "heavy", "Pattern": "tick", "DurationMs": 60, "MinIntervalMs": 300, "EnabledDefault": 1},
            {"ID": 7, "EventID": "gk_wrong_judge", "Category": "key_result", "Intensity": "medium", "Pattern": "double", "DurationMs": 70, "MinIntervalMs": 300, "EnabledDefault": 1},
            {"ID": 8, "EventID": "gk_save", "Category": "key_result", "Intensity": "heavy", "Pattern": "double", "DurationMs": 80, "MinIntervalMs": 300, "EnabledDefault": 1},
            {"ID": 9, "EventID": "hit_post", "Category": "key_result", "Intensity": "medium", "Pattern": "double", "DurationMs": 60, "MinIntervalMs": 300, "EnabledDefault": 1},
            {"ID": 10, "EventID": "rewind_reset", "Category": "key_result", "Intensity": "light", "Pattern": "continuous", "DurationMs": 120, "MinIntervalMs": 500, "EnabledDefault": 1},
        ],
    )

    # --- 3.3 关卡 ---
    make_sheet(
        wb,
        "ActvSoccerLevelCfg",
        c(
            id_col("int", "level_id"),
            ("IsTutorial", "bool", "引导关"),
            ("SliceList", "int[]", "切片实例序列"),
            ("AiProfileID", "int", "AI档位"),
            ("WinThreshold", "int", "胜利阈值"),
            ("DrawThreshold", "int", "平局阈值"),
            ("TicketCost", "int", "门票消耗"),
            ("OpponentTeamID", "int", "对手球队(队名/队服/队标)"),
            ("OpponentTeamStar", "int", "对手球队星级(球员属性计算依据)"),
            ("Group", "int", "所属联赛轮次(=SeasonCfg.ID)"),
            ("Remark", "string", "备注"),
        ),
        _build_levels(lc),
    )

    # --- FSM/BT/敌人AI (2026-06-09 design) ---
    make_sheet(
        wb,
        "ActvSoccerPlayerAiDutyEnumCfg",
        c(
            id_col("int", "枚举值"),
            ("EnumKey", "string", "枚举名"),
            ("Remark", "string", "说明"),
        ),
        [
            {"ID": 1, "EnumKey": "Goalkeeper", "Remark": "守门员"},
            {"ID": 2, "EnumKey": "Defender", "Remark": "后卫：对方除门将外所有球员"},
            {"ID": 3, "EnumKey": "Forward", "Remark": "前锋：我方所有球员(含玩家角色)"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerAiProfileCfg",
        c(
            id_col("int", "AI难度档ID"),
            ("Difficulty", "string", "easy/normal/hard"),
            ("GoalkeeperSaveRate", "int", "门将扑救成功率%"),
            ("DefenderSuccessRate", "int", "防守成功率%"),
            ("ShooterSuccessRate", "int", "对手射门成功率%"),
            ("DeadCornerCanSave", "int", "死角可扑(固定0)"),
            ("ReactionTimeMs", "int", "默认反应时间ms"),
            ("Remark", "string", "备注"),
        ),
        _build_ai_profiles(),
    )

    make_sheet(
        wb,
        "ActvSoccerEnemyAiCfg",
        c(
            id_col("int", "敌人AI配置ID"),
            ("Duty", "int", "球员AI职责→ActvSoccerPlayerAiDutyEnumCfg", "", PLAYER_AI_DUTY_ENUM_COMMENT),
            ("SaveWeight", "int", "扑救权重"),
            ("LeftWeight", "int", "左方向权重"),
            ("RightWeight", "int", "右方向权重"),
            ("UpWeight", "int", "上方向权重"),
            ("InterceptWeight", "int", "拦截权重"),
            ("ClearanceWeight", "int", "解围出界权重"),
            ("KeeperCatchFail", "int", "门将接球直接失败"),
            ("OutOfBoundsFail", "int", "踢出界外失败"),
            ("AnimationKey", "string", "默认表现动作"),
            ("Remark", "string", "备注"),
        ),
        _build_enemy_ai(),
    )

    make_sheet(
        wb,
        "ActvSoccerSliceAiCfg",
        c(
            id_col("int", "单切片AI配置ID"),
            ("SliceID", "int", "切片实例ID→ActvSoccerSliceInstanceCfg"),
            ("AiProfileID", "int", "难度档→ActvSoccerAiProfileCfg"),
            ("GoalkeeperAiID", "int", "门将AI"),
            ("DefenderAiID", "int", "防守AI"),
            ("ShooterAiID", "int", "射手AI"),
            ("ModifierID", "int", "机制→ActvSoccerAiModifierCfg"),
            ("IsGuideAi", "bool", "引导关AI"),
            ("RewindRandom", "bool", "回溯后重随机"),
            ("OverrideReactionTimeMs", "int", "覆盖反应时间(0=默认)"),
            ("Remark", "string", "备注"),
        ),
        _slice_ai_for_library(_build_instance_library()),
    )

    make_sheet(
        wb,
        "ActvSoccerAiModifierCfg",
        c(
            id_col("int", "机制ID"),
            ("ModifierType", "string", "机制类型"),
            ("Param1Key", "string", "参数1键"),
            ("Param1Value", "string", "参数1值"),
            ("Param2Key", "string", "参数2键"),
            ("Param2Value", "string", "参数2值"),
            ("Param3Key", "string", "参数3键"),
            ("Param3Value", "string", "参数3值"),
            ("Remark", "string", "备注"),
        ),
        _build_ai_modifiers(),
    )

    make_sheet(
        wb,
        "ActvSoccerSliceFlowCfg",
        c(
            id_col("int", "切片流程ID"),
            ("SliceType", "string", "切片类型"),
            ("ForceOperationMode", "string", "强制操作模式"),
            ("WaitInputTimeMs", "int", "等待限时(0=无限)"),
            ("NeedReplayClick", "bool", "回放需手动结束"),
            ("EnableRewind", "bool", "允许回溯"),
            ("SuccessReplayKey", "string", "成功回放key"),
            ("FailReplayKey", "string", "失败回放key"),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 5001, "SliceType": "attack", "ForceOperationMode": "none", "WaitInputTimeMs": 0, "NeedReplayClick": 1, "EnableRewind": 1, "SuccessReplayKey": "Celebrate", "FailReplayKey": "Fail", "Remark": "进攻切片"},
            {"ID": 5002, "SliceType": "free_kick", "ForceOperationMode": "none", "WaitInputTimeMs": 0, "NeedReplayClick": 1, "EnableRewind": 1, "SuccessReplayKey": "Celebrate", "FailReplayKey": "Fail", "Remark": "任意球"},
            {"ID": 5003, "SliceType": "penalty", "ForceOperationMode": "none", "WaitInputTimeMs": 0, "NeedReplayClick": 1, "EnableRewind": 1, "SuccessReplayKey": "Celebrate", "FailReplayKey": "Fail", "Remark": "点球"},
            {"ID": 5004, "SliceType": "goalkeep", "ForceOperationMode": "draw_line", "WaitInputTimeMs": 900, "NeedReplayClick": 1, "EnableRewind": 1, "SuccessReplayKey": "SaveSuccess", "FailReplayKey": "TimeoutFeedback", "Remark": "守门强制划线"},
            {"ID": 5005, "SliceType": "tutorial_attack", "ForceOperationMode": "none", "WaitInputTimeMs": 0, "NeedReplayClick": 1, "EnableRewind": 1, "SuccessReplayKey": "Celebrate", "FailReplayKey": "Fail", "Remark": "引导进攻(试训模式可切换)"},
            {"ID": 5006, "SliceType": "corner", "ForceOperationMode": "none", "WaitInputTimeMs": 0, "NeedReplayClick": 1, "EnableRewind": 1, "SuccessReplayKey": "Celebrate", "FailReplayKey": "Fail", "Remark": "角球P1"},
            {"ID": 5007, "SliceType": "throw_in", "ForceOperationMode": "none", "WaitInputTimeMs": 0, "NeedReplayClick": 1, "EnableRewind": 1, "SuccessReplayKey": "Celebrate", "FailReplayKey": "Fail", "Remark": "界外球P1"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerCharacterStateCfg",
        c(
            id_col("int", "ID"),
            ("StateKey", "string", "FSM状态"),
            ("Duty", "int", "球员AI职责→ActvSoccerPlayerAiDutyEnumCfg", "", CHARACTER_STATE_DUTY_COMMENT),
            ("AnimKey", "string", "美术动作key"),
            ("MirrorFromID", "int", "镜像来源ID"),
            ("IsLoop", "bool", "循环"),
            ("NeedEvent", "bool", "关键帧事件"),
            ("EventKey", "string", "事件名"),
            ("Priority", "string", "P0/P1/P2"),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 1001, "StateKey": "Idle", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "A01_Idle", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0"},
            {"ID": 1002, "StateKey": "Run", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "A02_Jog", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0"},
            {"ID": 1003, "StateKey": "Run", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "A03_Sprint", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0", "Remark": "冲刺跑"},
            {"ID": 1004, "StateKey": "Control", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "B01_ReceiveBall", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "ReceiveBall", "Priority": "P0"},
            {"ID": 1005, "StateKey": "Control", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "B02_DribbleTouch", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "TouchBall", "Priority": "P0"},
            {"ID": 1006, "StateKey": "Pass", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "C01_ShortPass", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "ReleaseBall", "Priority": "P0"},
            {"ID": 1007, "StateKey": "Pass", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "C01_ShortPass", "MirrorFromID": 1006, "IsLoop": 0, "NeedEvent": 1, "EventKey": "ReleaseBall", "Priority": "P0", "Remark": "长传复用短传"},
            {"ID": 1008, "StateKey": "Kick", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "D01_Shoot", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "ReleaseBall", "Priority": "P0"},
            {"ID": 1009, "StateKey": "Kick", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "D02_PowerShot", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "ReleaseBall", "Priority": "P0"},
            {"ID": 1010, "StateKey": "Celebrate", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "G03_JumpCelebrate", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 0, "Priority": "P0"},
            {"ID": 1011, "StateKey": "Fail", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "H03_KneelDown", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 0, "Priority": "P0", "Remark": "建议升P0"},
            {"ID": 2001, "StateKey": "SavePrepare", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E01_GKIdle", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0"},
            {"ID": 2002, "StateKey": "Run", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E02_GKMoveLeft", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0", "Remark": "门将左移"},
            {"ID": 2003, "StateKey": "Run", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E02_GKMoveLeft", "MirrorFromID": 2002, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0", "Remark": "门将右移镜像"},
            {"ID": 2004, "StateKey": "SaveLeft", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E04_GKDiveLeft", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "SaveContact", "Priority": "P0"},
            {"ID": 2005, "StateKey": "SaveRight", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E04_GKDiveLeft", "MirrorFromID": 2004, "IsLoop": 0, "NeedEvent": 1, "EventKey": "SaveContact", "Priority": "P0"},
            {"ID": 2006, "StateKey": "SaveUp", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E06_GKCatch", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "SaveContact", "Priority": "P0", "Remark": "临时复用接球"},
            {"ID": 2007, "StateKey": "SaveSuccess", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E06_GKCatch", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "SaveContact", "Priority": "P0"},
            {"ID": 2008, "StateKey": "Fail", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E07_GKMiss", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 0, "Priority": "P0"},
            {"ID": 3001, "StateKey": "Idle", "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "AnimKey": "F01_DefendIdle", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0"},
            {"ID": 3002, "StateKey": "Run", "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "AnimKey": "F02_DefendShuffle", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0"},
            {"ID": 3003, "StateKey": "Control", "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "AnimKey": "F03_Intercept", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "InterceptBall", "Priority": "P0"},
            {"ID": 3004, "StateKey": "Idle", "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "AnimKey": "K03_WallDefense", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P1", "Remark": "对方人墙(后卫)"},
            {"ID": 4001, "StateKey": "Kick", "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "AnimKey": "D01_Shoot", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "ReleaseBall", "Priority": "P0", "Remark": "守门切片对方后卫射门"},
            {"ID": 5001, "StateKey": "Transition", "Duty": CHARACTER_STATE_SCENE_DUTY, "AnimKey": "I02_KickoffReady", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 0, "Priority": "P0", "Remark": "场景表现,Duty=0非枚举"},
            {"ID": 5002, "StateKey": "Transition", "Duty": CHARACTER_STATE_SCENE_DUTY, "AnimKey": "I03_GoalFreeze", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 0, "Priority": "P0", "Remark": "场景表现,Duty=0非枚举"},
            {"ID": 5003, "StateKey": "Fail", "Duty": CHARACTER_STATE_SCENE_DUTY, "AnimKey": "J01_TimeoutFeedback", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 0, "Priority": "P0", "Remark": "守门超时反馈,Duty=0非枚举"},
        ],
    )

    # --- 3.4 养成 ---
    make_sheet(
        wb,
        "ActvSoccerCurrencyCfg",
        c(
            id_col("int", "currency_id"),
            ("CurrencyKey", "string", "货币键"),
            ("Usage", "string", "用途"),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 1, "CurrencyKey": "gold", "Usage": "生活等级升级", "Remark": "金币"},
            {"ID": 2, "CurrencyKey": "ticket", "Usage": "积分赛消耗", "Remark": "门票"},
            {"ID": 3, "CurrencyKey": "bet_coin", "Usage": "竞猜与兑换商店", "Remark": "竞猜币"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerFameGrowthLevelCfg",
        c(
            id_col("int", "编号"),
            ("Level", "int", "知名度等级"),
            ("ExpRequired", "int", "升级所需知名度经验"),
            ("ContractStarLicReward", "int", "合同星级许可奖励(0=无,2-5=license_id)"),
            ("TitleLcKey", "string", "称号→ActvSoccerLanguageCfg"),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 1, "Level": 1, "ExpRequired": 0, "ContractStarLicReward": 0, "TitleLcKey": lc.add(lc_key("growth", "fame_title", "1"), "业余球员", "FameGrowthLevelCfg/1")},
            {"ID": 2, "Level": 2, "ExpRequired": 100, "ContractStarLicReward": 0, "TitleLcKey": lc.add(lc_key("growth", "fame_title", "2"), "新秀", "FameGrowthLevelCfg/2"), "Remark": ""},
            {"ID": 3, "Level": 3, "ExpRequired": 150, "ContractStarLicReward": 2, "TitleLcKey": lc.add(lc_key("growth", "fame_title", "3"), "专业球员", "FameGrowthLevelCfg/3"), "Remark": "3级→2星许可"},
            {"ID": 4, "Level": 4, "ExpRequired": 180, "ContractStarLicReward": 2, "TitleLcKey": lc.add(lc_key("growth", "fame_title", "4"), "明星", "FameGrowthLevelCfg/4"), "Remark": ""},
            {"ID": 5, "Level": 5, "ExpRequired": 200, "ContractStarLicReward": 3, "TitleLcKey": lc.add(lc_key("growth", "fame_title", "5"), "大师", "FameGrowthLevelCfg/5"), "Remark": "文档示例:知名度5级→3星许可"},
            {"ID": 6, "Level": 6, "ExpRequired": 240, "ContractStarLicReward": 4, "TitleLcKey": lc.add(lc_key("growth", "fame_title", "6"), "世界级", "FameGrowthLevelCfg/6"), "Remark": "6级→4星许可"},
            {"ID": 7, "Level": 7, "ExpRequired": 300, "ContractStarLicReward": 5, "TitleLcKey": lc.add(lc_key("growth", "fame_title", "7"), "传奇", "FameGrowthLevelCfg/7"), "Remark": "7级→5星许可(tier9-10合同池可达)"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerLifeGrowthLevelCfg",
        c(
            id_col("int", "编号"),
            ("Level", "int", "生活等级"),
            ("ExpRequired", "int", "升级消耗金币"),
            ("RewardFame", "int", "升级奖励知名度(0=无)"),
            ("ContractStarLicReward", "int", "合同星级许可奖励(0=无,2-5=license_id)"),
            ("TicketCap", "int", "门票上限"),
            ("TicketRecoverMin", "int", "门票恢复间隔分钟"),
            ("FreeRewind", "int", "免费回溯次数"),
            ("ExtraRound", "int", "额外联赛轮次"),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 1, "Level": 1, "ExpRequired": 0, "ContractStarLicReward": 0, "TicketCap": 80, "TicketRecoverMin": 30, "Remark": ""},
            {"ID": 2, "Level": 2, "ExpRequired": 100, "ContractStarLicReward": 0, "TicketCap": 200, "TicketRecoverMin": 28, "FreeRewind": 1, "Remark": "升级消耗金币100"},
            {"ID": 3, "Level": 3, "ExpRequired": 150, "ContractStarLicReward": 2, "TicketCap": 220, "TicketRecoverMin": 26, "Remark": "3级→2星许可"},
            {"ID": 4, "Level": 4, "ExpRequired": 200, "RewardFame": 10, "ContractStarLicReward": 3, "TicketCap": 250, "TicketRecoverMin": 25, "ExtraRound": 5, "Remark": "文档示例:生活4级→3星许可"},
            {"ID": 5, "Level": 5, "ExpRequired": 300, "ContractStarLicReward": 4, "TicketCap": 280, "TicketRecoverMin": 22, "Remark": "5级→4星许可"},
            {"ID": 6, "Level": 6, "ExpRequired": 400, "RewardFame": 15, "ContractStarLicReward": 4, "TicketCap": 300, "TicketRecoverMin": 20, "FreeRewind": 2, "Remark": "6级→4星许可(维持)"},
            {"ID": 7, "Level": 7, "ExpRequired": 550, "RewardFame": 20, "ContractStarLicReward": 5, "TicketCap": 320, "TicketRecoverMin": 18, "FreeRewind": 2, "ExtraRound": 10, "Remark": "7级→5星许可(tier9-10合同池可达)"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerFameGainRuleCfg",
        c(
            id_col("int", "编号"),
            ("FromWin", "int", "胜"),
            ("FromDraw", "int", "平"),
            ("FromLose", "int", "负"),
            ("FromGoal", "int", "每进球"),
            ("FromAssist", "int", "每助攻"),
            ("TeamStarFactor", "float", "合同星级系数(读current_contract.team_star)"),
            ("Remark", "string", "TODO数值"),
        ),
        [{"ID": 1, "FromWin": 20, "FromDraw": 10, "FromLose": 5, "FromGoal": 5, "FromAssist": 3, "TeamStarFactor": 1.0, "Remark": "测试占位"}],
    )

    make_sheet(
        wb,
        "ActvSoccerTeamCfg",
        c(
            id_col("int", "team_id"),
            ("NameLcKey", "string", "球队名→ActvSoccerLanguageCfg"),
            ("Region", "string", "地区(纯展示)"),
            ("KitKey", "string", "队服资源"),
            ("BadgeKey", "string", "队标资源"),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 101, "NameLcKey": lc.add(lc_key("team", "name", "101"), "红星联", "TeamCfg/101"), "Region": "asia", "KitKey": "WC_Kit_01", "BadgeKey": "WC_Badge_01", "Remark": "默认展示球队"},
            {"ID": 102, "NameLcKey": lc.add(lc_key("team", "name", "102"), "莱茵青年", "TeamCfg/102"), "Region": "europe", "KitKey": "WC_Kit_02", "BadgeKey": "WC_Badge_02", "Remark": ""},
            {"ID": 103, "NameLcKey": lc.add(lc_key("team", "name", "103"), "桑巴之星", "TeamCfg/103"), "Region": "south_america", "KitKey": "WC_Kit_03", "BadgeKey": "WC_Badge_03", "Remark": ""},
            {"ID": 104, "NameLcKey": lc.add(lc_key("team", "name", "104"), "蓝白雄鹰", "TeamCfg/104"), "Region": "south_america", "KitKey": "WC_Kit_04", "BadgeKey": "WC_Badge_04", "Remark": ""},
            {"ID": 201, "NameLcKey": lc.add(lc_key("team", "name", "201"), "海港FC", "TeamCfg/201"), "Region": "asia", "KitKey": "WC_Kit_05", "BadgeKey": "WC_Badge_05", "Remark": "中国动态池"},
            {"ID": 202, "NameLcKey": lc.add(lc_key("team", "name", "202"), "东方之鹰", "TeamCfg/202"), "Region": "asia", "KitKey": "WC_Kit_06", "BadgeKey": "WC_Badge_06", "Remark": "中国动态池"},
            {"ID": 203, "NameLcKey": lc.add(lc_key("team", "name", "203"), "北欧狼", "TeamCfg/203"), "Region": "europe", "KitKey": "WC_Kit_07", "BadgeKey": "WC_Badge_07", "Remark": "联赛对手展示"},
            {"ID": 204, "NameLcKey": lc.add(lc_key("team", "name", "204"), "阿根廷神鹰", "TeamCfg/204"), "Region": "south_america", "KitKey": "WC_Kit_08", "BadgeKey": "WC_Badge_08", "Remark": "文档合同示例"},
            {"ID": 205, "NameLcKey": lc.add(lc_key("team", "name", "205"), "桑巴红魔", "TeamCfg/205"), "Region": "south_america", "KitKey": "WC_Kit_09", "BadgeKey": "WC_Badge_09", "Remark": ""},
            {"ID": 206, "NameLcKey": lc.add(lc_key("team", "name", "206"), "南美风暴", "TeamCfg/206"), "Region": "south_america", "KitKey": "WC_Kit_10", "BadgeKey": "WC_Badge_10", "Remark": ""},
            {"ID": 207, "NameLcKey": lc.add(lc_key("team", "name", "207"), "潘帕斯之翼", "TeamCfg/207"), "Region": "south_america", "KitKey": "WC_Kit_11", "BadgeKey": "WC_Badge_11", "Remark": ""},
            {"ID": 208, "NameLcKey": lc.add(lc_key("team", "name", "208"), "高卢雄鸡", "TeamCfg/208"), "Region": "europe", "KitKey": "WC_Kit_12", "BadgeKey": "WC_Badge_12", "Remark": "12队服/队标"},
            *_build_theme_teams(lc),
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerContractStarLicCfg",
        c(
            id_col("int", "license_id(=最高可出星级)"),
            ("AllowedTeamStars", "int[]", "允许出现的合同星级列表"),
            ("StarWeights", "int[]", "与AllowedTeamStars等长、按下标对应权重"),
            ("Remark", "string", "备注"),
        ),
        _contract_star_license_rows(),
    )

    make_sheet(
        wb,
        "ActvSoccerContractCfg",
        c(
            id_col("int", "contract_id"),
            ("TeamID", "int", "关联展示球队→TeamCfg"),
            ("TeamStar", "int", "合同星级(唯一生效星级)"),
            ("PayFinish", "int", "周薪/完赛待遇"),
            ("PayGoal", "int", "进球待遇"),
            ("PayAssist", "int", "助攻待遇"),
            ("PayFame", "int", "名气待遇"),
            ("SeasonGoal", "ext[]", "赛季目标", V_SEASON_GOAL, '[{"type":"rank","threshold":12,"settle_at":"season_end"}]'),
            ("SeasonReward", "ext[]", "目标奖励", P_TYIDVAL, '[{"typ":"vm","id":11151001,"val":84}]'),
            ("SignReward", "ext[]", "签约即时奖励", P_TYIDVAL, '[]'),
            ("GrantFameLevel", "int", "抽样门槛-知名度等级"),
            ("GrantLifeLevel", "int", "抽样门槛-生活等级"),
            ("GrantScene", "string", "first_sign/league_finish"),
            ("Remark", "string", "备注"),
        ),
        [
            *_first_sign_contract_rows(),
            *_league_finish_contract_rows(),
        ],
    )

    # --- 3.5 积分赛 ---
    make_sheet(
        wb,
        "ActvSoccerSeasonCfg",
        c(
            id_col("int", "season_id"),
            ("LeagueNameLcKey", "string", "联赛名称→ActvSoccerLanguageCfg"),
            ("Group", "int", "联赛系列(相同Group条数=总轮次)"),
            ("NextSeason", "int", "后置联赛(0=系列结束)"),
            ("ContractOfferCount", "int", "换约候选份数(0=读全局常量)"),
            ("Remark", "string", "备注"),
        ),
        _build_seasons(lc),
    )

    # --- 3.6 淘汰赛 ---
    make_sheet(
        wb,
        "ActvSoccerKnockoutCfg",
        c(
            id_col("int", "编号"),
            ("OpenLeagueLevel", "int", "开放所需积分赛关卡L"),
            ("TeamSizeMax", "int", "队伍人数上限M"),
            ("QualifierGroupCount", "int", "海选分组数G"),
            ("QualifyPerGroup", "int", "每组晋级K"),
            ("KnockoutGroupCount", "int", "单淘汰分组数(8组)"),
            ("MaxRounds", "int", "单淘汰轮次R"),
            ("BotPlayerRating", "int", "补位球员评分"),
            ("Remark", "string", "备注"),
        ),
        [
            {
                "ID": 1,
                "OpenLeagueLevel": KNOCKOUT_OPEN_LEVEL,
                "TeamSizeMax": 5,
                "QualifierGroupCount": 16,
                "QualifyPerGroup": 4,
                "KnockoutGroupCount": 8,
                "MaxRounds": 6,
                "BotPlayerRating": 10,
                "Remark": "最终文档:64强分8组,海选16组取前4",
            },
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerKnockoutPhaseCfg",
        c(
            id_col("int", "编号"),
            ("PhaseLcKey", "string", "阶段名→ActvSoccerLanguageCfg"),
            ("PhaseKey", "string", "阶段键"),
            ("StartTime", "string", "开始UTC"),
            ("EndTime", "string", "结束UTC"),
            ("DayContentLcKey", "string", "当日内容→ActvSoccerLanguageCfg"),
            ("BetOpen", "bool", "开放竞猜"),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 1, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "team_build"), "组队期", "KnockoutPhaseCfg/1"), "PhaseKey": "team_build", "StartTime": "2026-07-10 00:00:00", "EndTime": "2026-07-11 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "1"), "发起/加入组队、命名队名队标、审批", "KnockoutPhaseCfg/1"), "BetOpen": 0},
            {"ID": 2, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "team_build"), "组队期", "KnockoutPhaseCfg/2"), "PhaseKey": "team_build", "StartTime": "2026-07-11 00:00:00", "EndTime": "2026-07-11 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "2"), "组队结束补位", "KnockoutPhaseCfg/2"), "BetOpen": 0},
            {"ID": 3, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "3"), "海选", "KnockoutPhaseCfg/3"), "PhaseKey": "qualifier", "StartTime": "2026-07-12 00:00:00", "EndTime": "2026-07-12 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "3"), "1天内筛出64强", "KnockoutPhaseCfg/3"), "BetOpen": 0, "Remark": "不开竞猜"},
            {"ID": 4, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "4"), "正赛第1轮", "KnockoutPhaseCfg/4"), "PhaseKey": "knockout_r1", "StartTime": "2026-07-13 00:00:00", "EndTime": "2026-07-13 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "4"), "8组各一轮(64强)", "KnockoutPhaseCfg/4"), "BetOpen": 1},
            {"ID": 5, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "5"), "正赛第2轮", "KnockoutPhaseCfg/5"), "PhaseKey": "knockout_r2", "StartTime": "2026-07-14 00:00:00", "EndTime": "2026-07-14 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "5"), "8组各一轮(32强)", "KnockoutPhaseCfg/5"), "BetOpen": 1},
            {"ID": 6, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "6"), "正赛第3轮", "KnockoutPhaseCfg/6"), "PhaseKey": "knockout_r3", "StartTime": "2026-07-15 00:00:00", "EndTime": "2026-07-15 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "6"), "8组各一轮(16强)", "KnockoutPhaseCfg/6"), "BetOpen": 1},
            {"ID": 7, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "7"), "正赛第4轮", "KnockoutPhaseCfg/7"), "PhaseKey": "knockout_r4", "StartTime": "2026-07-16 00:00:00", "EndTime": "2026-07-16 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "7"), "8组决出组冠军→8强", "KnockoutPhaseCfg/7"), "BetOpen": 1},
            {"ID": 8, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "8"), "正赛第5轮", "KnockoutPhaseCfg/8"), "PhaseKey": "knockout_r5", "StartTime": "2026-07-17 00:00:00", "EndTime": "2026-07-17 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "8"), "8强淘汰赛(4强)", "KnockoutPhaseCfg/8"), "BetOpen": 1},
            {"ID": 9, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "9"), "决赛", "KnockoutPhaseCfg/9"), "PhaseKey": "knockout_final", "StartTime": "2026-07-18 00:00:00", "EndTime": "2026-07-18 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "9"), "冠亚军决赛", "KnockoutPhaseCfg/9"), "BetOpen": 1},
            {"ID": 10, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "10"), "展示期", "KnockoutPhaseCfg/10"), "PhaseKey": "showcase", "StartTime": "2026-07-19 00:00:00", "EndTime": "2026-07-19 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "10"), "冠军展示+兑换商店可用", "KnockoutPhaseCfg/10"), "BetOpen": 0},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerMatchSimulationCfg",
        c(
            id_col("int", "编号"),
            ("RuleKey", "string", "规则键"),
            ("Formula", "string", "公式/说明"),
            ("Params", "ext", "模拟参数", V_SIM_PARAMS, '{"base":3,"per_rating":0.1}'),
            ("Remark", "string", "TODO系数"),
        ),
        [
            {"ID": 1, "RuleKey": "single_rating", "Formula": "f(fame_lv,training_lv,life_lv)", "Params": '{"fame_w":1.0,"life_w":1.0,"training_w":1.0}', "Remark": "单主角评分"},
            {"ID": 2, "RuleKey": "team_total", "Formula": "sum(member_rating)", "Params": "{}", "Remark": "队伍总评"},
            {"ID": 3, "RuleKey": "slice_count", "Formula": "f(max_rating)", "Params": '{"base":3,"per_rating":0.1}', "Remark": "双方切片数可不同"},
            {"ID": 4, "RuleKey": "slice_success_p", "Formula": "own_total/(own_total+opp_total)", "Params": "{}", "Remark": "单切片成功期望"},
            {"ID": 5, "RuleKey": "tie_breaker", "Formula": "total_rating>max_rating>signup_time", "Params": "{}", "Remark": "平局破法"},
        ],
    )

    # --- 3.7 竞猜 ---
    make_sheet(
        wb,
        "ActvSoccerBetCoinSourceCfg",
        c(
            id_col("int", "编号"),
            ("DailyFree", "int", "每日免费竞猜币"),
            ("GiftGrant", "int", "礼包投放"),
            ("LoseRecycleRate", "int", "失败回收万分比"),
            ("StakeOptions", "int[]", "快捷投注档位"),
            ("Remark", "string", "备注"),
        ),
        [{"ID": 1, "DailyFree": 100, "GiftGrant": 0, "LoseRecycleRate": 8000, "StakeOptions": "[100,200,500,1000,5000]", "Remark": "失败回收80%"}],
    )

    make_sheet(
        wb,
        "ActvSoccerBetMatchCfg",
        c(
            id_col("int", "bet_match_id"),
            ("KnockoutMatchID", "int", "淘汰赛对阵ID"),
            ("OddsA", "float", "赔率A"),
            ("OddsB", "float", "赔率B"),
            ("OpenTime", "string", "开放"),
            ("CloseTime", "string", "截止"),
            ("Status", "string", "open/closed/settled"),
            ("Remark", "string", "测试模板"),
        ),
        [
            {"ID": 1, "KnockoutMatchID": 1001, "OddsA": 1.33, "OddsB": 1.45, "OpenTime": "2026-07-17 00:00:00", "CloseTime": "2026-07-17 20:00:00", "Status": "open", "Remark": "4强下注示例"},
        ],
    )

    # --- 3.9 BP ---
    make_sheet(
        wb,
        "ActvSoccerBattlePassCfg",
        c(
            id_col("int", "编号"),
            ("Level", "int", "BP等级"),
            ("ExpRequired", "int", "所需活跃度"),
            ("FreeReward", "ext[]", "免费轨", P_TYIDVAL, '[{"typ":"vm","id":11151001,"val":20}]'),
            ("PaidReward", "ext[]", "付费轨", P_TYIDVAL, '[{"typ":"vm","id":11151001,"val":50}]'),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 1, "Level": 1, "ExpRequired": 100, "FreeReward": '[{"typ":"vm","id":11151001,"val":20}]', "PaidReward": '[{"typ":"vm","id":11151001,"val":50}]'},
            {"ID": 2, "Level": 2, "ExpRequired": 200, "FreeReward": '[{"typ":"vm","id":11151001,"val":30}]', "PaidReward": '[{"typ":"vm","id":11151001,"val":80}]'},
            {"ID": 3, "Level": 3, "ExpRequired": 300, "FreeReward": '[{"typ":"item","id":5012109,"val":1}]', "PaidReward": '[{"typ":"item","id":5012109,"val":2}]', "Remark": "外观/道具占位"},
        ],
    )

    # --- 3.10 兑换商店 ---
    make_sheet(
        wb,
        "ActvSoccerExchangeShopCfg",
        c(
            id_col("int", "商品ID"),
            ("CostVal", "int", "竞猜币消耗"),
            ("Reward", "ext[]", "兑换奖励", P_TYIDVAL, '[{"typ":"item","id":5012109,"val":1}]'),
            ("BuyLimit", "int", "限购"),
            ("RefreshCycle", "string", "刷新周期"),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 1, "CostVal": 500, "Reward": '[{"typ":"item","id":5012109,"val":1}]', "BuyLimit": 1, "RefreshCycle": "7d", "Remark": "世界杯表情"},
            {"ID": 2, "CostVal": 1000, "Reward": '[{"typ":"item","id":5012109,"val":1}]', "BuyLimit": 1, "RefreshCycle": "7d", "Remark": "回溯道具包"},
        ],
    )

    # --- 3.11 礼包 ---
    make_sheet(
        wb,
        "ActvSoccerGiftCfg",
        c(
            id_col("int", "礼包ID"),
            ("GiftType", "int", "0免费1付费"),
            ("Price", "int", "价格档位"),
            ("Reward", "ext[]", "奖励", P_TYIDVAL, '[{"typ":"vm","id":11151001,"val":100}]'),
            ("BuyLimit", "int", "限购"),
            ("Duration", "string", "限时"),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 1, "GiftType": 0, "Price": 0, "Reward": '[{"typ":"vm","id":11151001,"val":100}]', "BuyLimit": 1, "Duration": "1d", "Remark": "免费每日"},
            {"ID": 2, "GiftType": 1, "Price": 1, "Reward": '[{"typ":"vm","id":11151001,"val":300},{"typ":"item","id":5012109,"val":1}]', "BuyLimit": 3, "Duration": "7d", "Remark": "付费礼包"},
        ],
    )

    # --- 3.8 排名档位 ---
    make_sheet(
        wb,
        "ActvSoccerRankSectionCfg",
        c(
            id_col("int", "编号"),
            ("RankType", "string", "slice_win/goal/bet_hit/bet_profit"),
            ("RankMin", "int", "名次下限"),
            ("RankMax", "int", "名次上限"),
            ("Reward", "ext[]", "奖励", P_TYIDVAL, '[{"typ":"item","id":5012109,"val":1}]'),
            ("Remark", "string", "备注"),
        ),
        [
            {"ID": 1, "RankType": "slice_win", "RankMin": 1, "RankMax": 1, "Reward": '[{"typ":"item","id":5012109,"val":1}]', "Remark": "积分榜冠军"},
            {"ID": 2, "RankType": "slice_win", "RankMin": 2, "RankMax": 10, "Reward": '[{"typ":"vm","id":11151001,"val":200}]', "Remark": "积分榜前10"},
            {"ID": 3, "RankType": "goal", "RankMin": 1, "RankMax": 3, "Reward": '[{"typ":"vm","id":11151001,"val":100}]', "Remark": "进球榜前三"},
            {"ID": 4, "RankType": "bet_hit", "RankMin": 1, "RankMax": 10, "Reward": '[{"typ":"vm","id":11151001,"val":50}]', "Remark": "竞猜命中榜"},
            {"ID": 5, "RankType": "bet_profit", "RankMin": 1, "RankMax": 10, "Reward": '[{"typ":"vm","id":11151001,"val":50}]', "Remark": "竞猜收益榜"},
        ],
    )

    make_const_format_sheet(wb, "ActvSoccerGlobalConstCfg", const_rows)

    return wb


def export_summary(sheets: list[str], lc_rows: list[dict], const_rows: list[dict]) -> None:
    summary = {
        "file": "ActivitySoccer.xlsx",
        "language_file": "ActivitySoccerLanguage.xlsx",
        "const_file": "ConstConfig_ActvSoccer.xlsx",
        "const_sheet_in_activity": "ActvSoccerGlobalConstCfg",
        "const_sheet_in_patch": "ConstConfigCfg",
        "const_entry_count": len(const_rows),
        "const_cfgid_range": f"{ACTV_SOCCER_CONST_CFGID_BASE}-{ACTV_SOCCER_CONST_CFGID_BASE + len(const_rows) - 1}",
        "const_merge_target": "dataconfig/ConstConfig.xlsx / ConstConfigCfg（可选合并；亦可仅保留 ActvSoccerGlobalConstCfg）",
        "sources": SOURCE_DOCS,
        "sheets": sheets,
        "language_sheet": "ActvSoccerLanguageCfg",
        "language_entry_count": len(lc_rows),
        "sheet_groups": {
            "玩法基础": [
                "ActvSoccerCharacterCfg", "ActvSoccerNationalityCfg", "ActvSoccerTutorialCfg",
                "ActvSoccerSliceTypeDefCfg", "ActvSoccerSlicePresetCfg", "ActvSoccerSliceInstanceCfg",
                "ActvSoccerLevelCfg", "ActvSoccerSeasonCfg",
            ],
            "FSM_BT_AI": [
                "ActvSoccerPlayerAiDutyEnumCfg",
                "ActvSoccerAiProfileCfg", "ActvSoccerEnemyAiCfg", "ActvSoccerSliceAiCfg",
                "ActvSoccerAiModifierCfg", "ActvSoccerSliceFlowCfg", "ActvSoccerCharacterStateCfg",
            ],
            "养成与配套": [
                "ActvSoccerFameGrowthLevelCfg", "ActvSoccerLifeGrowthLevelCfg",
                "ActvSoccerContractStarLicCfg",
                "ActvSoccerContractCfg", "ActvSoccerKnockoutCfg",
                "ActvSoccerBattlePassCfg", "ActvSoccerGiftCfg", "ActvSoccerRankSectionCfg",
                "ActvSoccerGlobalConstCfg",
            ],
        },
        "id_cross_ref": {
            "AiProfile": "1001-1010=tier1-10难度档(easy/normal/hard),单调递增,DeadCorner固定0",
            "PlayerAiDuty": "1=Goalkeeper守门员,2=Defender后卫(对方非门将),3=Forward前锋(我方含玩家)",
            "EnemyAi": "2001-2003=band1(tier1-3);20X1/20X2/20X3=bandX门将/后卫/射手(X=2,3,4)",
            "SliceAi": "3001-3006=试训/引导切片101-203;3100+=库实例(每库实例一行)",
            "Modifier": "4001/4002/4005=移动门将(普通/困难/极限),4003=无辅助线,4004=固定人墙,4006=收窄夹角,4007=随机扑救",
            "SliceInstance": "库实例id=tier*100+type*10+variant(type1-6,variant1-2);101-203=试训/引导",
            "Level": "1-500=50轮×10关;Group=轮次;第1关=引导关;淘汰赛round15起(level141)开放",
            "Season": "1-50轮单group=1;NextSeason链推进;总轮次=count(同group)",
        },
        "test_flow": [
            "创角→试训切片101/102/103 (SliceAi 3001-3003, easy档)",
            "引导关201/202/203 (3004-3006: 进攻+助攻+守门射手)",
            "正式关301移动门将 (3007+Modifier4001) / 302点球 (3008)",
            "困难关复用301 (3009+Profile1003+Modifier4002)",
            "切片FSM: SliceFlowCfg按类型读流程; 角色表现: CharacterStateCfg映射动画",
        ],
        "notes": [
            "球员AI职责仅三档:守门员/后卫(对方非门将)/前锋(我方含玩家);见ActvSoccerPlayerAiDutyEnumCfg",
            "CharacterState场景行可用Duty=0(非枚举);其余EnemyAi/CharacterState用Duty(int)",
            "PlayersInit每项含duty:我方Forward(3)对方门将Goalkeeper(1)对方其余Defender(2)",
            "AI难度只控成功率; 死角球见ConstConfig ActvSoccer_dead_corner_can_save",
            "单切片AI在ActvSoccerSliceAiCfg配置,移动门将归属切片级Modifier",
            "回溯后RewindRandom=1,种子含rewind_count",
            "参数叠加: preset→instance→ai_profile→modifier",
            "JSON字段使用ext/ext[]类型,第5行标注proto(如TypIDVal_P_cspb/SoccerObjective_V)",
            "ext/ext[]数据行不得留空: ext默认{}, ext[]默认[]; 有列示例时优先用第7行示例作默认值",
            "仅含单个参数时用int/float/string等基础类型,不用ext",
            "第1行读取端: 能确定仅前端c/仅后端s,拿不准或双端用cs; 见SHEET_DEFAULT_READ/READ_OVERRIDES",
            "展示文案字段用*LcKey(string)引用语言表ID,格式ActvSoccer_{category}_{semantic}_{seq}",
            "玩法数值常量: ActvSoccerGlobalConstCfg 与 ConstConfig_ActvSoccer.xlsx 字段相同(对齐 ConstConfig); 自行选择保留在活动表或合并进 dataconfig/ConstConfig.xlsx",
        ],
        "const_keys": [row["Constant"] for row in const_rows],
        "lc_id_format": "ActvSoccer_{category}_{semantic}_{seq}",
        "lc_fields": [
            "NameLcKey", "TitleLcKey", "LeagueNameLcKey", "PhaseLcKey", "DayContentLcKey", "DescLcKey",
        ],
        "ext_proto_map": {
            "TypIDVal_P_cspb": ["SeasonReward", "SignReward", "FreeReward", "PaidReward", "Reward"],
            "PositionTuple_P": ["BallPos", "BallVector", "TargetPoint"],
            "SoccerTypePayload_V": ["TypePayload"],
            "SoccerObjective_V": ["ExtraObjectives"],
            "SoccerModifier_V": ["Modifiers"],
            "SoccerPlayerInit_V": ["PlayersInit(team,idx,duty,pos)"],
            "SoccerSeasonGoal_V": ["SeasonGoal"],
            "SoccerSimParams_V": ["Params"],
        },
        "flattened_fields": {
            "DefaultCameraFov": "原DefaultCamera.fov",
            "CameraFov": "原Camera.fov",
            "OverrideOperableAngle": "原Overrides.operable_angle",
            "ObjectiveType": "原Objectives单目标type",
            "ActvSoccerFameGrowthLevelCfg/ActvSoccerLifeGrowthLevelCfg": "原ActvSoccerGrowthLevelCfg按养成线拆分",
            "RewardFame/ContractStarLicReward/TicketCap等": "原LevelUpReward/LevelUpEffect拆列",
            "effective_license_id": "max(知名度许可,生活许可) OR取较高",
            "ContractPool": "首签关联contract_id(原TeamPool)",
            "TeamCfg无Star": "星级仅在ContractCfg.TeamStar",
            "ActvSoccerContractStarLicCfg": "联赛换约星级权重(2-5星许可);同星级内均匀抽合同",
            "ActvSoccerContractCfg": "读取端cs(合同内容客户端展示)",
            "GrantScene": "首签走ContractPool;联赛换约走许可表+合同池",
            "pending_contract_choices": "服务端生成待选合同列表(玩家存档)",
            "GrantFameLevel/GrantLifeLevel": "原GrantLevelReq",
            "LevelCfg.Group": "所属联赛轮次=SeasonCfg.ID",
            "SeasonCfg.Group": "联赛系列;总轮次=count(同Group);小关卡由LevelCfg.Group关联",
            "SeasonCfg.NextSeason": "后置联赛(原UnlockPrevSeason反向)",
        },
    }
    (OUT_DIR / "test-config-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    lc = LcRegistry()
    const_rows = actv_soccer_const_rows()
    wb = build_workbook(lc, const_rows)
    lc_wb = build_language_workbook(lc)
    const_wb = build_const_config_workbook(const_rows)

    target = OUTPUT_FILE
    try:
        wb.save(target)
    except PermissionError:
        target = OUT_DIR / "ActivitySoccer.generated.xlsx"
        wb.save(target)
        print(f"WARN: {OUTPUT_FILE} 被占用，已写入 {target}")

    lc_target = OUTPUT_LC_FILE
    try:
        lc_wb.save(lc_target)
    except PermissionError:
        lc_target = OUT_DIR / "ActivitySoccerLanguage.generated.xlsx"
        lc_wb.save(lc_target)
        print(f"WARN: {OUTPUT_LC_FILE} 被占用，已写入 {lc_target}")

    const_target = OUTPUT_CONST_FILE
    try:
        const_wb.save(const_target)
    except PermissionError:
        const_target = OUT_DIR / "ConstConfig_ActvSoccer.generated.xlsx"
        const_wb.save(const_target)
        print(f"WARN: {OUTPUT_CONST_FILE} 被占用，已写入 {const_target}")

    export_summary(wb.sheetnames, lc.rows, const_rows)
    print(f"Wrote {target}")
    print(f"Wrote {lc_target} ({len(lc.rows)} language entries)")
    print(f"Wrote {const_target} ({len(const_rows)} const entries → merge into ConstConfig.xlsx)")
    print(f"Sheets ({len(wb.sheetnames)}): {', '.join(wb.sheetnames)}")


if __name__ == "__main__":
    main()
