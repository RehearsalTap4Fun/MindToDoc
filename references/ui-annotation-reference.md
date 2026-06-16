# 界面识图标注落地参考（mindtodoc 随附）

把界面图落进钉钉文档的完整链路（self-contained）。环境：Windows + bash + Python 3.12（用 `py` 启动器，非 WindowsApps 的 `python`）+ 钉钉 MCP。已装 Pillow。

## 链路
原图 → 识图（**优先：运行中模型自己看图**出元素名+归一化坐标；退路：外部视觉模型）→ PIL 画红圈编号 → 钉钉三步上传 → insert「左图右文」双列表格。

## 关键约束
- **识图优先用运行中模型自己的多模态视觉**：让用户把界面图发进当前对话，直接看图产出要素名+归一化坐标，零 Bash、零外部 API。下面「一、识图」的外部视觉模型方案，仅当图无法进入当前上下文时才退回使用；发送图片到外部接口前必须获得用户明确确认。
- **curl 本环境联网返回 000**，所有 HTTP 一律用 Python `urllib`。
- 终端 GBK，API 返回的中文在终端显示乱码属正常，写进文件/文档的内容是对的。

## 一、识图
仅在用户明确确认可以把图片发送到外部视觉接口后使用本方案。端点 `https://onehub.akacm.com/v1/chat/completions`（OpenAI 风格，**勿用** `/v1/messages`），模型 `claude-opus-4-8`，token 取环境变量 `ANTHROPIC_AUTH_TOKEN`。让模型输出 JSON，坐标归一化 0-1000：
```python
import os, json, base64, urllib.request, re
tk = os.environ["ANTHROPIC_AUTH_TOKEN"]
b64 = base64.b64encode(open(SRC,"rb").read()).decode()
prompt = """这是一张手游界面截图。请先整体描述这个界面是做什么的、有哪些功能区块、玩家能进行什么操作；精确识别所有UI要素，每个返回归一化坐标(0-1000,左上原点)。输出JSON对象：{"screen_desc":"整体功能描述","elements":[{"id":1,"name":"要素中文名","text":"界面上显示的文字(无则空)","cx":<int>,"cy":<int>}]}。按从上到下编号，把界面上能看到的中文文字尽量原样填进text。"""
body = json.dumps({"model":"claude-opus-4-8","max_tokens":2000,
  "messages":[{"role":"user","content":[
    {"type":"text","text":prompt},
    {"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64}"}}]}]}).encode()
req = urllib.request.Request("https://onehub.akacm.com/v1/chat/completions", data=body,
    headers={"Authorization":f"Bearer {tk}","content-type":"application/json"})
txt = json.loads(urllib.request.urlopen(req,timeout=120).read())["choices"][0]["message"]["content"]
elems = json.loads(re.search(r'\[.*\]', txt, re.S).group(0))
```

## 归类与编号原则（标注前先归类，别平铺）
视觉模型会把每个小控件都列出来，**不要照搬一个个标号**。标注前先按语义归类，同类/同组的元素合并成一个编号，差异收进右栏的二级列表：
- **同类元素归并**：如任务图钉的不同品质（绿/蓝/紫/橙/灰）、不同类型（骷髅/武器/望远镜…），合并为 1 个「任务图钉」编号，二级分「品质」「类型」「状态」分类总结。
- **父子组归并**：如顶部资源栏（药品图标+数量+添加、资源B图标+数量），合并为 1 个「资源」编号，二级按各资源分（药品→图标/数量/添加；资源B→图标/数量），形成父子层级。
- **真正不同类的不要硬合**：如盟友头像 vs 敌人头像，性质不同，各自独立编号。
- **代表性标号**：归并后，图上该类**只在一个代表性位置画一个红圈**（不是每个同类都标），右栏在该号下用二级列表展开全部。
- 结果是编号数量大幅收敛、右栏呈父子结构，而非一长串平铺。

## 二、标注（PIL 红圈数字）
圆圈**画在组件旁边靠近处、不要压在组件正上方**（从图心向外推一段偏移，避免遮住要素本身）。

**输出与产物命名**：JSON 与标注图同步落盘，**标注图必须以源图文件名 + `_annotated` 后缀**保存（如 `home.png` → `home_annotated.png`），并把 JSON 与 `_annotated.png` 一并交给用户**先审核再继续**——编号、归类、坐标对不上时在这一步就要纠正，不要带病进入下游钉钉上传与左图右文表。

```python
from PIL import Image, ImageDraw, ImageFont
import os, json
img = Image.open(SRC).convert("RGB"); W,H = img.size
d = ImageDraw.Draw(img); R = 26; OFF = 46  # OFF=圆圈相对要素中心的偏移
font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 30)  # 中文用 msyh.ttc
for e in elems:
    cx, cy = int(e["cx"]/1000*W), int(e["cy"]/1000*H)
    dx = -1 if cx < W/2 else 1; dy = -1 if cy < H/2 else 1   # 向外推，靠近但不遮挡
    ox, oy = max(R,min(W-R,cx+dx*OFF)), max(R,min(H-R,cy+dy*OFF))
    d.ellipse([ox-R,oy-R,ox+R,oy+R], fill=(220,0,0), outline=(255,255,255), width=3)
    t = str(e["id"]); tb = d.textbbox((0,0),t,font=font)
    d.text((ox-(tb[2]-tb[0])/2-tb[0], oy-(tb[3]-tb[1])/2-tb[1]), t, fill=(255,255,255), font=font)
base, ext = os.path.splitext(SRC)
img.save(f"{base}_annotated{ext}")
json.dump(elems, open(f"{base}_annotated.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
```

## 三、上传钉钉（三步，缺一不可）
1. MCP `get_doc_attachment_upload_info`(fileName, fileSize, mimeType="image/png", nodeId) → 返回 `resourceId`、`uploadUrl`、`resourceUrl`。
2. **用户审核通过后**，HTTP PUT 上一步落盘的 `<源图>_annotated.png` 二进制到 `uploadUrl`（Header `Content-Type: image/png`），须返回 200：
```python
data=open(ANNOTATED_PNG,"rb").read()  # ANNOTATED_PNG = f"{base}_annotated{ext}"
req=urllib.request.Request(UPLOAD_URL, data=data, method="PUT",
    headers={"Content-Type":"image/png","Content-Length":str(len(data))})
assert urllib.request.urlopen(req,timeout=120).status==200
```
3. 文档内 `img` 的 src **用接口返回的完整 `resourceUrl`**（形如 `/core/api/resources/img/<长hash>`）。⚠️ **不要用 `/core/api/resources/img/<resourceId>`** —— 那样图片加载失败（实测）。resourceUrl 才是可渲染地址。

## 四、写文档：左图右文双列表格
- 先 `list_document_blocks(format=jsonml)` 抄一个现成块照搬样式。
- 两列 table：`colsWidth:[250,400]`，左 `tc` `fill:#E8F2FE` 放 `img`，右 `tc` `fill:#FFFAE5` 放编号说明。
- 编号说明：主项 `list.isOrdered:true`（`%1.`）= 要素名；子说明 `level:1` + `○` bullet = 该要素的文本key/状态/交互。与正文两级列表规则一致。
- **凡界面文案要素，子说明必须注明其本地化枚举 key**（如 `LC_EVENT_tab_home`）；新建 key 用红字、复用 key 用黑字。右栏只写 key 名，key 的中文与占位符传参在**文末统一本地化表**登记，不在右栏重复写中文。
- 新建 key 的右栏说明若在源信息中写作 `{{red:...}}`，构造左图右文表 JSONML 时必须转成 leaf 的 `"color":"#FE0300"`；不要把 `{{red:...}}` 标记原样写进钉钉。复用 key 用默认黑字。
- 定位：`referenceBlockId`=参照块 blockId，`where:"after"`。

JSONML 骨架：
```json
["table",{"colsWidth":[250,400],"sr":true},["tr",{},
  ["tc",{"fill":"#E8F2FE","vAlign":"top"},["p",{},["img",{"src":"<完整 resourceUrl，非 resourceId>","width":236,"height":512}]]],
  ["tc",{"fill":"#FFFAE5","vAlign":"top"},
    ["p",{},["span",{"data-type":"text"},["span",{"bold":true,"data-type":"leaf"},"图中编号说明"]]],
    ["p",{"list":{"listId":"x","listStyle":{"format":"decimal","text":"%1.","align":"left"},"level":0,"isOrdered":true}},["span",{"data-type":"text"},["span",{"data-type":"leaf"},"要素名"]]],
    ["p",{"list":{"listId":"x","listStyle":{"format":"bullet","text":"○","align":"left"},"level":1,"isOrdered":false}},["span",{"data-type":"text"},["span",{"data-type":"leaf"},"子说明（key+文案/状态/交互）"]]],
    ["p",{"list":{"listId":"x","listStyle":{"format":"bullet","text":"○","align":"left"},"level":1,"isOrdered":false}},["span",{"data-type":"text"},["span",{"data-type":"leaf","color":"#FE0300"},"新建 key 示例：LC_EVENT_xxx｜中文文案"]]]
  ]]]
```

## 四之二、文档末尾的本地化文本汇总表
**所有标注图写完后，在派生文档末尾写一张统一的本地化汇总表**（不再每界面各写一张），汇总本文档全部标注涉及的界面文案：每个 key 一行，复用 key 与新建 key 都列入。供整列复制录入翻译表。
- 三列固定：`枚举 KEY`、`中文`、`占位符传参说明`。
- **占位符传参说明**列：无占位符写「无」；有占位符（`{0}{1}`，从 0 起连续编号）必须写清每个参数的含义、来源与示例，多语言版本参数数量与顺序须一致。
- 新建 key（文中标红的）在中文后或单独备注标「新建」；中文文案禁单元格内回车，换行用 `\n`。
- 定位：写在文档最末（派生文档说明/末尾），表头行用 `isTblHeader:true`。

JSONML 骨架（表头 + 一行示例）：
```json
["table",{"colsWidth":[200,300,300],"sr":true,"tblLook":{"firstRow":1}},
  ["tr",{"isTblHeader":true},
    ["tc",{},["p",{},["span",{"data-type":"text"},["span",{"bold":true,"data-type":"leaf"},"枚举 KEY"]]]],
    ["tc",{},["p",{},["span",{"data-type":"text"},["span",{"bold":true,"data-type":"leaf"},"中文"]]]],
    ["tc",{},["p",{},["span",{"data-type":"text"},["span",{"bold":true,"data-type":"leaf"},"占位符传参说明"]]]]],
  ["tr",{},
    ["tc",{},["p",{},["span",{"data-type":"text"},["span",{"data-type":"leaf"},"LC_EVENT_bet_win_tip"]]]],
    ["tc",{},["p",{},["span",{"data-type":"text"},["span",{"data-type":"leaf"},"恭喜押中 {0}，获得 {1} 竞猜币"]]]],
    ["tc",{},["p",{},["span",{"data-type":"text"},["span",{"data-type":"leaf"},"{0}=晋级队伍名（来源对局结果），{1}=派彩数量（整数）"]]]]]
]
```

## 踩坑
1. 插入超时 `HSF TimeOut(3000ms)` → 不一定真失败。先 `list_document_blocks` 查是否已写入，再决定重试，避免重复插入。
2. `function_is_rate_limit` 限流 → sleep 15~30s 后重试；批量写入控制并发（约10个/批）。
3. curl 000 → 改用 Python urllib。
4. 终端中文乱码 → 正常。

## 准确性边界（每次都要告知用户）
坐标与数值均来自模型视觉识别 = 估计值。圆圈位置可能偏移几十像素，界面内数值（如百分比）可能与原图有出入。**完成后让用户对照原图核对。**
