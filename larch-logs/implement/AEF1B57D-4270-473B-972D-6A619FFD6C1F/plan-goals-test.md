## Goal
Implement issue #6179: [IMPLEMENTING] [OOS] [OUT_OF_SCOPE] Audit step leaves other neither-tier runtime refs untracked by the new dropped-file ratchet.

## Implementation Plan
## Plan

## Files to modify/create

### UPDATED: python/larch/lint/lint_skill_closure_growth.py

Broaden the conditional prose classifier and fix implement macro handling.

- Replace the narrow background-only regex with a named conditional reference regex that recognizes `see`, `load`, `read`, and `follow`. `follow` is required because design's `final-summary-emit.md` citations use that verb, not `see`/`load`/`read`.
- Match qualified clauses like `only for`, `only when`, `only after`, `only before`, `only on`, and `only upon`. The connector set must cover every qualifier this plan's own example rephrasings use (including the `only on the ... routes` / `only upon reaching Step 5c item 5` design examples below), not just the initial four.
- Keep forced conditional behavior for these matches.
- Preserve strict path resolution for eager references, but keep conditional references non-fatal for unrelated text that does not resolve.
- Introduce one skill-keyed conditional-section-title registry (for example `CONDITIONAL_SECTIONS_BY_SKILL: dict[str, frozenset[str]]`) mapping each skill to its own section titles, with `design` entries `{"Plan command validator failure (shared)", "Split-path (decomposition panel)"}` (the current `CONDITIONAL_DESIGN_SECTIONS` contents) and `implement` entries `{"Checks Failure Entry Macro", "Durable Bail to Step 18 Macro"}` (the current `SUPPRESSED_IMPLEMENT_SECTIONS` contents). Drive both skills' scan-state updates from one shared depth-reset function keyed off this registry, using the **same peer/shallower heading-depth reset** `_update_design_scan_state` already implements (reuse `conditional_section_depth`, not a simplified "exit on any next heading" rule), so a heading nested inside any of these sections cannot reset scope early in either skill.
- Fully delete `SUPPRESSED_IMPLEMENT_SECTIONS`, the `suppressed_section` field, and its full-line skip (`if state.suppressed_section is not None: continue`). Do not leave any of this dangling alongside the new shared mechanism — if the implement macro headings are not explicitly named in the new registry, checks-repair-loop.md would go from untracked to *eager* (worse than today), so the registry entries and the deletion must land together.
- Do **not** extend the existing implement-only `IMPLEMENT_FINAL_SUMMARY_RE` / narrow-pattern mechanism to `design`. Design's `skills/shared/final-summary-emit.md` citations are a mix of cancel-only conditional paths (e.g. the `cancel-title-filter` / `cancel-reentry-guard` branch, and the `_publish_rc=2`-or-unexpected branch) and the more common Step 5c item 5 path reached on every completed run. Copying implement's unconditional narrow match would misclassify the cancel-only citations as eager, inflating `closure_lines` / `closure_estimated_tokens` — metrics that are actually growth-ratcheted for `design`. Instead, track all of design's `final-summary-emit.md` citations through the new generalized `only for|when|after|before|on|upon` regex (above, with `follow` as a trigger verb), landing them uniformly in `conditional_files`.
- Keep `SECURITY.md` and `skills/shared/oos-acceptance-rubric.md` untracked unless a new direct runtime read pattern makes them resolvable by existing rules. The widened verb/connector set must not start collecting paths from runtime-only prose (e.g. `oos-pipeline` branch text mentioning `SECURITY.md`) — keep path resolution strict enough that these two files stay absent from both `files` and `conditional_files` for every ratcheted target.

### UPDATED: python/tests/lint/test_lint_skill_closure_growth.py

Add focused regression coverage for the audit gaps and classifier changes.

- Replace `test_implement_failure_only_macro_sections_are_excluded_until_next_heading` with two cases: (a) conditional-tracking through the next **peer or shallower** heading (mirroring the existing design depth-reset test), and (b) a synthetic fixture with a heading **nested inside** one of the macro sections, asserting conditional state does NOT reset early at that nested heading and does not leak past the macro's actual peer/shallower boundary.
- Add tests for `load/read/see <path> only for|when|after|before|on|upon` forms, including relative and plugin-root paths, and a case confirming an unrelated `<other>.md` citation elsewhere on the same line does not get pulled into the matched clause.
- Add a real-design scan assertion for:
  - `skills/design/references/sentinel-host-table.md` (`conditional_files`)
  - `skills/design/references/step2b-drafter-failsafe.md` (`conditional_files`)
  - `skills/design/references/dialectic-clarifier.md` (`conditional_files`)
  - `skills/shared/final-summary-emit.md` (`conditional_files` — not `files`; assert this explicitly so a future accidental copy of implement's eager pattern fails loudly)
- Add a real-implement scan assertion for:
  - `skills/implement/references/checks-repair-loop.md` (`conditional_files`)
  - `skills/implement/references/extracted-script-registry.md` (`conditional_files`)
  - `skills/implement/references/phantom-probe.md` (`conditional_files`)
  - `skills/shared/orchestrator-never.md` (`conditional_files`)
  - `skills/shared/final-summary-emit.md` stays in `files` (implement's existing eager narrow pattern is unchanged)
- Add a real-review scan assertion for `skills/shared/run-id-flag.md` (`conditional_files`).
- Add an explicit negative-assertion test: after the classifier and baseline changes, `SECURITY.md` and `skills/shared/oos-acceptance-rubric.md` are absent from every ratcheted target's `files` and `conditional_files` (guards the deliberate-exclusion decision above against future regex over-collection).

### UPDATED: skills/design/SKILL.md

Make each audited reference name the target file inside a recognized qualifying clause. Wording only; no behavior changes.

- Rephrase the sentinel host-table sentence so it says to load `skills/design/references/sentinel-host-table.md` only when editing sentinel host mappings or debugging pause/resume sentinels.
- Leave the `failsafe-missing-rows` bullet's wording for `references/step2b-drafter-failsafe.md` unchanged. Its current phrasing ("...this token is valid only after exit 0 without a trusted postplan action row") already contains `only after`, so the widened regex resolves it from the existing text. Do not rewrite this bullet — rephrasing risks silently dropping the "run the retained terminal postplan path" instruction or the exit-0 guard, both of which are load-bearing for `design-step2b-drafter.sh`'s runtime contract.
- Keep the Gate C dialectic rule as a conditional load of `references/dialectic-clarifier.md` only for valid candidates or manual candidates (already matches `only for`; verify no rewrite is needed here either).
- Add an explicit `only for|when|after|on|upon` qualifier to each of the 4 `final-summary-emit.md` citations, matching its actual runtime condition (e.g. "only on the `cancel-title-filter` / `cancel-reentry-guard` routes", "only when `_publish_rc` is 2 or another unexpected value", "only upon reaching Step 5c item 5"), so every citation resolves as conditional under the new regex. Do not change the underlying instructions these sentences give, only add the qualifying clause.
- Do not add new mandatory read obligations beyond the existing runtime conditions.

### UPDATED: skills/implement/SKILL.md

Make implement-only audited references visible to the classifier. Wording only; no behavior changes.

- Rephrase the premature-notification rule so it says to read `skills/shared/orchestrator-never.md` only when that recovery condition is active.
- Rephrase the extracted script registry sentence so it loads `skills/implement/references/extracted-script-registry.md` only when editing or auditing extracted script contracts.
- Keep `checks-repair-loop.md` in the Checks Failure Entry Macro exactly as written today. The scanner fix above classifies it conditional without any prose duplication or change.
- Rephrase the phantom probe sentence so it sees or reads `skills/implement/references/phantom-probe.md` only when changing probe call sites.
- Preserve all existing orchestrator semantics and NEVER rules.

### UPDATED: skills/review/SKILL.md

Make the shared run-id reference classifier-visible. Wording only; no behavior change.

- Rephrase the flag paragraph so it says to read or see `skills/shared/run-id-flag.md` only for shared `--run-id` flag semantics.
- Keep flag parsing behavior unchanged.

### UPDATED: docs/linting.md

Keep the skill-closure-growth description in sync with the scanner change (the current text would otherwise go stale the moment this PR lands).

- Update the bullet that currently says the `/implement` `Checks Failure Entry Macro` and `Durable Bail to Step 18 Macro` sections are **excluded**: they are now tracked as **conditional**, not excluded.
- Leave the adjacent bullet describing the four narrow eager phrase patterns (including `final-summary-emit.md` follow instructions) unchanged — that pattern stays implement-only and eager, per the classifier decision above.

### UPDATED: python/skill-closure-baseline.json

Regenerate the baseline after code and prose changes.

- Run the canonical writer, not manual JSON edits:
  - `python3 python/cli.py lint skill-closure-growth --write`
- Expect the confirmed audit files to appear in the proper `files` or `conditional_files` rows (all newly-tracked audit files land in `conditional_files`; no eager-tier additions).
- Review the diff to confirm only intended closure metrics and file arrays changed.

## Approach

Implement the scanner fix first, then adjust prompt prose only where needed.

1. Update the regex path for conditional references (`see`/`load`/`read`/`follow`, `only for|when|after|before|on|upon`).
2. Introduce the shared `CONDITIONAL_SECTIONS_BY_SKILL` registry and one depth-reset function for both skills; point design's existing two section titles and implement's two macro titles at it; delete `CONDITIONAL_DESIGN_SECTIONS`, `SUPPRESSED_IMPLEMENT_SECTIONS`, and the `suppressed_section` field together.
3. Add tests with small synthetic fixtures — including a nested-heading fixture — before updating real-scan assertions.
4. Make minimal wording changes in the three `SKILL.md` files and `docs/linting.md`. For design's `final-summary-emit.md` citations, add qualifying clauses; do not add design to implement's eager narrow-pattern list.
5. Regenerate the closure baseline.
6. Run the targeted linter and tests.

This keeps the existing prose-classifier model. It avoids a new manifest or watchlist format, per the approved outline.

## Edge cases

- A line may contain multiple Markdown paths. The classifier should collect all paths inside the matched conditional clause.
- Conditional clauses should not turn runtime tmpdir operands like `$IMPLEMENT_TMPDIR/foo.md` into repo paths.
- Implement macro conditional state must end at the next peer or shallower heading, not at any nested heading — the same rule design already applies, and the new test must actually exercise a nested heading, not just the peer case.
- Two distinct `follow`-triggered mechanisms coexist after this change: implement's existing unconditional `IMPLEMENT_FINAL_SUMMARY_RE` narrow pattern (eager, implement-only, unchanged), and the new general conditional regex's `follow` verb (used by design's qualified final-summary-emit.md citations). Neither should cause an unrelated `follow ... other.md` citation elsewhere on the same line to become tracked.
- Existing deliberate exclusions for `SECURITY.md` and `skills/shared/oos-acceptance-rubric.md` should stay excluded.
- Rephrasing `step2b-drafter-failsafe.md`'s bullet is explicitly out of scope for this change; only the scanner's widened connector set (`only after`) is responsible for resolving it.

## Failure modes

1. **Over-broad regex pulls in prose citations as runtime references.**
   - Early signal: `skill-closure report` shows unrelated docs in `files` or `conditional_files`.
   - Mitigation: keep trigger verbs and `only for|when|after|before|on|upon` connectors required.

2. **Implement macro state leaks past the macro, or a nested heading resets it early.**
   - Early signal: always-loaded implement references after `Durable Bail to Step 18 Macro` move to `conditional_files`; or a nested-heading fixture shows conditional state clearing before the macro section actually ends.
   - Mitigation: add fixtures for both a following peer/shallower eager reference and a nested heading inside the macro section.

3. **Design's final-summary-emit.md citations get miscounted as eager, inflating a ratcheted metric.**
   - Early signal: `skill-closure report` shows `skills/shared/final-summary-emit.md` under design's eager `files` list instead of `conditional_files`.
   - Mitigation: the real-design scan test explicitly asserts `conditional_files` placement, and the classifier must not gain a design-scoped unconditional narrow pattern for this file.

4. **Baseline hides a classifier mistake.**
   - Early signal: regenerated JSON contains unexpected files or large metric jumps.
   - Mitigation: inspect `python3 python/cli.py skill-closure report` before committing the regenerated baseline.

## Testing strategy

Run only targeted checks.

- `python -m pytest python/tests/lint/test_lint_skill_closure_growth.py`
- `python3 python/cli.py skill-closure report`
- `python3 python/cli.py lint skill-closure-growth`
- If baseline freshness fails before regeneration, run `python3 python/cli.py lint skill-closure-growth --write`, then rerun the lint.

Difficulty rationale: MODERATE, high confidence. This is multi-file and workflow-affecting, but the surfaces are bounded and have direct scanner tests.

## Acceptance

Run only targeted checks.

- `python -m pytest python/tests/lint/test_lint_skill_closure_growth.py`
- `python3 python/cli.py skill-closure report`
- `python3 python/cli.py lint skill-closure-growth`
- If baseline freshness fails before regeneration, run `python3 python/cli.py lint skill-closure-growth --write`, then rerun the lint.

Difficulty rationale: MODERATE, high confidence. This is multi-file and workflow-affecting, but the surfaces are bounded and have direct scanner tests.

diff_lines: 220

## Test plan
(no test plan section in plan-file)
