## Goal
Implement issue #6162: [IMPLEMENTING] [BLOCKED] md-to-py-XII: first heatmap-driven eager-reference demotion round (blocked until 2026-07-17+ or 50 post-repair runs).

## Implementation Plan
## Plan

## Approach

Use the approved design-only scope. Do not demote implement references in this round.

Demote exactly two current design eager-closure members:

- `skills/shared/session-setup-output.md`: heatmap evidence row for design shows `reads_observed=0 / transcript_runs_observed=70`. It is currently pulled eager by the Step 0a “Use ... for setup KVs” directive.
- `skills/shared/external-reviewers.md`: heatmap evidence row for design shows `reads_observed=0 / transcript_runs_observed=70`. It is currently pulled eager by the Step 0a “procedure in ... external-reviewers.md” directive.

Keep both referenced file bodies byte-identical. Reword only the load directives in `skills/design/SKILL.md` so the closure scanner no longer treats them as eager reads. Preserve the inlined Step 0a branch handling.

Expected eager-closure drop: 159 lines, 11,063 bytes, about 2,763 estimated tokens before small wording deltas.

## Files to modify/create

### UPDATED: skills/design/SKILL.md

Reword the Step 0a setup-KV line near the session setup wrapper.

Replace the eager directive shape:

- Avoid `Use ... session-setup-output.md ... for ...`.
- Keep the exact KVs to parse in the skill body.
- Keep a maintainer contract pointer to `skills/shared/session-setup-output.md` without `Read`, `Use ... for`, `MANDATORY`, or other scanner-trigger words.

Reword the Step 0a degraded-tools gate line.


- Avoid `procedure in ... external-reviewers.md`.
- State that the Python wrapper owns the degraded-tools gate.
- Keep the existing `STEP0_STATUS` branch table and `AskUserQuestion` behavior.
- Keep a maintainer contract pointer to `skills/shared/external-reviewers.md` without making it an eager read.

Do not touch anti-halt, NEVER, background-wait, plan-review, or validator-failure eager or conditional references.

### UPDATED: python/skill-closure-baseline.json

After the `SKILL.md` rewording, refresh only the design closure baseline values to bank the lower eager closure.

Expected design `files` should remove:

- `skills/shared/session-setup-output.md`
- `skills/shared/external-reviewers.md`

Leave unrelated target rows unchanged unless the baseline writer proves they also changed from current source.

### UPDATED: python/tests/lint/test_lint_skill_closure_growth.py

The live design-scan regression test currently pins both demoted files as eager closure members, so verification fails after the demotion even when the scan and baseline are otherwise correct. Update `test_real_design_scan_keeps_plan_review_eager_and_branch_refs_conditional()` to match the new closure state:

- Assert `skills/shared/session-setup-output.md` and `skills/shared/external-reviewers.md` are no longer in the eager set (`result.files`).
- Mirror the live scan for the demoted paths: if the rewording leaves them fully untracked, assert they are absent from both `result.files` and `result.conditional_files`; if it demotes them to conditional, assert they appear in `result.conditional_files`. Match whichever state the SKILL.md rewording actually produces.
- Keep the existing expectations unchanged: `skills/design/references/plan-review.md` stays eager and branch-only references stay conditional.

### MAY_UPDATE: python/larch/lint/lint_skill_closure_growth.py

Do not change this file by default.

Only update it if the safest readable wording cannot preserve the Step 0a contract while dropping the two files from eager closure. If touched, keep the rule narrow and add or update focused tests for the exact scanner behavior.

## Edge cases

- The low read rate for `validator-failure.md` is expected because it is already conditional. Do not demote it.
- Keep compaction-resilience duplication eager even if heatmap rows are low.
- The degraded-tools branch must still handle `needs-degraded-decision`, `degraded-one-down`, and `degraded-both-down-hard-fail` exactly as before.
- If a fresh heatmap no longer shows `0 / 70` or better never-read evidence for either file, stop and do not force a demotion.

## Failure modes

- A wording change may still match `SESSION_SETUP_OUTPUT_RE` or `EXTERNAL_REVIEWERS_PROCEDURE_RE`, so the closure does not drop.
- A wording change may accidentally turn a contract pointer into a conditional read, increasing conditional closure unexpectedly.
- Updating the baseline before checking the live report may bank the wrong numbers.
- A generated heatmap TSV may dirty the tree. Use it as evidence, but keep the feature diff limited unless repo convention requires committing that artifact.

## Testing strategy

1. Run a fresh heatmap when implementing:
   - `python3 python/cli.py token measure-references-heatmap`
   - Confirm design transcript coverage satisfies the issue gate.
   - Confirm both demotion candidates show `reads_observed=0 / transcript_runs_observed>=50` or equivalent stronger evidence.
2. Run:
   - `python3 python/cli.py skill-closure report`
   - Confirm design eager files no longer include `skills/shared/session-setup-output.md` or `skills/shared/external-reviewers.md`.
3. Refresh or manually update `python/skill-closure-baseline.json` with the new design metrics.
4. Run:
   - `python3 python/cli.py lint skill-closure-growth`
5. Run the updated closure regression test:
   - `python3 -m pytest python/tests/lint/test_lint_skill_closure_growth.py`
6. Run changed-file relevant checks:
   - `python3 python/cli.py checks run-relevant`

confidence: medium

## Acceptance

1. Run a fresh heatmap when implementing:
   - `python3 python/cli.py token measure-references-heatmap`
   - Confirm design transcript coverage satisfies the issue gate.
   - Confirm both demotion candidates show `reads_observed=0 / transcript_runs_observed>=50` or equivalent stronger evidence.
2. Run:
   - `python3 python/cli.py skill-closure report`
   - Confirm design eager files no longer include `skills/shared/session-setup-output.md` or `skills/shared/external-reviewers.md`.
3. Refresh or manually update `python/skill-closure-baseline.json` with the new design metrics.
4. Run:
   - `python3 python/cli.py lint skill-closure-growth`
5. Run the updated closure regression test:
   - `python3 -m pytest python/tests/lint/test_lint_skill_closure_growth.py`
6. Run changed-file relevant checks:
   - `python3 python/cli.py checks run-relevant`

confidence: medium

diff_lines: 55

## Test plan
(no test plan section in plan-file)
