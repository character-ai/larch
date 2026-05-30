### FINDING_1: Byte-cap pipeline fails under inherited pipefail (SIGPIPE loses largest tails)
- **Reviewer(s)**: Cursor-Arch, unknown-slot
- **Severity**: important
- **Concern**: The planned `tail | redact-secrets | head -c` byte-cap pipeline runs under callers that enable `set -o pipefail` (`run-external-agent.sh`, `collect-agent-results.sh`, `launch-claude-subprocess.sh`). When stderr exceeds the byte cap, `head -c` closes the pipe early; `tail`/`redact` get SIGPIPE (exit 141). With pipefail, render/write can return non-zero or abort before `${OUTPUT}.stderr-tail` is written—exactly when tails are largest (#3119 background case).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Truncate without a failing pipeline: spool tail|redact to a temp file then head -c from the file, or wrap the pipeline with set +o pipefail / || true per scripts/lib-cursor-launcher-common.sh:282-294; assert non-zero exit_code still writes .stderr-tail in test-lib-failed-agent-stderr-tail.sh
  - From unknown-slot: Wrap the cap pipeline like lib-cursor-launcher-common.sh:281-282 (set +o pipefail around the head -c stage), or assign via if ! content=$(...) so SIGPIPE cannot abort set -e callers; add a harness case with set -e caller and oversized stderr


### FINDING_2: Stale `${ORIG_OUTPUT}.stderr-tail` after successful transient retry
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: When a first pass fails (`run-external-agent` writes `${ORIG}.stderr-tail`), a transient heuristic queues retry, and retry succeeds with `REVIEWER_FILE=${ORIG%.txt}-retry.txt` and `STATUS=OK`, dedup skips chat but `${ORIG}.stderr-tail` is not removed and is not excluded from `design_publish`, so a redacted failure tail can publish beside an OK result in `larch-logs`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: In collect-agent-results.sh after retry success (~1148-1154), rm -f "${ORIG_OUTPUT}.stderr-tail"; mirror in NS-retry success if a failure tail can exist on the preserved orig path; extend test-collect-agent-results.sh to assert ORIG.stderr-tail absent after successful retry


### FINDING_3: Dedup stderr tails via `larch_err` never reach chat on main `/review` path
- **Reviewer(s)**: unknown-slot, Cursor-dyn-source-selection-mapping
- **Severity**: important
- **Concern**: Plan §collect-agent-results dedup emits tails via `larch_err` (FD 2 → chat), but `/review` captures collector stderr into `$REVIEW_TMPDIR/collect-agent-results.log` and only replays that log on non-zero `collector_rc`; on success, dedup tails stay in the log. Additionally, review launches discard launcher stderr (`dispatch-with-waterfall.sh` `2>&1` to `/dev/null`), so `emit_failed_agent_stderr_tail_raw` never reaches chat—#3202/#3119 chat surfacing fails for inline `/review` external collection even when collection succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Minimal: tee collector stderr to the parent FD 2 while keeping the log (e.g. 2> >(tee -a "$collector_log" >&2)), or replay fenced tail blocks from collector_log via larch_err after a successful collect. Extend test-collect-findings.sh to assert tails are visible on the wrapper’s stderr.
  - From Cursor-dyn-source-selection-mapping: Minimum fix: after a successful collector run, scan failed slots for `.stderr-tail` and emit (or replay dedup lines from the log) via `larch_err`; or stop redirecting collector stderr to only a file on the review path


### FINDING_4: Default tail line count (30) drifts from issue #3202 (50)
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: Default tail line count is 30 while issue #3202 requires the last 50 lines and says to start at 50 with env tuning. Multi-line failures with root-cause detail in lines 31–50 never reach chat unless the operator sets `LARCH_FAILED_AGENT_STDERR_TAIL_LINES`—silent drift from the filed acceptance criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Set default to 50 in the lib/docs/harness, or document an explicit SIMPLE-tier rationale for 30 in the plan and docs/configuration-and-permissions.md


### FINDING_5: Plan omits `agent-lint.toml` dead-script exclusions for new lib/harness
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: New `scripts/lib-failed-agent-stderr-tail.sh` and `scripts/test-lib-failed-agent-stderr-tail.sh` match other sourced-only libs (e.g. `lib-validate-meta-path.sh`) that agent-lint flags as unreachable dead scripts; `make lint` / relevant-checks agent-lint phase will fail after the PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add an ### UPDATED: agent-lint.toml step mirroring lib-validate-meta-path.sh: exclude scripts/lib-failed-agent-stderr-tail.sh, scripts/lib-failed-agent-stderr-tail.md, scripts/test-lib-failed-agent-stderr-tail.sh, and scripts/test-lib-failed-agent-stderr-tail.md in the same sourced-only / harness-sibling blocks


### FINDING_6: Mode-blind stderr source order prefers wrapper `.diag` over merged agent stderr
- **Reviewer(s)**: Cursor-dyn-source-selection-mapping
- **Severity**: important
- **Concern**: Proposed stderr source order `.sidecar` → `.diag` → `OUTPUT_FILE` is mode-blind. FAILED/TIMED_OUT always append a non-empty wrapper line to `${OUTPUT_FILE}.diag` before selection. Under `--capture-stdout`, agent stderr is merged into `OUTPUT_FILE`, but `.diag` is still populated on every non-zero/timeout exit, so the second candidate wins and tails show wrapper text instead of merged agent stderr—contradicting the plan’s `--capture-stdout` merged-mode claim.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-source-selection-mapping: Branch on in-scope `CAPTURE_STDOUT` / `CAPTURE_STDOUT_ONLY`: e.g. merged → prefer non-empty `OUTPUT_FILE` before `.diag`; stdout-only → `.diag` before `OUTPUT`; default review → keep `.sidecar` first

---

**Merge summary**: 8 raw inputs → 6 normalized findings. Merged: FINDING_1+2 (pipefail/SIGPIPE), FINDING_4+8 (collector stderr not surfacing to chat). Kept separate: stale tail cleanup (3), default 30 vs 50 (5), agent-lint exclusions (6), mode-blind source selection (7). No `[OUT_OF_SCOPE]` tags in inputs.

