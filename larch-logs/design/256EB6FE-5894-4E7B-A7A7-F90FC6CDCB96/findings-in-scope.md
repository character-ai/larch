### FINDING_1: Auto-boundary must reject non-Mapping `gh` JSON before dict spread
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: `_run_gh_json` / `_resolve_era_boundary_auto` degrade non-zero exit and JSON decode failures, but a successful decode of a non-object (`null`, scalar, or array) still reaches `{**payload, "number": ...}` and `payload["closedAt"]`, raising `TypeError`/`KeyError` instead of the documented boundary-unavailable exit `0` path. This breaks no-`gh`/degraded-contract parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After `_run_gh_json`, require `isinstance(payload, Mapping)` (and non-empty if desired); otherwise return the same `BoundaryResult` unavailable branch used for malformed JSON.
  - From Cursor-Pragmatic: After `json.loads`, require `isinstance(payload, Mapping)` (and treat `None` as unavailable) before number normalization and `_ground_truth_calibration_incentive_shipped`; document in `voter-calibration.md` edge cases.
  - From Cursor-Requirements: After JSON load, require `isinstance(payload, Mapping)` (mirror `_incentive_issue_from_gh`); otherwise return unavailable-boundary.

### FINDING_2: Partition harness needs pinned pre/post section heading literals
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Era-mode partition greps require pre/post voter isolation, but the plan and harness do not pin exact `## ...` heading strings. Implementer-chosen titles can diverge from harness `awk`/grep delimiters, yielding flaky tests, false passes (global grep), or false failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document exact era slice headings (for example `## Pre-incentive era` / `## Post-incentive era`) in `voter-calibration.md` and reference the same literals in the harness partition assertions.
  - From Cursor-Innovation: Pin headings in `voter-calibration.md` (for example `## Pre-incentive corpus` and `## Post-incentive corpus` for `--era all`) and reference those exact strings in the harness partition assertions.
  - From Cursor-Pragmatic: Pin one heading pair in both rendering and harness (for example `## Pre-incentive Era` / `## Post-incentive Era`) and grep between those anchors in `test-voter-calibration.sh`.
  - From Cursor-Requirements: Pin headings such as `## Pre-incentive corpus` / `## Post-incentive corpus` in plan + harness and grep between them.

### FINDING_3: Exclusion dedup must not key on `run_dir.name` alone
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Grouping or excluding runs by basename merges distinct corpora (`design/run-1` vs `implement/run-1`). The reported missing-`started_at` exclusion count and era bucketing can be wrong while partition greps still pass, because those greps use distinct directory names and will not catch basename collisions in production logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin exclusion and any run-level sets to `_resolve_ground_truth_run_dir_key(run_dir, log_root=log_root)` (always pass `log_root`). Add a harness with the same basename under `design/` and `implement/` where only one run lacks `started_at`, and assert the exclusion count is `1`.
  - From Cursor-Pragmatic: Track excluded runs and bucket TSVs using `run_dir` `Path` objects from `_ground_truth_run_dir`, with `set[Path]` dedup matching `_ground_truth_verdict_run_qualifies`; do not key on basename alone.
  - From Cursor-Requirements: Key exclusion sets and pre/post buckets with `_resolve_ground_truth_run_dir_key(run_dir, log_root=log_root)` (same as `analyze_issues.py`); optionally add `design/run-x` + `implement/run-x` fixtures.

### FINDING_4: Era slices must keep `## Agreement Table`, not `voting.render_voter_scoreboard`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `voting.render_voter_scoreboard` emits `## Voter Agreement Scoreboard`, while contract, default output, and harness require `## Agreement Table`. Using the voting helper for era output makes era mode fail mandated heading greps or diverge from the no-flag report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Build era slices with existing `compute_voter_agreement` + local `_table` under `## Agreement Table` plus `render_voter_severity_scoreboard`; do not call `render_voter_scoreboard` / `render_voter_agreement_and_severity_scoreboards` for era output.

### FINDING_5: Synthetic era fixtures must write `manifest.json` `started_at` at each run root
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The harness bullets describe pre/post/missing `started_at` fixtures but only show TSV paths; `test-voter-calibration.sh` today writes no `manifest.json`. `_ground_truth_run_started_at_strict` reads `<run_dir>/manifest.json`, so without explicit fixture steps every run is excluded, partition greps fail, and era mode cannot be validated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend the harness Python fixture to write `design/<run>/manifest.json` (and peers) with ISO `started_at` before/after the cutoff, plus one run with absent/invalid `started_at`.

### FINDING_6: Fake-`gh` success coverage should assert resolved repo slug in era output
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan requires "resolved repo slug (when auto-detect attempted)" in era markdown, but fake-`gh` harness bullets only assert boundary source/timestamp. Implementer can omit the slug and still pass harness while auto-boundary output loses repo provenance the plan documents.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a grep that the resolved `owner/repo` slug appears in fake-`gh` success output (or in boundary metadata lines).

### FINDING_7: Missing test for missing-`git` fallback path in `_resolve_incentive_repo`
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds `FileNotFoundError` handling in `_resolve_incentive_repo`, but the harness only exercises missing `gh`, repo-unresolved, and missing-`closedAt` cases. A regression in the missing-`git` branch can still traceback and ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a git-shadow test that keeps `gh` available, removes `git` from `PATH`, and asserts exit `0` plus the boundary-unavailable markdown.
