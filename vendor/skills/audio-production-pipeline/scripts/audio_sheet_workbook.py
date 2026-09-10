#!/usr/bin/env python3
"""Maintain the local audio_sheet.xlsx workbook without third-party packages."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from html import escape
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


BASE_COLUMNS = ["事件名", "音效资源名", "功能模块", "声音类型", "描述", "触发时机"]
NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
REL_WORKSHEET = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
REL_OFFICE_DOCUMENT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
CELL_REF_RE = re.compile(r"([A-Z]+)([0-9]+)")


def col_to_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def col_name_to_index(name: str) -> int:
    result = 0
    for char in name:
        result = result * 26 + (ord(char) - 64)
    return result - 1


def validate_sheet_name(sheet_name: str) -> str:
    sheet_name = sheet_name.strip()
    if not sheet_name:
        raise ValueError("sheetName is required")
    if len(sheet_name) > 31:
        raise ValueError("sheetName must be 31 characters or fewer for xlsx compatibility")
    if any(char in sheet_name for char in r'[]:*?/\\'):
        raise ValueError(r"sheetName contains an invalid Excel character: []:*?/\\")
    return sheet_name


def normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for si in root.findall(f"{{{NS_MAIN}}}si"):
        parts = []
        for text in si.iter(f"{{{NS_MAIN}}}t"):
            parts.append(text.text or "")
        values.append("".join(parts))
    return values


def relationship_targets(zf: zipfile.ZipFile) -> dict[str, str]:
    rels_path = "xl/_rels/workbook.xml.rels"
    root = ET.fromstring(zf.read(rels_path))
    targets: dict[str, str] = {}
    for rel in root:
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        rel_type = rel.attrib.get("Type")
        if rel_id and target and rel_type == REL_WORKSHEET:
            targets[rel_id] = "xl/" + target.lstrip("/")
    return targets


def read_cell(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "s":
        value = cell.find(f"{{{NS_MAIN}}}v")
        if value is None or value.text is None:
            return ""
        try:
            return shared_strings[int(value.text)]
        except (ValueError, IndexError):
            return ""
    if cell_type == "inlineStr":
        text = cell.find(f"{{{NS_MAIN}}}is/{{{NS_MAIN}}}t")
        return text.text if text is not None and text.text is not None else ""
    value = cell.find(f"{{{NS_MAIN}}}v")
    return value.text if value is not None and value.text is not None else ""


def trim_rows(rows: list[list[str]]) -> list[list[str]]:
    for row in rows:
        while row and row[-1] == "":
            row.pop()
    while rows and not any(rows[-1]):
        rows.pop()
    return rows


def read_workbook(path: Path) -> dict[str, list[list[str]]]:
    if not path.exists():
        return {}
    with zipfile.ZipFile(path, "r") as zf:
        shared_strings = read_shared_strings(zf)
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        targets = relationship_targets(zf)
        result: dict[str, list[list[str]]] = {}
        sheets = workbook.find(f"{{{NS_MAIN}}}sheets")
        if sheets is None:
            return result
        for sheet in sheets:
            name = sheet.attrib.get("name")
            rel_id = sheet.attrib.get(f"{{{NS_REL}}}id")
            if not name or rel_id not in targets:
                continue
            xml_path = targets[rel_id]
            if xml_path not in zf.namelist():
                continue
            root = ET.fromstring(zf.read(xml_path))
            sheet_data = root.find(f"{{{NS_MAIN}}}sheetData")
            rows: list[list[str]] = []
            if sheet_data is not None:
                for row in sheet_data.findall(f"{{{NS_MAIN}}}row"):
                    values: list[str] = []
                    for cell in row.findall(f"{{{NS_MAIN}}}c"):
                        ref = cell.attrib.get("r", "")
                        match = CELL_REF_RE.match(ref)
                        col_index = col_name_to_index(match.group(1)) if match else len(values)
                        while len(values) <= col_index:
                            values.append("")
                        values[col_index] = read_cell(cell, shared_strings)
                    rows.append(values)
            result[name] = trim_rows(rows)
        return result


def worksheet_xml(rows: list[list[str]]) -> str:
    max_col = max((len(row) for row in rows), default=1)
    max_row = max(len(rows), 1)
    dimension = f"A1:{col_to_name(max_col - 1)}{max_row}"
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<worksheet xmlns="{NS_MAIN}" xmlns:r="{NS_REL}">',
        f'<dimension ref="{dimension}"/>',
        "<sheetData>",
    ]
    for row_index, row in enumerate(rows, start=1):
        parts.append(f'<row r="{row_index}">')
        for col_index, value in enumerate(row):
            value = normalize_cell(value)
            if value == "":
                continue
            cell_ref = f"{col_to_name(col_index)}{row_index}"
            parts.append(
                f'<c r="{cell_ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
            )
        parts.append("</row>")
    parts.extend(["</sheetData>", "</worksheet>"])
    return "".join(parts)


def write_workbook(path: Path, sheets: dict[str, list[list[str]]]) -> None:
    if not sheets:
        raise ValueError("workbook must contain at least one sheet")
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(sheets.keys())
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            + "".join(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                for i in range(1, len(names) + 1)
            )
            + "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{NS_PACKAGE_REL}">'
            f'<Relationship Id="rId1" Type="{REL_OFFICE_DOCUMENT}" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<workbook xmlns="{NS_MAIN}" xmlns:r="{NS_REL}"><sheets>'
            + "".join(
                f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>'
                for i, name in enumerate(names, start=1)
            )
            + "</sheets></workbook>",
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{NS_PACKAGE_REL}">'
            + "".join(
                f'<Relationship Id="rId{i}" Type="{REL_WORKSHEET}" Target="worksheets/sheet{i}.xml"/>'
                for i in range(1, len(names) + 1)
            )
            + "</Relationships>",
        )
        for i, name in enumerate(names, start=1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", worksheet_xml(sheets[name]))


def ensure_sheet(workbook: Path, sheet_name: str) -> None:
    sheet_name = validate_sheet_name(sheet_name)
    sheets = read_workbook(workbook)
    if sheet_name not in sheets:
        sheets[sheet_name] = [BASE_COLUMNS[:]]
        write_workbook(workbook, sheets)
        print(f"created sheet: {sheet_name}")
        return
    if not sheets[sheet_name]:
        sheets[sheet_name] = [BASE_COLUMNS[:]]
        write_workbook(workbook, sheets)
        print(f"initialized sheet headers: {sheet_name}")
        return
    headers = sheets[sheet_name][0]
    changed = False
    for column in BASE_COLUMNS:
        if column not in headers:
            headers.append(column)
            changed = True
    if changed:
        write_workbook(workbook, sheets)
        print(f"updated base headers: {sheet_name}")
    else:
        print(f"sheet ready: {sheet_name}")


def rows_to_dicts(rows: list[list[str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    headers = rows[0]
    result: list[dict[str, str]] = []
    for row in rows[1:]:
        if not any(row):
            continue
        item: dict[str, str] = {}
        for i, header in enumerate(headers):
            if not header:
                continue
            item[header] = row[i] if i < len(row) else ""
        result.append(item)
    return result


def read_sheet(workbook: Path, sheet_name: str, as_json: bool) -> None:
    sheet_name = validate_sheet_name(sheet_name)
    sheets = read_workbook(workbook)
    if sheet_name not in sheets:
        raise ValueError(f"sheet not found: {sheet_name}")
    rows = sheets[sheet_name]
    if as_json:
        print(json.dumps(rows_to_dicts(rows), ensure_ascii=False, indent=2))
        return
    for row in rows:
        print(",".join(row))


def upsert_rows(workbook: Path, sheet_name: str, rows_json: Path, key: str) -> None:
    sheet_name = validate_sheet_name(sheet_name)
    rows_to_upsert = json.loads(rows_json.read_text(encoding="utf-8-sig"))
    if not isinstance(rows_to_upsert, list):
        raise ValueError("rows-json must contain an array of objects")

    sheets = read_workbook(workbook)
    if sheet_name not in sheets or not sheets[sheet_name]:
        sheets[sheet_name] = [BASE_COLUMNS[:]]

    rows = sheets[sheet_name]
    headers = rows[0]
    for column in BASE_COLUMNS:
        if column not in headers:
            headers.append(column)
    for item in rows_to_upsert:
        if not isinstance(item, dict):
            raise ValueError("rows-json entries must be objects")
        for column in item.keys():
            if column not in headers:
                headers.append(str(column))

    key_index = headers.index(key)
    existing_by_key: dict[str, int] = {}
    for index, row in enumerate(rows[1:], start=1):
        row_key = row[key_index].strip() if key_index < len(row) else ""
        if row_key:
            existing_by_key[row_key] = index

    for item in rows_to_upsert:
        row_key = normalize_cell(item.get(key))
        if not row_key:
            raise ValueError(f"upsert row missing key: {key}")
        if row_key in existing_by_key:
            target = rows[existing_by_key[row_key]]
        else:
            target = []
            rows.append(target)
            existing_by_key[row_key] = len(rows) - 1
        while len(target) < len(headers):
            target.append("")
        for column, value in item.items():
            target[headers.index(str(column))] = normalize_cell(value)

    write_workbook(workbook, sheets)
    print(f"upserted rows: {len(rows_to_upsert)} into sheet {sheet_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create, read, and update .gdconfig_tmp audio_sheet.xlsx.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ensure = subparsers.add_parser("ensure-sheet")
    ensure.add_argument("--workbook", required=True)
    ensure.add_argument("--sheet-name", required=True)

    read = subparsers.add_parser("read-sheet")
    read.add_argument("--workbook", required=True)
    read.add_argument("--sheet-name", required=True)
    read.add_argument("--json", action="store_true")

    upsert = subparsers.add_parser("upsert-rows")
    upsert.add_argument("--workbook", required=True)
    upsert.add_argument("--sheet-name", required=True)
    upsert.add_argument("--rows-json", required=True)
    upsert.add_argument("--key", default="事件名")

    args = parser.parse_args()
    try:
        workbook = Path(args.workbook).resolve()
        if args.command == "ensure-sheet":
            ensure_sheet(workbook, args.sheet_name)
        elif args.command == "read-sheet":
            read_sheet(workbook, args.sheet_name, args.json)
        elif args.command == "upsert-rows":
            upsert_rows(workbook, args.sheet_name, Path(args.rows_json).resolve(), args.key)
        return 0
    except Exception as exc:
        print(f"audio sheet workbook failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
