# World Cup Level Tag Tool

关卡 Tag 配置工具用于读取 `LevelTagCfg.xlsx`,在主生成器的 tier 默认关卡数据上按单关 tag 做 patch,只输出关卡 tag 会直接改动或追加虚拟行的 2 张配置表:

- `ActvSoccerLevelCfg`
- `ActvSoccerSliceInstanceCfg`

基础模板、AI 定义、modifier 定义、球队与赛季表均由主配置生成器 `generate_activity_soccer_test_config.py` 产出；改关卡 tag 时不会在 `ActivitySoccer.LevelTagged.xlsx` 中重写这些表。

## Setup

```bash
python3 -m pip install -r requirements-dev.txt
```

## Generate

```bash
python3 output/test-config/level-tags/apply_level_tags.py
```

默认输入:

- `output/test-config/level-tags/LevelTagCfg.xlsx`

默认输出:

- `output/test-config/level-tags/ActivitySoccer.LevelTagged.xlsx`
- `output/test-config/level-tags/level-tag-summary.json`

## Verify

```bash
python3 -m pytest output/test-config/level-tags/tests -q
python3 scripts/check_protocol_drift.py
python3 scripts/check_preset_consistency.py
python3 scripts/check_xlsx_drift.py --summary
```

如果本机没有 `python` 命令,使用 `python3`。工具依赖 `openpyxl`;测试依赖 `pytest`。
