# -*- coding: utf-8 -*-
"""Generate ActivitySoccer.xlsx test config from 2026 World Cup DingTalk doc."""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

OUT_DIR = Path(__file__).parent
OUTPUT_FILE = OUT_DIR / "ActivitySoccer.xlsx"
OUTPUT_LC_FILE = OUT_DIR / "ActivitySoccerLanguage.xlsx"
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
    "ActvSoccerContractCfg": "s",
    "ActvSoccerFameGainRuleCfg": "s",
    "ActvSoccerKnockoutCfg": "s",
    "ActvSoccerKnockoutPhaseCfg": "s",
    "ActvSoccerMatchSimulationCfg": "s",
    "ActvSoccerBetCoinSourceCfg": "s",
    "ActvSoccerRankSectionCfg": "s",
}
READ_OVERRIDES: dict[str, dict[str, str]] = {
    "ActvSoccerCharacterCfg": {"AppearanceKey": "c", "DisplayPower": "c"},
    "ActvSoccerNationalityCfg": {"NameLcKey": "c", "TeamPool": "s"},
    "ActvSoccerTutorialCfg": {"SliceInstanceID": "cs", "DescLcKey": "c"},
    "ActvSoccerSliceTypeDefCfg": {
        "AllowedModes": "c", "PayloadSchema": "c", "DefaultCameraFov": "c",
    },
    "ActvSoccerSlicePresetCfg": {
        "NameLcKey": "c", "Tags": "c", "BallPos": "c", "BallVector": "c", "BallOwner": "c",
        "PlayersInit": "c", "CameraFov": "c", "TargetPoint": "c", "RecommendedModes": "c",
    },
    "ActvSoccerSliceInstanceCfg": {"OverrideOperableAngle": "c"},
    "ActvSoccerEnemyAiCfg": {"AnimationKey": "c"},
    "ActvSoccerTeamCfg": {"NameLcKey": "c", "KitKey": "c", "BadgeKey": "c"},
    "ActvSoccerGrowthLevelCfg": {"TitleLcKey": "c"},
    "ActvSoccerSeasonCfg": {"LeagueNameLcKey": "c"},
    "ActvSoccerContractCfg": {
        "CfgID": "cs", "TeamID": "cs", "TeamStar": "cs",
    },
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


def c(*specs: tuple) -> list[dict]:
    """Column spec: (field, type, desc) or (field, type, desc, proto_row5) or + json_example row7."""
    cols: list[dict] = []
    for spec in specs:
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
    """收集测试配置引用的本地化条目，CfgID 为英文字符串且全局唯一。"""

    def __init__(self) -> None:
        self._rows: list[dict] = []
        self._keys: dict[str, str] = {}

    def add(self, lc_id: str, cn: str, source: str = "") -> str:
        if lc_id in self._keys:
            return self._keys[lc_id]
        self._keys[lc_id] = lc_id
        self._rows.append({"CfgID": lc_id, "Cn": cn, "Source": source})
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
            ("CfgID", "string", "本地化唯一ID(英文+数字)"),
            ("Cn", "string", "简体中文"),
            ("Source", "string", "引用来源(测试追溯)"),
        ),
        registry.rows,
    )
    return wb


def build_workbook(lc: LcRegistry) -> Workbook:
    wb = Workbook()
    wb.remove(wb.active)

    # --- 3.1 创角 ---
    make_sheet(
        wb,
        "ActvSoccerCharacterCfg",
        c(
            ("CfgID", "int", "角色ID character_id"),
            ("AppearanceKey", "string", "外观资源键"),
            ("DisplayPower", "int", "展示战力(仅表现)"),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 1, "AppearanceKey": "WC_Char_01", "DisplayPower": 10, "Remark": "角色A"},
            {"CfgID": 2, "AppearanceKey": "WC_Char_02", "DisplayPower": 10, "Remark": "角色B"},
            {"CfgID": 3, "AppearanceKey": "WC_Char_03", "DisplayPower": 10, "Remark": "角色C"},
            {"CfgID": 4, "AppearanceKey": "WC_Char_04", "DisplayPower": 10, "Remark": "角色D"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerNationalityCfg",
        c(
            ("CfgID", "int", "国籍ID"),
            ("NameLcKey", "string", "国籍名称→ActvSoccerLanguageCfg"),
            ("Region", "string", "所属地区"),
            ("TeamPool", "int[]", "首签球队池"),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 1, "NameLcKey": lc.add(lc_key("nationality", "name", "1"), "中国", "NationalityCfg/1"), "Region": "asia", "TeamPool": "[101,201,202]", "Remark": ""},
            {"CfgID": 2, "NameLcKey": lc.add(lc_key("nationality", "name", "2"), "德国", "NationalityCfg/2"), "Region": "europe", "TeamPool": "[102,203,204]", "Remark": ""},
            {"CfgID": 3, "NameLcKey": lc.add(lc_key("nationality", "name", "3"), "巴西", "NationalityCfg/3"), "Region": "south_america", "TeamPool": "[103,205,206]", "Remark": ""},
            {"CfgID": 4, "NameLcKey": lc.add(lc_key("nationality", "name", "4"), "阿根廷", "NationalityCfg/4"), "Region": "south_america", "TeamPool": "[104,205,207]", "Remark": ""},
            {"CfgID": 5, "NameLcKey": lc.add(lc_key("nationality", "name", "5"), "法国", "NationalityCfg/5"), "Region": "europe", "TeamPool": "[105,203,208]", "Remark": ""},
            {"CfgID": 6, "NameLcKey": lc.add(lc_key("nationality", "name", "6"), "西班牙", "NationalityCfg/6"), "Region": "europe", "TeamPool": "[106,203,209]", "Remark": ""},
            {"CfgID": 7, "NameLcKey": lc.add(lc_key("nationality", "name", "7"), "葡萄牙", "NationalityCfg/7"), "Region": "europe", "TeamPool": "[107,203,210]", "Remark": ""},
            {"CfgID": 8, "NameLcKey": lc.add(lc_key("nationality", "name", "8"), "比利时", "NationalityCfg/8"), "Region": "europe", "TeamPool": "[108,203,211]", "Remark": ""},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerTutorialCfg",
        c(
            ("StepIndex", "int", "试训步骤序号"),
            ("SliceType", "string", "切片类型"),
            ("SliceInstanceID", "int", "关联切片实例(测试用)"),
            ("ForcedOrder", "bool", "强制顺序"),
            ("DescLcKey", "string", "步骤描述→ActvSoccerLanguageCfg"),
            ("Remark", "string", "备注"),
        ),
        [
            {"StepIndex": 1, "SliceType": "attack", "SliceInstanceID": 101, "ForcedOrder": 1, "DescLcKey": lc.add(lc_key("tutorial", "desc", "1"), "进攻教学", "TutorialCfg/1")},
            {"StepIndex": 2, "SliceType": "free_kick", "SliceInstanceID": 102, "ForcedOrder": 1, "DescLcKey": lc.add(lc_key("tutorial", "desc", "2"), "任意球教学", "TutorialCfg/2")},
            {"StepIndex": 3, "SliceType": "penalty", "SliceInstanceID": 103, "ForcedOrder": 1, "DescLcKey": lc.add(lc_key("tutorial", "desc", "3"), "点球教学", "TutorialCfg/3")},
        ],
    )

    # --- 3.2 切片 ---
    make_sheet(
        wb,
        "ActvSoccerSliceTypeDefCfg",
        c(
            ("SliceType", "string", "切片类型"),
            ("AllowedModes", "string[]", "允许操作模式"),
            ("JudgeFn", "string", "判定函数"),
            ("PayloadSchema", "string", "type_payload schema"),
            ("DefaultCameraFov", "float", "默认相机FOV(0=用预设)"),
            ("Remark", "string", "L1只读"),
        ),
        [
            {"SliceType": "attack", "AllowedModes": '["draw_line","slingshot"]', "JudgeFn": "judge_attack", "PayloadSchema": "dest,keeper_weight,angle", "DefaultCameraFov": 0, "Remark": ""},
            {"SliceType": "free_kick", "AllowedModes": '["draw_line","slingshot"]', "JudgeFn": "judge_free_kick", "PayloadSchema": "spot,wall,angle,keeper_weight", "DefaultCameraFov": 0, "Remark": ""},
            {"SliceType": "penalty", "AllowedModes": '["draw_line","slingshot"]', "JudgeFn": "judge_penalty", "PayloadSchema": "spot,keeper_dirs,reaction_ms", "DefaultCameraFov": 0, "Remark": ""},
            {"SliceType": "corner", "AllowedModes": '["draw_line","slingshot"]', "JudgeFn": "judge_corner", "PayloadSchema": "corner_spot,runs,first_touch", "DefaultCameraFov": 0, "Remark": ""},
            {"SliceType": "throw_in", "AllowedModes": '["draw_line","slingshot"]', "JudgeFn": "judge_throw_in", "PayloadSchema": "throw_spot,runs,second_attack", "DefaultCameraFov": 0, "Remark": ""},
            {"SliceType": "goalkeep", "AllowedModes": '["draw_line"]', "JudgeFn": "judge_goalkeep", "PayloadSchema": "shot_dirs,reaction_ms", "DefaultCameraFov": 0, "Remark": "仅划线"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerSlicePresetCfg",
        c(
            ("CfgID", "int", "preset_id"),
            ("SliceType", "string", "切片类型"),
            ("NameLcKey", "string", "预设名→ActvSoccerLanguageCfg"),
            ("Tags", "string[]", "标签"),
            ("BallPos", "ext", "球位置", P_VEC3, '{"x":0,"y":0,"z":0}'),
            ("BallVector", "ext", "球方向", P_VEC3, '{"x":0,"y":0,"z":1}'),
            ("BallOwner", "int", "控球球员索引"),
            ("PlayersInit", "ext[]", f"球员站位+duty({PLAYER_AI_DUTY_ENUM_COMMENT})", V_PLAYER_INIT, PLAYER_INIT_DEFAULT),
            ("CameraFov", "float", "相机FOV"),
            ("TargetPoint", "ext", "目标点", P_VEC3, '{"x":0,"y":0,"z":58}'),
            ("OperableAngle", "float", "可操作夹角"),
            ("TypePayload", "ext", "type_payload默认", V_TYPE_PAYLOAD, '{"keeper_weight":5000,"angle":35}'),
            ("RecommendedModes", "string[]", "建议模式"),
            ("Remark", "string", "备注"),
        ),
        [
            {
                "CfgID": 1, "SliceType": "attack", "NameLcKey": lc.add(lc_key("preset", "name", "1"), "右路单刀", "SlicePresetCfg/1"), "Tags": '["side","easy"]',
                "BallPos": '{"x":12,"y":0,"z":35}', "BallVector": '{"x":0,"y":0,"z":1}', "BallOwner": 0,
                "PlayersInit": players_init_json([
                    player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], 12, 0, 35),
                    player_init("home", 1, PLAYER_AI_DUTY_ENUM["Forward"], 10, 0, 30),
                    player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 12, 0, 55),
                    player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], 8, 0, 48),
                ]),
                "CameraFov": 45, "TargetPoint": '{"x":12,"y":0,"z":58}', "OperableAngle": 35.0,
                "TypePayload": '{"keeper_weight":5000,"angle":35}', "RecommendedModes": '["draw_line","slingshot"]',
            },
            {
                "CfgID": 2, "SliceType": "free_kick", "NameLcKey": lc.add(lc_key("preset", "name", "2"), "中路任意球", "SlicePresetCfg/2"), "Tags": '["center"]',
                "BallPos": '{"x":0,"y":0,"z":42}', "BallVector": '{"x":0,"y":0,"z":1}', "BallOwner": 0,
                "PlayersInit": players_init_json([
                    player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], 0, 0, 42),
                    player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 58),
                    player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], -2, 0, 50),
                    player_init("away", 2, PLAYER_AI_DUTY_ENUM["Defender"], 2, 0, 50),
                    player_init("away", 3, PLAYER_AI_DUTY_ENUM["Defender"], -1, 0, 50),
                    player_init("away", 4, PLAYER_AI_DUTY_ENUM["Defender"], 1, 0, 50),
                ]),
                "CameraFov": 42, "TargetPoint": '{"x":0,"y":1.8,"z":58}', "OperableAngle": 28.0,
                "TypePayload": '{"wall_count":4,"keeper_weight":4500}', "RecommendedModes": '["draw_line","slingshot"]',
            },
            {
                "CfgID": 3, "SliceType": "penalty", "NameLcKey": lc.add(lc_key("preset", "name", "3"), "标准点球", "SlicePresetCfg/3"), "Tags": '["penalty"]',
                "BallPos": '{"x":0,"y":0,"z":50}', "BallVector": '{"x":0,"y":0,"z":1}', "BallOwner": 0,
                "PlayersInit": players_init_json([
                    player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], 0, 0, 50),
                    player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 58),
                ]),
                "CameraFov": 40, "TargetPoint": '{"x":0,"y":0.5,"z":58}', "OperableAngle": 0.0,
                "TypePayload": '{"keeper_dirs":[2500,2500,2500,2500]}', "RecommendedModes": '["draw_line","slingshot"]',
            },
            {
                "CfgID": 4, "SliceType": "goalkeep", "NameLcKey": lc.add(lc_key("preset", "name", "4"), "基础守门", "SlicePresetCfg/4"), "Tags": '["gk"]',
                "BallPos": '{"x":0,"y":0,"z":56}', "BallVector": '{"x":0,"y":0,"z":-1}', "BallOwner": None,
                "PlayersInit": players_init_json([
                    player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], 0, 0, 58),
                    player_init("away", 0, PLAYER_AI_DUTY_ENUM["Defender"], 0, 0, 56),
                ]),
                "CameraFov": 50, "TargetPoint": None, "OperableAngle": 0.0,
                "TypePayload": '{"shot_dirs":[3000,3000,4000],"reaction_ms":2500}', "RecommendedModes": '["draw_line"]',
            },
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerSliceInstanceCfg",
        c(
            ("CfgID", "int", "slice_instance_id"),
            ("SliceType", "string", "切片类型"),
            ("PresetID", "int", "preset_id"),
            ("OverrideOperableAngle", "float", "覆盖可操作夹角(0=不覆盖)"),
            ("ObjectiveType", "string", "单一胜利目标(score/survive等)"),
            ("ExtraObjectives", "ext[]", "复合胜利目标", V_OBJECTIVE, '[{"type":"pass_to","params":{"target":1}},{"type":"score"}]'),
            ("Modifiers", "ext[]", "切片机制", V_MODIFIER, '[{"id":"moving_keeper","params":{"speed":1.0}}]'),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 101, "SliceType": "attack", "PresetID": 1, "ObjectiveType": "score", "Remark": "试训-进攻"},
            {"CfgID": 102, "SliceType": "free_kick", "PresetID": 2, "ObjectiveType": "score", "Remark": "试训-任意球"},
            {"CfgID": 103, "SliceType": "penalty", "PresetID": 3, "ObjectiveType": "score", "Remark": "试训-点球"},
            {"CfgID": 201, "SliceType": "attack", "PresetID": 1, "OverrideOperableAngle": 30, "ObjectiveType": "score", "Remark": "引导关1"},
            {"CfgID": 202, "SliceType": "attack", "PresetID": 1, "OverrideOperableAngle": 28, "ExtraObjectives": '[{"type":"pass_to","params":{"target":1}},{"type":"score"}]', "Remark": "引导关2-助攻"},
            {"CfgID": 203, "SliceType": "goalkeep", "PresetID": 4, "ObjectiveType": "survive", "Remark": "引导关3-守门"},
            {"CfgID": 301, "SliceType": "attack", "PresetID": 1, "ObjectiveType": "score", "Remark": "正式关切片1;移动门将见SliceAiCfg3007"},
            {"CfgID": 302, "SliceType": "penalty", "PresetID": 3, "ObjectiveType": "score", "Remark": "正式关切片2"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerInMatchItemCfg",
        c(
            ("CfgID", "int", "item_id"),
            ("ItemKey", "string", "道具键"),
            ("Effect", "string", "效果"),
            ("DefaultActive", "bool", "默认生效"),
            ("FreeCount", "int", "免费次数"),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 1, "ItemKey": "whistle", "Effect": "add_non_gk_slice", "DefaultActive": 1, "FreeCount": 0, "Remark": "哨子"},
            {"CfgID": 2, "ItemKey": "rewind", "Effect": "reset_slice", "DefaultActive": 0, "FreeCount": 1, "Remark": "回溯"},
            {"CfgID": 3, "ItemKey": "aim", "Effect": "aim_line", "DefaultActive": 1, "FreeCount": 0, "Remark": "瞄准"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerHapticCfg",
        c(
            ("CfgID", "int", "编号"),
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
            {"CfgID": 1, "EventID": "charge_locked", "Category": "core_operation", "Intensity": "light", "Pattern": "tick", "DurationMs": 30, "MinIntervalMs": 200, "EnabledDefault": 1},
            {"CfgID": 2, "EventID": "ball_released", "Category": "core_operation", "Intensity": "medium", "Pattern": "tick", "DurationMs": 40, "MinIntervalMs": 200, "EnabledDefault": 1},
            {"CfgID": 3, "EventID": "slice_success", "Category": "key_result", "Intensity": "heavy", "Pattern": "double", "DurationMs": 80, "MinIntervalMs": 300, "EnabledDefault": 1, "Remark": "进球"},
            {"CfgID": 4, "EventID": "saved", "Category": "key_result", "Intensity": "medium", "Pattern": "tick", "DurationMs": 50, "MinIntervalMs": 300, "EnabledDefault": 1},
            {"CfgID": 5, "EventID": "out_of_bounds", "Category": "key_result", "Intensity": "medium", "Pattern": "tick", "DurationMs": 50, "MinIntervalMs": 300, "EnabledDefault": 1},
            {"CfgID": 6, "EventID": "gk_timeout", "Category": "key_result", "Intensity": "heavy", "Pattern": "tick", "DurationMs": 60, "MinIntervalMs": 300, "EnabledDefault": 1},
            {"CfgID": 7, "EventID": "gk_wrong_judge", "Category": "key_result", "Intensity": "medium", "Pattern": "double", "DurationMs": 70, "MinIntervalMs": 300, "EnabledDefault": 1},
            {"CfgID": 8, "EventID": "gk_save", "Category": "key_result", "Intensity": "heavy", "Pattern": "double", "DurationMs": 80, "MinIntervalMs": 300, "EnabledDefault": 1},
            {"CfgID": 9, "EventID": "hit_post", "Category": "key_result", "Intensity": "medium", "Pattern": "double", "DurationMs": 60, "MinIntervalMs": 300, "EnabledDefault": 1},
            {"CfgID": 10, "EventID": "rewind_reset", "Category": "key_result", "Intensity": "light", "Pattern": "continuous", "DurationMs": 120, "MinIntervalMs": 500, "EnabledDefault": 1},
        ],
    )

    # --- 3.3 关卡 ---
    make_sheet(
        wb,
        "ActvSoccerLevelCfg",
        c(
            ("CfgID", "int", "level_id"),
            ("IsTutorial", "bool", "引导关"),
            ("SliceList", "int[]", "切片实例序列"),
            ("AiProfileID", "int", "AI档位"),
            ("WinThreshold", "int", "胜利阈值"),
            ("DrawThreshold", "int", "平局阈值"),
            ("TicketCost", "int", "门票消耗"),
            ("OpponentTeamID", "int", "对手球队(队名/队服/队标)"),
            ("OpponentTeamStar", "int", "对手球队星级(球员属性计算依据)"),
            ("LeagueRound", "int", "联赛轮次"),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 1, "IsTutorial": 1, "SliceList": "[201,202,203]", "AiProfileID": 1001, "WinThreshold": 2, "DrawThreshold": 1, "TicketCost": 1, "OpponentTeamID": 201, "OpponentTeamStar": 1, "LeagueRound": 1, "Remark": "第一关引导(含守门切片203)"},
            {"CfgID": 2, "IsTutorial": 0, "SliceList": "[301,302]", "AiProfileID": 1002, "WinThreshold": 1, "DrawThreshold": 0, "TicketCost": 1, "OpponentTeamID": 202, "OpponentTeamStar": 1, "LeagueRound": 2, "Remark": "地区预选赛第2轮"},
            {"CfgID": 3, "IsTutorial": 0, "SliceList": "[301,301,302]", "AiProfileID": 1003, "WinThreshold": 2, "DrawThreshold": 1, "TicketCost": 1, "OpponentTeamID": 203, "OpponentTeamStar": 2, "LeagueRound": 3, "Remark": "地区预选赛第3轮(困难档)"},
            {"CfgID": 10, "IsTutorial": 0, "SliceList": "[301,302]", "AiProfileID": 1002, "WinThreshold": 1, "DrawThreshold": 0, "TicketCost": 1, "OpponentTeamID": 204, "OpponentTeamStar": 2, "LeagueRound": 10, "Remark": "示例第10轮(文档原型)"},
        ],
    )

    # --- FSM/BT/敌人AI (2026-06-09 design) ---
    make_sheet(
        wb,
        "ActvSoccerPlayerAiDutyEnumCfg",
        c(
            ("CfgID", "int", "枚举值"),
            ("EnumKey", "string", "枚举名"),
            ("Remark", "string", "说明"),
        ),
        [
            {"CfgID": 1, "EnumKey": "Goalkeeper", "Remark": "守门员"},
            {"CfgID": 2, "EnumKey": "Defender", "Remark": "后卫：对方除门将外所有球员"},
            {"CfgID": 3, "EnumKey": "Forward", "Remark": "前锋：我方所有球员(含玩家角色)"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerAiProfileCfg",
        c(
            ("CfgID", "int", "AI难度档ID"),
            ("Difficulty", "string", "easy/normal/hard"),
            ("GoalkeeperSaveRate", "int", "门将扑救成功率%"),
            ("DefenderSuccessRate", "int", "防守成功率%"),
            ("ShooterSuccessRate", "int", "对手射门成功率%"),
            ("DeadCornerCanSave", "int", "死角可扑(固定0)"),
            ("ReactionTimeMs", "int", "默认反应时间ms"),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 1001, "Difficulty": "easy", "GoalkeeperSaveRate": 25, "DefenderSuccessRate": 15, "ShooterSuccessRate": 35, "DeadCornerCanSave": 0, "ReactionTimeMs": 1200, "Remark": "试训/引导关默认"},
            {"CfgID": 1002, "Difficulty": "normal", "GoalkeeperSaveRate": 45, "DefenderSuccessRate": 30, "ShooterSuccessRate": 50, "DeadCornerCanSave": 0, "ReactionTimeMs": 900, "Remark": "普通档"},
            {"CfgID": 1003, "Difficulty": "hard", "GoalkeeperSaveRate": 65, "DefenderSuccessRate": 45, "ShooterSuccessRate": 65, "DeadCornerCanSave": 0, "ReactionTimeMs": 700, "Remark": "困难档"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerEnemyAiCfg",
        c(
            ("CfgID", "int", "敌人AI配置ID"),
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
        [
            {"CfgID": 2001, "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "SaveWeight": 45, "LeftWeight": 40, "RightWeight": 40, "UpWeight": 20, "InterceptWeight": 0, "ClearanceWeight": 0, "KeeperCatchFail": 1, "OutOfBoundsFail": 0, "AnimationKey": "E04_GKDiveLeft", "Remark": "普通门将"},
            {"CfgID": 2002, "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "SaveWeight": 0, "LeftWeight": 0, "RightWeight": 0, "UpWeight": 0, "InterceptWeight": 35, "ClearanceWeight": 20, "KeeperCatchFail": 0, "OutOfBoundsFail": 1, "AnimationKey": "F03_Intercept", "Remark": "防守球员"},
            {"CfgID": 2003, "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "SaveWeight": 0, "LeftWeight": 40, "RightWeight": 40, "UpWeight": 20, "InterceptWeight": 0, "ClearanceWeight": 0, "KeeperCatchFail": 0, "OutOfBoundsFail": 0, "AnimationKey": "D01_Shoot", "Remark": "守门切片对方后卫射门"},
            {"CfgID": 2004, "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "SaveWeight": 50, "LeftWeight": 45, "RightWeight": 45, "UpWeight": 10, "InterceptWeight": 0, "ClearanceWeight": 0, "KeeperCatchFail": 1, "OutOfBoundsFail": 0, "AnimationKey": "E02_GKMoveLeft", "Remark": "移动门将(职责仍为Goalkeeper)"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerSliceAiCfg",
        c(
            ("CfgID", "int", "单切片AI配置ID"),
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
        [
            {"CfgID": 3001, "SliceID": 101, "AiProfileID": 1001, "GoalkeeperAiID": 2001, "DefenderAiID": 0, "ShooterAiID": 0, "ModifierID": 0, "IsGuideAi": 1, "RewindRandom": 1, "OverrideReactionTimeMs": 1200, "Remark": "试训-进攻"},
            {"CfgID": 3002, "SliceID": 102, "AiProfileID": 1001, "GoalkeeperAiID": 2001, "DefenderAiID": 0, "ShooterAiID": 0, "ModifierID": 0, "IsGuideAi": 1, "RewindRandom": 1, "OverrideReactionTimeMs": 1200, "Remark": "试训-任意球"},
            {"CfgID": 3003, "SliceID": 103, "AiProfileID": 1001, "GoalkeeperAiID": 2001, "DefenderAiID": 0, "ShooterAiID": 0, "ModifierID": 0, "IsGuideAi": 1, "RewindRandom": 1, "OverrideReactionTimeMs": 1200, "Remark": "试训-点球"},
            {"CfgID": 3004, "SliceID": 201, "AiProfileID": 1001, "GoalkeeperAiID": 2001, "DefenderAiID": 0, "ShooterAiID": 0, "ModifierID": 0, "IsGuideAi": 1, "RewindRandom": 1, "OverrideReactionTimeMs": 1200, "Remark": "引导关切片1-进攻"},
            {"CfgID": 3005, "SliceID": 202, "AiProfileID": 1001, "GoalkeeperAiID": 2001, "DefenderAiID": 2002, "ShooterAiID": 0, "ModifierID": 0, "IsGuideAi": 1, "RewindRandom": 1, "OverrideReactionTimeMs": 1200, "Remark": "引导关切片2-助攻"},
            {"CfgID": 3006, "SliceID": 203, "AiProfileID": 1002, "GoalkeeperAiID": 0, "DefenderAiID": 0, "ShooterAiID": 2003, "ModifierID": 0, "IsGuideAi": 1, "RewindRandom": 1, "OverrideReactionTimeMs": 900, "Remark": "引导关切片3-守门"},
            {"CfgID": 3007, "SliceID": 301, "AiProfileID": 1002, "GoalkeeperAiID": 2001, "DefenderAiID": 2002, "ShooterAiID": 0, "ModifierID": 4001, "IsGuideAi": 0, "RewindRandom": 1, "OverrideReactionTimeMs": 900, "Remark": "正式关-进攻+移动门将"},
            {"CfgID": 3008, "SliceID": 302, "AiProfileID": 1002, "GoalkeeperAiID": 2001, "DefenderAiID": 0, "ShooterAiID": 0, "ModifierID": 0, "IsGuideAi": 0, "RewindRandom": 1, "OverrideReactionTimeMs": 900, "Remark": "正式关-点球"},
            {"CfgID": 3009, "SliceID": 301, "AiProfileID": 1003, "GoalkeeperAiID": 2004, "DefenderAiID": 2002, "ShooterAiID": 0, "ModifierID": 4002, "IsGuideAi": 0, "RewindRandom": 1, "OverrideReactionTimeMs": 700, "Remark": "困难复用301(关卡3用)"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerAiModifierCfg",
        c(
            ("CfgID", "int", "机制ID"),
            ("ModifierType", "string", "机制类型"),
            ("Param1Key", "string", "参数1键"),
            ("Param1Value", "string", "参数1值"),
            ("Param2Key", "string", "参数2键"),
            ("Param2Value", "string", "参数2值"),
            ("Param3Key", "string", "参数3键"),
            ("Param3Value", "string", "参数3值"),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 4001, "ModifierType": "moving_keeper", "Param1Key": "speed", "Param1Value": "1.0", "Param2Key": "range", "Param2Value": "2.5", "Param3Key": "start_offset", "Param3Value": "0.0", "Remark": "普通移动门将"},
            {"CfgID": 4002, "ModifierType": "moving_keeper", "Param1Key": "speed", "Param1Value": "1.5", "Param2Key": "range", "Param2Value": "3.5", "Param3Key": "start_offset", "Param3Value": "0.5", "Remark": "困难移动门将"},
            {"CfgID": 4003, "ModifierType": "no_aim_line", "Param1Key": "enabled", "Param1Value": "1", "Remark": "关闭辅助线"},
            {"CfgID": 4004, "ModifierType": "fixed_wall", "Param1Key": "enabled", "Param1Value": "1", "Remark": "任意球固定人墙"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerSliceFlowCfg",
        c(
            ("CfgID", "int", "切片流程ID"),
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
            {"CfgID": 5001, "SliceType": "attack", "ForceOperationMode": "none", "WaitInputTimeMs": 0, "NeedReplayClick": 1, "EnableRewind": 1, "SuccessReplayKey": "Celebrate", "FailReplayKey": "Fail", "Remark": "进攻切片"},
            {"CfgID": 5002, "SliceType": "free_kick", "ForceOperationMode": "none", "WaitInputTimeMs": 0, "NeedReplayClick": 1, "EnableRewind": 1, "SuccessReplayKey": "Celebrate", "FailReplayKey": "Fail", "Remark": "任意球"},
            {"CfgID": 5003, "SliceType": "penalty", "ForceOperationMode": "none", "WaitInputTimeMs": 0, "NeedReplayClick": 1, "EnableRewind": 1, "SuccessReplayKey": "Celebrate", "FailReplayKey": "Fail", "Remark": "点球"},
            {"CfgID": 5004, "SliceType": "goalkeep", "ForceOperationMode": "draw_line", "WaitInputTimeMs": 900, "NeedReplayClick": 1, "EnableRewind": 1, "SuccessReplayKey": "SaveSuccess", "FailReplayKey": "TimeoutFeedback", "Remark": "守门强制划线"},
            {"CfgID": 5005, "SliceType": "tutorial_attack", "ForceOperationMode": "none", "WaitInputTimeMs": 0, "NeedReplayClick": 1, "EnableRewind": 1, "SuccessReplayKey": "Celebrate", "FailReplayKey": "Fail", "Remark": "引导进攻(试训模式可切换)"},
            {"CfgID": 5006, "SliceType": "corner", "ForceOperationMode": "none", "WaitInputTimeMs": 0, "NeedReplayClick": 1, "EnableRewind": 1, "SuccessReplayKey": "Celebrate", "FailReplayKey": "Fail", "Remark": "角球P1"},
            {"CfgID": 5007, "SliceType": "throw_in", "ForceOperationMode": "none", "WaitInputTimeMs": 0, "NeedReplayClick": 1, "EnableRewind": 1, "SuccessReplayKey": "Celebrate", "FailReplayKey": "Fail", "Remark": "界外球P1"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerCharacterStateCfg",
        c(
            ("CfgID", "int", "ID"),
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
            {"CfgID": 1001, "StateKey": "Idle", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "A01_Idle", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0"},
            {"CfgID": 1002, "StateKey": "Run", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "A02_Jog", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0"},
            {"CfgID": 1003, "StateKey": "Run", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "A03_Sprint", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0", "Remark": "冲刺跑"},
            {"CfgID": 1004, "StateKey": "Control", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "B01_ReceiveBall", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "ReceiveBall", "Priority": "P0"},
            {"CfgID": 1005, "StateKey": "Control", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "B02_DribbleTouch", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "TouchBall", "Priority": "P0"},
            {"CfgID": 1006, "StateKey": "Pass", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "C01_ShortPass", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "ReleaseBall", "Priority": "P0"},
            {"CfgID": 1007, "StateKey": "Pass", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "C01_ShortPass", "MirrorFromID": 1006, "IsLoop": 0, "NeedEvent": 1, "EventKey": "ReleaseBall", "Priority": "P0", "Remark": "长传复用短传"},
            {"CfgID": 1008, "StateKey": "Kick", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "D01_Shoot", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "ReleaseBall", "Priority": "P0"},
            {"CfgID": 1009, "StateKey": "Kick", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "D02_PowerShot", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "ReleaseBall", "Priority": "P0"},
            {"CfgID": 1010, "StateKey": "Celebrate", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "G03_JumpCelebrate", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 0, "Priority": "P0"},
            {"CfgID": 1011, "StateKey": "Fail", "Duty": PLAYER_AI_DUTY_ENUM["Forward"], "AnimKey": "H03_KneelDown", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 0, "Priority": "P0", "Remark": "建议升P0"},
            {"CfgID": 2001, "StateKey": "SavePrepare", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E01_GKIdle", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0"},
            {"CfgID": 2002, "StateKey": "Run", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E02_GKMoveLeft", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0", "Remark": "门将左移"},
            {"CfgID": 2003, "StateKey": "Run", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E02_GKMoveLeft", "MirrorFromID": 2002, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0", "Remark": "门将右移镜像"},
            {"CfgID": 2004, "StateKey": "SaveLeft", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E04_GKDiveLeft", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "SaveContact", "Priority": "P0"},
            {"CfgID": 2005, "StateKey": "SaveRight", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E04_GKDiveLeft", "MirrorFromID": 2004, "IsLoop": 0, "NeedEvent": 1, "EventKey": "SaveContact", "Priority": "P0"},
            {"CfgID": 2006, "StateKey": "SaveUp", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E06_GKCatch", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "SaveContact", "Priority": "P0", "Remark": "临时复用接球"},
            {"CfgID": 2007, "StateKey": "SaveSuccess", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E06_GKCatch", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "SaveContact", "Priority": "P0"},
            {"CfgID": 2008, "StateKey": "Fail", "Duty": PLAYER_AI_DUTY_ENUM["Goalkeeper"], "AnimKey": "E07_GKMiss", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 0, "Priority": "P0"},
            {"CfgID": 3001, "StateKey": "Idle", "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "AnimKey": "F01_DefendIdle", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0"},
            {"CfgID": 3002, "StateKey": "Run", "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "AnimKey": "F02_DefendShuffle", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P0"},
            {"CfgID": 3003, "StateKey": "Control", "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "AnimKey": "F03_Intercept", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "InterceptBall", "Priority": "P0"},
            {"CfgID": 3004, "StateKey": "Idle", "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "AnimKey": "K03_WallDefense", "MirrorFromID": 0, "IsLoop": 1, "NeedEvent": 0, "Priority": "P1", "Remark": "对方人墙(后卫)"},
            {"CfgID": 4001, "StateKey": "Kick", "Duty": PLAYER_AI_DUTY_ENUM["Defender"], "AnimKey": "D01_Shoot", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 1, "EventKey": "ReleaseBall", "Priority": "P0", "Remark": "守门切片对方后卫射门"},
            {"CfgID": 5001, "StateKey": "Transition", "Duty": CHARACTER_STATE_SCENE_DUTY, "AnimKey": "I02_KickoffReady", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 0, "Priority": "P0", "Remark": "场景表现,Duty=0非枚举"},
            {"CfgID": 5002, "StateKey": "Transition", "Duty": CHARACTER_STATE_SCENE_DUTY, "AnimKey": "I03_GoalFreeze", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 0, "Priority": "P0", "Remark": "场景表现,Duty=0非枚举"},
            {"CfgID": 5003, "StateKey": "Fail", "Duty": CHARACTER_STATE_SCENE_DUTY, "AnimKey": "J01_TimeoutFeedback", "MirrorFromID": 0, "IsLoop": 0, "NeedEvent": 0, "Priority": "P0", "Remark": "守门超时反馈,Duty=0非枚举"},
        ],
    )

    # --- 3.4 养成 ---
    make_sheet(
        wb,
        "ActvSoccerCurrencyCfg",
        c(
            ("CfgID", "int", "currency_id"),
            ("CurrencyKey", "string", "货币键"),
            ("Usage", "string", "用途"),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 1, "CurrencyKey": "gold", "Usage": "生活等级升级", "Remark": "金币"},
            {"CfgID": 2, "CurrencyKey": "ticket", "Usage": "积分赛消耗", "Remark": "门票"},
            {"CfgID": 3, "CurrencyKey": "bet_coin", "Usage": "竞猜与兑换商店", "Remark": "竞猜币"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerGrowthLevelCfg",
        c(
            ("CfgID", "int", "编号"),
            ("GrowthType", "string", "fame/life"),
            ("Level", "int", "等级"),
            ("ExpRequired", "int", "升级经验/金币"),
            ("RewardFame", "int", "升级奖励知名度(0=无)"),
            ("TeamStarUnlock", "int", "解锁球队星级(知名度)"),
            ("TicketCap", "int", "门票上限(生活)"),
            ("TicketRecoverMin", "int", "门票恢复间隔分钟(生活)"),
            ("FreeRewind", "int", "免费回溯次数(生活)"),
            ("ExtraRound", "int", "额外联赛轮次(生活)"),
            ("TitleLcKey", "string", "称号→ActvSoccerLanguageCfg"),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 101, "GrowthType": "fame", "Level": 1, "ExpRequired": 0, "TeamStarUnlock": 1, "TitleLcKey": lc.add(lc_key("growth", "fame_title", "1"), "业余球员", "GrowthLevelCfg/101")},
            {"CfgID": 102, "GrowthType": "fame", "Level": 2, "ExpRequired": 150, "TeamStarUnlock": 2, "TitleLcKey": lc.add(lc_key("growth", "fame_title", "2"), "专业球员", "GrowthLevelCfg/102"), "Remark": "文档示例"},
            {"CfgID": 103, "GrowthType": "fame", "Level": 3, "ExpRequired": 200, "TeamStarUnlock": 3, "TitleLcKey": lc.add(lc_key("growth", "fame_title", "3"), "大师", "GrowthLevelCfg/103"), "Remark": "文档示例"},
            {"CfgID": 201, "GrowthType": "life", "Level": 1, "ExpRequired": 0, "TicketCap": 80, "TicketRecoverMin": 30, "Remark": ""},
            {"CfgID": 202, "GrowthType": "life", "Level": 2, "ExpRequired": 100, "TicketCap": 200, "TicketRecoverMin": 28, "FreeRewind": 1, "Remark": "升级消耗金币100"},
            {"CfgID": 203, "GrowthType": "life", "Level": 3, "ExpRequired": 200, "RewardFame": 10, "TicketCap": 250, "TicketRecoverMin": 25, "ExtraRound": 5, "Remark": "文档:门票+1/剩余轮次+5"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerFameGainRuleCfg",
        c(
            ("CfgID", "int", "编号"),
            ("FromWin", "int", "胜"),
            ("FromDraw", "int", "平"),
            ("FromLose", "int", "负"),
            ("FromGoal", "int", "每进球"),
            ("FromAssist", "int", "每助攻"),
            ("TeamStarFactor", "float", "球队星级系数"),
            ("Remark", "string", "TODO数值"),
        ),
        [{"CfgID": 1, "FromWin": 20, "FromDraw": 10, "FromLose": 5, "FromGoal": 5, "FromAssist": 3, "TeamStarFactor": 1.0, "Remark": "测试占位"}],
    )

    make_sheet(
        wb,
        "ActvSoccerTeamCfg",
        c(
            ("CfgID", "int", "team_id"),
            ("NameLcKey", "string", "球队名→ActvSoccerLanguageCfg"),
            ("Star", "int", "星级"),
            ("Region", "string", "地区"),
            ("KitKey", "string", "队服资源"),
            ("BadgeKey", "string", "队标资源"),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 101, "NameLcKey": lc.add(lc_key("team", "name", "101"), "红星联", "TeamCfg/101"), "Star": 1, "Region": "asia", "KitKey": "WC_Kit_01", "BadgeKey": "WC_Badge_01", "Remark": "默认1星"},
            {"CfgID": 102, "NameLcKey": lc.add(lc_key("team", "name", "102"), "莱茵青年", "TeamCfg/102"), "Star": 1, "Region": "europe", "KitKey": "WC_Kit_02", "BadgeKey": "WC_Badge_02", "Remark": ""},
            {"CfgID": 103, "NameLcKey": lc.add(lc_key("team", "name", "103"), "桑巴之星", "TeamCfg/103"), "Star": 1, "Region": "south_america", "KitKey": "WC_Kit_03", "BadgeKey": "WC_Badge_03", "Remark": ""},
            {"CfgID": 104, "NameLcKey": lc.add(lc_key("team", "name", "104"), "蓝白雄鹰", "TeamCfg/104"), "Star": 1, "Region": "south_america", "KitKey": "WC_Kit_04", "BadgeKey": "WC_Badge_04", "Remark": ""},
            {"CfgID": 201, "NameLcKey": lc.add(lc_key("team", "name", "201"), "海港FC", "TeamCfg/201"), "Star": 1, "Region": "asia", "KitKey": "WC_Kit_05", "BadgeKey": "WC_Badge_05", "Remark": "中国动态池"},
            {"CfgID": 202, "NameLcKey": lc.add(lc_key("team", "name", "202"), "东方之鹰", "TeamCfg/202"), "Star": 1, "Region": "asia", "KitKey": "WC_Kit_06", "BadgeKey": "WC_Badge_06", "Remark": "中国动态池"},
            {"CfgID": 203, "NameLcKey": lc.add(lc_key("team", "name", "203"), "北欧狼", "TeamCfg/203"), "Star": 2, "Region": "europe", "KitKey": "WC_Kit_07", "BadgeKey": "WC_Badge_07", "Remark": "联赛对手"},
            {"CfgID": 204, "NameLcKey": lc.add(lc_key("team", "name", "204"), "阿根廷神鹰", "TeamCfg/204"), "Star": 2, "Region": "south_america", "KitKey": "WC_Kit_08", "BadgeKey": "WC_Badge_08", "Remark": "文档合同示例"},
            {"CfgID": 205, "NameLcKey": lc.add(lc_key("team", "name", "205"), "桑巴红魔", "TeamCfg/205"), "Star": 2, "Region": "south_america", "KitKey": "WC_Kit_09", "BadgeKey": "WC_Badge_09", "Remark": ""},
            {"CfgID": 206, "NameLcKey": lc.add(lc_key("team", "name", "206"), "南美风暴", "TeamCfg/206"), "Star": 2, "Region": "south_america", "KitKey": "WC_Kit_10", "BadgeKey": "WC_Badge_10", "Remark": ""},
            {"CfgID": 207, "NameLcKey": lc.add(lc_key("team", "name", "207"), "潘帕斯之翼", "TeamCfg/207"), "Star": 2, "Region": "south_america", "KitKey": "WC_Kit_11", "BadgeKey": "WC_Badge_11", "Remark": ""},
            {"CfgID": 208, "NameLcKey": lc.add(lc_key("team", "name", "208"), "高卢雄鸡", "TeamCfg/208"), "Star": 2, "Region": "europe", "KitKey": "WC_Kit_12", "BadgeKey": "WC_Badge_12", "Remark": "12队服/队标"},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerContractCfg",
        c(
            ("CfgID", "int", "contract_id"),
            ("TeamID", "int", "球队"),
            ("TeamStar", "int", "星级"),
            ("PayFinish", "int", "周薪/完赛待遇"),
            ("PayGoal", "int", "进球待遇"),
            ("PayAssist", "int", "助攻待遇"),
            ("PayFame", "int", "名气待遇"),
            ("SeasonGoal", "ext[]", "赛季目标", V_SEASON_GOAL, '[{"type":"rank","threshold":12,"settle_at":"season_end"}]'),
            ("SeasonReward", "ext[]", "目标奖励", P_TYIDVAL, '[{"typ":"vm","id":11151001,"val":84}]'),
            ("SignReward", "ext[]", "签约即时奖励", P_TYIDVAL, '[]'),
            ("GrantFameLevel", "int", "发放门槛-知名度等级"),
            ("GrantLifeLevel", "int", "发放门槛-生活等级"),
            ("Remark", "string", "备注"),
        ),
        [
            {
                "CfgID": 1, "TeamID": 101, "TeamStar": 1,
                "PayFinish": 10, "PayGoal": 5, "PayAssist": 5, "PayFame": 20,
                "SeasonGoal": '[{"type":"rank","threshold":12,"settle_at":"season_end"}]',
                "SeasonReward": '[{"typ":"vm","id":11151001,"val":84}]',
                "SignReward": "[]",
                "GrantFameLevel": 1, "GrantLifeLevel": 1,
                "Remark": "首签1星-文档待遇示例",
            },
            {
                "CfgID": 2, "TeamID": 204, "TeamStar": 2,
                "PayFinish": 20, "PayGoal": 8, "PayAssist": 6, "PayFame": 30,
                "SeasonGoal": '[{"type":"slice_win","threshold":5,"settle_at":"season_end"}]',
                "SeasonReward": '[{"typ":"vm","id":11151001,"val":120}]',
                "SignReward": "[]",
                "GrantFameLevel": 2, "GrantLifeLevel": 2,
                "Remark": "完成第1轮联赛",
            },
        ],
    )

    # --- 3.5 积分赛 ---
    make_sheet(
        wb,
        "ActvSoccerSeasonCfg",
        c(
            ("CfgID", "int", "season_id"),
            ("LeagueNameLcKey", "string", "联赛名称→ActvSoccerLanguageCfg"),
            ("TotalRounds", "int", "总轮次"),
            ("SubLevelIDs", "int[]", "小关卡序列"),
            ("ContractOnFinish", "bool", "完成发合同"),
            ("UnlockPrevSeason", "int", "前置赛季"),
            ("Remark", "string", "备注"),
        ),
        [
            {
                "CfgID": 1,
                "LeagueNameLcKey": lc.add(lc_key("season", "league_name", "1"), "地区预选赛", "SeasonCfg/1"),
                "TotalRounds": 32,
                "SubLevelIDs": "[1,2,3,10]",
                "ContractOnFinish": 1,
                "UnlockPrevSeason": 0,
                "Remark": "测试赛季(文档原型第10/32轮)",
            },
        ],
    )

    # --- 3.6 淘汰赛 ---
    make_sheet(
        wb,
        "ActvSoccerKnockoutCfg",
        c(
            ("CfgID", "int", "编号"),
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
                "CfgID": 1,
                "OpenLeagueLevel": 3,
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
            ("CfgID", "int", "编号"),
            ("PhaseLcKey", "string", "阶段名→ActvSoccerLanguageCfg"),
            ("PhaseKey", "string", "阶段键"),
            ("StartTime", "string", "开始UTC"),
            ("EndTime", "string", "结束UTC"),
            ("DayContentLcKey", "string", "当日内容→ActvSoccerLanguageCfg"),
            ("BetOpen", "bool", "开放竞猜"),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 1, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "team_build"), "组队期", "KnockoutPhaseCfg/1"), "PhaseKey": "team_build", "StartTime": "2026-07-10 00:00:00", "EndTime": "2026-07-11 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "1"), "发起/加入组队、命名队名队标、审批", "KnockoutPhaseCfg/1"), "BetOpen": 0},
            {"CfgID": 2, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "team_build"), "组队期", "KnockoutPhaseCfg/2"), "PhaseKey": "team_build", "StartTime": "2026-07-11 00:00:00", "EndTime": "2026-07-11 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "2"), "组队结束补位", "KnockoutPhaseCfg/2"), "BetOpen": 0},
            {"CfgID": 3, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "3"), "海选", "KnockoutPhaseCfg/3"), "PhaseKey": "qualifier", "StartTime": "2026-07-12 00:00:00", "EndTime": "2026-07-12 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "3"), "1天内筛出64强", "KnockoutPhaseCfg/3"), "BetOpen": 0, "Remark": "不开竞猜"},
            {"CfgID": 4, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "4"), "正赛第1轮", "KnockoutPhaseCfg/4"), "PhaseKey": "knockout_r1", "StartTime": "2026-07-13 00:00:00", "EndTime": "2026-07-13 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "4"), "8组各一轮(64强)", "KnockoutPhaseCfg/4"), "BetOpen": 1},
            {"CfgID": 5, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "5"), "正赛第2轮", "KnockoutPhaseCfg/5"), "PhaseKey": "knockout_r2", "StartTime": "2026-07-14 00:00:00", "EndTime": "2026-07-14 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "5"), "8组各一轮(32强)", "KnockoutPhaseCfg/5"), "BetOpen": 1},
            {"CfgID": 6, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "6"), "正赛第3轮", "KnockoutPhaseCfg/6"), "PhaseKey": "knockout_r3", "StartTime": "2026-07-15 00:00:00", "EndTime": "2026-07-15 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "6"), "8组各一轮(16强)", "KnockoutPhaseCfg/6"), "BetOpen": 1},
            {"CfgID": 7, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "7"), "正赛第4轮", "KnockoutPhaseCfg/7"), "PhaseKey": "knockout_r4", "StartTime": "2026-07-16 00:00:00", "EndTime": "2026-07-16 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "7"), "8组决出组冠军→8强", "KnockoutPhaseCfg/7"), "BetOpen": 1},
            {"CfgID": 8, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "8"), "正赛第5轮", "KnockoutPhaseCfg/8"), "PhaseKey": "knockout_r5", "StartTime": "2026-07-17 00:00:00", "EndTime": "2026-07-17 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "8"), "8强淘汰赛(4强)", "KnockoutPhaseCfg/8"), "BetOpen": 1},
            {"CfgID": 9, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "9"), "决赛", "KnockoutPhaseCfg/9"), "PhaseKey": "knockout_final", "StartTime": "2026-07-18 00:00:00", "EndTime": "2026-07-18 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "9"), "冠亚军决赛", "KnockoutPhaseCfg/9"), "BetOpen": 1},
            {"CfgID": 10, "PhaseLcKey": lc.add(lc_key("knockout", "phase_name", "10"), "展示期", "KnockoutPhaseCfg/10"), "PhaseKey": "showcase", "StartTime": "2026-07-19 00:00:00", "EndTime": "2026-07-19 23:59:59", "DayContentLcKey": lc.add(lc_key("knockout", "day_content", "10"), "冠军展示+兑换商店可用", "KnockoutPhaseCfg/10"), "BetOpen": 0},
        ],
    )

    make_sheet(
        wb,
        "ActvSoccerMatchSimulationCfg",
        c(
            ("CfgID", "int", "编号"),
            ("RuleKey", "string", "规则键"),
            ("Formula", "string", "公式/说明"),
            ("Params", "ext", "模拟参数", V_SIM_PARAMS, '{"base":3,"per_rating":0.1}'),
            ("Remark", "string", "TODO系数"),
        ),
        [
            {"CfgID": 1, "RuleKey": "single_rating", "Formula": "f(fame_lv,training_lv,life_lv)", "Params": '{"fame_w":1.0,"life_w":1.0,"training_w":1.0}', "Remark": "单主角评分"},
            {"CfgID": 2, "RuleKey": "team_total", "Formula": "sum(member_rating)", "Params": "{}", "Remark": "队伍总评"},
            {"CfgID": 3, "RuleKey": "slice_count", "Formula": "f(max_rating)", "Params": '{"base":3,"per_rating":0.1}', "Remark": "双方切片数可不同"},
            {"CfgID": 4, "RuleKey": "slice_success_p", "Formula": "own_total/(own_total+opp_total)", "Params": "{}", "Remark": "单切片成功期望"},
            {"CfgID": 5, "RuleKey": "tie_breaker", "Formula": "total_rating>max_rating>signup_time", "Params": "{}", "Remark": "平局破法"},
        ],
    )

    # --- 3.7 竞猜 ---
    make_sheet(
        wb,
        "ActvSoccerBetCoinSourceCfg",
        c(
            ("CfgID", "int", "编号"),
            ("DailyFree", "int", "每日免费竞猜币"),
            ("GiftGrant", "int", "礼包投放"),
            ("LoseRecycleRate", "int", "失败回收万分比"),
            ("StakeOptions", "int[]", "快捷投注档位"),
            ("Remark", "string", "备注"),
        ),
        [{"CfgID": 1, "DailyFree": 100, "GiftGrant": 0, "LoseRecycleRate": 8000, "StakeOptions": "[100,200,500,1000,5000]", "Remark": "失败回收80%"}],
    )

    make_sheet(
        wb,
        "ActvSoccerBetMatchCfg",
        c(
            ("CfgID", "int", "bet_match_id"),
            ("KnockoutMatchID", "int", "淘汰赛对阵ID"),
            ("OddsA", "float", "赔率A"),
            ("OddsB", "float", "赔率B"),
            ("OpenTime", "string", "开放"),
            ("CloseTime", "string", "截止"),
            ("Status", "string", "open/closed/settled"),
            ("Remark", "string", "测试模板"),
        ),
        [
            {"CfgID": 1, "KnockoutMatchID": 1001, "OddsA": 1.33, "OddsB": 1.45, "OpenTime": "2026-07-17 00:00:00", "CloseTime": "2026-07-17 20:00:00", "Status": "open", "Remark": "4强下注示例"},
        ],
    )

    # --- 3.9 BP ---
    make_sheet(
        wb,
        "ActvSoccerBattlePassCfg",
        c(
            ("CfgID", "int", "编号"),
            ("Level", "int", "BP等级"),
            ("ExpRequired", "int", "所需活跃度"),
            ("FreeReward", "ext[]", "免费轨", P_TYIDVAL, '[{"typ":"vm","id":11151001,"val":20}]'),
            ("PaidReward", "ext[]", "付费轨", P_TYIDVAL, '[{"typ":"vm","id":11151001,"val":50}]'),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 1, "Level": 1, "ExpRequired": 100, "FreeReward": '[{"typ":"vm","id":11151001,"val":20}]', "PaidReward": '[{"typ":"vm","id":11151001,"val":50}]'},
            {"CfgID": 2, "Level": 2, "ExpRequired": 200, "FreeReward": '[{"typ":"vm","id":11151001,"val":30}]', "PaidReward": '[{"typ":"vm","id":11151001,"val":80}]'},
            {"CfgID": 3, "Level": 3, "ExpRequired": 300, "FreeReward": '[{"typ":"item","id":5012109,"val":1}]', "PaidReward": '[{"typ":"item","id":5012109,"val":2}]', "Remark": "外观/道具占位"},
        ],
    )

    # --- 3.10 兑换商店 ---
    make_sheet(
        wb,
        "ActvSoccerExchangeShopCfg",
        c(
            ("CfgID", "int", "商品ID"),
            ("CostVal", "int", "竞猜币消耗"),
            ("Reward", "ext[]", "兑换奖励", P_TYIDVAL, '[{"typ":"item","id":5012109,"val":1}]'),
            ("BuyLimit", "int", "限购"),
            ("RefreshCycle", "string", "刷新周期"),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 1, "CostVal": 500, "Reward": '[{"typ":"item","id":5012109,"val":1}]', "BuyLimit": 1, "RefreshCycle": "7d", "Remark": "世界杯表情"},
            {"CfgID": 2, "CostVal": 1000, "Reward": '[{"typ":"item","id":5012109,"val":1}]', "BuyLimit": 1, "RefreshCycle": "7d", "Remark": "回溯道具包"},
        ],
    )

    # --- 3.11 礼包 ---
    make_sheet(
        wb,
        "ActvSoccerGiftCfg",
        c(
            ("CfgID", "int", "礼包ID"),
            ("GiftType", "int", "0免费1付费"),
            ("Price", "int", "价格档位"),
            ("Reward", "ext[]", "奖励", P_TYIDVAL, '[{"typ":"vm","id":11151001,"val":100}]'),
            ("BuyLimit", "int", "限购"),
            ("Duration", "string", "限时"),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 1, "GiftType": 0, "Price": 0, "Reward": '[{"typ":"vm","id":11151001,"val":100}]', "BuyLimit": 1, "Duration": "1d", "Remark": "免费每日"},
            {"CfgID": 2, "GiftType": 1, "Price": 1, "Reward": '[{"typ":"vm","id":11151001,"val":300},{"typ":"item","id":5012109,"val":1}]', "BuyLimit": 3, "Duration": "7d", "Remark": "付费礼包"},
        ],
    )

    # --- 3.8 排名档位 ---
    make_sheet(
        wb,
        "ActvSoccerRankSectionCfg",
        c(
            ("CfgID", "int", "编号"),
            ("RankType", "string", "slice_win/goal/bet_hit/bet_profit"),
            ("RankMin", "int", "名次下限"),
            ("RankMax", "int", "名次上限"),
            ("Reward", "ext[]", "奖励", P_TYIDVAL, '[{"typ":"item","id":5012109,"val":1}]'),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 1, "RankType": "slice_win", "RankMin": 1, "RankMax": 1, "Reward": '[{"typ":"item","id":5012109,"val":1}]', "Remark": "积分榜冠军"},
            {"CfgID": 2, "RankType": "slice_win", "RankMin": 2, "RankMax": 10, "Reward": '[{"typ":"vm","id":11151001,"val":200}]', "Remark": "积分榜前10"},
            {"CfgID": 3, "RankType": "goal", "RankMin": 1, "RankMax": 3, "Reward": '[{"typ":"vm","id":11151001,"val":100}]', "Remark": "进球榜前三"},
            {"CfgID": 4, "RankType": "bet_hit", "RankMin": 1, "RankMax": 10, "Reward": '[{"typ":"vm","id":11151001,"val":50}]', "Remark": "竞猜命中榜"},
            {"CfgID": 5, "RankType": "bet_profit", "RankMin": 1, "RankMax": 10, "Reward": '[{"typ":"vm","id":11151001,"val":50}]', "Remark": "竞猜收益榜"},
        ],
    )

    # --- 全局常数 ---
    make_sheet(
        wb,
        "ActvSoccerGlobalConstCfg",
        c(
            ("CfgID", "int", "编号"),
            ("Constant", "string", "常量名"),
            ("Value", "string", "值"),
            ("Remark", "string", "备注"),
        ),
        [
            {"CfgID": 1, "Constant": "TicketCapDefault", "Value": "250", "Remark": "主界面示例80/250"},
            {"CfgID": 2, "Constant": "TicketRecoverMinutes", "Value": "30", "Remark": "恢复间隔"},
            {"CfgID": 3, "Constant": "KnockoutOpenLevel", "Value": "3", "Remark": "淘汰赛开放关卡"},
            {"CfgID": 4, "Constant": "DefaultCharacterCount", "Value": "4", "Remark": "可选角色数"},
            {"CfgID": 5, "Constant": "FirstSignTeamStar", "Value": "1", "Remark": "首签固定1星"},
            {"CfgID": 6, "Constant": "AiRandomSeedFormula", "Value": "attempt_id+slice_id+ai_profile_id+rewind_count", "Remark": "SeededRng种子组成"},
            {"CfgID": 7, "Constant": "DeadCornerCanSave", "Value": "0", "Remark": "死角不可扑(策划确认)"},
            {"CfgID": 8, "Constant": "ConfigOverlayOrder", "Value": "preset->instance->ai_profile->modifier", "Remark": "参数叠加顺序"},
            {"CfgID": 9, "Constant": "MoveSpeedIdle", "Value": "0", "Remark": "待机移动速度(固定值,单位m/s TODO)"},
            {"CfgID": 10, "Constant": "MoveSpeedWalk", "Value": "2.5", "Remark": "慢走移动速度(固定值,单位m/s TODO)"},
            {"CfgID": 11, "Constant": "MoveSpeedRunMin", "Value": "4", "Remark": "跑动速度下限;run=lerp(能力值,min,max)"},
            {"CfgID": 12, "Constant": "MoveSpeedRunMax", "Value": "8", "Remark": "跑动速度上限;run=lerp(能力值,min,max)"},
            {"CfgID": 13, "Constant": "MoveSpeedRatioIdle", "Value": "0", "Remark": "待机倍率;0=读MoveSpeedIdle,不乘run"},
            {"CfgID": 14, "Constant": "MoveSpeedRatioWalk", "Value": "0", "Remark": "慢走倍率;0=读MoveSpeedWalk,不乘run"},
            {"CfgID": 15, "Constant": "MoveSpeedRatioRun", "Value": "0", "Remark": "正常跑倍率;0=读能力值映射run速度(其余行为以此为基准)"},
            {"CfgID": 16, "Constant": "MoveSpeedRatioJog", "Value": "0.75", "Remark": "慢跑跑位-队友/对手;相对run倍率"},
            {"CfgID": 17, "Constant": "MoveSpeedRatioSprint", "Value": "1.25", "Remark": "冲刺-主角/对手;相对run倍率"},
            {"CfgID": 18, "Constant": "MoveSpeedRatioDribble", "Value": "0.85", "Remark": "带球推进-控球者;相对run倍率,进入可操作区后切idle"},
            {"CfgID": 19, "Constant": "MoveSpeedRatioPress", "Value": "1.1", "Remark": "逼抢-对手;相对run倍率,keep_possession断球跑位"},
            {"CfgID": 20, "Constant": "MoveSpeedRatioKeeperLateral", "Value": "0.9", "Remark": "门将横移-门将;相对run倍率,moving_keeper再乘params.speed"},
            {"CfgID": 21, "Constant": "KickForceMin", "Value": "10", "Remark": "出球力量下限;force=lerp(能力值,min,max)*力度百分比"},
            {"CfgID": 22, "Constant": "KickForceMax", "Value": "25", "Remark": "出球力量上限;force=lerp(能力值,min,max)*力度百分比"},
            {"CfgID": 23, "Constant": "BallControlDistance", "Value": "1.2", "Remark": "停球/控球距离;球员与球距离<此值时获得足球控制权(单位m TODO)"},
            {"CfgID": 24, "Constant": "OperableAngleSpanMin", "Value": "20", "Remark": "可操作夹角宽度下限(°);以接球方向为锚,扇形内须∃合法目标(友方+球门)"},
            {"CfgID": 25, "Constant": "OperableAngleSpanMax", "Value": "70", "Remark": "可操作夹角宽度上限(°);max仍无合法目标则带球转向最近合法目标后重试"},
        ],
    )

    return wb


def export_summary(sheets: list[str], lc_rows: list[dict]) -> None:
    summary = {
        "file": "ActivitySoccer.xlsx",
        "language_file": "ActivitySoccerLanguage.xlsx",
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
                "ActvSoccerGrowthLevelCfg", "ActvSoccerContractCfg", "ActvSoccerKnockoutCfg",
                "ActvSoccerBattlePassCfg", "ActvSoccerGiftCfg", "ActvSoccerRankSectionCfg",
            ],
        },
        "id_cross_ref": {
            "AiProfile": "1001=easy, 1002=normal, 1003=hard",
            "PlayerAiDuty": "1=Goalkeeper守门员,2=Defender后卫(对方非门将),3=Forward前锋(我方含玩家)",
            "EnemyAi": "2001=门将, 2002=后卫, 2003=后卫射门, 2004=移动门将",
            "SliceAi": "3001-3008 绑定切片101-302; 3009=困难复用301",
            "Modifier": "4001=移动门将, 4002=困难移动门将, 4003=无辅助线, 4004=固定人墙",
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
            "AI难度只控成功率; 死角球DeadCornerCanSave固定0",
            "单切片AI在ActvSoccerSliceAiCfg配置,移动门将归属切片级Modifier",
            "回溯后RewindRandom=1,种子含rewind_count",
            "参数叠加: preset→instance→ai_profile→modifier",
            "JSON字段使用ext/ext[]类型,第5行标注proto(如TypIDVal_P_cspb/SoccerObjective_V)",
            "ext/ext[]数据行不得留空: ext默认{}, ext[]默认[]; 有列示例时优先用第7行示例作默认值",
            "仅含单个参数时用int/float/string等基础类型,不用ext",
            "第1行读取端: 能确定仅前端c/仅后端s,拿不准或双端用cs; 见SHEET_DEFAULT_READ/READ_OVERRIDES",
            "展示文案字段用*LcKey(string)引用语言表CfgID,格式ActvSoccer_{category}_{semantic}_{seq}",
        ],
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
            "RewardFame/TeamStarUnlock/TicketCap等": "原LevelUpReward/LevelUpEffect拆列",
            "GrantFameLevel/GrantLifeLevel": "原GrantLevelReq",
        },
    }
    (OUT_DIR / "test-config-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    lc = LcRegistry()
    wb = build_workbook(lc)
    lc_wb = build_language_workbook(lc)

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

    export_summary(wb.sheetnames, lc.rows)
    print(f"Wrote {target}")
    print(f"Wrote {lc_target} ({len(lc.rows)} language entries)")
    print(f"Sheets ({len(wb.sheetnames)}): {', '.join(wb.sheetnames)}")


if __name__ == "__main__":
    main()
