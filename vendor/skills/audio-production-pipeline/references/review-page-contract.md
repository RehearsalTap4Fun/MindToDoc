# Review Page Contract

The review page is a product surface, not a static report and not a free-form web design task.

Different planners and projects may use different manifests, but the page contract must remain consistent so the workflow is reusable.

## Contract Version

Current contract: `x15-planner-review-v1`

Every generated review page should expose this version in visible text or page metadata/comment so later agents can tell which interaction model it follows.

## Required Layout

Use the same high-level layout every time:

- Top status bar: feature name, total event count, review progress, export/status messages.
- Left pane: event list with filters.
- Right pane: selected event detail, candidate list, AI gap/retry controls when applicable.
- Bottom or top export area: planner decision export.

Do not replace this with a gallery, card-only page, marketing page, dashboard-only page, or static table.

## Required Event List Behavior

Each event row should show:

- `request_id` if available.
- `event_name`.
- `asset_name`.
- tag/status: `新增`, `复用`, `沿用X1`, `AI待补`, `已选择`, or equivalent.
- best short candidate hint when candidates exist.
- whether the event needs planner attention.

Required filters:

- `全部`
- `有合格候选`
- `有短候选`
- `需重点听`
- `无候选`
- `复用/沿用`

Reuse/X1 rows should not appear as unfinished work in the default attention queue.

## Required Candidate Controls

Every playable candidate must have:

- Native audio control or equivalent in-page playback.
- Source label: company library, AI gap, reuse, or imported final.
- Duration if known.
- Score fields if available.
- Decision buttons:
  - `直接用`
  - `改后用`
  - `不合适`
- Notes field.

Do not use external "在线试听" links as the only listening path. The planner must be able to listen inside the review page.

## Required Sort And Score Controls

Company-library and AI candidate pages must support:

- Score filter:
  - `中高分+最佳短`
  - `只看60分以上`
  - `显示全部分数`
- Sort:
  - `短候选优先`
  - `匹配分优先`
  - `搜索排名优先`

Best short candidate must remain visible even when below the normal score threshold.

## Required AI Gap Controls

AI generation controls are shown only for real unresolved gaps.

Default AI settings:

- full/non-combined
- WAV output
- no raw stems
- no combined output
- company API only

Planner may explicitly opt into combined/stems, but the default page must not generate them.

Reuse/X1 rows must not show normal AI generate/retry controls unless a force-generate override is intentionally added.

## Required Export Format

The page must export structured planner decisions as JSON. CSV is optional but useful.

Each exported decision should include:

- `request_id`
- `event_name`
- `asset_name`
- `decision`
- `candidate_id`
- `source_path`
- `source_type`
- `note`
- `score` or score object if available
- timestamp if possible

Final package generation should prefer exported decisions JSON over browser localStorage.

## State Safety

Before page refresh, rebuild, URL-origin change, server switch, or template migration:

1. Export planner decisions JSON.
2. Back up current state if localStorage is involved.
3. Only then rebuild or move the page.

`file://` and `http://127.0.0.1` are different localStorage origins. Treat them as different state containers.

## Generator Rule

If a project has a page generator, update the generator first and regenerate the page.

Do not hand-edit generated HTML as the only fix. Hand edits disappear on rebuild and make skill reuse inconsistent.

Use the generator bundled with this skill, then validate the generated page:

```bash
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/build_company_library_review_page.py [arguments]
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/validate_review_page_contract.py <review-page.html>
```

## Visual Consistency Rule

The exact colors can vary, but the workflow shape cannot:

- left event queue
- right event details
- in-page audio playback
- candidate decisions
- notes
- filters/sorts
- AI gap area
- export area
- one-click `提交判断并生成交付包` command backed by `serve_review.py`

If another planner gets a page without these elements, treat it as a broken implementation of this skill, not as an acceptable variant.
