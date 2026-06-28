# Review Round 1

- Mode: `diff`
- 4 accepted, 5 rejected (4 neutral)

## Accepted Findings

### FINDING_1: Ambiguous JSONL joins counted in fluff-analysis false-negative rows
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: When two same-round JSONL records share a FINDING token, `_lookup_jsonl_record()` can return `"ambiguous"`. `rejected_analysis` skips the TSV row in that case, but `fluff-analysis` still counts it in neutral-rate and important-reject-rate, distorting false-negative metrics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Skip the TSV row when _lookup_jsonl_record returns "ambiguous", mirroring rejected_analysis.
  - From codex-specialist-edge-cases: Skip rows when _lookup_jsonl_record() returns "ambiguous".


### FINDING_2: Missing degraded `--realized-outcomes` harness coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-realized-outcomes
- **Severity**: important
- **Concern**: `test-voter-calibration.sh` only asserts the offline success path with `--filed-issue-details-json`. Plan-required degraded branches (`fetch_main()` / missing `gh`, `load_issues()` `SystemExit`, `gh_unavailable` / `repo_unresolved` fail-open) are untested, so regressions can abort reports, exit non-zero, leak temp files, or bypass era degraded handling without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add tests that assert skipped/degraded note and exit 0 for those paths.
  - From cursor-specialist-testing: Add harness cases: no-gh PATH + filed-OOS fixture + --repo expecting Skipped: gh_unavailable exit 0; malformed issue dump expecting bulk_load_failed/skipped note exit 0.
  - From dyn-dyn-realized-outcomes: Add fixture cases that run `--realized-outcomes` without `gh` on `PATH`, with a truncated issue dump, and with `--era` plus boundary-unavailable stubs; assert `## Realized-outcome voter calibration` skip lines, exit `0`, and no uncaught `SystemExit`.


### FINDING_4: Zero-YES voters omitted from false-negative YES table
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-testing, codex-generalist
- **Severity**: important
- **Concern**: Only voters with at least one YES vote are emitted in the false-negative table. Voters who only cast NO or EXONERATE on eligible panels are omitted entirely, so the report cannot show the required `n/a` row (`yes_votes=0`, `false_negative_yes_rate=n/a`). Example: on accepted/neutral panels where Claude votes YES and Codex/Cursor only vote NO, the table reports Claude only and omits Codex/Cursor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Track every eligible voter that appears on a parseable panel, even if all of their votes are NO, and render n/a when yes_votes is zero.
  - From codex-specialist-testing: Seed rows for voters before YES filtering, keep yes_votes at 0 for NO-only voters, and add a zero-YES fixture plus assertion
  - From codex-generalist: Store all parseable voters in `voters`, then in `_compute_false_negative_yes_rates()` create an aggregate record for each voter, increment `yes_votes` only for `YES`, and leave the rate as `None` when `yes_votes == 0`.


### FINDING_6: `load_issues()` forced into lenient mode hides bulk-load failure
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: `load_issues()` is called in lenient mode. Duplicate-heavy or truncated issue dumps no longer trigger the degraded realized-outcomes note and instead render partial metrics as if loading succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Call `load_issues(..., lenient=False)` and surface the SystemExit path as degraded.


