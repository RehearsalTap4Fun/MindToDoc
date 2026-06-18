# Reviewer Spec-Grounding 补丁

> 强制 reviewer subagent **先读 spec/plan 再评判**,避免凭通用规范误判项目专有设计。
>
> 适用 skill:`superpowers:subagent-driven-development` 的 spec-reviewer 与 code-quality-reviewer 阶段。
> 用法:controller 派发 reviewer 时,把本文件「Mandatory pre-judgment ritual」段原文 inline 进 prompt。

---

## 背景

本项目里发生过的真实摩擦(2026-06-18 关卡 tag 工具 Task 3):

- code quality reviewer 用 haiku 跑,凭"通用规范"判定阈值类 patch 函数应做 `n<2` 防御。
- 实际上 plan §4.4 + §7 明确把校验放在 `validate_dataset` 生成阶段统一处理;主生成器路径 n 最小为 2;互斥组阻止双 patch 叠加。
- controller 反复 prompt 才挡下,最后用一次注释 commit(`4b1ca85`)沉淀设计意图。
- 代价:多 1 个 reviewer + 1 个 fix subagent + 1 次注释 commit,约浪费 ~20% 该 task 的 token。

根因:reviewer prompt 没要求 reviewer 在评判前 **引用 spec/plan 原文**。reviewer 直接基于 commit diff 评,看不到设计选择背后的取舍。

---

## Mandatory pre-judgment ritual(reviewer prompt 必含段)

把以下段原文加到任何 spec-reviewer 或 code-quality-reviewer 的 prompt 里(放在你给 reviewer 的 prompt 末尾、`## 报告` 之前):

```
## Mandatory pre-judgment ritual(评判前必做)

在做任何 SPEC_VIOLATIONS 或 QUALITY_ISSUES 判定之前,你必须先:

1. 读 spec 文件至少 2 个相关章节:`<spec_path>`
2. 读 plan 文件对应的 task 章节:`<plan_path>`
3. 在每条「Issues」前**引用 spec 或 plan 的具体段落作为支撑**(章节号 + 简短引用),例如:
     - "Critical: X 函数应防御 Y。Spec §4.3 写「...」,plan Task 5 的 patch 函数预期...,因此..."

凡引用不到原文支撑的「建议」,请:
- 降级为 `Minor` / `Nit` 级别,或
- 完全不报。

**特别警惕这些反模式**:
- "通用规范要求 X"(项目可能违反通用规范是有意为之)
- "防御性编程应 ..."(校验可能放在另一个层)
- "应有边界测试"(边界可能在生产路径不可达)
- "应抽 helper / 加 docstring / 命名应改"(没引到 spec 章节就不属于 quality 问题)

如果你的判断与 spec/plan 直接冲突,**优先信 spec/plan**,把你的"通用直觉"写在 `Notes(非阻塞)` 段而不是 Issues 段。
```

---

## 何时使用

- 凡 reviewer 跑 haiku 模型时强制注入(haiku 更易凭直觉判)。
- sonnet 跑 reviewer 也建议注入,但可省略「特别警惕反模式」一段。
- spec / plan 没有正式落盘的 ad-hoc 任务可不注入(此时本就没参考依据)。

---

## controller 该怎么应对 reviewer 的"伪 issue"

当 reviewer 报了一个不引 spec 的 Important/Critical 时,controller 不应直接派 fix subagent 改代码,而应:

1. **复议**:Read spec/plan 相关章节,判断 reviewer 是否误读。
2. **挡下 + 沉淀**:若是误读,用一个 docs-only commit 在代码里加注释说明「此处不做 X 是因为 spec §Y / plan Task Z 把校验放在 ...」,引用具体章节。这样下次 reviewer / 维护者 / 未来你自己再看同一段代码不会再被同样质疑。
3. **不要**:让 reviewer 直接重审。reviewer 还会基于同样的"通用规范"再判一次。

参考案例:`4b1ca85 docs(level-tags): 说明阈值类 patch 不做 n<2 防御的设计意图`。

---

## 与 plan §11 自检的关系

`scripts/check_plan_signatures.py`(plan §11 自检)负责**机器可验的签名一致性**。
本补丁负责**人/AI 评判时的 spec 锚定**。两者互补,缺一不可。
