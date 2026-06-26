### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:74-88
- **Concern**: Auto-boundary must reject non-Mapping `gh` JSON before dict spread. Scenario: The plan degrades non-zero `gh` exit and JSON decode failures, but not a decoded non-object (`[]`, scalar, or valid JSON that is not a mapping). `{**payload, "number": ...}` and `payload["closedAt"]` raise `TypeError`/`KeyError`, bypassing the documented exit-0 boundary-unavailable path and breaking the no-`gh`/degraded-contract parity.
- **Proposed resolution**: After `_run_gh_json`, require `isinstance(payload, Mapping)` (and non-empty if desired); otherwise return the same `BoundaryResult` unavailable branch used for malformed JSON.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/voter-calibration/scripts/voter-calibration.md:119-121
- **Concern**: Partition harness greps need pinned pre/post section heading literals. Scenario: The plan mandates pre/post voter partition greps (lines 146-149) but only names generic "pre-incentive" / "post-incentive" sections without stable `## ...` headings. Implementer-chosen titles can diverge from harness `awk` delimiters, yielding flaky tests or greps that pass without true section isolation.
- **Proposed resolution**: Document exact era slice headings (for example `## Pre-incentive era` / `## Post-incentive era`) in `voter-calibration.md` and reference the same literals in the harness partition assertions.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:95-96
- **Concern**: Exclusion dedup must use `_resolve_ground_truth_run_dir_key(run_dir, log_root=log_root)`, not `run_dir.name`. Scenario: The plan groups runs by "unique run dir" and failure modes claim partition greps prevent basename collision, but only name `_ground_truth_run_dir` for tagging. `design/run-1` and `implement/run-1` share basename `run-1`. A `run_dir.name` exclusion set merges them, so the reported missing-`started_at` count can be wrong while pre/post row assignment and voter partition greps still pass.
- **Proposed resolution**: Pin exclusion and any run-level sets to `_resolve_ground_truth_run_dir_key(run_dir, log_root=log_root)` (always pass `log_root`). Add a harness with the same basename under `design/` and `implement/` where only one run lacks `started_at`, and assert the exclusion count is `1`.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/voter-calibration/scripts/test-voter-calibration.sh:146-149
- **Concern**: Partition harness needs pinned era section heading delimiters. Scenario: The plan requires pre/post voter isolation greps but does not define the markdown headings that bound each era slice. Without pinned titles, awk/grep anchors are ambiguous and can false-pass (global grep) or false-fail.
- **Proposed resolution**: Pin headings in `voter-calibration.md` (for example `## Pre-incentive corpus` and `## Post-incentive corpus` for `--era all`) and reference those exact strings in the harness partition assertions.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:74-87
- **Concern**: Auto-boundary must reject non-Mapping `gh` JSON before normalize/shipped. Scenario: `_run_gh_json` only lists decode failure and empty payload. `gh issue view` can return JSON `null`, a scalar, or an array. `{**payload, "number": ...}` or `_merged_issue_index` then raises `TypeError`/`KeyError` instead of the documented boundary-unavailable exit `0`.
- **Proposed resolution**: After `json.loads`, require `isinstance(payload, Mapping)` (and treat `None` as unavailable) before number normalization and `_ground_truth_calibration_incentive_shipped`; document in `voter-calibration.md` edge cases.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/voter-calibration.md:119-121
- **Concern**: Partition harness lacks pinned pre/post section heading literals. Scenario: Tests require `pre-era-voter` only under the pre-incentive section and `post-era-voter` only under post, but rendering and harness never agree on exact heading text. Implementer and test author can pick different markers and partition greps pass or fail for the wrong reason.
- **Proposed resolution**: Pin one heading pair in both rendering and harness (for example `## Pre-incentive Era` / `## Post-incentive Era`) and grep between those anchors in `test-voter-calibration.sh`.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:97-98
- **Concern**: Era slices must keep `## Agreement Table`, not `voting.render_voter_scoreboard`. Scenario: Plan allows shared table builders. `voting.render_voter_scoreboard` emits `## Voter Agreement Scoreboard`, while contract, default output, and harness require `## Agreement Table`. Using the voting helper makes era mode fail mandated heading greps or diverge from the no-flag report.
- **Proposed resolution**: Build era slices with existing `compute_voter_agreement` + local `_table` under `## Agreement Table` plus `render_voter_severity_scoreboard`; do not call `render_voter_scoreboard` / `render_voter_agreement_and_severity_scoreboards` for era output.



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:35-41
- **Concern**: Missing-`started_at` exclusion dedup should mirror `seen_excluded: set[Path]`. Scenario: Plan counts each excluded run once but does not pin dedup shape. `run_dir.name` merges `design/run-1` and `implement/run-1`, under-counting exclusions and mis-bucketing corpora. `analyze_issues._ground_truth_verdict_run_qualifies` already dedups with `set[Path]` on `_ground_truth_run_dir` results.
- **Proposed resolution**: Track excluded runs and bucket TSVs using `run_dir` `Path` objects from `_ground_truth_run_dir`, with `set[Path]` dedup matching `_ground_truth_verdict_run_qualifies`; do not key on basename alone.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:74-84
- **Concern**: `_run_gh_json` / `_resolve_era_boundary_auto` must reject non-Mapping JSON before `{**payload, "number": ...}`. Scenario: The plan degrades JSON decode failures and empty payloads, but a successful decode of a non-object (`[]`, `"str"`, scalar) still reaches `{**payload, "number": GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER}` and `normalized_payload["closedAt"]`, raising `TypeError`/`KeyError` instead of boundary-unavailable exit `0`. Round-4 neutral FINDING_6 remains unaddressed.
- **Proposed resolution**: After JSON load, require `isinstance(payload, Mapping)` (mirror `_incentive_issue_from_gh`); otherwise return unavailable-boundary.



### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/test-voter-calibration.sh:135-149
- **Concern**: Synthetic era fixtures must write `manifest.json` `started_at` at each run root. Scenario: The harness bullets say add manifests for pre/post/missing `started_at`, but only TSV paths are shown and `test-voter-calibration.sh` today writes no `manifest.json`. `_ground_truth_run_started_at_strict` reads `<run_dir>/manifest.json`; without explicit fixture steps every run is excluded, partition greps fail, and era mode cannot be validated.
- **Proposed resolution**: Extend the harness Python fixture to write `design/<run>/manifest.json` (and peers) with ISO `started_at` before/after the cutoff, plus one run with absent/invalid `started_at`.



### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/voter-calibration/scripts/test-voter-calibration.sh:152-156
- **Concern**: Fake-`gh` success coverage omits resolved repo slug required in era output. Scenario: Approach requires "resolved repo slug (when auto-detect attempted)" in era markdown, but fake-`gh` bullets only assert boundary source/timestamp. Implementer can omit the slug and still pass harness while auto-boundary output loses repo provenance the plan documents.
- **Proposed resolution**: Add a grep that the resolved `owner/repo` slug appears in fake-`gh` success output (or in boundary metadata lines).



### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:95-97
- **Concern**: Segmented bucketing must key exclusion and corpora with `_resolve_ground_truth_run_dir_key`. Scenario: Plan says "unique run dir" and failure mode warns on basename collisions, but never pins the key helper. `design/run-1` and `implement/run-1` share a basename; dedupe on `run_dir.name` merges corpora. Partition greps use distinct dir names and will not catch this production collision.
- **Proposed resolution**: Key exclusion sets and pre/post buckets with `_resolve_ground_truth_run_dir_key(run_dir, log_root=log_root)` (same as `analyze_issues.py`); optionally add `design/run-x` + `implement/run-x` fixtures.



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/test-voter-calibration.sh:146-149
- **Concern**: Partition greps need pinned pre/post section headings. Scenario: Tests require `pre-era-voter` only under the "pre-incentive section" but the plan does not pin markdown headings, so awk/grep boundaries are ambiguous and weak partition checks can pass with both voters in one block.
- **Proposed resolution**: Pin headings such as `## Pre-incentive corpus` / `## Post-incentive corpus` in plan + harness and grep between them.



### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/test-voter-calibration.sh:95-108
- **Concern**: Missing test for the new missing-`git` fallback path. Scenario: The plan adds `FileNotFoundError` handling in `_resolve_incentive_repo`, but the harness only exercises missing `gh`, repo-unresolved, and missing-`closedAt` cases. A regression in the missing-`git` branch can still traceback and ship undetected.
- **Proposed resolution**: Add a git-shadow test that keeps `gh` available, removes `git` from `PATH`, and asserts exit `0` plus the boundary-unavailable markdown.



