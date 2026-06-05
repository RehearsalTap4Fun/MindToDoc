# 工作流：识图 → 标注 → 写钉钉文档

> 把这份文件贴给新会话即可复现整套流程。适用环境：Windows + bash(GBK 终端)+ Python 3.12(`py` 启动器)+ 钉钉 MCP 工具。

## 链路总览
```
原图 → [识图] claude-opus-4-8 视觉识别 → 元素名+归一化坐标(JSON)
     → [标注] PIL 画红色数字圆圈 → 标注图
     → [上传] 钉钉 OSS 三步上传 → resourceId
     → [写文档] insert_document_block 插入「左图右文」双列表格
```

## 环境前置
- **Read 工具看不到图像像素**，识图必须调外部视觉模型（见下）。
- **curl 在本环境联网全部返回 000**，所有 HTTP 请求统一用 Python `urllib`。
- 终端是 GBK，API 返回的 UTF-8 中文在终端显示为乱码，但写进文件/文档的内容是正确的，别被终端输出误导。
- Python：用 `py`（真 3.12），不是 `python`（WindowsApps shim）。已装 `Pillow`。

## 鉴权（视觉模型网关）
- 端点：`https://onehub.akacm.com/v1/chat/completions`（OpenAI 风格）
  - ⚠️ 不要用 `/v1/messages`（Anthropic 原生），维护期被禁，返回 `relay_disabled`。
- 模型：`claude-opus-4-8`（网关只代理 Claude，无 GPT）。
- Token：环境变量 `ANTHROPIC_AUTH_TOKEN`（本机已持久化）。
- 钉钉图片生图/编辑用的 `ART_TOKEN` 也已持久化（art-skills skill）。

## 一、识图（关键 prompt 要点）
让模型**只输出 JSON**，坐标用**归一化 0-1000**（不是像素，换任何尺寸都能用）：
```python
import os, json, base64, urllib.request, re
tk = os.environ["ANTHROPIC_AUTH_TOKEN"]
b64 = base64.b64encode(open(SRC,"rb").read()).decode()
prompt = ("这是一张手游界面截图。精确识别所有UI要素，每个返回归一化坐标(0-1000,左上原点)。"
          '只输出JSON数组：[{"id":1,"name":"要素中文名","cx":整数,"cy":整数}]，cx/cy为中心点。按从上到下编号。')
body = json.dumps({"model":"claude-opus-4-8","max_tokens":2000,
  "messages":[{"role":"user","content":[
    {"type":"text","text":prompt},
    {"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64}"}}]}]}).encode()
req = urllib.request.Request("https://onehub.akacm.com/v1/chat/completions", data=body,
    headers={"Authorization":f"Bearer {tk}","content-type":"application/json"})
txt = json.loads(urllib.request.urlopen(req,timeout=120).read())["choices"][0]["message"]["content"]
elems = json.loads(re.search(r'\[.*\]', txt, re.S).group(0))
```

## 二、标注（PIL）
```python
from PIL import Image, ImageDraw, ImageFont
img = Image.open(SRC).convert("RGB"); W,H = img.size
d = ImageDraw.Draw(img); R = 30
font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 34)  # 中文用 msyh.ttc
for e in elems:
    cx, cy = int(e["cx"]/1000*W), int(e["cy"]/1000*H)
    d.ellipse([cx-R,cy-R,cx+R,cy+R], fill=(220,0,0), outline=(255,255,255), width=3)
    t = str(e["id"]); tb = d.textbbox((0,0),t,font=font)
    d.text((cx-(tb[2]-tb[0])/2-tb[0], cy-(tb[3]-tb[1])/2-tb[1]), t, fill=(255,255,255), font=font)
img.save("marked.png")
```

## 三、上传图片到钉钉（三步，缺一不可）
1. MCP `get_doc_attachment_upload_info`(fileName, fileSize, mimeType="image/png", nodeId) → 得 `resourceId` + `uploadUrl`
2. **HTTP PUT** 图片二进制到 `uploadUrl`（Header `Content-Type: image/png`），须返回 200：
```python
data=open("marked.png","rb").read()
req=urllib.request.Request(UPLOAD_URL, data=data, method="PUT",
    headers={"Content-Type":"image/png","Content-Length":str(len(data))})
assert urllib.request.urlopen(req,timeout=120).status==200
```
3. 图片在文档里的引用 src = `/core/api/resources/img/<resourceId>`

## 四、写文档（insert_document_block + JSONML）
- 先用 `list_document_blocks(format=jsonml)` 抄一个现成样式块照搬。
- 「左图右文」= 两列 table：`colsWidth:[250,400]`，左 `tc` `fill:#E8F2FE` 放 `img`，右 `tc` `fill:#FFFAE5` 放编号说明。
- 编号：主项 `list.isOrdered:true`（`%1.`）；子说明 `level:1` + `○` bullet。
- 定位：`referenceBlockId`=末块 blockId，`where:"after"`。

JSONML 骨架：
```json
["table",{"colsWidth":[250,400],"sr":true},["tr",{},
  ["tc",{"fill":"#E8F2FE","vAlign":"top"},["p",{},["img",{"src":"/core/api/resources/img/<resourceId>","width":236,"height":512}]]],
  ["tc",{"fill":"#FFFAE5","vAlign":"top"},
    ["p",{},["span",{"data-type":"text"},["span",{"bold":true,"data-type":"leaf"},"图中编号说明"]]],
    ["p",{"list":{"listId":"x","listStyle":{"format":"decimal","text":"%1.","align":"left"},"level":0,"isOrdered":true}},["span",{"data-type":"text"},["span",{"data-type":"leaf"},"要素名"]]],
    ["p",{"list":{"listId":"x","listStyle":{"format":"bullet","text":"○","align":"left"},"level":1,"isOrdered":false}},["span",{"data-type":"text"},["span",{"data-type":"leaf"},"子说明"]]]
  ]]]
```

## 踩坑清单
1. **插入超时 `HSF TimeOut(3000ms)`** → 不一定真失败。**先 `list_document_blocks` 查文档是否已写入**，再决定是否重试，避免重复插入。
2. **`function_is_rate_limit` 限流** → `sleep 15~30` 后重试。
3. **curl 000** → 改用 Python urllib。
4. **终端中文乱码** → 正常，文件/文档内容是对的。

## 准确性边界（每次都要告知用户）
坐标与数值均来自模型视觉识别 = 估计值。圆圈位置可能偏移几十像素，界面内数值（如百分比）可能与原图有出入。**完成后让用户对照原图核对。**
