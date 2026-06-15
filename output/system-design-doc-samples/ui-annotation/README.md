# 界面标注素材目录

本目录存放 **界面标注派生文档** 的原始截图与标注产物。

## 目录约定

```
ui-annotation/
  assets/
    {界面ID}.png              # 用户提供的原图
    {界面ID}_annotated.png    # 红圈编号标注图（审核通过后）
    {界面ID}_annotated.json   # 识图要素与坐标（0–1000 归一化）
```

## 界面 ID 列表

见上级文档 `2026世界杯主题活动-界面标注.md` → **子界面清单与进度**。

## 流程

1. 用户将截图放入 `assets/`（或由 agent 从对话保存）。
2. 按 `system-design-doc` → `ui-annotation-reference.md` 生成 `_annotated` 文件。
3. 用户审核标注图。
4. 写入 `2026世界杯主题活动-界面标注.md` 并同步钉钉。

未审核通过的标注图不要上传钉钉。
