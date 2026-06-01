# Review Round 2

- Mode: `diff`
- 16 accepted, 4 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: Pre-push flush stubs and empty/wrong run-log batches
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `flush_logs_pre` / batch rendering in `run_logs.py` does not port `refresh-run-logs.sh` helpers (`flush-execution-issues`, `write-final-report`, real token/timing re-render, `capture-session-transcript`, full step9a1 heuristics). Stubs can write empty NDJSON for execution issues when markdown exists, omit transcripts/tokens/timing, and still pass happy-path tests—so Phase 7 cutover would claim flush parity while publishing incomplete or wrong `larch-logs` artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: `effective_run_id` path traversal when state `RUN_ID` absent
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: When state-file `RUN_ID` is absent, `effective_run_id()` returns unvalidated `ctx.run_id`; a malicious or buggy Phase 7 driver could set `../../../outside` and escape `ctx.tmpdir` for manifest/transcript paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_11: Session transcript published without redaction choke point
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `flush_logs_pre` copies/commits raw `session-transcript-refresh.txt` into the run tree without `redact.redact()` or the full `render-session-transcript` + `larch_log_redact_file` pipeline; agent session secrets could land in public `larch-logs` on GitHub.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_12: `copytree` follows symlinks into published run logs
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Default `shutil.copytree` follows symlinks and inlines target content; a symlink under the staging run dir (e.g. to `~/.ssh/id_ed25519`) could be copied into `larch-logs/implement/<run-id>/` for git add/commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_13: `plan_goals_file` read without repo containment when `cwd` unset
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `pr_body` reads `plan_goals_file` without `path_under_repo` when `cwd` is `None`; a caller could pass `/etc/passwd` or another sensitive path and embed goal text into a PR body sent to `gh` (even if redacted).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_14: Manifest recovery picks wrong `run_id` / splits paths across directories
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Manifest recovery selects newest implement child by mtime or disagrees with `effective_run_id` write paths when manifest is corrupt or multiple runs share a tmpdir—manifest vs batch files can land under different run directories and cross-run content can be committed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_15: Token/timing batch copy not fail-closed on redaction truncation marker
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Token/timing batch copy does not fail closed when redaction leaves a PEM/truncation marker (`[content truncated in redact output`); truncated secrets could be committed to `larch-logs` batches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: `repo_unavailable` disposition skip not unit-tested
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Acceptance criteria require `repo_unavailable` skip coverage; without `test_disposition_skips_repo_unavailable`, Phase 7 could call `disposition_ok` with `repo_unavailable=True` and get unexpected blocking behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: `tokens.py` not wired into flush entrypoints
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `tokens.scrape_run` exists but is not called from `run_logs` flush paths; token/timing batches stay empty stubs at flush time even when sidecars exist, so telemetry the bash path publishes is lost on cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Merge routing and flush-recovery test matrix incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test_merge.py` does not exhaustively cover the eight `MERGE_RESULT` literals, admin-first / no-admin-fallback paths, or flush-recovery cases (K1, P1, N1, N2a). Regressions in `_attempt_merge`, `_version_race_gate`, `_flush_recoverable`, or flush pre/post behavior could reach Phase 7 undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: Bash parity harness missing recovery variants and Python path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test_merge_bash_parity.py` only exercises BEHIND → `main_advanced` via bash; K1/P1/N1/N2a and shared fixtures from `scripts/test-merge-pr.sh` are unguarded, and the harness does not run `merge.merge_pr` alongside `merge-pr.sh`, so Python/bash drift on flush-commit recovery could ship silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: `ensure_pr` / `test_pr.py` missing planned recovery and escalation tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Planned tests for create-conflict recovery, `ctx.draft=True`, and push failure escalating to `force_push_recovery` on an existing OPEN PR are absent; regressions could stop escalating after flush commits and leave remote behind local without pytest failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_6: `merge_pr` treats non-fatal flush skips as fatal vs bash/ship-pr
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Python `merge_pr` aborts on `flush_logs_pre` skips outside `REFRESH_SKIP_MERGE_OK` (e.g. no run id / `NO_LOGS_COMMIT=true`) where bash `refresh` + `merge-pr.sh` would continue and still merge; a driver replacing only `merge-pr.sh` may block merge on benign refresh outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: `merge_pr` not idempotent after successful merge / post-merge flush skip
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After a post-merge `flush_logs_pre` skip, re-entry with `MERGE_RESULT=merged` still attempts `gh pr merge` instead of a no-op; there is no early probe for PR state `MERGED`/`CLOSED`, so re-invoked `merge_pr` can retry merge incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: `update_manifest` accepts unknown kwargs into `steps_ran`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Callers passing undocumented keys (e.g. `version`, `updated_at`) can corrupt manifest schema by storing them inside `steps_ran`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_9: Text CI fallback substring false positives in `gh.py`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Text CI fallback uses substring matching instead of bash word-boundary parity; check text containing `fail` as a substring can block merge as `ci_not_ready` incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


