---
description: Google Sheets 文件操作流程精简版
tags: [test, google-sheets, mcp]
---

# 文件操作（精简版）

> ⚠️ **AI 强制检查点**  
> 写入用例前必须完整阅读本文件！  
> **禁止**直接创建新 Google Sheet，必须按以下流程：  
> 1. 查找最新版本目录（根目录 → 年份 → 季度 → 版本）  
> 2. 复制模板文件到版本目录  
> 3. 写入 PRD 链接到 B6 单元格  
> 4. 使用 `write_test_cases.py` 脚本写入用例

> 🚫 **写入流程硬性约束（不可绕过）**  
> **禁止使用 MCP `writeSpreadsheet` 直接写入用例数据！**  
> MCP 工具只能写值，**无法执行合并单元格**，会导致 B/C/D 列行重叠。  
> **唯一允许的写入方式**：`python scripts/write_test_cases.py <spreadsheet_id> <json_file>`  
> 如果脚本因凭证缺失无法运行，必须先恢复凭证（从 `mcp-servers/google-docs-mcp-for-claudecode/credentials.json` 复制），**不得降级为 MCP 直写**。  
> MCP `writeSpreadsheet` 仅允许用于写入 PRD 链接（B6）和用例总数（B2）等单值操作。

---

## ⚠️ 重要：Google Sheet 访问规则

> **禁止使用 WebFetch、curl、browser_navigate 等工具访问 Google Sheet！**  
> 这些工具无法通过 OAuth 认证，会导致读取失败。

### 读取 Google Sheet（PRD）

```bash
# 必须使用 excel_tool.py 读取
python3 -c "
from scripts.excel_tool import SheetDataReader

sheet_id = '从URL提取的ID'  # 例: 1fuImzdVdrhcRYmvqFBpeLE57xBUoZYTQJwQq1waFPhA
reader = SheetDataReader(sheet_id, use_oauth=True)

# 列出所有工作表
sheets = reader.list_sheets()
print('工作表:', sheets)

# 读取指定工作表
data = reader.read_raw_values('工作表名称')
for row in data:
    print(row)
"
```

### URL 提取 Sheet ID

```
https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid=xxx
                                       ↑ 这部分是 Sheet ID
```

---

## Google Drive 目录结构

**根目录 ID**：从 `testcase-config/project_config.md` 的「用例根目录 ID」获取

**目录路径**：根目录/ → 年份/ → 季度/ → 版本/ → 模板文件

**当前最新路径** → 参考 SKILL.md

---

## MCP 工具操作流程

### 步骤1：查找最新版本

```javascript
// 依次查找：根目录 → 最新年份 → 最新季度 → 最新版本
listFolderContents({ folderId: "根目录ID" })
listFolderContents({ folderId: "年份ID" })
listFolderContents({ folderId: "季度ID" })
```

**查找规则**：
- 年份：数字最大（2026 > 2025）
- 季度：Q4 > Q3 > Q2 > Q1
- 版本：语义化比较（0.86.0 > 0.85.0）

### 步骤2：复制模板

```javascript
copyFile({
  fileId: "模板ID",
  newName: "{版本号}_AI_{功能名称}",
  parentFolderId: "版本目录ID"
})
// 返回 spreadsheetId
```

### 步骤3：写入策划案链接

```javascript
writeSpreadsheet({
  spreadsheetId: "新文件ID",
  range: "用例!B6",
  values: [['=HYPERLINK("URL", "名称")']],
  valueInputOption: "USER_ENTERED"  // 重要！
})
```

---

## Python 脚本执行

### 一键写入脚本（v2 - 原地更新）

```bash
# 标准写入（含手工修改检测）
python scripts/write_test_cases.py <spreadsheet_id> test_cases.json

# 跳过手工修改检测，直接覆盖
python scripts/write_test_cases.py <spreadsheet_id> test_cases.json --force
```

**v2 特性**：
- **原地更新**：先清除旧数据区域，再写入新数据，**不留脏数据**
- **手工修改保护**：写入前对比 Sheet 与 JSON，检测手工新增/修改行并警告
- **智能行管理**：数据变多→自动插入行；数据变少→自动删除多余空行
- 自动合并 B/C/D 列单元格
- 固定内容区域自动保护（国服/跨服/合服等模板区域）

### 🔴 写入前必做：同步手工修改

> **如果测试人员或策划在 Google Sheet 上手工添加/修改了用例，必须在写入前将这些修改同步到本地 JSON 文件！**

**流程**：
1. 运行不带 `--force` 的写入命令
2. 脚本会自动检测 Sheet 与 JSON 的差异并列出
3. 将手工新增的行添加到 JSON 文件中对应模块的正确位置
4. 将手工修改的内容更新到 JSON 文件
5. 确认同步完成后再执行写入

**⚠️ 使用 `--force` 会跳过检测直接覆盖，仅在确认无手工修改时使用！**

### JSON 格式要求

**关键规则**：
- 每行必须6列：`[用例编号, 功能模块, 检查点, 操作步骤, 预期结果, 备注]`
- 空值用 `""` 占位，不能省略
- 使用英文引号

**⚠️ 合并单元格格式** → 详见 [SKILL.md](../SKILL.md) 的「输出格式」章节（唯一权威来源）。

核心要点：同模块/同检查点/同操作步骤的后续行，对应列写空字符串 `""`，脚本会自动合并。


---

## 写入前校验（建议）

> **写入 Google Sheets 前建议执行**。脚本会提示检查点过密（如仅1条用例的检查点），可据此合并该合并的再写入。

```bash
# 写入前先校验格式与检查点密度
python scripts/validate_cases.py test_cases.json

# 严格模式：硬编码检测也视为错误
python scripts/validate_cases.py test_cases.json --strict
```

校验内容：格式完整性（6列）、**检查点密度（仅1条会提示，建议该合并的合并；单检查点建议≤15条）**、合并标记一致性、硬编码数值检测

---

## 故障排查

**Q1：JSON格式错误**
- 检查每行是否严格6列
- 空值是否用 `""` 占位

**Q2：固定内容被覆盖**
- v2 脚本自动检测固定内容位置并保护
- 数据区与固定内容之间保持2行空隙

**Q3：MCP工具找不到最新版本**
- 实时查询目录结构
- 不要依赖缓存的ID

**Q4：手工修改被覆盖**
- 不带 `--force` 运行写入命令，脚本会提示差异
- 将手工修改同步到 JSON 后再写入
