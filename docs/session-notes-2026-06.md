# 会话经验记录（mindtodoc 文档生成 · 2026-06）

本文件记录使用 mindtodoc 技能生成《2026世界杯主题活动开发文档》过程中的关键经验，供后续会话参考。

## ⚠️ 环境注意：工具调用"中断"的真相（最重要）

本环境（Windows + 跨境访问）下频繁出现"看似中断"，根因有两层：

1. **会话层（主因）**：命令**已执行成功，但结果在回传途中 API socket 断开**。表现为命令像没跑/失败，实际已生效。`git commit`、`git push`、文件 Write 都中过招——实际都成功了，只是没收到回执。
2. **网络层**：GitHub 跨境 + Windows schannel 后端偶发 `SSL handshake failed` / `socket closed`，重试即可。

**对策（务必遵守）**：
- 对**有副作用或网络**的操作，执行后**先查状态确认结果，再决定是否重试**——绝不盲目重跑，否则可能重复提交/推送。
- 网络命令用 `timeout N` 包裹 + 失败重试 N 次，避免单次抖动卡死。
- 写文件后用 `grep`/`ls` 校验是否真的落盘，再继续下一步。
- 一轮**只发一个有副作用的工具调用**，等结果返回再发下一个；不要一次批量发 Write+Edit+多个调用（整批易随连接断开而丢失）。

## git push 的"假失败"模式

- push 报 `remote rejected: cannot lock ref ... expected <old>` 往往是**上一次 push 其实成功了**，本地 fetch 缓存过期所致。
- 排查顺序：`git ls-remote <url> refs/heads/main` 直查远程真实位置 → 对比本地 HEAD → 一致则说明已推送成功，只需 `git fetch` 更新本地跟踪缓存。

## 安全

- **不要把 token/密钥贴进对话**。本次贴了两个 GitHub token（应 Revoke）。push 用临时内联 URL，避免写入 `.git/config`；若误用 `git push -u` 把含 token 的 URL 写进 upstream，需 `git config --unset branch.main.remote/merge` 后用干净 origin 重设。

## mindtodoc 实践经验

- 输入 xmind 是 zip 包：`unzip -p x.xmind content.json` 取脑图树。
- 流程有效：逐系统深入（一次一个系统，规则→流程图→原型→数据表→用户确认）；澄清提问一次问一个或一组、避免疲劳。
- 降级实际触发：未装 mermaid 技能 → 手写 Mermaid；shadcn 是 React 组件库无法独立预览 → 手写 HTML+Tailwind 原型。均按 SKILL.md 降级规则标注。
- 数值缺口统一收进 Checklist 的 TODO 清单，文档内留字段+标注，不擅自编造。
- 后期发现的口径冲突（如 S5 排名 vs S8 赛季独立排名）在收尾阶段回头校准，保持跨系统一致。
