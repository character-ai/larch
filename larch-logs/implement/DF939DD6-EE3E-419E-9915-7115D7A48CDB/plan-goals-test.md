## Goal
Implement issue #6346: [IMPLEMENTING] Add a merit ("worth doing?") judgment gate to /combine-issues --oos.

## Implementation Plan
## Plan

## Context

- `approach-synthesis.txt` is `NO_SKETCHES`; draft from direct repo inspection.
- Round 1 and the approved outline bind scope to `.claude/skills/combine-issues/SKILL.md`, steps `oos-2` and `oos-4`.
- Current `oos-2` checks actuality only, builds stale-only closures, and emits `Actuality check: <K> items kept, <M> discarded across <N> OOS issues.`
- No current test pins the `oos-2` summary text.

## Approach

1. In `oos-2`, keep the existing actuality flow unchanged through file existence, blocked-item handling, and concern-still-present checks.
2. After an item passes actuality and is not blocked, add a merit gate:
   - Reject only with a concrete reason tied to code read or documented repo principles.
   - Use `KARPATHY_CLAUDE.md` §2 and §3 as named rubric anchors.
   - Include the issue body rubric: speculative feature, single-use abstraction, unrequested flexibility, defensive impossible-state handling, refactor of unbroken code, pure nit, lopsided cost-benefit, or contradiction of a documented decision.
   - Default to keep when evidence is weak.
3. Stage low-merit items in a proposed rejection list with source issue, item title, stable display key, and a 1-3 sentence cause. Do not combine, deduplicate, or close them until operator confirmation.
4. Update the `oos-2` summary to count kept, stale, and pending low-merit items separately. Keep the blocked-item suffix.
5. Collect into the `oos-3/oos-4` flat list only items that passed both actuality and merit and are not blocked. Merit-pending items stay in the staged rejection list only; they are never added to the flat list before batch confirmation.
6. The no-actual-items terminal path in `oos-2` fires only when zero items pass actuality AND no merit rejections are pending. If any merit rejections are pending, continue to `oos-3/oos-4` even when no kept items remain, so the batch gate can run.
7. In `oos-4`, show all proposed merit rejections as one consolidated list before the combination scheme.
8. Make the `oos-4` approval semantics explicit:
   - The merit batch is decided independently of group/stale selections: approve all listed rejections, reply in free prose to rescue a subset, or cancel. Merit rejections require an explicit merit batch outcome.
   - Partial group or stale-closure selections do not confirm or apply any merit rejection. If the operator approves only some groups without an explicit merit decision, all merit rejections remain pending, and sources with pending merit items remain open and ineligible for `oos-5`.
   - Approval (merit batch) confirms all listed merit rejections.
   - Free-prose rescue keeps named items and returns them to the actual-item set.
   - Cancel stops without rejecting merit items.
   - Do not prompt per item.
9. After the operator confirms merit rejections and resolves any rescues, rerun deduplication and grouping with the final kept-item set. If any rescue changed kept-item membership or grouping, re-emit the combination proposal and require explicit operator approval before `oos-5` apply.
10. Generalize stale-only closure prose to fully discarded closure prose after confirmation:
    - A source is fully discarded only when every item is stale auto-discarded or confirmed merit-rejected, and no item is blocked, rescued, still actionable, or consumed by a combined host.
    - Use `combine-issues close-stale` with reason `not planned`.
    - Write an honest close comment that says items were discarded as stale or out of line with repo principles.
    - Do not use `close-sources` or the `larch:combined-away` marker for these closures.
11. Update `oos-5` deferred-close logic:
    - Only stale auto-discards, confirmed merit-rejected items, and items consumed into approved groups count as consumed/handled.
    - Blocked-on-source items, pending (unconfirmed) merit items, and rescued items are not consumed. Any source with such an item stays close-blocking, must appear in `blocked_sources.json` with a reason (`merit_pending`, `blocked_on_source`, etc.), and must not be listed in `--source-issues` or eligible for `close-sources`.
    - `close-eligible` must treat sources with pending merit items as ineligible.

## Files to modify/create

### UPDATED: .claude/skills/combine-issues/SKILL.md

- Update the `oos-2` heading or first prose sentence to mention actuality plus merit.
- Insert the merit rubric after the existing concern-still-present check and before collecting actual items into the `oos-3/oos-4` flat list.
- Clarify that only items passing both actuality and merit (and not blocked) go into the flat list; merit-pending items stay staged.
- Update the no-actual-items terminal branch: do not stop if any merit rejections are pending; continue to `oos-3/oos-4` so the batch gate can run.
- Replace fully stale source tracking with pending fully discarded tracking, while preserving the stale-only behavior until merit rejections are confirmed.
- Change the summary grammar to separate kept, stale, and low-merit pending counts.
- Update `oos-4` to show `Rejected items (merit):` with one line per item (stable display key, issue number, title) and a 1-3 sentence cause.
- Update the `oos-4` approval prompt to cover groups, stale closures, and merit rejections in one batch; pin partial-list semantics: merit rejections require an explicit merit batch outcome (approve all, free-prose rescue, or cancel); partial group/stale selections do not confirm merit; sources with pending merit remain open.
- Add `oos-4` rescue regrouping prose: after any rescue that changes the kept-item set or grouping, re-emit the combination proposal and require operator approval before `oos-5` apply.
- Update `oos-5` prose: only stale auto-discards, confirmed merit rejections, and consumed-group items count as consumed; blocked, pending, and rescued items keep sources close-blocking and must appear in `blocked_sources.json`; `close-eligible` treats sources with pending merit as ineligible.
- Update close-comment prose for confirmed fully discarded sources (honest text covering stale and merit reasons).
- Update the dependency summary labels from stale-only to stale or fully discarded where needed.
- Update the `Anti-patterns` section: scope "NEVER discard actionable content" to combined-body merges (confirmed merit rejections after `oos-4` batch approval are permitted discards); add "NEVER auto-apply merit rejections before `oos-4` confirmation" as an explicit rule.

## Edge cases

- **Ambiguous merit evidence**: keep the item.
- **Contradicting documented decisions**: reject only when the contradiction is concrete and cited in the cause.
- **Operator rescues a subset**: reinsert rescued items before regrouping; reject only the unrescued items; if grouping changed, re-present and require re-approval.
- **All items proposed low-merit**: do not close sources until the operator confirms; if any merit rejections are pending, still continue to `oos-4` (zero kept items is allowed).
- **Blocked items plus low-merit items**: keep the source open; blocked items remain actionable later and stay in `blocked_sources.json`.
- **Stale plus confirmed low-merit only**: source qualifies for `not planned` closure with the honest discarded-source comment.
- **Partial approval of groups only**: merit rejections remain pending; sources with pending merit items stay open and ineligible for `oos-5`.
- **Pending merit items in oos-5**: source cannot be listed in `--source-issues` or deferred-close; treat as ineligible until confirmation.
- **Partial `close-stale` failure**: keep current warning and left-open reporting behavior.

## Failure modes

- The prompt could close sources before merit confirmation. Prevent this by stating that proposed merit rejections are not discarded until `oos-4` approval, and that sources with pending merit items are ineligible for `oos-5`.
- The prompt could apply a combination scheme that omitted rescued items. Prevent this by requiring regrouping and re-approval after any rescue that changes the kept-item set.
- The prompt could over-reject subjective items. Prevent this with default-keep bias and the concrete-reason requirement.
- The close comment could claim stale-only when merit contributed. Prevent this by adding distinct fully discarded comment text.
- The `oos-5` deferred-close path could treat pending merit items as consumed. Prevent this with the explicit `oos-5` prose update and `blocked_sources.json` requirement.
- Partial group approval could silently confirm merit rejections. Prevent this by making merit a separate, independent batch decision.

## Testing strategy

- Run `pre-commit run --files .claude/skills/combine-issues/SKILL.md`.
- If the edit changes no Bash fences, no implement fence-shape test is needed.
- No Python tests are expected because the change is prompt-side only and adds no CLI verb.
- If implementation discovers an existing test or lint that pins the `oos-2` summary literal, update only that assertion and run the narrow test.

## Acceptance

- Run `pre-commit run --files .claude/skills/combine-issues/SKILL.md`.
- If the edit changes no Bash fences, no implement fence-shape test is needed.
- No Python tests are expected because the change is prompt-side only and adds no CLI verb.
- If implementation discovers an existing test or lint that pins the `oos-2` summary literal, update only that assertion and run the narrow test.

diff_lines: 105

## Test plan
(no test plan section in plan-file)
