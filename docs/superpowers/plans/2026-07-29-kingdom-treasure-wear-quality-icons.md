# Kingdom Treasure Wear Quality Icons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成“完美、稀有、常见、高磨损”四档王国秘宝磨损度品质图标、透明正式资源和横排评审预览图。

**Architecture:** 先生成一张统一轮廓的“完美”母版，再以母版为编辑目标派生其他三档，保证构图一致。所有源图使用纯绿色键控背景，之后通过标准去背工具生成透明 PNG，再用 Sharp 统一为 512×512，并制作不进入客户端的评审预览图。

**Tech Stack:** 内置 `image_gen`、`view_image`、`remove_chroma_key.py`、Node.js 及 Sharp。

## Global Constraints

- 四档统一为圆形古代宝藏印章，中心使用抽象圣甲虫与宝石符号。
- 正式资源为 512×512 透明 PNG，不包含文字、数字、水印、方形底板或大面积外发光。
- 四档构图、视角、外轮廓尺寸、主体安全边距和光照方向必须一致。
- 完美=金色与象牙白；稀有=紫色与金边；常见=蓝色与青铜边；高磨损=灰褐色与暗红点缀。
- 在 64×64 像素显示尺寸下仍能根据颜色与破损程度区分四档。
- 不修改 `C:\Project\K1Client`、`C:\Project\K1Game`、`C:\Project\K1Dataconfig` 和 `E:\art_k1` 中的现有文件。

---

### Task 1: 生成完美品质母版

**Files:**
- Create: `output/K1/王国秘宝磨损度品质图标/source/perfect_chroma.png`
- Reference: `E:/art_k1/UI/H_活动/W-王国秘宝图鉴/王国秘宝_图鉴_蓝色图鉴弹窗.png`
- Reference: `E:/art_k1/UI/H_活动/W-王国秘宝图鉴/王国秘宝_图鉴_解锁图鉴.png`

**Interfaces:**
- Consumes: 王国秘宝弹窗截图，仅作为美术风格参考。
- Produces: 后续三档派生时使用的统一母版 `perfect_chroma.png`。

- [ ] **Step 1: 创建输出目录**

使用 PowerShell 创建以下目录，不删除已有内容：

```powershell
New-Item -ItemType Directory -Force -Path `
  'C:\Project\MindToDoc\output\K1\王国秘宝磨损度品质图标\source', `
  'C:\Project\MindToDoc\output\K1\王国秘宝磨损度品质图标\final', `
  'C:\Project\MindToDoc\output\K1\王国秘宝磨损度品质图标\review'
```

- [ ] **Step 2: 使用内置 image_gen 生成母版**

使用上述两张截图作为“风格参考图”，不是编辑目标。执行一次生成，使用以下完整提示词：

```text
Use case: logo-brand
Asset type: square mobile-game quality badge icon
Primary request: create the PERFECT preservation-quality icon for the Kingdom Treasure activity.
Input images: the Kingdom Treasure popup screenshots are style references only.
Subject: one centered circular ancient treasure seal, with an abstract scarab and faceted gemstone emblem in the center.
Style/medium: polished stylized 3D cartoon mobile-game UI icon, chunky beveled shapes, crisp readable silhouette, matching the supplied Kingdom Treasure UI.
Color palette: premium gold and ivory-white, restrained cyan-white highlights.
Materials/textures: pristine polished metal and enamel, completely intact edges, clean surface, three small star glints.
Composition/framing: front-facing, perfectly centered, square composition, generous even padding, no perspective tilt.
Scene/backdrop: perfectly flat solid #00ff00 chroma-key background, one uniform color with no shadow, gradient, texture, reflection, floor plane, or lighting variation.
Constraints: no text, no letters, no numbers, no watermark, no square backing plate, no cast shadow, no contact shadow, no reflection outside the badge; do not use #00ff00 in the badge; keep the whole badge separated from the background with crisp edges.
Avoid: treasure chest, crown, shield, character portrait, realistic archaeology, thin fragile details.
```

- [ ] **Step 3: 保存并检查母版**

将生成结果复制为 `source/perfect_chroma.png`，保留默认生成目录中的原文件。用 `view_image` 检查：圆形轮廓、中心圣甲虫与宝石、三处闪光、绿色背景均符合提示词，且不存在文字和方形底板。

- [ ] **Step 4: 提交阶段结果**

```powershell
git add -- 'output/K1/王国秘宝磨损度品质图标/source/perfect_chroma.png'
git commit -m "art: generate perfect wear quality badge source"
```

### Task 2: 派生稀有、常见和高磨损品质

**Files:**
- Create: `output/K1/王国秘宝磨损度品质图标/source/rare_chroma.png`
- Create: `output/K1/王国秘宝磨损度品质图标/source/common_chroma.png`
- Create: `output/K1/王国秘宝磨损度品质图标/source/high_wear_chroma.png`
- Reference: `output/K1/王国秘宝磨损度品质图标/source/perfect_chroma.png`

**Interfaces:**
- Consumes: Task 1 的完美品质母版。
- Produces: 与母版轮廓一致的三个键控背景源图。

- [ ] **Step 1: 生成稀有品质**

先用 `view_image` 打开母版，再将其作为编辑目标执行一次 `image_gen`：

```text
Use case: precise-object-edit
Asset type: square mobile-game quality badge icon
Primary request: transform the PERFECT badge into the RARE preservation-quality badge.
Preserve exactly: circular silhouette, scarab-and-gem emblem, camera, scale, padding, lighting direction, and flat #00ff00 background.
Change only: enamel becomes saturated royal purple with a gold rim; add very light patina and one tiny edge scuff; keep one small star glint; edges remain almost fully intact.
Constraints: no text, letters, numbers, watermark, square backing plate, cast shadow, contact shadow, or background variation; do not use #00ff00 in the badge.
```

保存为 `source/rare_chroma.png`。

- [ ] **Step 2: 生成常见品质**

继续以完美母版为编辑目标，不以稀有图标作二次母版：

```text
Use case: precise-object-edit
Asset type: square mobile-game quality badge icon
Primary request: transform the PERFECT badge into the COMMON preservation-quality badge.
Preserve exactly: circular silhouette, scarab-and-gem emblem, camera, scale, padding, lighting direction, and flat #00ff00 background.
Change only: enamel becomes deep blue with a bronze rim; reduce surface gloss; add several clearly readable fine scratches and mild patina; remove all star glints; keep the outer edge structurally intact.
Constraints: no text, letters, numbers, watermark, square backing plate, cast shadow, contact shadow, or background variation; do not use #00ff00 in the badge.
```

保存为 `source/common_chroma.png`。

- [ ] **Step 3: 生成高磨损品质**

继续以完美母版为编辑目标：

```text
Use case: precise-object-edit
Asset type: square mobile-game quality badge icon
Primary request: transform the PERFECT badge into the HIGH WEAR preservation-quality badge.
Preserve exactly: circular silhouette, scarab-and-gem emblem, camera, scale, padding, lighting direction, and flat #00ff00 background.
Change only: materials become muted gray-brown oxidized metal with restrained dark-red accents; add two bold readable cracks, several scratches, chipped outer edges, and visible patina; no star glints; the badge must remain recognizable and mostly contained within the original silhouette.
Constraints: no text, letters, numbers, watermark, square backing plate, cast shadow, contact shadow, dust outside the silhouette, or background variation; do not use #00ff00 in the badge.
```

保存为 `source/high_wear_chroma.png`。

- [ ] **Step 4: 检查四档一致性**

依次用 `view_image` 查看四张源图。若任意派生图的轮廓、中心符号、缩放或视角偏离母版，只针对该问题重新编辑一次；不得同时更换配色方案或中心符号。

- [ ] **Step 5: 提交阶段结果**

```powershell
git add -- 'output/K1/王国秘宝磨损度品质图标/source/rare_chroma.png' `
  'output/K1/王国秘宝磨损度品质图标/source/common_chroma.png' `
  'output/K1/王国秘宝磨损度品质图标/source/high_wear_chroma.png'
git commit -m "art: generate wear quality badge variants"
```

### Task 3: 去除键控背景并生成正式资源

**Files:**
- Create: `output/K1/王国秘宝磨损度品质图标/final/UI_Activity_KingdomTreasure_Wear_Quality_01.png`
- Create: `output/K1/王国秘宝磨损度品质图标/final/UI_Activity_KingdomTreasure_Wear_Quality_02.png`
- Create: `output/K1/王国秘宝磨损度品质图标/final/UI_Activity_KingdomTreasure_Wear_Quality_03.png`
- Create: `output/K1/王国秘宝磨损度品质图标/final/UI_Activity_KingdomTreasure_Wear_Quality_04.png`

**Interfaces:**
- Consumes: Task 1–2 的四张绿色键控源图。
- Produces: 客户端可使用的四张 512×512 透明 PNG。

- [ ] **Step 1: 运行标准去背工具**

使用工作区 Python 逐张执行标准去背工具：

```powershell
$taskPython = 'C:\Users\jiangzhenyu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$removeKey = 'C:\Users\jiangzhenyu\.codex\skills\.system\imagegen\scripts\remove_chroma_key.py'
$sourceDir = 'C:\Project\MindToDoc\output\K1\王国秘宝磨损度品质图标\source'
$finalDir = 'C:\Project\MindToDoc\output\K1\王国秘宝磨损度品质图标\final'

& $taskPython $removeKey --input "$sourceDir\perfect_chroma.png" --out "$finalDir\perfect_transparent.png" --auto-key border --soft-matte --transparent-threshold 12 --opaque-threshold 220 --despill
& $taskPython $removeKey --input "$sourceDir\rare_chroma.png" --out "$finalDir\rare_transparent.png" --auto-key border --soft-matte --transparent-threshold 12 --opaque-threshold 220 --despill
& $taskPython $removeKey --input "$sourceDir\common_chroma.png" --out "$finalDir\common_transparent.png" --auto-key border --soft-matte --transparent-threshold 12 --opaque-threshold 220 --despill
& $taskPython $removeKey --input "$sourceDir\high_wear_chroma.png" --out "$finalDir\high_wear_transparent.png" --auto-key border --soft-matte --transparent-threshold 12 --opaque-threshold 220 --despill
```

- [ ] **Step 2: 用 Sharp 统一为 512×512**

使用工作区依赖中的 Node.js 和 Sharp，将四张临时透明图按 `contain` 方式缩放到 512×512，保持透明背景并写入正式文件名：

```powershell
$taskNode = 'C:\Users\jiangzhenyu\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$env:NODE_PATH = 'C:\Users\jiangzhenyu\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
$resizeCode = @'
const path = require('path');
const sharp = require('sharp');
const dir = 'C:/Project/MindToDoc/output/K1/王国秘宝磨损度品质图标/final';
const files = [
  ['perfect_transparent.png', 'UI_Activity_KingdomTreasure_Wear_Quality_01.png'],
  ['rare_transparent.png', 'UI_Activity_KingdomTreasure_Wear_Quality_02.png'],
  ['common_transparent.png', 'UI_Activity_KingdomTreasure_Wear_Quality_03.png'],
  ['high_wear_transparent.png', 'UI_Activity_KingdomTreasure_Wear_Quality_04.png'],
];
(async () => {
  for (const [input, output] of files) {
    await sharp(path.join(dir, input))
      .resize(512, 512, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
      .png()
      .toFile(path.join(dir, output));
  }
})().catch(error => { console.error(error); process.exit(1); });
'@
& $taskNode -e $resizeCode
```

- [ ] **Step 3: 验证透明通道与尺寸**

对四张正式资源读取 Sharp metadata 和四角像素；任一断言失败时进程以非零状态退出：

```powershell
$validateCode = @'
const path = require('path');
const sharp = require('sharp');
const dir = 'C:/Project/MindToDoc/output/K1/王国秘宝磨损度品质图标/final';
const files = [1, 2, 3, 4].map(n => `UI_Activity_KingdomTreasure_Wear_Quality_0${n}.png`);
(async () => {
  for (const file of files) {
    const source = sharp(path.join(dir, file));
    const meta = await source.metadata();
    if (meta.width !== 512 || meta.height !== 512 || meta.channels !== 4 || !meta.hasAlpha) {
      throw new Error(`${file}: invalid metadata ${JSON.stringify(meta)}`);
    }
    for (const [left, top] of [[0,0], [511,0], [0,511], [511,511]]) {
      const pixel = await sharp(path.join(dir, file)).extract({ left, top, width: 1, height: 1 }).raw().toBuffer();
      if (pixel[3] !== 0) throw new Error(`${file}: corner alpha is ${pixel[3]}`);
    }
  }
  console.log('validated 4 transparent 512x512 icons');
})().catch(error => { console.error(error); process.exit(1); });
'@
& $taskNode -e $validateCode
```

若失败，针对对应源图重新执行 Step 1 并额外加入 `--edge-contract 1`，随后重新执行 Step 2–3；不得手工擦除边缘。

- [ ] **Step 4: 提交正式资源**

```powershell
git add -- 'output/K1/王国秘宝磨损度品质图标/final/UI_Activity_KingdomTreasure_Wear_Quality_01.png' `
  'output/K1/王国秘宝磨损度品质图标/final/UI_Activity_KingdomTreasure_Wear_Quality_02.png' `
  'output/K1/王国秘宝磨损度品质图标/final/UI_Activity_KingdomTreasure_Wear_Quality_03.png' `
  'output/K1/王国秘宝磨损度品质图标/final/UI_Activity_KingdomTreasure_Wear_Quality_04.png'
git commit -m "art: add transparent wear quality badges"
```

### Task 4: 制作评审预览并完成视觉验收

**Files:**
- Create: `output/K1/王国秘宝磨损度品质图标/review/王国秘宝_磨损度品质图标_四档预览.png`
- Create: `output/K1/王国秘宝磨损度品质图标/review/王国秘宝_磨损度品质图标_64px预览.png`

**Interfaces:**
- Consumes: Task 3 的四张正式透明图标。
- Produces: 全尺寸横排评审图和 64×64 实际识别度评审图。

- [ ] **Step 1: 使用 Sharp 制作横排预览**

执行以下脚本创建 1600×520 横排评审图；标题文字仅存在于评审图，禁止回写正式图标：

```powershell
$taskNode = 'C:\Users\jiangzhenyu\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$env:NODE_PATH = 'C:\Users\jiangzhenyu\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
$previewCode = @'
const path = require('path');
const sharp = require('sharp');
const root = 'C:/Project/MindToDoc/output/K1/王国秘宝磨损度品质图标';
const icons = [1, 2, 3, 4].map(n => path.join(root, 'final', `UI_Activity_KingdomTreasure_Wear_Quality_0${n}.png`));
const xs = [70, 450, 830, 1210];
const labels = [
  ['完美', '0%–5%'],
  ['稀有', '6%–20%'],
  ['常见', '21%–70%'],
  ['高磨损', '71%–100%'],
];
(async () => {
  const background = Buffer.from(`<svg width="1600" height="520" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#18385e"/><stop offset="1" stop-color="#071528"/></linearGradient></defs><rect width="1600" height="520" rx="28" fill="url(#g)"/><text x="800" y="52" text-anchor="middle" fill="#ffffff" font-family="Microsoft YaHei" font-size="32" font-weight="700">王国秘宝 · 磨损度品质图标</text>${labels.map((v,i)=>`<text x="${xs[i]+150}" y="430" text-anchor="middle" fill="#ffffff" font-family="Microsoft YaHei" font-size="28" font-weight="700">${v[0]}</text><text x="${xs[i]+150}" y="470" text-anchor="middle" fill="#a9c6e8" font-family="Arial" font-size="24">${v[1]}</text>`).join('')}</svg>`);
  const composites = [{ input: background, left: 0, top: 0 }];
  for (let i = 0; i < icons.length; i++) {
    const icon = await sharp(icons[i]).resize(300, 300, { fit: 'contain' }).png().toBuffer();
    composites.push({ input: icon, left: xs[i], top: 90 });
  }
  await sharp({ create: { width: 1600, height: 520, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
    .composite(composites)
    .png()
    .toFile(path.join(root, 'review', '王国秘宝_磨损度品质图标_四档预览.png'));
})().catch(error => { console.error(error); process.exit(1); });
'@
& $taskNode -e $previewCode
```

- [ ] **Step 2: 制作 64px 识别度预览**

用以下脚本将四张正式图分别缩放到 64×64，横排放到 320×96 深蓝底图中，不加文字：

```powershell
$smallPreviewCode = @'
const path = require('path');
const sharp = require('sharp');
const root = 'C:/Project/MindToDoc/output/K1/王国秘宝磨损度品质图标';
const icons = [1, 2, 3, 4].map(n => path.join(root, 'final', `UI_Activity_KingdomTreasure_Wear_Quality_0${n}.png`));
(async () => {
  const composites = [];
  for (let i = 0; i < icons.length; i++) {
    const icon = await sharp(icons[i]).resize(64, 64, { fit: 'contain' }).png().toBuffer();
    composites.push({ input: icon, left: 24 + i * 76, top: 16 });
  }
  await sharp({ create: { width: 320, height: 96, channels: 4, background: { r: 7, g: 21, b: 40, alpha: 1 } } })
    .composite(composites)
    .png()
    .toFile(path.join(root, 'review', '王国秘宝_磨损度品质图标_64px预览.png'));
})().catch(error => { console.error(error); process.exit(1); });
'@
& $taskNode -e $smallPreviewCode
```

- [ ] **Step 3: 视觉验收**

用 `view_image` 检查两张预览图，逐项确认：四档顺序正确；轮廓一致；完美有三处闪光；稀有有一处闪光；常见无闪光且有细划痕；高磨损的裂纹与缺口在 64px 仍可识别；所有图标无绿色边缘和方形底板。

- [ ] **Step 4: 提交评审图**

```powershell
git add -- 'output/K1/王国秘宝磨损度品质图标/review/王国秘宝_磨损度品质图标_四档预览.png' `
  'output/K1/王国秘宝磨损度品质图标/review/王国秘宝_磨损度品质图标_64px预览.png'
git commit -m "art: add wear quality badge review sheets"
```

### Task 5: 最终交付检查

**Files:**
- Verify: `output/K1/王国秘宝磨损度品质图标/final/*.png`
- Verify: `output/K1/王国秘宝磨损度品质图标/review/*.png`

**Interfaces:**
- Consumes: Task 1–4 的全部产物。
- Produces: 可供用户复核并交给客户端接入的最终交付说明。

- [ ] **Step 1: 检查文件完整性**

确认正式目录仅包含四张命名正确的 512×512 透明 PNG；评审目录包含两张预览图；源目录保留四张键控源图用于返修。

- [ ] **Step 2: 检查工作区边界**

运行 `git status --short`，确认没有修改 K1 客户端、服务端、配置仓库或 `E:\art_k1` 参考目录，也没有暂存用户原有改动。

- [ ] **Step 3: 向用户交付**

在回复中展示四档横排预览图，并提供正式资源目录、四张正式文件链接、使用的最终提示词摘要，以及“内置 image_gen + 本地键控去背”的制作路径。
