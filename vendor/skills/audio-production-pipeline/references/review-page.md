# Planner Review Page Rules

Before creating or modifying the page, read `review-page-contract.md`. That file defines the stable UI/behavior contract. This file adds implementation guidance.

## Required UI

A review page must be playable and planner-facing:

- Event list on the left.
- Event detail and candidates on the right.
- Audio controls for each playable candidate.
- Decision controls: `直接用`, `改后用`, `不合适`.
- Notes fields for feedback and retry instructions.
- Event-level AI fallback controls only for real gaps.
- Export to JSON/CSV planner decisions.
- Progress summary at the top.

Rows marked `复用` or `沿用X1` should be hidden from the main decision workload by default, or shown in a reuse-only view. They do not need normal AI retry controls.

The review page must not be improvised per planner. If the data changes, update the manifest; if the UI behavior changes, update the generator and keep the contract stable.

## Company Candidate Screening

Use short-candidate-first review behavior:

- Default order: `短候选优先`.
- Keep the best short candidate visible even below the normal threshold.
- Provide score filters:
  - `中高分+最佳短`
  - `只看60分以上`
  - `显示全部分数`
- Provide sort controls:
  - `短候选优先`
  - `匹配分优先`
  - `搜索排名优先`
- Provide event filters:
  - `有合格候选`
  - `有短候选`
  - `需重点听`
  - `无候选`
- Mark the suggested first-listen candidate with a visible badge such as `建议先听`.

## State Safety

Do not ask the planner to refresh, switch from `file://` to `http://127.0.0.1`, or rebuild the page before decisions are exported or backed up.

`file://...review.html` and `http://127.0.0.1:PORT/...review.html` use different browser localStorage origins. Planner choices can appear to vanish after switching.

Safe order:

1. Export planner decisions JSON from current page.
2. Back up/export state if available.
3. Then rebuild page, change server, or move URLs.
4. Final package should prefer exported planner decisions JSON over fragile browser state.

The normal planner path is the in-page one-click production handoff. Keep manual decisions JSON export as a backup, not as a required chat handoff step.

## AI Gap Behavior

- AI generation controls are only for unresolved gaps.
- AI generation depends on a local backend service with the user's company token. The page must never embed tokens. OpenClaw auto-injects `TAPPER_AUTH_TOKEN`; external environments should read `TAPPER_AUTH_TOKEN` or this skill root's private `config.json` fields in order: `api_key`, `jwt_token`, then legacy `tapper_auth_token`. If no token exists, show the login link `https://voiceclone.tap4fun.com/auth/apikey-login` and ask the user to paste back the `tts_...` api_key so `scripts/set_api_key.py` can write it locally.
- If the token is missing, expired, or rejected, show a clear authentication/generation-service failure and keep retry controls available. Do not display an endless queued state.
- Every non-reuse event must expose a `生成AI候选` action; unresolved gaps use it as the primary action and events with existing AI candidates expose `重新生成AI候选`.
- A non-reuse event with no company candidate at or above the qualified threshold must automatically request AI generation when the generation service is available. Writing only `ready_for_ai` to a queue is not completion.
- Successful AI output must be written into the review manifest and immediately shown as playable candidates on the same page. Do not require the planner to export a queue and send it back to the agent.
- If automatic generation times out or the service is unavailable, show a clear retryable status on that event and keep the generation button enabled.
- `生成全部AI缺口` must submit and await events sequentially. Do not fire every generation request concurrently; the local generation service serializes work and concurrent submissions create a long opaque queue.
- Disable event and global generation buttons while their task is active, and reject duplicate clicks for the same event.
- Persist each job status URL so polling can resume after a page refresh. Treat `missing`, a service restart, network failure, or a bounded polling timeout as an interrupted task and restore a retry button; never display `排队等待生成` indefinitely.
- Default AI generation to multiple full candidates per gap, normally `variants_needed=3`, so planners can compare options before deciding. If the generation service reports quota or stability pressure, reduce to `variants_needed=1` for that run and show the reason in the event status.
- `生成全部AI缺口` still runs sequentially by event, but each unresolved gap should request the default variant count for that event rather than only one candidate.
- Bulk generation must skip events that already have playable AI candidates. When every gap is filled, disable the bulk button and show `AI缺口已补齐`; keep event-level regeneration available.
- Surface the generation service's actual failure message (for example HTTP 500) instead of collapsing server failures into `排队等待生成` or a generic interrupted state.
- Reuse rows must not enter AI gap queues unless the planner explicitly force-generates.
- AI candidates should be written into the review manifest and scored like company-library candidates.
- Do not leave generated candidates as temporary page-only paths.

## Verification

After page changes:

- Open the actual local page if possible.
- Check audio controls render.
- Check score filter and sort controls exist.
- Check reuse rows are not treated as missing.
- Check export still works.
- Check browser console if frontend behavior changed.
