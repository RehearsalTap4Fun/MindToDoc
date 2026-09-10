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
     - **markdown 主体也有 payload 上限（血泪教训）**：实测 ~40KB 的 body.md 一次 overwrite 仍会 `API Error`。超限时按 **H1 边界把 body.md 切成多段**（每段 ≤ ~16KB，切点落在 `# 标题` 行上、不切断 mermaid/表格）：**第 1 段用 `mode="overwrite"` 打底，其余段用 `mode="append"` 顺序续写**。切分用脚本按 `grep -n "^# "` 的行号做，逐段 `Read` 后写入，每段成功即落档，便于中断续传。
  2. `list_document_blocks(format="jsonml")` 取全部块，拿到各块 blockId 与文本；
  3. 按 `scripts/md2jsonml.py` 算好的目标块顺序与写入后的钉钉块顺序一一映射，拿到每个目标块对应的 blockId；文本只做错位校验，不做主定位。
  4. 按目标块的 ind/list 属性，**分批** `update_document_block`（每条消息并行 ~10 个小请求，每个块 jsonml 都很小、不会断；约每 10 块一批）。标题块同时补 `list` 编号。
  - **禁止仅靠文本唯一性匹配 blockId**。真实文档里"领取/确认/配置/开放条件/关闭按钮"等重复文本很多，文本只能辅助校验；若目标块数量、顺序或关键文本明显对不上，停止批量补写，改用小批量重写或人工确认。
- **偶发单块 `HSF TimeOut(3000ms)`**：不一定真失败，`list_document_blocks` 核实该块是否已更新，未更新再重发。

## 四、补表格（markdown 管道，不炸）

**占位字符（v2 起统一）**：md2jsonml.py 现在生成 `〚TBL-N〛` / `〚IMG-N〛`（生僻中文标点，不会被钉钉 markdown 误识为强调/分隔），且占位段**前后强制空行**，避免与上一段列表/正文合并到同一 block。旧文档残留的 `__TABLE_n__` 经钉钉 markdown 解析会变成 `TABLE_n`（下划线被吃掉）；处理旧文档时记得识别两种形态。

**空方括号安全编码（硬性）**：钉钉 Markdown 会把表格单元格中的 `ext[]`、`int[]`、`string[]` 或独立 `[]` 误解析成待办项，当前表会从该行开始截断，剩余内容散成 task/paragraph。`md2jsonml.py` 生成 table sidecar 时会把空方括号编码为 `\[\]`，钉钉生成的表格单元格仍显示 `[]`；本地正式 md 始终保留干净原文。不要使用 `&#91;&#93;`，钉钉会把实体原样显示在单元格中。若源单元格写的是 `` `[]` ``，converter 会仅在 sidecar 中去掉这对反引号后再发送 `\[\]`，否则钉钉会把反斜杠显示出来；最终文本仍为 `[]`，但该空数组示例不保留行内代码底色。

- 补表必须直接使用 converter 生成的 tables sidecar，不得重新从源 md 复制表格，也不得把实体改回 `[]`。
- 只编码空方括号 token；普通 Markdown 链接 `[文字](URL)` 保持不变。
- 绕过 converter 的临时操作也必须在发送前执行等价转换，但不得反写本地 SSOT。

对每个占位段：
1. `list_document_blocks` 找到占位段 blockId 与其全局 `index`；
2. 用 **markdown 管道表格** `update_document(append, index=占位index+1)` 把表插到占位段**之后**，或 `insert_document_block` 写在占位段前/后；
   - **`update_document` 的 `index=N` 语义 = 插到「第 N 个 block 之前」**（实测）。要插到占位段后面就传 `占位段index + 1`。
   - **从后往前补**：每补一张表，其后所有块 index 会 +1。按文档**倒序**（最后一张表先补）处理，前面块的 index 不受影响，避免逐张重新定位。
3. **删除占位段**——占位文字会**原样渲染成可见文本**，必须清除：
   - 占位独占一个 paragraph 块时：`delete_document_block` 整块删。
   - 占位**黏在正文段尾/中间**时（旧版 md2jsonml 占位前后无空行，钉钉 markdown 把占位与相邻正文并进同一块）：不能整块删，用 `update_document_block` 改写该块文本、去掉占位字样。v2 生成的文档中此情况不应再出现。

**自动出补表计划（推荐）**：批量场景（数十张表）用 `scripts/dingtalk_table_inserter.py`：
```bash
# 1) 把 list_document_blocks 输出存到 blocks.json
# 2) 让脚本算出 anchor 倒序 + 同 anchor 内 table_idx DESC 的执行计划
python scripts/dingtalk_table_inserter.py \
  --blocks blocks.json \
  --tables output/dingtalk-sync/<doc>.jsonml.tables.json \
  --node-id <node_id> \
  --out plan.json
# 3) 按 plan.ops 顺序执行 append_table → update_block/delete_block；
#    同一 anchor 的多张表必须串行（钉钉服务端按到达顺序应用），不同 anchor 可 ~8 并行
# 旧文档（占位是 TABLE_）传 --marker TABLE_
```
脚本只生成计划、不调 MCP；agent 按计划顺次执行，避免人工算 index。

**markdown 管道表格一定渲染成真 table**（变更记录表、KEY 表均如此）。但有以下大表症状需注意：

### 大表渲染散开（已知症状）

钉钉 markdown 解析对超大或含特殊字符的表会**逐行拆段**，结果不是单个 `table` 块、而是若干 `paragraph` 块（每行甚至每两个 `|` 一段）。已观察的触发条件（任一即可）：
- **行数 ≥ ~30**：典型如玩法常量大表。
- **单元格内含连续下划线标识符**（如 `ActvSoccer_bet_constraint_return_rate`）：底层 markdown parser 把 `_..._` 当 emphasis 解析失败、降级。
- **单元格内含空方括号 `[]`**：可能被识别为 task list；常见于 `ext[]`、`int[]`、`string[]` 与空数组示例。必须使用 converter 生成的 `\[\]` 传输编码，单纯拆表不能消除该触发条件。
- **行长过长**：单行总字符数 > ~200 时观察到散开。

**规避方案**：
1. **拆表（推荐）**：超大常量表拆成"表头说明 + 多组小表"（按业务维度分组，每组 ≤ 20 行）。源 md 维护多张小表，钉钉同步后视觉一致。
2. **改走 jsonml `table` 块**：理论可行（带 `cellAttrs` 规避 columns 降级），但纯文字表很容易被降级，工作量大、不推荐作为常规路径。
3. **接受散开**：如果只是常量表给程序读取、人不需要逐项浏览，散开不影响功能；下次大批量重构时再拆表。


## 五、补界面图

**本地化参数保护**：已实测钉钉会吞掉表格单元格末尾的 `{0}`，反斜杠转义也不能保护。`md2jsonml.py` 在 tables sidecar 内用行内代码保护数字参数（已有行内代码不重复包装），远端仍显示原始 `{0}`；本地正式 md 不改。回读须逐个比较参数，不能只验证行列数。

按 images sidecar 中的 `__IMG_n__` 占位段插图：
1. `list_document_blocks` 找到占位段 blockId；
2. 用 `insert_document_block`（jsonml）在占位段后插左图右文表（左 `tc` `fill:#E8F2FE` 放 `img`、右 `tc` `fill:#FFFAE5` 放编号说明）；
3. 删除占位段。

图带 `resourceUrl`，所以是 table、不炸 columns。图表块结构与上传链路见 [`ui-annotation-reference.md`](ui-annotation-reference.md)。

## 五之二、补标题自动编号（markdown 路径必做）

走 markdown 路径写入后，**所有标题都是"光的"——没有 `1.` `1.1` 自动编号**。需逐个标题块用 `update_document_block(format="jsonml")` 补 `list` 属性（element/markdown 格式的 heading 不含 list 字段，只能 jsonml）：

- 全文同一 `listId`（如 `worldcup-h`）才能连续编号；`autoLevel:true`、`listStyleType:"DEC_DEC_DEC_P"`。
- 按层级套模板：**H1** `level:0`/`text:"%1"`/`ind.left:0`/`sz:21`；**H2** `level:1`/`text:"%1.%2"`/`ind.left:32`/`sz:18`；**H3** `level:2`/`text:"%1.%2.%3"`/`ind.left:64`/`sz:16`。

H1 模板（H2/H3 改 level、text、ind.left、sz 即可）：
```json
["h1",{"ind":{"hanging":0,"left":0},"list":{"listId":"<doc>-h","level":0,"isOrdered":true,"autoLevel":true,"listStyleType":"DEC_DEC_DEC_P","symbolStyle":{"sz":21,"bold":true},"listStyle":{"format":"decimal","text":"%1","align":"left"}}},["span",{"data-type":"text"},["span",{"data-type":"leaf"},"标题文本"]]]
```

`list_document_blocks(blockType="heading")` 一次取全部标题及 blockId，可并行分批补（标题块互不依赖，编号由 autoLevel 自动算，删改其一不影响其余编号连续性）。

## 六、注意事项

1. 写入前先 `get_document_info` 确认目标文档（除非新建）。
2. 新建用 `create_document`；整稿替换用上面的写入流程。内容源始终是本地正式 md。
3. **纯文字表绝不能走 jsonml**（必炸 columns）；只能 markdown 管道。带 `img` 的图文表走 jsonml 不炸。
4. **加粗与红字**：源 md 只使用 `**加粗**` 与 `{{red:红字}}`；不要用 markdown 的 `<span style>`、代码块、链接、删除线等未支持格式。
5. **回读结构验收**（写入后必做，禁止只比较 table 块数量）：
   - 标题有 `list`，正文 `ind.left ≠ 0`；
   - 每张源表按顺序核对标题、列数和数据行数，远端必须逐表相等；
   - 表格必须是 `table`，不能是 `columns`，也不能只保留表头或前几行；
   - 全文不得出现由表格散开产生的 task list，表外 paragraph 不得残留以 `|` 开头/结尾的表格行；
   - fenced code 的内容以 JSONML `code.attrs.code` 为准；钉钉 Markdown 导出可能只返回空围栏，禁止据此判定线上代码为空或把空内容反写本地；
   - 任一项不符都视为同步失败，修正编码或拆表后重新写入并完整回读。
6. 终端中文乱码属正常（GBK），写进文档的内容是对的。
7. **block id 在编辑后会变动（重要）**：每次 `update_document` overwrite / 补表 / 补编号等写操作后，受影响范围的 blockId **可能全部重新分配**（前缀都变）。后果：
   - 上一次 `list_document_blocks` 拿到的 id **可能失效**（删/改时报 `invalidRequest.resource.notFound … expected to be found`）。
   - **每批增删改前重新 `list_document_blocks` 取最新 id**；批量删除时**一次只删少量、删完重新拉取**，不要拿一份旧清单连删一长串。
   - 经验：纯 `paragraph` 块的 id 相对稳定，`heading` 块在补编号/删除后最易换 id。失效就重新列、重新删。
8. **blockquote 不支持 `update_document_block`**（报 `unsupported type blockquote`）。要改引用块内容，只能用 `paragraph` 类型替换它（丢引用样式但保内容），或删后重插。

## 七、钉钉 → 本地 反转义(双向同步必做)

钉钉 `get_document_content(format=markdown)` 返回的字符串走 GFM 严格转义（`\+`、`\*\*x\*\*`、`\{` `\}`、`\[` `\]`、`&#91;` `&#93;` 等），**直接写到本地 md 会出现满屏反斜杠或 markdown 失效**。统一用 `scripts/dingtalk_md_unescape.py` 清洗：

```bash
# 一行清洗:把 dingtalk-raw.md 反转义后写到 output/<name>.md
python scripts/dingtalk_md_unescape.py dingtalk-raw.md -o "output/2026世界杯主题活动.md"

# 校验本地 md 没有残留转义(CI/pre-commit 用)
python scripts/dingtalk_md_unescape.py --check "output/<name>.md"
```

反向(本地 → 钉钉)**不要在本地 SSOT 手工加 `\\+` `\\*\\*` 等 GFM 转义**，本地写干净 markdown 即可，钉钉 `update_document` / `insert_document_block` 接 markdown 时会自动转义；**只需保证 `markdown` 参数里换行是真实 `\n`(U+000A)**，不能是字面字符串 `\n`(反斜杠+字母 n)，否则全部塞到一行。表格 sidecar 对 `[]` 的 `\[\]` 编码属于 converter 的传输层安全处理，不属于本地 SSOT 手工转义，必须保留。

详细规则与全部转义对照见 memory/dingtalk-md-escape-diff.md。

## 八、导入本地表格生成钉钉表格（无 spreadsheet MCP 时的正确做法）

某些环境没有 `get_all_sheets`/`get_range`/`update_spreadsheet_range` 这类读写钉钉表格（axls）单元格的 MCP 工具——对 axls 节点调用 `get_document_content`/`download_file`/`submit_export_job` 都会报错并提示"改用 get_spreadsheet_range 等表格相关 MCP Tool"，但那些工具在这类环境里并不存在，不是记错名字。**这不代表交付不了钉钉表格**：真正可行的路径是"本地生成 + 导入"，不是"远程读写"。

1. 本地用 openpyxl（或对应专用 Skill 自带的生成脚本，如 `vendor/skills/bi-log-requirements/scripts/gen_bi_requirements_excel.py`）生成 `.xlsx`。
2. `create_import_session(fileName, suffix="xlsx", fileSize, targetFolderId=<挂载位置的 nodeId>)`，拿到 `uploadUrl`、`sessionId`。
3. HTTP PUT 上传文件二进制到 `uploadUrl`：

   ```bash
   curl -X PUT -H "Content-Type:" --data-binary @本地文件.xlsx "<uploadUrl>"
   ```

   **必须显式传空 `Content-Type`**（`get_file_upload_info` 的工具说明写明了这条："Content-Type 必须设置为空字符串"，`create_import_session` 的 `uploadUrl` 同样适用）。不传时 curl 对 `--data-binary` 默认用 `application/x-www-form-urlencoded`，会导致 OSS 返回 `SignatureDoesNotMatch`——服务端签名时是按空 Content-Type 算的。确认返回 HTTP 200 再往下走。
4. `confirm_import(sessionId)` 拿到 `taskId`；`query_import_task(taskId)` 轮询到 `status:"completed"`，返回新建节点的 `documentUrl`（32 位 nodeId 在其中）。
5. `rename_document` 把节点名从默认的 `文件名.xlsx` 改成不带后缀的名字，对齐同级派生子节点的命名风格（如"BI日志需求"）。

**覆盖更新的坑**：`get_file_upload_info(overwriteNodeId=<已存在的 axls 节点>)` 对着一个由「导入」生成的 ALIDOC 原生表格节点会稳定返回 `internalError`（不是偶发超时，重试仍一样）——这条覆盖上传路径大概率只认"直接上传产生的原始文件节点"，认不了"导入转换后的在线表格"。**需要更新内容时不要走 overwrite**，改为：`delete_document` 删旧节点（进回收站，30 天内可恢复，不是永久删除）→ 按上面 1-5 步重新导入一份。新节点会有新的 nodeId/URL，必须同步更新主案「派生文档说明」等处引用的链接。

如果同一挂载位置下已有旧版本产物（例如之前生成的 adoc 版），确认新 axls 内容核对无误后可以 `delete_document` 旧节点，避免同名两份混着看；这一步同样是可恢复的软删除。
