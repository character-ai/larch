### FINDING_2: Partition harness needs pinned pre/post section heading literals
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Era-mode partition greps require pre/post voter isolation, but the plan and harness do not pin exact `## ...` heading strings. Implementer-chosen titles can diverge from harness `awk`/grep delimiters, yielding flaky tests, false passes (global grep), or false failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document exact era slice headings (for example `## Pre-incentive era` / `## Post-incentive era`) in `voter-calibration.md` and reference the same literals in the harness partition assertions.
  - From Cursor-Innovation: Pin headings in `voter-calibration.md` (for example `## Pre-incentive corpus` and `## Post-incentive corpus` for `--era all`) and reference those exact strings in the harness partition assertions.
  - From Cursor-Pragmatic: Pin one heading pair in both rendering and harness (for example `## Pre-incentive Era` / `## Post-incentive Era`) and grep between those anchors in `test-voter-calibration.sh`.
  - From Cursor-Requirements: Pin headings such as `## Pre-incentive corpus` / `## Post-incentive corpus` in plan + harness and grep between them.


### FINDING_5: Synthetic era fixtures must write `manifest.json` `started_at` at each run root
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The harness bullets describe pre/post/missing `started_at` fixtures but only show TSV paths; `test-voter-calibration.sh` today writes no `manifest.json`. `_ground_truth_run_started_at_strict` reads `<run_dir>/manifest.json`, so without explicit fixture steps every run is excluded, partition greps fail, and era mode cannot be validated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend the harness Python fixture to write `design/<run>/manifest.json` (and peers) with ISO `started_at` before/after the cutoff, plus one run with absent/invalid `started_at`.


### FINDING_7: Missing test for missing-`git` fallback path in `_resolve_incentive_repo`
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds `FileNotFoundError` handling in `_resolve_incentive_repo`, but the harness only exercises missing `gh`, repo-unresolved, and missing-`closedAt` cases. A regression in the missing-`git` branch can still traceback and ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a git-shadow test that keeps `gh` available, removes `git` from `PATH`, and asserts exit `0` plus the boundary-unavailable markdown.


