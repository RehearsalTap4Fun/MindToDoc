import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const sourceJsonPath = path.join(__dirname, "worldcup-slice-test-config.json");
const outputXlsxPath = path.join(__dirname, "worldcup-slice-test-config.xlsx");
const renderDir = path.join(__dirname, "_rendered");

const raw = await fs.readFile(sourceJsonPath, "utf8");
const data = JSON.parse(raw);

const workbook = Workbook.create();

function toJson(value) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value, null, 0);
}

function writeSheet(name, headers, rows, options = {}) {
  const sheet = workbook.worksheets.getOrAdd(name, {
    renameFirstIfOnlyNewSpreadsheet: true,
  });
  sheet.reset();
  sheet.showGridLines = true;

  const matrix = [headers, ...rows];
  const block = sheet.getRange("A1").write(matrix);

  const headerRange = sheet.getRange(`A1:${colName(headers.length)}1`);
  headerRange.format = {
    fill: "accent1",
    font: { color: "lt1", bold: true, size: 11 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: "#B8C4D6" },
  };
  headerRange.format.rowHeight = 24;

  if (rows.length > 0) {
    const bodyRange = sheet.getRange(`A2:${colName(headers.length)}${rows.length + 1}`);
    bodyRange.format = {
      verticalAlignment: "top",
      wrapText: true,
      borders: { preset: "outside", style: "thin", color: "#D9E2F3" },
    };
  }

  sheet.freezePanes.freezeRows(1);
  if (options.freezeFirstColumn) {
    sheet.freezePanes.freezeColumns(1);
  }

  if (options.columnWidthsPx) {
    for (const [col, width] of Object.entries(options.columnWidthsPx)) {
      sheet.getRange(`${col}:${col}`).format.columnWidthPx = width;
    }
  }

  if (options.centerCols) {
    for (const col of options.centerCols) {
      sheet.getRange(`${col}2:${col}${rows.length + 1}`).format.horizontalAlignment = "center";
    }
  }

  return { sheet, block };
}

function colName(index1Based) {
  let n = index1Based;
  let out = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    out = String.fromCharCode(65 + rem) + out;
    n = Math.floor((n - 1) / 26);
  }
  return out;
}

function enumerateSliceTypeCounts(items, key = "slice_type") {
  const order = ["attack", "free_kick", "penalty", "corner", "throw_in", "goalkeep"];
  const counts = new Map(order.map((t) => [t, 0]));
  for (const item of items) {
    counts.set(item[key], (counts.get(item[key]) || 0) + 1);
  }
  return order.map((sliceType) => [sliceType, counts.get(sliceType) || 0]);
}

const readmeRows = [
  ["Workbook", "2026 World Cup slice test config"],
  ["Source of truth", data.meta.source_of_truth],
  ["Generated at", data.meta.generated_at],
  ["Purpose", data.meta.purpose],
  ["Assumption: outcome_judged_by", data.assumptions.outcome_judged_by],
  ["Assumption: goals_count_only_on_objective_score", String(data.assumptions.goals_count_only_on_objective_score)],
  ["Assumption: mode_lock_rule", data.assumptions.mode_lock_rule],
  ["Assumption: whistle_handling", data.assumptions.whistle_handling],
  ["AI profile count", data.ai_profile_config.length],
  ["Preset count", data.slice_preset.length],
  ["Instance count", data.slice_instance.length],
  ["Level count", data.level_config.length],
  ["Season count", data.season_config.length],
  ["", ""],
  ["Slice preset counts by type", ""],
  ...enumerateSliceTypeCounts(data.slice_preset),
  ["", ""],
  ["Slice instance counts by type", ""],
  ...enumerateSliceTypeCounts(data.slice_instance),
];

const readmeSheet = workbook.worksheets.getOrAdd("README", {
  renameFirstIfOnlyNewSpreadsheet: true,
});
readmeSheet.reset();
readmeSheet.showGridLines = false;
readmeSheet.getRange("A1").values = [["2026 World Cup Slice Test Config"]];
readmeSheet.getRange("A1").format = {
  font: { size: 18, bold: true, color: "#123B5D" },
};
readmeSheet.getRange("A3").write([["Field", "Value"], ...readmeRows]);
readmeSheet.getRange("A3:B3").format = {
  fill: "accent1",
  font: { color: "lt1", bold: true, size: 11 },
  horizontalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: "#B8C4D6" },
};
readmeSheet.getRange(`A4:B${readmeRows.length + 3}`).format = {
  wrapText: true,
  verticalAlignment: "top",
  borders: { preset: "outside", style: "thin", color: "#D9E2F3" },
};
readmeSheet.freezePanes.freezeRows(3);
readmeSheet.getRange("A:A").format.columnWidthPx = 260;
readmeSheet.getRange("B:B").format.columnWidthPx = 620;

readmeSheet.getRange(`D3:E9`).values = [
  ["Object", "Count"],
  ["AI Profiles", data.ai_profile_config.length],
  ["Slice Presets", data.slice_preset.length],
  ["Slice Instances", data.slice_instance.length],
  ["Levels", data.level_config.length],
  ["Seasons", data.season_config.length],
  ["Goalkeep Instances", data.slice_instance.filter((x) => x.slice_type === "goalkeep").length],
];
readmeSheet.getRange("D3:E3").format = {
  fill: "accent2",
  font: { color: "lt1", bold: true },
  horizontalAlignment: "center",
};
readmeSheet.getRange("D3:E9").format.borders = { preset: "outside", style: "thin", color: "#D9E2F3" };
readmeSheet.getRange("D:D").format.columnWidthPx = 180;
readmeSheet.getRange("E:E").format.columnWidthPx = 120;

writeSheet(
  "ai_profile_config",
  ["ai_profile_id", "difficulty", "param_overrides_json"],
  data.ai_profile_config.map((item) => [
    item.ai_profile_id,
    item.difficulty,
    toJson(item.param_overrides),
  ]),
  {
    freezeFirstColumn: true,
    columnWidthsPx: { A: 110, B: 120, C: 340 },
    centerCols: ["A", "B"],
  },
);

writeSheet(
  "slice_preset",
  [
    "preset_id",
    "slice_type",
    "name",
    "tags",
    "ball_pos",
    "ball_vector",
    "ball_owner",
    "attackers_json",
    "defenders_json",
    "camera_json",
    "target_point",
    "operable_angle",
    "type_payload_json",
    "recommended_modes",
  ],
  data.slice_preset.map((item) => [
    item.preset_id,
    item.slice_type,
    item.name,
    toJson(item.tags),
    toJson(item.ball_pos),
    toJson(item.ball_vector),
    item.ball_owner ?? "",
    toJson(item.players_init.attackers),
    toJson(item.players_init.defenders),
    toJson(item.camera),
    toJson(item.target_point),
    item.operable_angle,
    toJson(item.type_payload),
    toJson(item.recommended_modes),
  ]),
  {
    freezeFirstColumn: true,
    columnWidthsPx: {
      A: 90, B: 110, C: 180, D: 140, E: 130, F: 130, G: 100,
      H: 420, I: 420, J: 180, K: 130, L: 120, M: 340, N: 160,
    },
    centerCols: ["A", "B", "G", "L"],
  },
);

writeSheet(
  "slice_instance",
  [
    "slice_instance_id",
    "slice_type",
    "preset_id",
    "overrides_json",
    "type_payload_json",
    "objectives_json",
    "modifiers_json",
    "ai_override_json",
  ],
  data.slice_instance.map((item) => [
    item.slice_instance_id,
    item.slice_type,
    item.preset_id ?? "",
    toJson(item.overrides),
    toJson(item.type_payload),
    toJson(item.objectives),
    toJson(item.modifiers),
    toJson(item.ai_override),
  ]),
  {
    freezeFirstColumn: true,
    columnWidthsPx: { A: 120, B: 110, C: 90, D: 260, E: 240, F: 260, G: 260, H: 240 },
    centerCols: ["A", "B", "C"],
  },
);

writeSheet(
  "level_config",
  [
    "level_id",
    "name",
    "is_tutorial",
    "slice_list",
    "ai_profile_id",
    "win_threshold",
    "draw_threshold",
    "ticket_cost",
    "validation_focus",
  ],
  data.level_config.map((item) => [
    item.level_id,
    item.name,
    String(item.is_tutorial),
    toJson(item.slice_list),
    item.ai_profile_id,
    item.win_threshold,
    item.draw_threshold,
    item.ticket_cost,
    toJson(item.validation_focus),
  ]),
  {
    freezeFirstColumn: true,
    columnWidthsPx: { A: 90, B: 220, C: 100, D: 140, E: 90, F: 100, G: 100, H: 90, I: 320 },
    centerCols: ["A", "C", "E", "F", "G", "H"],
  },
);

writeSheet(
  "season_config",
  ["season_id", "sub_level_ids", "contract_on_finish", "unlock_prev_season"],
  data.season_config.map((item) => [
    item.season_id,
    toJson(item.sub_level_ids),
    String(item.contract_on_finish),
    item.unlock_prev_season,
  ]),
  {
    freezeFirstColumn: true,
    columnWidthsPx: { A: 90, B: 160, C: 130, D: 130 },
    centerCols: ["A", "C", "D"],
  },
);

for (const sheetName of ["ai_profile_config", "slice_preset", "slice_instance", "level_config", "season_config"]) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const used = sheet.getUsedRange();
  used.format.autofitRows();
}

const inspectResult = await workbook.inspect({
  kind: "table",
  range: "level_config!A1:I7",
  include: "values",
  tableMaxRows: 10,
  tableMaxCols: 10,
});
console.log(inspectResult.ndjson);

const errorScan = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
});
console.log(errorScan.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputXlsxPath);

console.log(`Saved workbook to ${outputXlsxPath}`);
