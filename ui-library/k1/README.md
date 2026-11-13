# K1 常用界面图层库

从 K1 客户端 prefab 导出的常用界面，供交互预演直接使用。

- **图层只放本机**：图层是项目美术资源，不进仓库。仓库里只有导出规格 `spec.json`。
- **每台设备先获取一次**：需要本机有客户端工程、已打开的 Unity 编辑器和 UnityMCP。
  1. `python scripts/ui_library.py status ui-library/k1`：查看本机是否已获取、是否过期。
  2. `python scripts/ui_library.py prepare ui-library/k1`：生成导出代码，按提示交给 Unity 执行。
  3. `python scripts/ui_library.py finish ui-library/k1 --client <客户端仓库路径>`：核对、记录来源、生成清单。
- **获取后**：图层在 `layers/`，带缩略图的清单在 `layers/README.md`。
- **使用**：`python scripts/build_preview_ui.py ui-library/k1/layers/msgbox_two.json <其他来源> output/<功能名>-交互预演.html`，流程里用 `c.layer(图层名, {slots, acts})`。
- **过期**：改了 `spec.json` 或客户端界面改版后重新获取。`status` 会提示规格变动，客户端改版要自己留意。

## 收录范围

| 类别 | 图层 |
|---|---|
| 通用确认弹窗 | `msgbox_two`（蓝+金）、`msgbox_two_red_green`（红+绿）、`msgbox_one`（单金按钮） |
| 文字类弹窗 | `text_pop`、`scroll_text_pop`、`cost_confirm` |
| 奖励类 | `reward_get`（恭喜获得）、`reward_pop`（奖励列表） |
| 道具类 | `use_item`、`buy_item` |
| 面板与入口 | `troop`（出征面板）、`hud_menu`（主界面底部导航） |
| 整屏界面 | `screen_task`、`screen_rank`、`screen_mail`、`screen_chat`、`screen_alliance`、`screen_player`、`screen_hero_list` |

## 使用须知

- 弹窗的标题、正文、按钮字是文字槽，由网页填写。字体是系统字体，和游戏内略有差别。
- `screen_*` 的内容是 prefab 自带的占位数据，只表达布局和入口位置，不代表真实运行状态。
- 通用确认弹窗用哪组按钮，以界面脚本里的取值为准。
- 含项目美术资源的预演网页只在内部传阅。
