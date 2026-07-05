## Goal
Implement issue #6406: [IMPLEMENTING] [OOS] Reviewer OOS proposal tooling — 3 items.

## Implementation Plan
## Plan

## Approach

Implement the three OOS follow-ups with the smallest shared changes.

1. Replace OOS proposal cap wording from `highest-materiality` to `highest-legitimacy concrete items`.
2. Regenerate generated reviewer agents and pre-rendered reviewer bodies after source prompt edits.
3. Make design OOS annotation map a cap-1 rollup issue URL back to every original accepted OOS block in the filing order.
4. Make rejected-OOS audit read vote outcomes from `findings-classification.tsv`, while keeping markdown footer parsing only as a legacy fallback when the TSV is absent or unusable.

## Files to modify/create

### UPDATED: skills/shared/reviewer-templates.md

Change all four `### Out-of-Scope Observations` cap lines to match the current legitimacy standard:

- `keep only the highest-legitimacy concrete items under skills/shared/oos-acceptance-rubric.md`
- Keep the cap and overflow behavior unchanged.
- Do not loosen in-scope necessity wording.

### UPDATED: agents/code-reviewer.md

Regenerate from `skills/shared/reviewer-templates.md` via `python3 python/cli.py generate code-reviewer-agent`.

### UPDATED: agents/reviewer-plan-fidelity.md

Regenerate from `skills/shared/reviewer-templates.md` via `python3 python/cli.py generate reviewer-plan-fidelity-agent`.

### UPDATED: agents/reviewer-code-robustness.md

Regenerate from `skills/shared/reviewer-templates.md` via `python3 python/cli.py generate reviewer-code-robustness-agent`.

### UPDATED: agents/reviewer-security-structure-tests.md

Regenerate from `skills/shared/reviewer-templates.md` via `python3 python/cli.py generate reviewer-security-structure-tests-agent`.

### UPDATED: agents/reviewer-correctness.md

Manually sync the hand-maintained OOS cap line to `highest-legitimacy concrete items`.

### UPDATED: agents/reviewer-edge-cases.md

Manually sync the hand-maintained OOS cap line to `highest-legitimacy concrete items`.

### UPDATED: agents/reviewer-security.md

Manually sync the hand-maintained OOS cap line to `highest-legitimacy concrete items`.

### UPDATED: agents/reviewer-structure.md

Manually sync the hand-maintained OOS cap line to `highest-legitimacy concrete items`.

### UPDATED: agents/reviewer-testing.md

Manually sync the hand-maintained OOS cap line to `highest-legitimacy concrete items`.

### UPDATED: agents/pre-rendered/reviewer-code-robustness-body.txt

Regenerate with `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/reviewer-correctness-body.txt

Regenerate with `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/reviewer-edge-cases-body.txt

Regenerate with `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/reviewer-plan-fidelity-body.txt

Regenerate with `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/reviewer-security-body.txt

Regenerate with `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/reviewer-security-structure-tests-body.txt

Regenerate with `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/reviewer-structure-body.txt

Regenerate with `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/reviewer-testing-body.txt

Regenerate with `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: skills/shared/oos-acceptance-rubric.md

Add `skills/shared/reviewer-templates.md` to the Update triggers list.

### UPDATED: python/tests/rendering/test_rendering.py

Add prompt drift coverage:

- Assert rendered OOS proposal cap text uses `highest-legitimacy concrete items`.
- Assert checked-in reviewer prompt surfaces no longer contain `highest-materiality`.
- Include template, generated agents, hand-maintained agents, and pre-rendered bodies in the fixture list.

### UPDATED: python/larch/design/design_oos.py

In `file_oos_annotate_main`, preserve the current one-row-per-created-issue behavior for normal batches.

Add a narrow cap-1 rollup path:

- Read `oos-combined.md` after `issue-cap`.
- If combined has exactly one parseable OOS block, the order file has more than one original OOS id, and issue stdout has exactly one successful or deduped URL, annotate every original OOS block from `oos-design-filing-order.txt` with that URL.
- Write one `OOS_FILE_MAP` row per original OOS id.
- Keep failed issue slots excluded.
- Do not infer multi-url mappings when combined count is greater than one or stdout has ambiguous slot data.

This keeps reruns idempotent because `_prepare_sentinel_handled` and `_recover_accepted_from_sentinel` already understand `OOS_FILE_MAP` rows.

### UPDATED: python/tests/design/test_design_oos.py

Add a multi-accepted cap-1 regression:

- Accepted file has at least two original OOS blocks.
- Order file lists both originals.
- Combined file contains one capped rollup block.
- Issue stdout contains only `ISSUE_1_URL`.
- After annotate, every original block has the same `Filed URL`.
- `oos-issues-created.md` contains `OOS_FILE_MAP` rows for every original.
- A prepare rerun with the sentinel skips refiling and preserves annotations.

Also keep a non-rollup multi-slot case covered so normal per-slot mapping does not regress.

### UPDATED: python/larch/report/review_phase_detail.py

Change rejected-OOS audit outcome lookup:

- Add a small classification TSV reader keyed by `finding_id`.
- Prefer `round-*/findings-classification.tsv` `voting_result` for each `OOS_N` or legacy `FINDING_N` block parsed from `oos.md`.
- Treat rows with `voting_result=accepted` as accepted and skip them.
- Treat rejected, neutral, and other non-accepted results as audit candidates.
- Retain the current security-sensitive block skip.
- Fall back to the existing `Vote tally: ... Result=` footer parser only when no usable TSV row exists, to keep older logs readable.

### UPDATED: python/tests/report/test_review_phase_detail.py

Add TSV-first audit tests:

- A malformed or missing `Vote tally` footer still renders a rejected OOS candidate when `findings-classification.tsv` says `rejected`.
- A footer that says rejected is skipped when the TSV says `accepted`.
- A legacy no-TSV fixture still uses footer parsing.
- Security-sensitive blocks remain skipped even when the TSV says rejected.

## Edge cases

- Cap-1 rollups embed original OOS headings indented inside the rollup. Use the filing order file for original ids rather than parsing embedded rollup bodies.
- Partial issue creation must not stamp failed originals.
- Deduped URLs should behave like created URLs because both identify the filed issue.
- Existing accepted blocks with `Filed URL` lines should not get duplicate lines.
- Legacy run logs may lack classification TSVs, so the audit must keep a fallback.

## Failure modes

- If the rollup mapping is ambiguous, leave current conservative behavior rather than stamping wrong originals.
- If generated files drift, `python3 python/cli.py generate check` should fail.
- If TSV parsing fails, rejected-OOS audit should degrade to legacy footer parsing, not fail final report rendering.

## Testing strategy

Run focused checks:

- `python3 python/cli.py generate`
- `python3 python/cli.py generate check`
- `python3 -m pytest python/tests/rendering/test_rendering.py`
- `python3 -m pytest python/tests/design/test_design_oos.py`
- `python3 -m pytest python/tests/report/test_review_phase_detail.py`

Optionally run:

- `make py-lint`
- `make py-test`

## Difficulty

This is MODERATE. The change spans prompt contracts, generated artifacts, design OOS filing idempotency, and final report audit logic. Evidence is direct, but workflow state and generated prompt drift make integration risk real.

## Acceptance

Run focused checks:

- `python3 python/cli.py generate`
- `python3 python/cli.py generate check`
- `python3 -m pytest python/tests/rendering/test_rendering.py`
- `python3 -m pytest python/tests/design/test_design_oos.py`
- `python3 -m pytest python/tests/report/test_review_phase_detail.py`

Optionally run:

- `make py-lint`
- `make py-test`

diff_lines: 210

## Test plan
(no test plan section in plan-file)
