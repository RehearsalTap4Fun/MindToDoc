# 钉钉数据源读取

## 读取优先级（axls 电子表格）

| 优先级 | 方式 | 适用 |
|--------|------|------|
| **首选** | **钉钉表格 MCP**（`user-钉钉表格`） | `extension=axls` 在线电子表格 |
| **备选** | **`dws` CLI** | MCP 不可用、鉴权失败、或工具报错时 |

> **axls ≠ AI 智能表格（able）**。axls 走 `get_all_sheets` + `get_range`；able 走 AI 表格 MCP 的 `get_tables` + `query_records`，**禁止混用**。

## 类型探测（任何 alidocs 链接第一步）

**首选** 钉钉文档 MCP `get_document_info`（server: `user-钉钉文档`）：

```json
{ "nodeId": "<URL 或 32 位 nodeId>" }
```

**备选** `dws doc info`：

```bash
dws doc info --node "<URL或32位nodeId>" --format json
```

| extension | 类型 | 读取方式 |
|-----------|------|----------|
| **adoc** | 在线文档 | 见下文「功能策划文档」 |
| **axls** | 电子表格 | **钉钉表格 MCP** → 失败时 `dws sheet` |
| xlsx 等 | 上传文件 | `dws doc download` 后本地解析，**禁止** sheet 子命令 / 表格 MCP |

## axls 读取（首选：钉钉表格 MCP）

调用前必须先读工具 schema（`get_all_sheets`、`get_range`），再 `call_mcp_tool`。

### Step A：列出工作表

```json
// server: user-钉钉表格 · tool: get_all_sheets
{ "nodeId": "<nodeId 或完整 alidocs URL>" }
```

从返回中取目标 Sheet 的 `sheetId`（或 Sheet 名称）。

### Step B：读取区域

```json
// server: user-钉钉表格 · tool: get_range
{
  "nodeId": "<nodeId>",
  "sheetId": "<sheetId>",
  "range": "A1:D40"
}
```

- `nodeId` 支持 32 位 ID 或完整 `alidocs.dingtalk.com` URL
- `sheetId` 未知时**必须先** Step A，禁止臆测 `Sheet1` / `0` / `default`
- 大范围可分块读取（如 `A1:D40`、`A41:D80`）

### axls 读取（备选：dws CLI）

MCP 失败时再执行：

```bash
DWS=dws   # Windows: %USERPROFILE%\.local\bin\dws.exe
NODE=<nodeId>

$dws sheet list --node $NODE --format json
$dws sheet range read --node $NODE --sheet-id <SHEET_ID> --range "A1:D40" --format json
```

## 表结构工作簿（三项目公用）

- **nodeId**：`ZX6GRezwJl7zDo6zhnBEDKEpVdqbropQ`
- **名称**：X1_BI日志表说明
- **Sheet 数**：27（表名即 BI 表名，如 `user_asset`）

**MCP 示例**：

1. `get_all_sheets({ "nodeId": "ZX6GRezwJl7zDo6zhnBEDKEpVdqbropQ" })`
2. `get_range({ "nodeId": "...", "sheetId": "<user_asset 的 sheetId>", "range": "A1:D40" })`

**Reason/Event 枚举**：Sheet `Reason&Event&Attr说明`（sheetId 以 list 为准，当前约为 `st-619a16c0-1414`）。

## 需求样例库（K1 登记风格）

- **nodeId**：`dpYLaezmVNLROXARIZwOlNLK8rMqPxX6`
- **名称**：K1_BI日志统计需求

| Sheet | sheetId（以 list 为准） | 内容 |
|-------|-------------------------|------|
| 日志需求举例 | `st-497667ca-8674` | user_asset / user_hero 字段展开范例 |
| 服务器日志 | `st-0a8479b9-72097` | 服务器侧需求登记 |
| 客户端日志 | `st-a8bc6c77-85155` | 客户端 user_click 等登记 |

**MCP 示例**：

```json
// get_range
{
  "nodeId": "dpYLaezmVNLROXARIZwOlNLK8rMqPxX6",
  "sheetId": "st-497667ca-8674",
  "range": "A1:F35"
}
```

## 功能策划文档（输入）

通常为 **adoc**，与上表同文件夹或用户单独提供 URL。

**首选** 钉钉文档 MCP `get_document_content`（server: `user-钉钉文档`）或 `user-dingtalk-doc` `get_html`。

**备选**：

```bash
dws doc get_document_content --node "<策划文档node>" --format json
```

若策划文档本身是 **axls**，按上文 axls 流程读取。

## 故障排查

| 现象 | 处理 |
|------|------|
| 钉钉表格 MCP 工具不存在 / 报错 | 回退 `dws sheet list` + `dws sheet range read` |
| `dws` 找不到 | 将 `%USERPROFILE%\.local\bin` 加入 PATH，或用绝对路径 |
| MCP / dws 均授权失败 | 检查 Cursor MCP 配置（`~/.cursor/mcp.json` 中「钉钉表格」）或重新 dws 登录 |
| 误用 AI 表格 MCP 读 axls | 确认 `extension=axls`，改走 `get_all_sheets` + `get_range` |
| JSON 含换行导致解析失败 | 用 Python `json.loads` 读 stdout，勿用 PowerShell `ConvertFrom-Json` |
