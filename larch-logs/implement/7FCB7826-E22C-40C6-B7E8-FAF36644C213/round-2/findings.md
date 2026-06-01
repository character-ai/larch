### FINDING_1: Duplicated rename parse/WARN block in phase drivers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `design-publish.sh` (lines 287–303) duplicates the tracking-issue-write rename parse/WARN logic already present in `design-init-runparams.sh`. Future changes to the rename stdout contract may be fixed in one driver and missed in the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared helper in `lib-phase-driver.sh` and use it from both drivers.

### FINDING_2: Local `parse_kv_from_output` duplicates phase-driver KV pattern
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `design-publish.sh` (lines 35–48) implements local `parse_kv_from_output` that mirrors an emerging phase-driver KV parsing pattern; a third driver may copy the same loop again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Move parsing to `lib-phase-driver.sh` with allowlisted keys when a third caller appears.

### FINDING_3: Structural tests omit `${REPO:+--repo}` pin on `design-publish.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required `${REPO:+--repo}` forwarding on `design-publish.sh` is not pinned in `scripts/test-design-structure.sh` (lines 1032–1058). `REPO` forwarding on upsert/publish/rename/render could be removed without CI failure, so forked or non-default-repo design runs could target the wrong GitHub repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `grep -Fq '${REPO:+--repo' "$DESIGN_PUBLISH_SH"` (or per-helper pins) alongside existing (15b) driver checks.

### FINDING_4: Marker-before-publish ordering under-tested (structure + unit harness)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-test-harness-isolation-output.txt
- **Severity**: important
- **Concern**: Reentry marker must precede `design-log-publish.sh` (not only tracking-issue rename). Static check 25 in `test-design-structure.sh` pins marker before `[DESIGNED]` rename but not before publish; `test-design-publish.sh` happy-path checks only `plan-block-write` → upsert → publish in `CALL_LOG` and does not log or assert `design_reentry_marker_write` before publish/rename. A regression that runs publish/rename before the marker could pass happy-path unit tests (and partial structure pins) while breaking session-cache reentry guard during publish in live `/design` runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Log marker stub calls in `CALL_LOG` and assert ordering vs publish/rename.
  - From cursor-specialist-testing-output.txt: Add `publish_marker_line < publish_log_line` line-order assertion on `design-publish.sh`.
  - From cursor-specialist-testing-output.txt: Add source line-order `marker before design-log-publish` in `test-design-structure.sh` or runtime ordering in `test-design-publish.sh`.
  - From cursor-specialist-edge-cases-output.txt: Assert marker invocation between `plan-block-write` and `design-log-publish` in `CALL_LOG`.
  - From cursor-specialist-plan-fidelity-output.txt: Stub or log marker write in the happy-path case and assert marker precedes `design-log-publish` and `tracking-issue-write` in the ordered trace.
  - From dyn-test-harness-isolation-output.txt: After `run_publish`, assert reentry marker file exists (e.g. `$HOME/.cache/larch/sessions/design-completed-42-9999` for `--issue 42 --claude-pid 9999`) and mtime is not after the first `design-log-publish` entry in `PUBLISH_LOG` / `CALL_LOG`, or add a thin test-only wrapper that logs marker invocation before publish.

### FINDING_5: Driver exit 1 conflates plan-block-write failure with result-env write failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-euo-safety-output.txt
- **Severity**: important
- **Concern**: On the plan-block-write failure path, `write_result_env_and_emit` only calls `emit_kv` after `phase_driver_write_result_env` succeeds (`design-publish.sh` 146–155). If the atomic result-env write fails, the driver exits `1` without writing `.design-publish-result.env` and without emitting `PLAN_WRITE_OK=false` on stdout, while the orchestrator still treats exit `1` as the normal plan-write failure path (`SKILL.md` 1356–1362). Plan may already be on GitHub; operator may see no preserve banner, Step 5c may be skipped, and Step 6 cleanup gating may not match the “plan published, preserve tmpdir” contract. Sibling `design-init-runparams.sh` emits machine lines before `phase_driver_write_result_env` on failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use a distinct exit code or write result env earlier with an explicit orchestrator branch.
  - From cursor-specialist-edge-cases-output.txt: Reserve exit `1` for plan-write only; use distinct exit for contract/tail failures or ERR-trap partial result env; extend harness for result-env and source failures.
  - From dyn-bash-euo-safety-output.txt: On the failure branch, emit `PLAN_WRITE_OK=false` and `FINAL_SUMMARY_PATH` (and any `WARN=` lines) to stdout before calling `phase_driver_write_result_env`, or split `write_result_env_and_emit` so contract-critical `emit_kv` calls precede the write the way Step 0b drivers do; keep `exit 1` after both when plan-block-write failed.

### FINDING_6: Missing harness cases for marker-fail-continue and RENAMED= omit WARN
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Offline harness does not cover marker non-blocking failure, omitted `RENAMED=` warn paths, or exercise `RENAMED_OMIT_LINE` despite stub support. Regressions in append-tool-failure, `WARN=` for those branches, or rename helper contract dropping `RENAMED=` would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add marker-fail-continue and RENAMED-omit stub scenarios.
  - From cursor-specialist-testing-output.txt: Add case with `RENAMED_OMIT_LINE=true` asserting `WARN=` in `.design-publish-result.env`.

### FINDING_7: Unexpected driver exit abort prose not structurally pinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Driver exit codes outside `{0,1}` (`_publish_rc` not 0 or 1) and the fatal abort banner are not pinned in `SKILL.md` / structure tests. Orchestrator prose for fatal driver failures could regress while exit 2/1 pins still pass; operators might parse result env after a crash exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add grep for `design-publish.sh failed (exit ${_publish_rc}); aborting /design` mirroring design-route/init pins.

### FINDING_8: PUBLISH_OK=false / unexpected-publish cases do not assert execution-issues.md
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness cases that skip rename on `PUBLISH_OK=false` or unexpected publish do not assert warnings land in `execution-issues.md`; `append-tool-failure` regressions could silence operator-visible publish failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert `execution-issues.md` contains design Step 5c after those harness cases.

### FINDING_9: Unvalidated `FINAL_SUMMARY_PATH` read in Step 5c orchestrator block
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Parsed `FINAL_SUMMARY_PATH` from `.design-publish-result.env` is used for verbatim file read without tmpdir-prefix or symlink checks. A same-UID writer could point the result env at a sensitive readable file; the orchestrator would emit its contents to top chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Constrain reads to a non-symlink path under `$DESIGN_TMPDIR` or ignore parsed `FINAL_SUMMARY_PATH` for the emit step.

### FINDING_10: Verbatim `WARN=` replay from result env can steer orchestrator
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Step 5c replays parsed `WARN` bodies verbatim to top chat. Tampered `WARN=` lines in `.design-publish-result.env` could inject orchestrator-steering prose into the session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Bound/sanitize WARN replay or allowlist known driver WARN templates only.

### FINDING_11: Non-zero publish rc with `PUBLISH_OK=true` still allows rename
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If `design-log-publish.sh` returns non-zero but stdout still has `PUBLISH_OK=true`, rename may proceed and the tracking title becomes `[DESIGNED]` while log publish failed or is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Force `PUBLISH_OK=false` when `_publish_rc≠0` unless `rc=0`; add harness case.

### FINDING_12: Exit-code contract docs omit result-env failure on exit 1
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `design-publish.md` exit-code table does not document result-env write failure sharing exit `1` with plan-block-write failure, misleading operator/runbook expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Align contract table with implementation or split exit codes.

### FINDING_13: Publish harness stub exports leak between cases
- **Reviewer(s)**: dyn-test-harness-isolation-output.txt
- **Severity**: important
- **Concern**: `test-design-publish.sh` does not reset stub exports between cases that call `bash "$SUBJECT"` directly or via `run_publish`. After **PUBLISH_OK=false** or **unexpected publish**, `PUBLISH_OK_VALUE`, `PUBLISH_STUB_RC`, `PUBLISH_EMIT_OK`, etc. remain exported; later cases (e.g. clear-architecture, upsert failure) inherit polluted state and exercise the wrong publish path while still passing narrow assertions. Only `PLAN_BLOCK_RC` is cleared after the plan-write-failure case; `run_publish` uses `${PUBLISH_STUB_RC:-0}` so prior non-default exports persist across `run_publish` calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-harness-isolation-output.txt: Add a `reset_publish_stub_env()` (or per-case `unset`/`export` block) before every direct `bash "$SUBJECT"` and at the start of `run_publish`, clearing `PLAN_BLOCK_RC`, `PUBLISH_STUB_RC`, `PUBLISH_EMIT_OK`, `PUBLISH_OK_VALUE`, `UPSERT_STUB_RC`, `UPSERT_STATUS_VALUE`, `ARCH_SOURCE_VALUE`, `RENAME_STUB_RC`, and `RENAMED_OMIT_LINE`, then set only what the case needs.
  - From dyn-test-harness-isolation-output.txt: Either call the same reset helper at the top of `run_publish` before applying defaults, or use explicit assignments (`export PUBLISH_STUB_RC=0`) instead of `:-` so each invocation gets a known baseline unless the case overrides.

### OOS_1: [OUT_OF_SCOPE] Unrelated upgrade-larch / tooling bundled in branch diff
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Same branch bundles `upgrade-larch`, `plugin.json`, `CHANGELOG`, `lib-net.sh`, or other tooling changes with Step 5c `design-publish` extraction. Reviewers and bisect must separate unrelated work from #3133 Step 5c / design-publish behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split or rebase so feature commits are isolated.
  - From cursor-specialist-plan-fidelity-output.txt: Keep as separate commits/PR slice if merge hygiene matters; not a defect in design-publish itself.

### OOS_2: [OUT_OF_SCOPE] `validate_repo` triplicated across phase drivers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `validate_repo` is duplicated across three phase drivers (`design-publish.sh` 27–33 and siblings); predates this PR. Repo validation rule changes require three edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Centralize in `lib-phase-driver.sh` on next library touch.

### OOS_3: [OUT_OF_SCOPE] Plan-block-write / upsert `set +e` subshell behavior verified OK
- **Reviewer(s)**: dyn-bash-euo-safety-output.txt
- **Severity**: nit
- **Concern**: `if ! plan-block-write.sh` failure guard, subshell capture for upsert/publish, and `set -e` restoration after `set +e` behave as intended; `exit` inside `upsert-diagrams-comment.sh` only terminates the `$(…)` subshell, not the driver.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Bash 3.2 indirect expansion in SKILL.md orchestrator block OK
- **Reviewer(s)**: dyn-bash-euo-safety-output.txt
- **Severity**: nit
- **Concern**: `${!_key:-}` with `printf -v` at `SKILL.md` 1319–1344 is valid on macOS Bash 3.2; parsing vars initialized before use so `set -u` is not tripped.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] Happy-path `render-final-summary.sh` without `|| true` under `set -e`
- **Reviewer(s)**: dyn-bash-euo-safety-output.txt
- **Severity**: latent
- **Concern**: Non-zero render on happy path (`238-244`, `281-285`) would abort before publish/rename/result-env—stricter than old inline Step 5c. In practice render is built to fall back and exit `0` for pre/post publish phases unless validation exits early with code `2`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Rename-failure WARN grep pattern behavior
- **Reviewer(s)**: dyn-test-harness-isolation-output.txt
- **Severity**: nit
- **Concern**: Assertion at `test-design-publish.sh` 381–382 uses escaped `\[` `\]` so `[DESIGNED]` is matched literally; driver WARN line matches and does not false-positive with basic grep on this platform.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] `RENAMED_OMIT_LINE` stub unused (not harness contamination)
- **Reviewer(s)**: dyn-test-harness-isolation-output.txt
- **Severity**: nit
- **Concern**: `RENAMED_OMIT_LINE` is defined in the tracking stub (88–90) but no case sets it; unused harness surface, distinct from cross-case export leakage (see FINDING_13).
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] Static source line-order pins partially cover marker ordering
- **Reviewer(s)**: dyn-test-harness-isolation-output.txt
- **Severity**: nit
- **Concern**: Runtime marker ordering on `design-publish.sh` is partially covered by `scripts/test-design-structure.sh` source line-order pins; remaining gap is harness-runtime / plan acceptance ordering vs absence of all CI pins (see FINDING_4).
- **Suggested revisions (informational for voters; coder decides)**:
