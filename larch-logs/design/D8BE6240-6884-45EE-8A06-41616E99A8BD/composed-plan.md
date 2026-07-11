## Plan

## Approach

Canonicalize every generated bug title through `title_match.BUG_PREFIX`.

Use `[BUG]` in the shipped stall-recovery title contract. Continue accepting mixed-case `[Bug]` only as historical input; do not change `bug_title_match`, its compatibility tests, or `larch-logs/`.

## Files to modify/create

### UPDATED: python/larch/state/_report.py

- Import the shared `title_match` module.
- Build terminal-failure and escalation titles with `title_match.BUG_PREFIX`.
- Remove both mixed-case generation literals.

### UPDATED: python/larch/design/design_terminal.py

- Build the chat-fallback heading with `title_match.BUG_PREFIX`.
- Strip the canonical prefix when deriving a title from generated content.
- Continue stripping legacy `[Bug]` so old persisted reports remain usable.
- Keep the existing lifecycle-prefix lint baseline entry for the intentional compatibility literal.

### UPDATED: python/stall-recovery-report.md

- Change the canonical terminal and escalation title-format examples from `[Bug]` to `[BUG]`.
- If documenting mixed-case `[Bug]`, describe it only as accepted historical input rather than a generated-title contract.

### UPDATED: scripts/file-failure-report-cross-repo.sh

- Expand the Tier B raw-report heading regex to reject both canonical `[BUG]` and historical `[Bug]` headings.
- Keep the match narrow to `/implement` and `/design` report headings.

### UPDATED: scripts/test-file-failure-report-cross-repo.sh

- Change generated report fixtures to canonical `[BUG]`.
- Cover canonical raw-heading rejection for both `/implement` and `/design`.
- Retain focused legacy `[Bug]` raw-heading coverage so backward-compatible rejection cannot regress.

### UPDATED: python/tests/design/test_design_lifecycle.py

- Update the mocked composed Tier A report heading to canonical `[BUG]`.
- Preserve the test’s existing filing and normalization behavior.

## Edge cases

- Historical reports and comments may still start with `[Bug]`.
- Canonical `[BUG]` headings may appear in Tier B comment slices and must trigger the raw-body safety rejection.
- The lifecycle-prefix lint forbids new production string literals where `title_match.BUG_PREFIX` can be used.
- The stall-recovery report contract must match runtime-generated terminal and escalation titles.

## Failure modes

- Updating generation without the title-strip consumer can leak `[BUG]` into the GitHub issue title.
- Updating runtime generation without the stall-recovery contract leaves maintainers documenting the obsolete mixed-case prefix.
- Replacing the shell regex with a canonical-only match can allow historical raw reports into Tier B comments.
- Removing the legacy `removeprefix` literal or its baseline row can break compatibility or lint validation.

## Testing strategy

- Run the focused Python lifecycle test containing the Tier A report fixture.
- Run `python/tests/state/test_stall_recovery.py` to exercise report composition and issue-input parsing.
- Run `scripts/test-file-failure-report-cross-repo.sh` for canonical and legacy raw-heading rejection.
- Run the lifecycle-prefix literal lint against the changed production modules.
- Grep outside `larch-logs/` to confirm generated-title sites and the stall-recovery contract use `[BUG]`, while any remaining `[Bug]` references are explicitly compatibility-only.
- Leave the mixed-case matcher tests in `test_learn_from_bugs.py`, `test_analyze_bugs.py`, and lint-rule detector tests unchanged.

## Acceptance

- Run the focused Python lifecycle test containing the Tier A report fixture.
- Run `python/tests/state/test_stall_recovery.py` to exercise report composition and issue-input parsing.
- Run `scripts/test-file-failure-report-cross-repo.sh` for canonical and legacy raw-heading rejection.
- Run the lifecycle-prefix literal lint against the changed production modules.
- Grep outside `larch-logs/` to confirm generated-title sites and the stall-recovery contract use `[BUG]`, while any remaining `[Bug]` references are explicitly compatibility-only.
- Leave the mixed-case matcher tests in `test_learn_from_bugs.py`, `test_analyze_bugs.py`, and lint-rule detector tests unchanged.

review_status: complete
rounds_completed: 1
difficulty: MODERATE
diff_added: 13
diff_deleted: 10
mechanical_churn: true
diff_lines: 23
