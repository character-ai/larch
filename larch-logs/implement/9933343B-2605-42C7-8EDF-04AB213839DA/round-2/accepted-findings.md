### FINDING_10: `test-launch-cursor-ci.sh`: No tree-channel stall sidecar fixture
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: No tree-channel stall sidecar test despite real tree stalls in cited incidents; mis-resolution or wrong channel string for tree mode could regress unnoticed. Add tree-mode stall fixture asserting channel and sidecar path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: `test-audit-runs.sh`: Duplicate `[35c]` / Test 35c naming collides with existing ns-retry assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Duplicate Test 35c naming collides with existing `[35c]` ns-retry assertions; harness logs are harder to grep and maintainers may misread failures. Rename the new test block and assertion tags to unique ids.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: `lib-cursor-launcher-common.sh`: Redaction failures can still place sensitive git/transcript/process material into committed stall JSON (`cat` fallback; unredacted temps fed to `jq --rawfile`)
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-shell-safety-output.txt
- **Concern**: `cursor_launcher_redact_stdin` can fall back to `cat` when `redact-secrets` exits non-zero, copying git porcelain/rebase patch excerpts unredacted into stall JSON. Separately, when timeout-wrapped `redact-secrets` fails, intermediate `.r` files may be removed while original `ps_tmp`/`lsof_tmp`/`tr_tmp` stay unredacted and are still passed to `jq --rawfile`, so OOM or exit-1 on huge snapshots can embed secrets (e.g. API keys, paths) in committed `round-*/cursor-ci-stall-*.json` as if redaction succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: On redactor failure emit a fixed placeholder or empty git_state instead of piping through cat; log stderr to a local-only fd if debugging is needed.
  - From cursor-specialist-security-output.txt: On any redact failure overwrite the capture file with a short failure marker or skip emitting ps/lsof/transcript fields unless redaction succeeded.
  - From dyn-shell-safety-output.txt: On any redact failure for a given temp file, substitute a fixed placeholder string for that field (or skip emitting the sidecar) instead of proceeding with the unredacted `--rawfile` payload.


### FINDING_16: `.diag` vs stall JSON vs post-`SIGTERM` lsof/ps: capture-phase mismatch risks mis-triage (and post-TERM snapshots may miss pre-stall FD state)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-artifact-contract-output.txt
- **Concern**: `ps`/lsof/argv captured after `SIGTERM` on `target_pid` may miss hung-child FD state that existed at stall time. Separately, the stall handler appends a `ps` snapshot into `${OUTPUT}.diag` before `kill -TERM`, while `cursor_launcher_emit_cursor_ci_stall_json_sidecar` runs after the wrapper/direct children receive `SIGTERM`, so JSON fields (`ps`, `lsof`, `last_transcript_lines`) reflect post-signal I/O/process state while `.diag` reflects a last pre-kill view—diffing the two during triage can read as contradictory “stall-time” evidence unless phases are explicit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Document tradeoff or add minimal pre-TERM lsof if audits show weak signal.
  - From dyn-artifact-contract-output.txt: Call this out explicitly in `scripts/launch-cursor-ci.md` (and optionally add a small machine-readable hint in the JSON, e.g. a `capture_phase` or `note` string) so consumers treat `.diag` as the immediate pre-kill snapshot and the JSON as the heavier, intentionally post-`SIGTERM` capture.


### FINDING_17: `test-audit-runs.sh`: New Test 35c lacks pass-path coverage when zero stall JSON files (regression could break empty-run NDJSON silently)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Test 35c does not assert pass path when zero stall JSON files; regression could break empty-run NDJSON without failing harness. Add fixture asserting `cursor-ci-stall-causes` result pass count 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_18: `lib-cursor-launcher-common.sh`: `pipefail` + `lsof … | head …` + error clobber can empty `lsof_tmp` on benign `SIGPIPE`
- **Reviewer(s)**: dyn-shell-safety-output.txt
- **Concern**: With `set -o pipefail` inherited from callers such as `scripts/launch-cursor-ci.sh` (`set -euo pipefail`), `timeout … lsof … | head -n 400 >"$lsof_tmp"` can exit non-zero when `lsof` receives `SIGPIPE` after `head` closes the pipe even though useful lines were already written; the trailing `|| : >"$lsof_tmp"` then truncates the file and drops the snapshot entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-safety-output.txt: Temporarily `set +o pipefail` around this pipeline (or avoid clobber-on-error, e.g. write to a temp path and only `mv` on success), similar in spirit to the `set +o pipefail` guard already used for the tree-channel `find` pipeline in `cursor_launcher_run_stall_monitor`.


### FINDING_19: `lib-cursor-launcher-common.sh`: On `jq` assembly failure, no sidecar and no `.diag` marker—audits cannot distinguish “no stall” from “stall without parseable sidecar”
- **Reviewer(s)**: dyn-artifact-contract-output.txt
- **Concern**: When `jq` assembly fails, staging may be removed with no `round-*/cursor-ci-stall-*.json` and no `${OUTPUT}.diag` annotation, while stall termination / “Stall detected” still occurs—`scan_cursor_ci_stall_causes` can see zero matching sidecars even though the run clearly stalled, so channel histograms are not a complete stall census.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-contract-output.txt: On `jq` failure, append a single-line marker to `${OUTPUT}.diag` (or write a minimal fallback JSON via plain shell with `channel`, `pid`, `time_since_last_progress`, and an `assembly_error` string) so audits can distinguish “no stall” from “stall without parseable sidecar.”

---

## Out-of-scope / review-input observations


### FINDING_2: `test-audit-runs.sh`: Test 35c block ordered before 35b (non-monotonic labels)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The Test 35c block sits before Test 35b, breaking ascending harness order; readers who grep or extend by number hit confusing out-of-order sections. Move 35c after 35b or renumber so labels ascend.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_4: Stall sidecar directory: max `round-*` / glob heuristics can mis-attribute JSON to the wrong round
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Round-dir selection via “max” `round-*` or loose glob/numeric compare can stick on a non-maximal or wrong directory when `OUTPUT` is not under a `round-*` path, multi-round `IMPLEMENT_TMPDIR` exists, or naming is unusual—stall JSON can land under a stale or higher round, mis-tagging audit evidence and operator triage. Prefer deriving the sidecar dir from the canonical per-round output path, explicit round metadata from the orchestrator, or a deterministic sort/filter of conforming names; document constraints if behavior is intentional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: `test-launch-cursor-ci.sh`: Strict `.lsof` size vs post-`SIGTERM` capture order (flaky / false negatives)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-test-harness-output.txt
- **Concern**: The harness requires a non-trivial `lsof` payload whenever `lsof` exists, but the implementation sends `SIGTERM` to the monitored wrapper (and children) before running `lsof -p` on the target; a cooperative stub can exit quickly and yield empty or tiny `lsof` output even when the stall path behaved correctly—intermittent false failures on busy or slower runners.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-test-harness-output.txt: Treat `.lsof` as best-effort in the harness (for example assert only when `wc -c` exceeds a threshold, or skip the lsof assertion when the field is empty while still requiring the sidecar file and other fields), or capture `lsof` before signaling the target in production code if a strict test invariant is required.


### FINDING_8: `lib-cursor-launcher-common.sh`: Stall JSON capture can block a long time before `SIGKILL` when subprocesses are unbounded (lsof, git, redact; missing `timeout`/`gtimeout`)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Heavy stall JSON capture runs synchronously in the stall-recovery path (including after `SIGTERM` but before `sleep`+`SIGKILL` on some descriptions): `lsof|head` can block without a wall-clock cap if `lsof` never emits lines; git status / rebase-patch capture can fall back to unbounded `git` when `timeout`/`gtimeout` are missing; redact-related steps can also lack portable wall-clock caps on macOS / without GNU coreutils—so NFS/git lock or wedged `lsof` can freeze the stall handler, delay `SIGKILL`, stretch CI or `/implement` runs, and keep hung children alive longer than intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Wall-clock cap lsof (or run capture after SIGKILL with documented trade-off); do not rely on head alone for time bounding.
  - From cursor-specialist-testing-output.txt: Require timeout for git capture or use a portable wall-clock wrapper; skip git fields when unbounded git is unsafe.
  - From cursor-specialist-security-output.txt: Document timeout as a prerequisite for stall diagnostics or wrap each subprocess in a portable time-bounded wrapper.
  - From cursor-specialist-edge-cases-output.txt: Defer heavy capture until after SIGKILL or wrap every expensive step (incl. redact and lsof) in a portable wall-clock bound; or detach capture without joining before SIGKILL.


### FINDING_9: `test-launch-cursor-ci.sh`: Fixture 7 skips when `jq` is absent instead of failing the harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-harness-output.txt
- **Concern**: JSON sidecar regression is gated on `command -v jq`; if `jq` is missing the script prints `SKIP` and can exit 0 without asserting `round-*/cursor-ci-stall-*.json`, weakening integration signal when `jq` is accidentally dropped from CI or minimal images.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Fail harness if jq missing for fixture 7 or document jq as mandatory and assert at harness entry.
  - From dyn-test-harness-output.txt: Require `jq` for this test file when the sidecar feature is considered mandatory (fail with a clear message at the start of fixture 7 or the stall suite), or document and enforce `jq` as a hard prerequisite in the CI job that runs this script so SKIP cannot mask a regression.


