# Review Round 1

- Mode: `diff`
- 3 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Blank gh stdout misreported as incentive not shipped
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When `gh` exits 0 with empty stdout, `_run_gh_json` parses `{}` and the auto-boundary path reports `calibration_incentive_not_shipped` instead of treating the fetch as unavailable (`gh_issue_view_unavailable`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Treat blank stdout or empty object as `gh_issue_view_unavailable` before shipped predicate
  - From codex-specialist-correctness-output.txt: return unavailable on blank stdout before parsing, or return a sentinel from `_run_gh_json`


### FINDING_2: Era fixtures break byte-stable default-mode report
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-era-bucketing-output.txt, dyn-dyn-era-harness-output.txt
- **Severity**: important
- **Concern**: Era test fixtures (`run-pre-era`, `run-post-era`, `run-missing-started-at`) live in the same synthetic `larch-logs` tree used by no-flag default assertions. Default mode discovers all TSVs, so era-only voters and higher corpus counts appear without `--era`, violating the plan’s byte-stable default path. The harness only greps legacy substrings and does not catch the regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Isolate era fixtures to a separate log-root or add byte-stable default corpus guards
  - From dyn-dyn-era-bucketing-output.txt: Put era fixtures in a separate log-root (or subdirectory) used only by `--era` tests, or add an explicit full-report hash/cmp guard on the default invocation so corpus growth cannot pass silently.
  - From dyn-dyn-era-harness-output.txt: Keep the original five-run fixture in a separate log root for default-mode assertions (or snapshot the full default report and diff it), and build era-only runs in a second fixture directory used exclusively by `--era` tests. Add negative greps such as `pre-era-voter` / `post-era-voter` / `missing-era-voter` must not appear in default-mode output, plus an exact corpus-count assertion if byte stability remains a contract.


### FINDING_3: Harness omits invalid `started_at` exclusion fixture
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-era-harness-output.txt
- **Severity**: important
- **Concern**: The harness asserts exclusion for missing or invalid `started_at` but only fixtures a run with no `manifest.json`. Invalid values (empty manifest, empty string, non-ISO date) are untested, so bucketing regressions for invalid `started_at` could ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add manifest with non-ISO started_at and assert exclusion from both eras
  - From dyn-dyn-era-harness-output.txt: Add fixtures such as `manifest.json` with `{}`, `{"started_at": ""}`, or `{"started_at": "not-a-date"}` under distinct run dirs, bump the expected exclusion count, and assert those voters never appear in either era slice.


