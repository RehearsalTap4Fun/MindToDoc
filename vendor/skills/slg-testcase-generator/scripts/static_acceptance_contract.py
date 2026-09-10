import argparse
import json
import os
import re
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str


class ContractError(Exception):
    def __init__(self, issues: list[ValidationIssue]):
        super().__init__("static testcase payload is invalid")
        self.issues = issues


def validate_payload(payload: Mapping[str, Any]) -> list[ValidationIssue]:
    if not isinstance(payload, Mapping):
        return [ValidationIssue("FIELD_REQUIRED", "payload", "payload must be an object")]
    issues: list[ValidationIssue] = []
    if type(payload.get("schemaVersion")) is not int or payload.get("schemaVersion") != 1:
        issues.append(ValidationIssue("SCHEMA_VERSION_INVALID", "schemaVersion", "expected 1"))
    for name in (
        "metadata", "requirements", "staticCases", "runtimeCases", "manualCaseReconciliation",
    ):
        if name not in payload:
            issues.append(ValidationIssue("FIELD_REQUIRED", name, "field is required"))

    def add(code: str, path: str, message: str) -> None:
        issues.append(ValidationIssue(code, path, message))

    def required(mapping: Any, name: str, path: str, *, text: bool = True) -> Any:
        if (
            not isinstance(mapping, Mapping)
            or name not in mapping
            or mapping[name] is None
            or (text and (not isinstance(mapping[name], str) or not mapping[name].strip()))
        ):
            add("FIELD_REQUIRED", f"{path}.{name}", "field is required")
            return None
        return mapping[name]

    def check_ends(value: Any, path: str) -> None:
        if not isinstance(value, list) or not value:
            add("FIELD_REQUIRED", path, "expectedEnds must be a non-empty list")
            return
        if any(not isinstance(end, str) or end not in {"Client", "Server", "Config"} for end in value):
            add("EXPECTED_END_INVALID", path, "expectedEnds must contain only Client, Server, Config")

    metadata = payload.get("metadata")
    if "metadata" not in payload:
        pass
    elif not isinstance(metadata, Mapping):
        add("FIELD_REQUIRED", "metadata", "metadata must be an object")
    else:
        for name in ("featureName", "documentSource", "featureType", "generatedAt"):
            required(metadata, name, "metadata")
        document_hash = required(metadata, "documentHash", "metadata")
        if document_hash is not None and (
            not isinstance(document_hash, str) or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", document_hash)
        ):
            add("ID_FORMAT_INVALID", "metadata.documentHash", "expected sha256 hash")
        if "manualSources" not in metadata:
            add("FIELD_REQUIRED", "metadata.manualSources", "field is required")
        elif not isinstance(metadata["manualSources"], list):
            add("FIELD_REQUIRED", "metadata.manualSources", "manualSources must be a list")
        elif any(not isinstance(source, str) or not source.strip() for source in metadata["manualSources"]):
            add("FIELD_REQUIRED", "metadata.manualSources", "manualSources entries must be source locators")

    requirements = payload.get("requirements")
    requirements_available = isinstance(requirements, list) and bool(requirements)
    if "requirements" not in payload:
        requirements = []
    elif not requirements_available:
        add("FIELD_REQUIRED", "requirements", "requirements must be a non-empty list")
        requirements = []
    requirements_by_id: dict[str, Mapping[str, Any]] = {}
    conditions_by_id: dict[str, tuple[str, Mapping[str, Any]]] = {}
    for index, requirement in enumerate(requirements):
        path = f"requirements[{index}]"
        if not isinstance(requirement, Mapping):
            add("FIELD_REQUIRED", path, "requirement must be an object")
            continue
        req_id = required(requirement, "requirementId", path, text=False)
        if req_id is not None:
            if not isinstance(req_id, str) or not re.fullmatch(r"REQ-[0-9]{3,}", req_id):
                add("ID_FORMAT_INVALID", f"{path}.requirementId", "invalid requirement ID")
            elif req_id in requirements_by_id:
                add("REQUIREMENT_ID_DUPLICATE", f"{path}.requirementId", "duplicate requirement ID")
            else:
                requirements_by_id[req_id] = requirement
        for name in ("module", "requirement", "documentLocator"):
            required(requirement, name, path)
        check_ends(requirement.get("expectedEnds"), f"{path}.expectedEnds")
        for name in ("boundaries", "dependencies"):
            if name not in requirement or not isinstance(requirement[name], list):
                add("FIELD_REQUIRED", f"{path}.{name}", "field must be a list")
        condition_list = requirement.get("conditions")
        if not isinstance(condition_list, list) or not condition_list:
            add("FIELD_REQUIRED", f"{path}.conditions", "conditions must be a non-empty list")
            continue
        for condition_index, condition in enumerate(condition_list):
            condition_path = f"{path}.conditions[{condition_index}]"
            if not isinstance(condition, Mapping):
                add("FIELD_REQUIRED", condition_path, "condition must be an object")
                continue
            condition_id = required(condition, "conditionId", condition_path, text=False)
            required(condition, "text", condition_path)
            for boolean_name in ("core", "decisive"):
                if not isinstance(condition.get(boolean_name), bool):
                    add("FIELD_REQUIRED", f"{condition_path}.{boolean_name}", "field must be a boolean")
            if not isinstance(condition.get("verificationKind"), str) or condition.get("verificationKind") not in {"static", "runtime"}:
                add("FIELD_REQUIRED", f"{condition_path}.verificationKind", "must be static or runtime")
            if condition_id is None:
                continue
            if not isinstance(condition_id, str) or not isinstance(req_id, str) or not re.fullmatch(
                re.escape(req_id) + r"-C[0-9]{2,}", condition_id
            ):
                add("ID_FORMAT_INVALID", f"{condition_path}.conditionId", "invalid condition ID")
            elif condition_id in conditions_by_id:
                add("CONDITION_ID_DUPLICATE", f"{condition_path}.conditionId", "duplicate condition ID")
            else:
                conditions_by_id[condition_id] = (req_id, condition)

    all_cases: list[tuple[str, int, Mapping[str, Any]]] = []
    case_ids: set[str] = set()
    covered_static: set[str] = set()
    covered_runtime: set[str] = set()
    cases_by_requirement: Counter[str] = Counter()
    case_branches_available = {"static": False, "runtime": False}
    for kind, case_key, action_name in (("static", "staticCases", "checkAction"), ("runtime", "runtimeCases", "steps")):
        if case_key not in payload:
            continue
        cases = payload[case_key]
        if not isinstance(cases, list):
            add("FIELD_REQUIRED", case_key, "field must be a list")
            continue
        case_branches_available[kind] = True
        for index, case in enumerate(cases):
            path = f"{case_key}[{index}]"
            if not isinstance(case, Mapping):
                add("FIELD_REQUIRED", path, "case must be an object")
                continue
            all_cases.append((kind, index, case))
            case_id = required(case, "caseId", path, text=False)
            requirement_id = required(case, "requirementId", path, text=False)
            if case_id is not None:
                pattern = r"TC-(REQ-[0-9]{3,})-" + ("S" if kind == "static" else "R") + r"[0-9]{2,}"
                if not isinstance(case_id, str):
                    add("ID_FORMAT_INVALID", f"{path}.caseId", "invalid case ID")
                    match = None
                else:
                    match = re.fullmatch(pattern, case_id)
                    if match is None:
                        add("ID_FORMAT_INVALID", f"{path}.caseId", "invalid case ID")
                    if case_id in case_ids:
                        add("CASE_ID_DUPLICATE", f"{path}.caseId", "duplicate case ID")
                    case_ids.add(case_id)
                if match is not None and requirement_id is not None and match.group(1) != requirement_id:
                    add("CASE_ID_REQUIREMENT_MISMATCH", f"{path}.caseId", "case ID requirement does not match")
            if requirements_available and (
                not isinstance(requirement_id, str) or requirement_id not in requirements_by_id
            ):
                add("CASE_REQUIREMENT_UNKNOWN", f"{path}.requirementId", "unknown requirement")
            elif requirements_available:
                cases_by_requirement[requirement_id] += 1
            for name in ("module", "precondition", action_name, "expectedResult", "documentLocator", "remarks"):
                required(case, name, path)
            check_ends(case.get("expectedEnds"), f"{path}.expectedEnds")
            if not isinstance(case.get("priority"), str) or case.get("priority") not in {"P0", "P1", "P2", "P3", "常规"}:
                add("FIELD_REQUIRED", f"{path}.priority", "invalid priority")
            condition_ids = case.get("conditionIds")
            if not isinstance(condition_ids, list):
                add("FIELD_REQUIRED", f"{path}.conditionIds", "conditionIds must be a list")
                condition_ids = []
            elif not condition_ids:
                has_uncovered_decisive_static = (
                    kind == "static"
                    and isinstance(requirement_id, str)
                    and any(
                        condition_req_id == requirement_id
                        and condition.get("verificationKind") == "static"
                        and (condition.get("core") or condition.get("decisive"))
                        for condition_req_id, condition in conditions_by_id.values()
                    )
                )
                if not has_uncovered_decisive_static:
                    add("FIELD_REQUIRED", f"{path}.conditionIds", "conditionIds must not be empty")
            for condition_id in condition_ids:
                if not isinstance(condition_id, str):
                    add("ID_FORMAT_INVALID", f"{path}.conditionIds", "condition ID must be a string")
                    continue
                if not requirements_available:
                    continue
                target = conditions_by_id.get(condition_id)
                if target is None:
                    add("CONDITION_UNKNOWN", f"{path}.conditionIds", "unknown condition")
                    continue
                condition_req_id, condition = target
                if condition_req_id != requirement_id:
                    add("CASE_CONDITION_REQUIREMENT_MISMATCH", f"{path}.conditionIds", "condition belongs to another requirement")
                if condition.get("verificationKind") != kind:
                    add("CONDITION_KIND_MISMATCH", f"{path}.conditionIds", "condition has the wrong verification kind")
                elif kind == "static":
                    covered_static.add(condition_id)
                else:
                    covered_runtime.add(condition_id)

    for req_id in requirements_by_id:
        if all(case_branches_available.values()) and not cases_by_requirement[req_id]:
            add("REQUIREMENT_UNCOVERED", f"requirements[{req_id}]", "requirement has no cases")
    for condition_id, (_, condition) in conditions_by_id.items():
        if case_branches_available["static"] and condition.get("verificationKind") == "static" and (condition.get("core") or condition.get("decisive")) and condition_id not in covered_static:
            add("STATIC_CONDITION_UNCOVERED", f"conditions[{condition_id}]", "core or decisive static condition is uncovered")
        if case_branches_available["runtime"] and condition.get("verificationKind") == "runtime" and condition_id not in covered_runtime:
            add("RUNTIME_CONDITION_UNCOVERED", f"conditions[{condition_id}]", "runtime condition is uncovered")

    reconciliation = payload.get("manualCaseReconciliation")
    if "manualCaseReconciliation" not in payload:
        pass
    elif not isinstance(reconciliation, Mapping):
        add("MANUAL_RECONCILIATION_INVALID", "manualCaseReconciliation", "must be an object")
    else:
        for name in ("added", "unsupported", "conflicts"):
            entries = reconciliation.get(name)
            if not isinstance(entries, list):
                add("MANUAL_RECONCILIATION_INVALID", f"manualCaseReconciliation.{name}", "must be a list")
                continue
            for index, entry in enumerate(entries):
                path = f"manualCaseReconciliation.{name}[{index}]"
                if not isinstance(entry, Mapping) or any(not isinstance(entry.get(field), str) or not entry[field].strip() for field in ("source", "originalCaseId", "reason")):
                    add("MANUAL_RECONCILIATION_INVALID", path, "source, originalCaseId, and reason are required")
                    continue
                if name == "added" and (not isinstance(entry.get("caseId"), str) or entry["caseId"] not in case_ids):
                    add("MANUAL_RECONCILIATION_INVALID", path, "added item must reference a known caseId")
    return issues


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def render_markdown(payload: Mapping[str, Any]) -> str:
    metadata = payload["metadata"]
    static_by_req = Counter(case["requirementId"] for case in payload["staticCases"])
    runtime_by_req = Counter(case["requirementId"] for case in payload["runtimeCases"])
    static_links: defaultdict[str, list[str]] = defaultdict(list)
    runtime_links: defaultdict[str, list[str]] = defaultdict(list)
    for case in payload["staticCases"]:
        for condition_id in case["conditionIds"]:
            static_links[case["requirementId"]].append(f"{condition_id}→{case['caseId']}")
    for case in payload["runtimeCases"]:
        for condition_id in case["conditionIds"]:
            runtime_links[case["requirementId"]].append(f"{condition_id}→{case['caseId']}")
    manual_sources = metadata["manualSources"]
    lines = [
        f"# {cell(metadata['featureName'])}静态验收测试用例", "",
        "## 1. 元数据", "",
        f"- 功能名称：{cell(metadata['featureName'])}",
        f"- 开发文档：{cell(metadata['documentSource'])}",
        f"- 文档哈希：{cell(metadata['documentHash'])}",
        f"- 功能类型：{cell(metadata['featureType'])}",
        f"- 生成时间：{cell(metadata['generatedAt'])}",
        f"- 需求数量：{len(payload['requirements'])}",
        f"- 人工用例来源：{cell('；'.join(sorted(manual_sources)) if manual_sources else '无')}", "",
        "## 2. 需求覆盖表", "",
        "| 需求 ID | 静态条件→用例 | 运行条件→用例 | 静态用例数 | 运行用例数 | 覆盖结果 |",
        "|---|---|---|---:|---:|---|",
    ]
    for requirement in sorted(payload["requirements"], key=lambda item: item["requirementId"]):
        req_id = requirement["requirementId"]
        lines.append(
            f"| {req_id} | {cell('；'.join(sorted(static_links[req_id])) or '无')} | "
            f"{cell('；'.join(sorted(runtime_links[req_id])) or '无')} | "
            f"{static_by_req[req_id]} | {runtime_by_req[req_id]} | 已覆盖 |"
        )
    lines.extend([
        "", "## 3. 静态验收用例", "",
        "| 用例 ID | 需求 ID | 模块 | 前置条件/状态 | 静态检查动作 | 预期结果 | 预期端 | 开发文档定位 | 优先级 | 备注 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])
    for case in sorted(payload["staticCases"], key=lambda item: item["caseId"]):
        values = [case["caseId"], case["requirementId"], case["module"], case["precondition"],
                  case["checkAction"], case["expectedResult"], "/".join(case["expectedEnds"]),
                  case["documentLocator"], case["priority"], case["remarks"]]
        lines.append("| " + " | ".join(cell(value) for value in values) + " |")
    lines.extend([
        "", "## 4. 运行验收附录", "",
        "| 用例 ID | 需求 ID | 模块 | 前置条件/状态 | 操作步骤 | 预期结果 | 预期端 | 开发文档定位 | 优先级 | 备注 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])
    for case in sorted(payload["runtimeCases"], key=lambda item: item["caseId"]):
        values = [case["caseId"], case["requirementId"], case["module"], case["precondition"],
                  case["steps"], case["expectedResult"], "/".join(case["expectedEnds"]),
                  case["documentLocator"], case["priority"], case["remarks"]]
        lines.append("| " + " | ".join(cell(value) for value in values) + " |")
    lines.extend(["", "## 5. 一致性结果", ""])
    reconciliation = payload["manualCaseReconciliation"]
    if not any(reconciliation[name] for name in ("added", "unsupported", "conflicts")):
        lines.append("未提供人工用例对账项")
    else:
        for name, title in (("added", "人工用例新增覆盖"), ("unsupported", "无开发文档依据用例"), ("conflicts", "人工用例冲突")):
            for item in sorted(reconciliation[name], key=lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True)):
                lines.append(f"- {title}：{cell(json.dumps(item, ensure_ascii=False, sort_keys=True))}")
    return "\n".join(lines).rstrip() + "\n"


def validate_and_render(input_path: Path, output_path: Path) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    issues = validate_payload(payload)
    if issues:
        raise ContractError(issues)
    rendered = render_markdown(payload)
    temp = output_path.with_name(f".{output_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temp.write_text(rendered, encoding="utf-8", newline="\n")
        os.replace(temp, output_path)
    finally:
        if temp.exists():
            temp.unlink()
    return {
        "status": "ok", "code": "STATIC_TESTCASES_RENDERED",
        "requirements": len(payload["requirements"]), "staticCases": len(payload["staticCases"]),
        "runtimeCases": len(payload["runtimeCases"]), "output": str(output_path.resolve()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        receipt = validate_and_render(args.input, args.output)
    except ContractError as error:
        receipt = {"status": "error", "code": "STATIC_TESTCASES_INVALID", "errors": [asdict(issue) for issue in error.issues]}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        receipt = {"status": "error", "code": "STATIC_TESTCASES_ERROR", "errors": [{"code": "IO_OR_JSON_ERROR", "path": "", "message": str(error)}]}
    else:
        print(json.dumps(receipt, ensure_ascii=False))
        return 0
    print(json.dumps(receipt, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
