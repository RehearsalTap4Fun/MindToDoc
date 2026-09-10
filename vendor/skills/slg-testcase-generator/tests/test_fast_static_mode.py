from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL = SKILL_ROOT / "SKILL.md"
STATIC_MODE = SKILL_ROOT / "references" / "static_acceptance.md"


def test_static_route_is_fast_and_precedes_standard_prerequisites() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    route = skill[
        skill.index("## Mode selection") : skill.index("## 🔧 项目配置")
    ]

    assert "2 分钟" in route
    assert "最多 20 条" in route
    assert "Markdown" in route
    assert "立即返回" in route


def test_fast_static_contract_is_concise_and_document_authoritative() -> None:
    text = STATIC_MODE.read_text(encoding="utf-8")

    required = (
        "主流程",
        "关键边界",
        "明显异常",
        "冲突与缺口",
        "开发文档优先",
        "不得覆盖开发文档",
        "最多 20 条",
    )
    forbidden = (
        "Google",
        "schema-v1",
        "static_acceptance_contract.py",
        "完整 manifest",
    )

    assert all(value in text for value in required)
    assert all(value not in text for value in forbidden)


def test_fast_static_contract_defines_one_markdown_table() -> None:
    text = STATIC_MODE.read_text(encoding="utf-8")

    assert (
        "| ID | 类别 | 关联需求 | 前置条件 | 操作/静态检查 | 预期 | 来源 | 备注 |"
        in text
    )
    for prefix in ("TC-MAIN-", "TC-BOUNDARY-", "TC-ABNORMAL-"):
        assert prefix in text
