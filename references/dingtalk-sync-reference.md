# 钉钉落地操作参考（mindtodoc 随附）

把本地正式 md 同步到钉钉在线文档的完整操作链路（self-contained）。环境：钉钉文档 MCP（`update_document` / `update_document_block` / `insert_document_block` / `list_document_blocks` / `get_document_info` / `create_document`）+ 本 skill 目录的转换器 `scripts/md2jsonml.py`。

> 设计原则见 SKILL.md「外部技能与降级」「主案 / 派生写作要点」；本文件只讲"怎么操作"。

## 一、为什么是"jsonml 主体 + markdown 补表格"（两条解析路径互补）

`update_document` 既能吃 markdown 也能吃 jsonml，二者能力互补，已实测确认，别再试图用一条路径包打天下：

| | 标题 `list` 自动编号 | 正文/列表 `ind.left` 台阶缩进 | 纯文字表 |
|---|---|---|---|
| **jsonml 路径** | ✅ | ✅ | ❌ 必降级成 `columns` 分栏块 |
| **markdown 路径** | ❌（标题"光"的） | ❌（所有块 ind 全是 0） | ✅ 稳定渲染成真 `table` |

- **纯文字表炸 columns**：jsonml 写两列纯文字表，钉钉 `jsonMLToNode` 必把它降级成 `columns` 分栏块（markdown 视图塌成单列）。试过 `tblW` / `styleId` / `tblLook` / `rowSpan/colSpan` / `uuid` / 像素列宽 **全部无效**，是固有行为，无法用属性绕过。→ 纯文字表只能走 markdown 管道 `| a | b |`。带 `img` 的图文表走 jsonml 不炸。
- **markdown 列表只有相对层级**：markdown 的两级列表只有"●比○靠右一点"的相对层级，**没有"相对所属标题的台阶缩进"**——正文段贴最左、列表也从最左起。所以"markdown 写完只补标题编号"不够，正文和列表块的 `ind` 照样全要补。

## 二、转换器 `scripts/md2jsonml.py`

把 md 转成 `["root", {}, block1, block2, ...]` 整篇 jsonml。用法：

```bash
# 真实 Python（Windows 上 WindowsApps 的 python 是空壳，会 exit 49，要用真解释器）
PY="/c/Users/<user>/AppData/Local/Programs/Python/Python312/python.exe"
"$PY" scripts/md2jsonml.py <系统名>.md <out>.jsonml.json <listId如 balloon-h>
# 产出：<out>.jsonml.json（主体 root） + <out>.jsonml.tables.json（表格 sidecar） + <out>.jsonml.images.json（图片 sidecar） + <out>.jsonml.body.md（大文档 markdown 主体）
```

转换规则（脚本已实现，便于核对/改写）：
- **根节点**必须是 `["root", {}, ...]`，块作为 root 的后续元素。**不能传裸块数组**，否则报 "Cannot find any rule which match"。
- **主功能案标题口径**：功能名放在 md 文件名和钉钉文档名中，正文不再额外写同名总标题。正文真正章节从 H1 开始，如 `# 变更记录`、`# 简介`、`# 详细规则`。
- **ind.left 台阶**：维护"当前所属标题层级"，逐块算 ind——H1 标题=0、其下正文/列表=32；H2 标题=32、其下=64；H3 标题=64、其下=96（每级 +32，正文比所属标题多缩一档）。二级列表在所属正文档基础上再 +32。
- **标题编号**：所有正文标题都补 `list`（全文同一 `listId`、`isOrdered:true`、`autoLevel:true`、`listStyleType:"DEC_DEC_DEC_P"`、`listStyle.text` 按层级 `%1`/`%1.%2`/`%1.%2.%3`、`symbolStyle.sz` H1=21/H2=18/H3=16）。H1 从 `1.` 开始自动编号且 `ind.left=0`，不要把文档名作为首个 H1 写进正文。
- **两级列表**：`- 项` / 两空格 `- 子项` → `p`+`list`（bullet `●`/`○`、level 0/1）+ ind。
- **行内格式**：仅支持 `**加粗**` 与 `{{red:红字}}`；红字转为 leaf 的 `"color":"#FE0300"`。
- **表格不输出 jsonml table**（会炸 columns）：改输出占位段（文本 `__TABLE_n__`、ind 跟随当前标题），并把表格 markdown 顺序存进 tables sidecar。
- **图片占位输出可回读锚点**：`<!-- IMG: 界面名 | image_id -->` 转成占位段 `__IMG_n__`，并把 `{marker,name,id}` 存进 images sidecar。普通注释仍跳过。
- **大文档主体**：额外输出 `<out>.body.md`，用于大文档 markdown overwrite；该文件保留 `__TABLE_n__` / `__IMG_n__` 占位，不能用手工"去掉注释与表格"的正文替代。

标题块 jsonml 模板（H1，供手改参考）：
```json
["h1",{"ind":{"hanging":0,"left":0},"list":{"listId":"doc-h","level":0,"isOrdered":true,"autoLevel":true,"listStyleType":"DEC_DEC_DEC_P","symbolStyle":{"sz":21,"bold":true},"listStyle":{"format":"decimal","text":"%1","align":"left"}}},["span",{"data-type":"text"},["span",{"data-type":"leaf"},"标题文本"]]]
```

## 三、写入主体（按 payload 大小分两条路）

**payload 大小硬限制（血泪教训）**：jsonml 作为 MCP 参数直接传，**约 60KB 以上会撑断 socket 连接**（报 "The socket connection was closed unexpectedly"）。气球文档 ~204 块 / 64KB 就断了。断连后文档可能未写入（需 `list_document_blocks` 核实），但不会写坏。

- **小文档（jsonml < ~50KB）**：直接整篇 overwrite，一步带好编号+缩进+列表。
  ```
  update_document(nodeId, format="jsonml", jsonml=<root字符串>, mode="overwrite")
  ```
- **大文档（≥ ~50KB，如 150+ 块）**：不要硬传整篇，改走"markdown 主体 + 分批补 ind/编号"：
  1. `update_document(nodeId, markdown=<out>.body.md 的内容, mode="overwrite")` —— markdown 体积小不会断；`__TABLE_n__` / `__IMG_n__` 占位必须保留，供后续补表/补图定位；两级列表自带相对层级；
  2. `list_document_blocks(format="jsonml")` 取全部块，拿到各块 blockId 与文本；
  3. 按 `scripts/md2jsonml.py` 算好的目标块顺序与写入后的钉钉块顺序一一映射，拿到每个目标块对应的 blockId；文本只做错位校验，不做主定位。
  4. 按目标块的 ind/list 属性，**分批** `update_document_block`（每条消息并行 ~10 个小请求，每个块 jsonml 都很小、不会断；约每 10 块一批）。标题块同时补 `list` 编号。
  - **禁止仅靠文本唯一性匹配 blockId**。真实文档里"领取/确认/配置/开放条件/关闭按钮"等重复文本很多，文本只能辅助校验；若目标块数量、顺序或关键文本明显对不上，停止批量补写，改用小批量重写或人工确认。
- **偶发单块 `HSF TimeOut(3000ms)`**：不一定真失败，`list_document_blocks` 核实该块是否已更新，未更新再重发。

## 四、补表格（markdown 管道，不炸）

对每个 `__TABLE_n__` 占位段：
1. `list_document_blocks` 找到占位段 blockId；
2. 用 **markdown 管道表格** `update_document(append)` 或 `insert_document_block` 写在占位段前/后；
3. 删除占位段。

markdown 管道表格一定渲染成真 table（变更记录表、KEY 表均如此）。文档常只有变更记录表（最前）、KEY 表（最末）等少数几张，可控。

## 五、补界面图

按 images sidecar 中的 `__IMG_n__` 占位段插图：
1. `list_document_blocks` 找到占位段 blockId；
2. 用 `insert_document_block`（jsonml）在占位段后插左图右文表（左 `tc` `fill:#E8F2FE` 放 `img`、右 `tc` `fill:#FFFAE5` 放编号说明）；
3. 删除占位段。

图带 `resourceUrl`，所以是 table、不炸 columns。图表块结构与上传链路见 [`ui-annotation-reference.md`](ui-annotation-reference.md)。

## 六、注意事项

1. 写入前先 `get_document_info` 确认目标文档（除非新建）。
2. 新建用 `create_document`；整稿替换用上面的写入流程。内容源始终是本地正式 md。
3. **纯文字表绝不能走 jsonml**（必炸 columns）；只能 markdown 管道。带 `img` 的图文表走 jsonml 不炸。
4. **加粗与红字**：源 md 只使用 `**加粗**` 与 `{{red:红字}}`；不要用 markdown 的 `<span style>`、代码块、链接、删除线等未支持格式。
5. **回读抽查**（写入后必做）：`list_document_blocks` 抽查——标题有 `list`、正文 `ind.left ≠ 0`、表格用 `element` 模式确认是 `table` 而非 `columns`。
6. 终端中文乱码属正常（GBK），写进文档的内容是对的。
