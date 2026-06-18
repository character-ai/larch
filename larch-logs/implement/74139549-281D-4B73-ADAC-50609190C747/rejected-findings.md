### [rejected] FINDING_14

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_14: Sentinel `touch()` operations lack symlink guards
- **Reviewer(s)**: dyn-trust-boundary-output.txt
- **Severity**: important
- **Concern**: `step3_loop_write_completed_step3`, `step3_wrapper_write_completed_step3_only` (`python/plan_review.py:155-166`), and `emit_design_plan_preview` (`python/plan_review.py:524`) call `Path.touch()` on `.completed/step-3`, `.completed/step-3.5`, and `.step3-entry-plan-printed` without symlink refusal or `follow_symlinks=False`. A symlink at those paths can mutate files outside `DESIGN_TMPDIR` and spoof pause/resume or plan-preview sentinels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-trust-boundary-output.txt: Before `mkdir`/`touch`, refuse symlink parents and leaves (mirror `phase_driver_write_result_env`), or use `touch(..., follow_symlinks=False)` only after confirming each path is a regular file or absent; create via `O_NOFOLLOW` open where appropriate.
  - From dyn-trust-boundary-output.txt: Reject symlink targets before touch, or create the sentinel with the same `O_NOFOLLOW` / `is_symlink()` guard pattern used for result-env writes.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_15: `latest-reviewer-status.tsv` copy follows destination symlinks
- **Reviewer(s)**: dyn-trust-boundary-output.txt
- **Severity**: important
- **Concern**: `run_plan_review_round` (`python/plan_review.py:762-766`) checks the source `reviewer-status.tsv` is not a symlink but copies into `latest-reviewer-status.tsv` without verifying the destination. `shutil.copyfile` follows a destination symlink and overwrites the link target outside the session tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-trust-boundary-output.txt: Refuse the copy when `latest_status.is_symlink()` or when `latest_status.exists()` and is not a regular file; only copy after `O_NOFOLLOW` creation or after `unlink` of a symlink leaf.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_16: `timing-ledger.tsv` append lacks symlink guard
- **Reviewer(s)**: dyn-trust-boundary-output.txt
- **Severity**: important
- **Concern**: `record_plan_review_round_timing` (`python/plan_review.py:653-656`) appends to `timing-ledger.tsv` with `Path.open("a")` and no symlink guard. A symlink at that path appends timing rows to an arbitrary host file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-trust-boundary-output.txt: Treat `timing-ledger.tsv` like a trust-boundary artifact: refuse symlinks, create with `O_NOFOLLOW | O_CREAT | O_EXCL` on first write, and append only to a verified regular file.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_17: Panel manifest writes lack symlink refusal
- **Reviewer(s)**: dyn-trust-boundary-output.txt
- **Severity**: important
- **Concern**: Native panel dispatch (`python/plan_review_panel.py:90-94,108-110,160-161`) writes `plan-review-slots.ndjson` and prune sidecars with `open("w")` / `write_text()` and no symlink refusal. A symlink at those paths redirects manifest data outside `DESIGN_TMPDIR`, affecting downstream reviewer dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-trust-boundary-output.txt: Before every manifest/sidecar write, require `not path.is_symlink()` and `(not path.exists() or path.is_file())`; prefer `O_NOFOLLOW` creation or the shared atomic writer used for result-env files.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (0 YES)

### FINDING_18: `persist_retally_step3_env` accepts unconstrained `retally-stdout-file` path
- **Reviewer(s)**: dyn-trust-boundary-output.txt
- **Severity**: important
- **Concern**: `persist_retally_step3_env` (`python/plan_review.py:588-597`) reads `--retally-stdout-file` from an unconstrained path via `_read_kv_file`, while only `SCOPE_ANCHOR_FILE` is tmpdir-bound before persistence. A caller supplying a sensitive host file can leak path-valued keys such as `SCOPE_ANCHOR_FILE` and `VOTING_TALLY_FILE` into `.step3-review-result.env` and stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-trust-boundary-output.txt: Require `retally-stdout-file` to resolve under the validated `DESIGN_TMPDIR`, reject symlinks, and validate every path-valued key the same way before `phase_driver_write_result_env`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

