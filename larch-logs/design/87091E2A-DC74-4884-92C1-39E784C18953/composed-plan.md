## Plan

### Context

`approach-synthesis.txt` is `NO_SKETCHES`, so draft from direct repo inspection.

The approved outline is binding:
- Reclassify `decompose-panel.md`, `validator-failure.md`, `settle-rc-dispatch.md`, and `step2b5-rc-handling.md` as conditional.
- Split `skill-closure report` into eager and conditional sections.
- Keep the JSON baseline schema unchanged.
- Do not edit skill markdown.
- Do not change `/implement` eager closure.

In `skills/design/SKILL.md`, `#### Split-path (decomposition panel)` (line 354) sits under `### Step 2b.5`. The next markdown heading at equal or shallower depth is `### External Reviewer Setup` (line 385), not `<!-- step:3 — Plan Review -->` (line 366). Heading-depth closure alone leaves Step 3 prose, including the eager `plan-review.md` MANDATORY READ (line 382), inside the open Split-path scope. Eager-wins dedup cannot recover a file that never enters the eager list.

**FINDING_1 addendum.** Today `_paths_for_directive_match` returns `[]` for every conditional line, so runtime `$IMPLEMENT_TMPDIR/*.md` operands are never resolved. Once conditional harvesting collects repo paths from those lines, `_extract_markdown_paths` will also match operands like `$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md` (implement line 373) and `$IMPLEMENT_TMPDIR/security-oos-observations.md` (implement line 671). `_resolve_markdown_path` would raise `ScanError`, breaking `scan_skill(..., "implement")` and the unchanged implement baseline row. Conditional harvesting must skip runtime/non-repo markdown operands and must not fail closed when a conditional clause mentions only runtime paths.

### Files to modify/create

### UPDATED: `python/larch/lint/lint_skill_closure_growth.py`

Add conditional reference tracking while preserving eager baseline rows and safe implement scanning.

Planned changes:
- Extend `ScanState` to track scoped sections with heading depth and design step boundaries.
  - Keep the existing suppressed `/implement` macro behavior.
  - Add conditional section state for design headings:
    - `Split-path (decomposition panel)`
    - `Plan command validator failure (shared)`
  - End a scoped section when:
    - A heading of equal or lower depth appears, or
    - A design step HTML comment boundary appears: `<!-- step:` (matches `<!-- step:3 — Plan Review -->` and siblings throughout `skills/design/SKILL.md`).
  - Process step-comment closure before directive harvesting on each line so `<!-- step:3 -->` closes Split-path before the Step 3 `plan-review.md` read is classified.
  - Keep nested headings inside an open conditional section; only equal/shallower headings or step comments end scope.
- Add `STEP_COMMENT_RE` (or equivalent) for `^<!--\s*step:` lines.
- Add `retained` to `CONDITIONAL_TEXT_RE`.
  - This catches `Retained callers...` before the `step2b5-rc-handling.md` directive.
- Add a suffix check in `_line_is_conditional`.
  - Treat directive suffixes like `(if not already loaded...)` as conditional.
  - This catches the `settle-rc-dispatch.md` re-entry directives.
- Add runtime-operand filtering before path resolution.
  - Add `_is_runtime_markdown_operand(raw: str) -> bool` (or equivalent) that returns true for markdown operands rooted in session/runtime env vars, including `$IMPLEMENT_TMPDIR/`, `$DESIGN_TMPDIR/`, and other `$[A-Z_]+/` prefixes that are not `${CLAUDE_PLUGIN_ROOT}/`.
  - Apply this filter inside `_extract_markdown_paths` (or a thin wrapper) so runtime operands are never passed to `_resolve_markdown_path`.
  - For **eager** directives, keep existing fail-closed semantics when no resolvable repo markdown path remains.
  - For **conditional** directives, collect only successfully resolved repo-relative paths; silently skip runtime operands and other unresolvable markdown mentions instead of raising `ScanError`.
- Change direct-reference parsing to return eager and conditional tuples.
  - Suggested shape: `parse_direct_markdown_references(...) -> tuple[tuple[str, ...], tuple[str, ...]]`.
  - Keep helper logic private to this module.
  - Deduplicate each list in first-seen order.
  - If a path is eager anywhere, exclude it from `conditional_files` so repeated conditional mentions of an eager file do not inflate the conditional report.
- Extend `SkillClosureResult` with conditional-only report fields.
  - Add `conditional_files: tuple[str, ...]`.
  - Add conditional line/token totals, or compute those from `conditional_files` in `scan_skill`.
  - Do not include conditional fields in `to_baseline_row`.
- Keep `BaselineRowDict`, `BaselineRow`, `BASELINE_KEYS`, and committed baseline schema unchanged.
- Keep `_growth_violations` comparing only existing eager metrics.
- Update `_print_report` to show:
  - An eager closure section with the current ratcheted metrics and eager files.
  - A conditional closure section with conditional files and non-gated totals.
  - Include zero-file conditional sections only if that keeps output clearer and tests simple; either way, ensure the four design references appear under conditional and not eager.

### UPDATED: `python/tests/lint/test_lint_skill_closure_growth.py`

Update existing tests and add focused regression coverage.

- Adjust helper and assertions for the new `SkillClosureResult` field.
  - Existing tests that assert `result.files` should keep checking eager files.
  - Add assertions for `result.conditional_files` where relevant.
- Update conditional-reference tests so excluded references are reported as conditional, not dropped.
- Add tests for the four newly required detection paths:
  - Section-scoped `Split-path (decomposition panel)` marks `decompose-panel.md` conditional.
  - Section-scoped `Plan command validator failure (shared)` marks `validator-failure.md` conditional.
  - Suffix `(if not already loaded...)` marks `settle-rc-dispatch.md` conditional.
  - Prefix text with `Retained` marks `step2b5-rc-handling.md` conditional.
- Add Split-path scope-boundary regression coverage (addresses original FINDING_1):
  - Fixture mirroring real layout: `#### Split-path (decomposition panel)` with a `decompose-panel.md` read, then `<!-- step:3 — Plan Review -->`, then an eager `plan-review.md` MANDATORY READ.
  - Assert `decompose-panel.md` is conditional-only and `plan-review.md` is eager-only.
  - Integration test scanning the real repo `skills/design/SKILL.md`: assert `skills/design/references/plan-review.md` is in `result.files` (eager), not only in `conditional_files`.
- Add implement runtime-operand regression coverage (addresses reviewer FINDING_1):
  - Fixture mirroring implement line 373: conditional `If main agent finds...` MANDATORY READ clause mentioning both `$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md` and `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/execution-issues-tracking.md`.
  - Assert scan succeeds, the runtime path is not in eager or conditional lists, and `execution-issues-tracking.md` lands in `conditional_files` only.
  - Fixture mirroring implement line 671: branch bullet `**`oos-pipeline`**:` with `$IMPLEMENT_TMPDIR/security-oos-observations.md` plus MANDATORY READ of `ship-pr-oos-checkpoint-router.md`.
  - Assert scan succeeds and only the resolvable repo reference is collected under `conditional_files`.
  - Integration test scanning the real repo `skills/implement/SKILL.md`: assert `scan_skill` succeeds, eager `result.files` matches the committed implement baseline row file list, and implement eager metrics are unchanged.
- Add or update report-mode coverage.
  - Assert the report has separate eager and conditional sections.
  - Assert conditional files appear in the conditional section.
  - Assert eager files remain in the eager section.
  - Assert `plan-review.md` appears under eager, not conditional.
- Keep the strict committed-baseline freshness test.
  - It should pass after baseline regeneration.

### UPDATED: `python/skill-closure-baseline.json`

Regenerate with the existing command:

`make regen-skill-closure-baseline`

Expected design-row changes:
- Remove these from the design eager `files` list:
  - `skills/design/references/settle-rc-dispatch.md`
  - `skills/design/references/step2b5-rc-handling.md`
  - `skills/design/references/decompose-panel.md`
  - `skills/design/references/validator-failure.md`
- Keep these in the design eager `files` list:
  - `skills/design/references/plan-review.md` (and other common-path references)
- Reduce design eager closure by about 318 lines and about 8,179 estimated tokens.
- Leave the implement row unchanged (same eager `files`, `closure_lines`, and `closure_estimated_tokens`).

## Approach

Keep this as a detector and baseline change only.

Implementation order:
1. Add runtime-operand filtering helper and wire it into markdown path extraction with conditional-vs-eager error semantics.
2. Add scoped heading parsing plus `<!-- step:` comment boundary closure for design.
3. Add conditional section detection.
4. Split direct reference collection into eager and conditional paths.
5. Add conditional metrics to scan results.
6. Update report rendering.
7. Update tests, including Split-path-then-step-comment and implement runtime-operand integration coverage.
8. Regenerate the baseline.

Key decisions:
- Close design conditional sections at `<!-- step:` HTML comment boundaries, not heading depth alone. Step comments are the authoritative step boundaries in `skills/design/SKILL.md` and prevent Split-path scope from swallowing Step 3 eager reads.
- Keep heading-depth closure as a secondary end condition for sections without an intervening step comment.
- When harvesting conditional files, skip runtime/non-repo markdown operands (`$IMPLEMENT_TMPDIR/`, `$DESIGN_TMPDIR/`, etc.) before resolution. Conditional clauses may mention session-local `.md` paths without aborting the scan.
- Keep conditional files out of the baseline JSON.
- Preserve eager `files` as the only ratcheted closure list.
- Do not add machine markers to markdown, because approved non-goals prohibit skill markdown edits.
- Do not refactor CLI registration or baseline loading.

## Edge cases

- A file can appear in both eager and conditional contexts.
  - Treat it as eager only.
- A conditional section can contain nested headings.
  - Keep the conditional state through deeper headings.
  - End it at the next equal or shallower heading or at the next `<!-- step:` comment.
- Split-path scope must not extend past `<!-- step:3 -->` even though `### External Reviewer Setup` is the next shallower markdown heading.
- Existing `/implement` suppressed macro sections should not change eager metrics.
- Implement branch bullets and `If ...` prefixes may pair runtime `$IMPLEMENT_TMPDIR/*.md` mentions with resolvable `${CLAUDE_PLUGIN_ROOT}/...` references in the same clause.
  - Collect only the repo path under `conditional_files`; ignore the runtime operand.
- Unsupported read directives with no markdown path should still fail closed when eager classification reaches path extraction and no resolvable repo path or non-md fallback exists.
- Conditional directives that mention only runtime `.md` operands should succeed with an empty contribution to `conditional_files`.

## Failure modes

1. **Conditional references disappear from both report sections.**
   - Warning signal: tests see neither eager nor conditional file entries.
   - Mitigation: parse every directive first, then classify paths as eager or conditional.

2. **Baseline schema accidentally changes.**
   - Warning signal: baseline validation tests fail or JSON gains conditional keys.
   - Mitigation: keep `to_baseline_row` unchanged except for regenerated eager values.

3. **Heading scope is too broad.**
   - Warning signal: `plan-review.md` or `finalize-step5.md` moves to conditional.
   - Mitigation: close conditional scope at `<!-- step:` boundaries in addition to heading depth; regression-test real `skills/design/SKILL.md` so `plan-review.md` stays eager.

4. **Implement scan fails on runtime tmpdir operands.**
   - Warning signal: `skill-closure report` or `scan_skill(..., "implement")` raises `ScanError` for `$IMPLEMENT_TMPDIR/...md`; implement baseline row drifts or freshness test fails.
   - Mitigation: filter runtime operands before resolution; use lenient conditional extraction; integration-test the real `skills/implement/SKILL.md` and assert the implement eager row is unchanged.

## Testing strategy

Run focused tests:
- `python3 -m pytest python/tests/lint/test_lint_skill_closure_growth.py`
- `python3 python/cli.py skill-closure report`
- `python3 python/cli.py lint skill-closure-growth`

Also run the baseline regen before the final lint check:
- `make regen-skill-closure-baseline`

Expected verification:
- The report lists the four named design references under conditional.
- The report no longer lists those four files under design eager closure.
- `skills/design/references/plan-review.md` remains in design eager closure.
- Design eager closure drops to roughly 1,729 lines and 62,285 estimated tokens.
- Real `skills/implement/SKILL.md` scans without error.
- The implement eager baseline row (`files`, `closure_lines`, `closure_estimated_tokens`) stays unchanged.
- Runtime `$IMPLEMENT_TMPDIR/*.md` operands never appear in eager or conditional file lists.

## Acceptance

Run focused tests:
- `python3 -m pytest python/tests/lint/test_lint_skill_closure_growth.py`
- `python3 python/cli.py skill-closure report`
- `python3 python/cli.py lint skill-closure-growth`

Also run the baseline regen before the final lint check:
- `make regen-skill-closure-baseline`

Expected verification:
- The report lists the four named design references under conditional.
- The report no longer lists those four files under design eager closure.
- `skills/design/references/plan-review.md` remains in design eager closure.
- Design eager closure drops to roughly 1,729 lines and 62,285 estimated tokens.
- Real `skills/implement/SKILL.md` scans without error.
- The implement eager baseline row (`files`, `closure_lines`, `closure_estimated_tokens`) stays unchanged.
- Runtime `$IMPLEMENT_TMPDIR/*.md` operands never appear in eager or conditional file lists.

review_status: ok
rounds_completed: 3
diff_added: 250
diff_deleted: 40
mechanical_churn: false
diff_lines: 290
