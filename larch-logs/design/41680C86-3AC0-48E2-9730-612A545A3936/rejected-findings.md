### [Plan Review] FINDING_2

### FINDING_2: Prompt-missing relaunches are not wired into waterfall control flow
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Concern**: The plan says `_prompt_file_for_tool` may return `None` and the slot must be dropped, but phase1/phase2/phase3 loops still unconditionally append `_launch_slot(...)` results. Missing `prompt_files[tool]` cases would still try to launch or break collection instead of using existing drop semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the waterfall phase loops to handle a nullable launch result or explicit drop sentinel, and record the slot as dropped before collection when the resolved prompt is absent.


### [Plan Review] FINDING_5

### FINDING_5: Snapshot run-dir helper risks circular import and logic drift from `/voter-calibration`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Run-directory derivation is specified as duplicated logic or a direct call to `analyze_issues._ground_truth_run_dir`, but `analyze_issues` already imports `voting` at module load, so a top-level `voting -> analyze_issues` import creates a circular-import trap. A copy-paste in `voting.py` can also drift from `/voter-calibration` and ground-truth windowing, skewing recency ordering and rollups.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extract `_ground_truth_run_dir` (and timestamp reader if needed) into a small shared module imported by both `analyze_issues` and `voting`, or move the helper into `voting.py` and repoint `analyze_issues` to import it. State the chosen ownership explicitly in the plan.
  - From Cursor-Pragmatic: The plan tells `voting.py` to call `analyze_issues._ground_truth_run_dir` / `_ground_truth_run_started_at`, but `analyze_issues` already imports `voting` at module load. A top-level import in `voting.py` creates a circular import and can break snapshot CLI or dispatch. Move `_ground_truth_run_dir` and the manifest timestamp reader into `voting.py` (or a small shared module both import). Keep thin wrappers in `analyze_issues` for ground-truth callers. Have the new snapshot discovery call the `voting` helpers directly; do not add `voting -> analyze_issues` imports.


### [Plan Review] FINDING_6

### FINDING_6: `/voter-calibration` analyzer not wired through base-tool rollup helper
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds base-tool normalization in `python/voting.py`, but it never wires the existing `/voter-calibration` analyzer through that helper, so the report still splits codex-plan-fidelity, codex-pragmatism, and cursor-validity into separate rows instead of one base-tool rollup. That leaves the advertised per-voter-tool validation path fragmented, so the new incentive cannot be measured the way the feature description requires.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Update skills/voter-calibration/scripts/voter-calibration.py to reuse the new base-tool rollup helper for its global section, and refresh skills/voter-calibration/scripts/test-voter-calibration.sh to expect merged codex and cursor rows.


### [Plan Review] FINDING_7

### FINDING_7: Test plan omits `design_tmpdir` fallback branch for log-root resolution
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The test plan covers consumer-root resolution only with env vars set, but it never exercises the `design_tmpdir` fallback branch of `_resolve_voter_calibration_log_root` that plan-review dispatch will use when `LARCH_CONSUMER_REPO` and `CLAUDE_PROJECT_DIR` are absent. A regression in that branch could still point plan-review at the plugin checkout's `larch-logs`, feeding prompt feedback from the wrong corpus on the main dispatch path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a focused integration test that unsets the consumer-repo env vars, supplies a design tmpdir rooted in a consumer worktree, and asserts the snapshot argv targets that worktree's larch-logs.
```

**Merge notes**

- **FINDING_1 + FINDING_6** → merged **FINDING_1** (same code-review log-root gap; different anchor wording).
- **FINDING_5 + FINDING_7** → merged **FINDING_5** (same circular-import / run-dir ownership risk).
- **FINDING_2, 3, 4, 8, 9** kept separate (distinct fixes or paths).
- No `[OUT_OF_SCOPE]` inputs; no empty merge attestation.


