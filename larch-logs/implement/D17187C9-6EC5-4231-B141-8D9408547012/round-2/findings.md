Here is the normalized finding list (merged where the same risk/fix direction; distinct where fixes or paths differ). Source slots use the reviewer output filenames from your input.

```text
### FINDING_1: Plan and traceability omit `scripts/run-external-agent.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Implementation plan file lists and fidelity readers can miss `run-external-agent.sh` even though it gains stdbuf-aware capture behavior that affects all `CAPTURE_STDOUT_ONLY` callers, not only launcher files; reviewers may underestimate buffering impact across the stack.
- **Suggested revision**: Extend the canonical plan’s “files to change” (and rationale) to explicitly include `run-external-agent.sh` alongside launcher and test updates.

### FINDING_2: Fixture 5 stall budget vs pasted plan (3s vs 300s) and single-threshold story
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Written plan/fixture acceptance implies a ~3s stall story for wall-clock vs stall proof, while the harness uses a much larger `LARCH_CURSOR_CI_STALL_THRESHOLD` (e.g. 300s) with rationale only in comments; plan fidelity and operator expectations diverge.
- **Suggested revision**: Reconcile plan text with the harness (restore a 3s-oriented path if feasible, or amend the plan to the real threshold/stdbuf story) and optionally cross-link `launch-cursor-ci.md` so one coherent threshold narrative exists outside comments.

### FINDING_3: `launch-cursor-ci.md` kill ordering vs launcher implementation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Documentation describes signaling as if only the wrapper gets SIGTERM, while code paths that have `pgrep` may terminate direct children first; operators comparing docs to `strace` can misread ordering.
- **Suggested revision**: Update prose to the child-then-wrapper sequence that matches `lib-cursor-launcher-common.sh`.

### FINDING_4: `read` / `jq` pipelines use `|| true` and can swallow failures under `set -e`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Broad `|| true` on token/read paths (e.g. around `launch-cursor-ci.sh` jq extraction and related reads) masks pipeline/read failures unrelated to stall detection, blurring PR intent and risking silent drops of `.token-record` on partial JSON after kills.
- **Suggested revision**: Narrow `|| true` scope, or log/exit on unexpected read failure when output is expected to be JSON-shaped.

### FINDING_5: `file:` stall channel shipped but unused and untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: `file:` mode adds surface area without a `launch-cursor-ci.sh` caller (“dead code” perception) and has no harness coverage, so regressions in size/mtime polling would not fail `make test-launch-cursor-ci`.
- **Suggested revision**: Remove until needed, clearly mark as reserved, or add a focused fixture that drives `file:` progress and asserts no false stall.

### FINDING_6: Without `pgrep`, teardown may only signal the wrapper; deep child trees linger longer
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: In minimal environments lacking `pgrep`, only the wrapper PID may be signaled; deep agent child trees may be torn down less cleanly, extending stray processes until outer timeouts.
- **Suggested revision**: Document the `pgrep` dependency and supported environments, or add a `ps`-based fallback if required platforms lack `pgrep`.

### FINDING_7: Unknown `STALL_CHANNEL` values silently disable monitoring (exit 0)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Unrecognized non-empty channel strings can fall through such that monitoring is effectively off with no operator-visible signal (e.g. future typo in `STALL_CHANNEL`).
- **Suggested revision**: Log/assert on unknown non-empty channels at parse time or at the launcher callsite.

### FINDING_8: Tree-mode stall expression can treat `.git` activity as working-tree progress
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `find` tree expressions may allow `.git` metadata changes to satisfy the “progress” predicate even when conflicted working-tree paths are untouched, resetting the stall clock until wall-clock timeout.
- **Suggested revision**: Adjust `find` prune/expr so `.git` and its contents never satisfy the progress predicate used for stall resets.

### FINDING_9: Tree-mode `.git` pruning makes `.git`-only mutations invisible to progress
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: If a legitimate workflow only mutates paths under `.git`, tree monitoring may never observe “progress” and could misclassify activity as stalled (documented limitation vs bug, depending on intended contract).
- **Suggested revision**: Expand the monitored set if `.git`-internal work must count, or explicitly document that `.git`-only activity is intentionally invisible to the tree channel.

### FINDING_10: Zero-byte stdout warmup reuses `STALL_THRESHOLD`, stretching effective hang detection
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Warmup logic that refreshes `last_prog_ts` on synthetic zero-byte ticks can push a permanently zero-byte capture toward roughly `2 * STALL_THRESHOLD` (plus poll quantization) before SIGTERM, weakening the stated CI guardrail versus operator-facing “180s” messaging.
- **Suggested revision**: Use a shorter separate warmup bound, or stop advancing `last_prog_ts` on synthetic zero-byte ticks so the post-warmup window matches `STALL_THRESHOLD`.

### FINDING_11: `find` tree root not separated with `--` (paths starting with `-`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: If `tree_root` can begin with `-`, some `find` builds may parse it as flags; the monitor may watch the wrong tree or behave unpredictably.
- **Suggested revision**: Use `find -- "$tree_root"` and prefer normalized absolute roots in tree mode.

### FINDING_12: `file:` channel splices paths without trust validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: A future caller passing `channel=file:...` with influenced path components could direct `stat`/`wc` reads at sensitive or unintended locations.
- **Suggested revision**: Document trusted-caller-only constraints, or validate allowlisted absolute paths before polling.

### FINDING_13: Stdout stall polling uses `wc -c` on a growing capture every interval
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Repeated full-file reads at `RUN_EXTERNAL_AGENT_POLL_INTERVAL` can dominate disk/CPU on large JSON captures and slow the same CI run the guardrail is meant to rescue.
- **Suggested revision**: Prefer inode/byte-size via `stat` (Darwin `stat -f %z`, Linux `stat -c %s`) for regular-file stdout monitoring, with a narrow fallback if `stat` fails.

### FINDING_14: Missing `--output` while wrapper PID is alive treated as perpetual progress
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-stall-logic-output.txt
- **Concern**: If the capture file never appears (or disappears and never returns) while the PID remains alive, treating each poll as progress prevents `stall_seconds` accrual; only the outer wall-clock timeout remains.
- **Suggested revision**: Time-bound “missing file counts as progress” similarly to the zero-byte grace window, or enforce/document an invariant that the capture exists before monitoring and drop the unbounded branch.

### FINDING_15: Stall escalation `SIGKILL`s the `run-external-agent` wrapper, risking missing completion sentinels
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-process-lifecycle-output.txt
- **Concern**: `SIGKILL` cannot run `_write_sentinel_on_exit`; `${OUTPUT}.inner.done` / `${OUTPUT}.done`-style completion may diverge from the built-in timeout path that keeps the wrapper exiting normally after killing the inner capture PID—downstream collectors relying on the sentinel contract may see missing/stale artifacts after stall kills even though the launcher promotes/reaps.
- **Suggested revision**: Prefer kill escalation that still allows normal wrapper exit where possible; or parent-side best-effort synthesis of the sentinel shape after `wait` when the trap did not run; or avoid wrapper `SIGKILL` once the inner capture PID is already gone and the wrapper is exiting.

### FINDING_16: Header/comments claim missing stdout capture “equals zero bytes” but code treats missing+alive as rolling progress
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Mismatch between comments/docs and actual missing-file/spin-up semantics can mislead future edits and test expectations.
- **Suggested revision**: Align comments/docs with the real missing-file and grace semantics (or change code to match documented contract).

### FINDING_17: Redundant `|| true` after `cursor_launcher_run_stall_monitor`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Noise only; monitor helper always returns 0 today.
- **Suggested revision**: Remove redundant `|| true` unless the monitor gains meaningful non-zero statuses.

### FINDING_18: `run-external-agent.md` not updated for new capture/stdbuf behavior
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Script behavior changed but sibling markdown is stale versus the repo’s scripts `*.sh` ↔ `*.md` sibling documentation expectation.
- **Suggested revision**: Update `run-external-agent.md` in the same change set as the script changes.

### FINDING_19: Plan wording on process exit codes vs launcher always exiting 0 with harness `LAUNCHER_EXIT`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Plan text says the process exits non-zero in some fixtures while the launcher contract/harness encodes failures via `LAUNCHER_EXIT` patterns; readers infer the wrong failure surface.
- **Suggested revision**: Align plan wording with harness/launcher semantics, or change semantics if the plan is meant to be normative.

### FINDING_20: Plan mentions cursor-related `ps` diagnostics; implementation uses `pgrep -P` child targeting
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Literal plan wording is not met by the implementation, reducing plan-as-spec usefulness.
- **Suggested revision**: Clarify the plan to match `pgrep -P` behavior, or add cursor-filtered diagnostics if the plan’s `ps` story is required.

### FINDING_21: `${OUTPUT}.diag` shared between child stderr (`2>`) and appended stall diagnostics
- **Reviewer(s)**: dyn-process-lifecycle-output.txt
- **Concern**: Non-append child stderr and append-side stall blocks can interleave at arbitrary byte boundaries, garbling auth-oriented greps (e.g. `external_is_auth_failure`) and post-mortem reads.
- **Suggested revision**: Write stall diagnostics to a separate sidecar (e.g. `${OUTPUT}.stall`) and merge after exit, or coordinate writes (`flock` / dedicated append fd).

### FINDING_22: [OUT_OF_SCOPE] `docs/linting.md` row for `test-launch-cursor-ci` understates new stall fixtures/runtime
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Readers may underestimate harness runtime/behavior; not necessarily introduced only by files touched in this diff.
- **Suggested revision**: Update the linting doc row when convenient.

### FINDING_23: [OUT_OF_SCOPE] `run-external-agent.sh` deletes `OUTPUT_FILE` before relaunching capture (startup ordering race window)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Behavior predates stall logic but widens missing-output races independent of stall monitoring; changing ordering is a separate product decision.
- **Suggested revision**: Address only if changing startup ordering is acceptable in a dedicated follow-up.

### FINDING_24: [OUT_OF_SCOPE] Committed `larch-logs/implement/...` artifacts add review noise vs functional `scripts/` changes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-process-lifecycle-output.txt, dyn-stall-logic-output.txt
- **Concern**: Orthogonal to stall-monitor correctness; increases diff noise for reviewers focused on launcher semantics.
- **Suggested revision**: None required for stall correctness; treat as repo/process hygiene follow-up if desired.

### FINDING_25: [OUT_OF_SCOPE] Clarification: `RUN_EXTERNAL_AGENT_CAPTURE_STDOUT_STDBUF=1` / `$!` note applies to capture-job PID inside `run-external-agent.sh`, not `_REA_PID` in `launch-cursor-ci.sh`
- **Reviewer(s)**: dyn-process-lifecycle-output.txt
- **Concern**: Scout note scope correction: wrapper PID choice for `wait` / `kill -0` is not contradicted by stdbuf/capture-job internals.
- **Suggested revision**: None (documentation/clarification only).

### FINDING_26: [OUT_OF_SCOPE] `read ... || true` on jq token extraction is defensive for `pipefail` edge cases and not part of stall integration semantics
- **Reviewer(s)**: dyn-process-lifecycle-output.txt
- **Concern**: Argues the change is intentionally non-fatal for the background agent/stall path even if other reviewers want narrower failure handling.
- **Suggested revision**: None within stall scope; reconcile separately with in-scope masking concerns if policy requires hard failures.

### FINDING_27: [OUT_OF_SCOPE] `dyn-stall-logic-output.txt` scout clarifications (non-issues): zero-byte branch, `pipefail` pipeline status, `date +%s` quantization
- **Reviewer(s)**: dyn-stall-logic-output.txt
- **Concern**: (a) The `cur_size==0` early grace does not permanently suppress stalls after `stall_threshold` age; (b) `set +o pipefail` makes the `find|head|grep` condition behave as intended regarding `grep` exit status / `SIGPIPE`; (c) 1-second timestamp resolution mostly adds jitter/skew rather than systematically firing a full poll interval early.
- **Suggested revision**: None (retain as reviewer-side risk triage notes; do not treat as confirmed defects without separate verification).
```
