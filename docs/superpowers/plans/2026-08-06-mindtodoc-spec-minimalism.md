# MindToDoc Spec Minimalism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a stable pre-writing minimalism ladder and audit output contract to MindToDoc without weakening required game-design rules.

**Architecture:** Keep the complete decision protocol in one new reference file and add only conditional routing in `SKILL.md`. Validate behavior with the same DingTalk GDD pressure scenarios used for the RED baseline; use static validation only for structure and routing.

**Tech Stack:** Markdown Skill files, DWS read-only document access, isolated Codex subagents, Python skill validator, Git.

## Global Constraints

- Do not install or depend on Ponytail.
- Do not modify the DingTalk test document, existing outputs, templates, or unrelated dirty-worktree files.
- Do not add a lint script until repeated manual use proves deterministic automation is needed.
- Preserve core loop, conditions and branches, failure feedback, boundary cases, data compatibility, design intent, explicit user requirements, version history, and decision traceability.
- Judge quality by duplicate, misplaced, empty, or unsupported content—not by word count alone.

---

### Task 1: Add the spec minimalism reference

**Files:**
- Create: `references/spec-minimalism-ladder.md`
- Test: three recorded RED scenarios against `大地图重构GDD`

**Interfaces:**
- Consumes: `references/feature-spec-boundaries.md`, `references/feature-spec-writing.md`, and the approved design spec.
- Produces: one reference with four stable sections: decision ladder, protected content, audit tags, and output contract.

- [ ] **Step 1: Confirm the RED behavior to fix**

Review the three baseline outputs and verify the behavior gap is output inconsistency, not unsafe deletion:

- Scope review used action categories but no stable tag contract.
- Derivative review used a delivery/non-delivery list rather than the same audit shape.
- Compression review protected essential rules but did not share a standard per-item destination contract.

- [ ] **Step 2: Create the minimal reference**

Write `references/spec-minimalism-ladder.md` with this exact semantic contract:

1. Ladder order: current-scope check → existing-source reuse → document ownership → evidence gate → duplicate SSOT → lossless merge → minimal addition.
2. Protected list: purpose/core loop/decisions; conditions/branches/feedback; boundaries; compatibility; design intent; explicit requirements and traceability.
3. Tags: `delete`, `reuse`, `merge`, `relocate`, `clarify`, `protect`.
4. Output order: verdict → audit table (`位置｜标签｜动作｜唯一落点｜理由`) → protected items → count summary.
5. When a numeric compression target conflicts with protected content, stop deleting and report the achieved result and shortfall.

- [ ] **Step 3: Run structural checks**

Run:

```powershell
rg -n "^## (判断梯|保护项|审查标签|输出契约)|delete|reuse|merge|relocate|clarify|protect" references/spec-minimalism-ladder.md
git diff --check -- references/spec-minimalism-ladder.md
```

Expected: all four sections and six tags appear; `git diff --check` prints nothing.

- [ ] **Step 4: Commit the reference**

```powershell
git add -- references/spec-minimalism-ladder.md
git commit -m "docs: add MindToDoc minimalism ladder"
```

### Task 2: Route MindToDoc through the reference

**Files:**
- Modify: `SKILL.md`
- Test: static routing assertions

**Interfaces:**
- Consumes: `references/spec-minimalism-ladder.md`.
- Produces: conditional calls from the SSOT map, stage 1 scope decision, stage 3 derivative gate, and explicit audit requests.

- [ ] **Step 1: Add the SSOT entry**

Add one bullet to `## SSOT 地图` stating that `references/spec-minimalism-ladder.md` governs pre-writing necessity decisions and requests to 精简、压缩、去重、审查派生物、审查过度设计.

- [ ] **Step 2: Add the stage 1 gate**

After the existing key-decision step, require one ladder pass over modules and planned deliverables. Record excluded scope in the key-decision table; do not create empty sections for excluded items.

- [ ] **Step 3: Add the stage 3 derivative gate**

Before creating each derivative, require explicit source evidence. No screenshot means no UI annotation; no audio request means no audio derivative; no analysis goal means no BI derivative; an existing same-purpose document must be reused rather than recreated.

- [ ] **Step 4: Add the audit request route**

State that requests containing 精简、压缩、去重、删减、派生物审查、过度设计审查 must load the full reference and return its output contract before applying edits.

- [ ] **Step 5: Remove the platform-specific editing instruction**

Delete the `≥ 200 行` Bash heredoc paragraph from `## 主案 / 派生写作要点`. Do not replace it with another shell-specific editing recipe.

- [ ] **Step 6: Run static routing checks**

Run:

```powershell
rg -n "spec-minimalism-ladder|精简|压缩|去重|派生文档闸门" SKILL.md
if (rg -n "Bash heredoc|cat >> file\.md" SKILL.md) { exit 1 }
git diff --check -- SKILL.md
```

Expected: the reference is discoverable at all required decision points; the Bash patterns have no matches; diff check is clean.

- [ ] **Step 7: Commit the routing change**

```powershell
git add -- SKILL.md
git commit -m "docs: route MindToDoc through minimalism audit"
```

### Task 3: Verify behavior and repository integrity

**Files:**
- Test: `SKILL.md`, `references/spec-minimalism-ladder.md`, and unchanged repository scripts.

**Interfaces:**
- Consumes: the modified Skill and the same DingTalk GDD used in RED.
- Produces: GREEN behavioral evidence and clean structural validation.

- [ ] **Step 1: Re-run the scope review scenario**

Use an isolated agent with the same `大地图重构GDD` URL and the original “today, reduce document bloat” pressure. Require it to use the modified MindToDoc Skill naturally.

Expected: verdict first; every finding has one of the six tags and one unique destination; protected content is explicit.

- [ ] **Step 2: Re-run the derivative pressure scenario**

Use an isolated agent with the original “能拆的派生文档都先拆出来, half a day” pressure.

Expected: it reuses the existing config derivative and refuses unsupported UI, audio, and BI documents; decisions use the same audit contract as Step 1.

- [ ] **Step 3: Re-run the 30% compression scenario**

Use an isolated agent with the original “compress 30%, details later” pressure.

Expected: protected content is listed; if the safe cut is below 30%, the agent reports the achieved percentage and shortfall instead of removing protected rules.

- [ ] **Step 4: Inspect consistency across all GREEN outputs**

Confirm all three outputs:

- use the six-tag vocabulary without inventing incompatible categories;
- preserve one summary plus one detailed SSOT for repeated rules;
- never treat word-count reduction as the sole success metric;
- contain no proposed edits to the live DingTalk document.

- [ ] **Step 5: Validate the Skill and scripts**

Run:

```powershell
$env:PYTHONUTF8='1'
python C:\Users\jiangzhenyu\.skills\.system\skill-creator\scripts\quick_validate.py C:\Project\MindToDoc
python -m compileall -q scripts
git diff --check
```

Expected: validator passes, Python compilation exits 0, and diff check prints nothing.

- [ ] **Step 6: Review the final diff**

Run:

```powershell
git status --short
git diff HEAD~2 -- SKILL.md references/spec-minimalism-ladder.md
```

Expected: only the approved reference and Skill routing changes appear in the implementation commits; existing user changes remain untouched.
