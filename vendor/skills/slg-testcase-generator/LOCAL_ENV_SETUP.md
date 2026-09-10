# 新电脑环境说明

## Python

项目根目录已创建虚拟环境：

```powershell
.\.venv\Scripts\python.exe
```

已安装 `requirements.txt` 中的 Google API 依赖。运行项目脚本时优先使用这个 Python。

## Google 凭证

Python 写表脚本使用：

```text
slg-testcase-generator/scripts/token.json
```

Google Workspace MCP 使用：

```text
google-workspace-mcp-with-script-main/credentials.json
google-workspace-mcp-with-script-main/token.json
```

两条链路都已做过 Drive 只读验证。

## Node 与 Google Workspace MCP

当前机器未把系统 Node/npm 加到 PATH，因此 MCP 配置使用 Codex 自带 Node：

```text
C:\Users\lipeijie\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe
```

MCP 服务入口：

```text
google-workspace-mcp-with-script-main/dist/server.js
```

已安装 `node_modules`，并新增 `pnpm-workspace.yaml` 批准 `esbuild` 和 `tldjs` 的 postinstall 构建。

## Cursor/Codex Skill

已创建两个 Junction：

```text
C:\Users\lipeijie\.cursor\skills\slg-testcase-generator
C:\Users\lipeijie\.codex\skills\slg-testcase-generator
```

它们都指向本项目的 `slg-testcase-generator` 目录。

## MCP 配置

已配置：

```text
.cursor/mcp.json
google-workspace-mcp-with-script-main/.cursor/mcp.json
C:\Users\lipeijie\.codex\config.toml
```

Codex/Cursor 重启后会重新加载 MCP 与 skill。

## Chrome 扩展

Chrome 已安装，但当前检测到 ChatGPT Chrome Extension 与 Native Messaging Host 未安装/未注册。Browser 插件文档要求不要手工修复 native host，需要从 Codex/ChatGPT 插件 UI 重新安装 Chrome 插件或扩展。
