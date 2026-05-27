## Plan

# Implementation Plan — #2996: prevent orphaned ship-pr.sh from background+monitor pair

## Approach

The orphan-process bug is a **caller-contract** defect, not a `breadcrumb-monitor.sh` or `ship-pr.sh` defect. The background+monitor pair, when expressed as `<writer> &` followed by `breadcrumb-monitor.sh`, exits the wrapper Bash shell as soon as the monitor returns — leaving the backgrounded writer running as an orphan whenever the done sentinel fires before the writer actually exits (the documented sub-pipeline exit-trap propagation issue from incident `984F0AA4-4436-40F3-A82E-9D114C1A58B4`).

The fix makes the wrapper Bash shell `wait` on the captured writer PID after the monitor returns **while preserving load-bearing exit-status semantics**. The canonical shape every wrapper of a **top-level Family B writer** (the five scripts in AGENTS.md that own `LARCH_PAIRED_PID_FILE`) must adopt:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh" \
  --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" \
  --branch-name "$BRANCH_NAME" \
  ... &
SHIP_PR_PID=$!

monitor_rc=0
"${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh" \
  --stream "$LARCH_BREADCRUMB_STREAM" \
  --done-sentinel "$LARCH_DONE_SENTINEL" \
  --status-file "$LARCH_STATUS_FILE" \
  --quiet-log "$LARCH_QUIET_LOG_FILE" \
  --surfaced-sentinel "$LARCH_BREADCRUMBS_SURFACED_FILE" \
  --paired-pid-file "$LARCH_PAIRED_PID_FILE" \
  || monitor_rc=$?

if [ "$monitor_rc" -eq 0 ]; then
  writer_rc=0
  wait "$SHIP_PR_PID" || writer_rc=$?
  exit "$writer_rc"
else
  # Bounded reap: monitor already SIGTERM/SIGKILL'd the paired PID per its existing
  # timeout discipline. Wait briefly so we don't leak orphans, then exit with monitor_rc
  # to preserve the infrastructure-failure signal.
  wait "$SHIP_PR_PID" 2>/dev/null || true
  exit "$monitor_rc"
fi
```

Two **load-bearing properties** the contract preserves:

1. **Writer exit code is propagated** on the success path. Orchestrator code branches on `ship-pr.sh`'s exit (0/3/4/5/6) for resume/stall/conflict-handoff routing (see `skills/implement/SKILL.md` Step 8+ exit-code matrix); a wrapper that exits 0 after a writer that exited 5 silently breaks that routing. The canonical pattern above propagates writer_rc on the monitor-success path.
2. **Monitor failure is not masked** by a successful writer reap. When the monitor errors (bad argv, path validation failure, the 1800-second `larch_bm_signal_paired_pid` SIGTERM→SIGKILL timeout escalation), the wrapper exits with the monitor_rc so the orchestrator sees the infrastructure failure rather than a stale writer-success reading.

Orchestrator prose (Step 8+, Step 5, Step 2 dispatch, sketch collection, voter dispatch) must read `EXIT_CODE` from `$LARCH_STATUS_FILE` (the canonical writer status file, populated by `lib-quiet`'s done trap) **as well as** the wrapper exit code, since the wrapper exit reflects the monitor branch first and the writer branch second.

Three changes carry the load:

1. **Normative prose**: `BASH_AUTHORING.md` §4 declares the explicit two-branch shape canonical, documents when shell `&` is required (when the same Bash tool call must run writer + monitor as a pair) versus when Bash-tool `run_in_background` alone suffices (when the writer is the *only* command in its Bash tool call and the monitor is in a *separate* foreground Bash tool call), reconciles the apparent tension surfaced by FINDING_8, and explains the writer_rc / monitor_rc propagation rationale citing incident `984F0AA4`.
2. **Mechanical enforcement**: `scripts/lint-foreground-markers.sh` grows a new per-anchor invariant that requires shell `&` on the writer command, PID capture, monitor invocation, and a later `wait` against the same identifier — in **every Markdown fence** AND **every shell file** that invokes a top-level Family B writer as a background pair.
3. **Documentation sweep**: every Markdown fence currently invoking one of the five writers in the pair pattern is rewritten to the explicit canonical shape, including the previously-omitted `skills/shared/external-reviewers.md` and `skills/shared/dialectic-protocol.md` files that the existing linter already scans.

Top-level Family B writer set (matches AGENTS.md's 5-script list and `lint-foreground-markers.sh`'s `family_b_pid_writer_required` case):
- `scripts/ship-pr.sh`
- `scripts/run-step5-review.sh`
- `scripts/collect-agent-results.sh`
- `scripts/dispatch-plan-voters.sh`
- `skills/implement/scripts/run-step2-dispatch.sh`

Additionally, **`scripts/collect-agent-results.sh` itself receives a one-line behavior fix** independent of the wrapper contract: its current code installs `larch_quiet_append_done_trap` and then replaces the `EXIT` trap with its own `WAIT_STDERR` cleanup, which silently destroys the quiet done-trap and prevents the done sentinel from being written on normal exit (the FINDING_7 latent bug — monitor-based fences only complete via timeout). The fix composes both behaviors: chain the new cleanup through `LARCH_QUIET_PREV_EXIT_TRAP` (the existing `lib-quiet` mechanism for trap composition) or install cleanup *before* `larch_quiet_append_done_trap` so the quiet trap's `larch_quiet__exit_combo` re-invokes the cleanup. A small offline harness in `scripts/test-collect-agent-results.sh` (existing harness; extend it) verifies the done sentinel is written on normal exit.

The fix does **not** alter `breadcrumb-monitor.sh` itself (its existing `--paired-pid-file` SIGTERM-then-SIGKILL escalation on the 1800-second timeout remains the bounded hang-stop) and does **not** add an orphan-reaper at session teardown (out of scope per Round 1 Decision 3).

## Files to modify/create

### UPDATED: `BASH_AUTHORING.md`

Extend §4 to:
1. Declare the explicit two-branch canonical shape (writer `&` + `<pid_var>=$!` + `monitor_rc=0` + monitor `|| monitor_rc=$?` + branch on monitor_rc, propagating writer_rc on success and monitor_rc on failure).
2. Supply the worked example using a concrete real top-level Family B writer (`ship-pr.sh`) so the validator doesn't reject a placeholder and so contributors can copy-paste.
3. Add a "Shell `&` vs tool JSON `run_in_background`" subsection (resolves FINDING_8): shell `&` is required when the writer and monitor must run in the same Bash tool call; the Bash-tool `run_in_background` flag is used to keep the *whole* pair Bash call from blocking the orchestrator turn. Both apply together: tool JSON backgrounds the *pair*, shell `&` backgrounds the *writer within the pair*.
4. Add a "Why wait and propagate?" paragraph citing incident `984F0AA4-4436-40F3-A82E-9D114C1A58B4`, naming the orphan-process bug, the discarded-exit-code regression risk, and the bounded-reap rule on monitor failure.
5. Cross-reference the new lint invariant by name.

Keep the §3 (Bash 3.2 portability) constraint visible — `<var>=$!`, `wait "$<var>"`, `monitor_rc=0; ... || monitor_rc=$?` are all POSIX/Bash-3.2 safe.

### UPDATED: `scripts/lint-foreground-markers.sh`

Add a new helper `fence_has_family_b_pid_capture_and_wait` (Bash 3.2-safe, parse-only, no eval) that, given the joined fence body and a denylisted-script anchor identified as a top-level Family B writer via the existing `family_b_pid_writer_required`, asserts:

1. **Logical command end** — after walking backslash-line-continuations from the anchor line forward, identify the line where the writer command logically ends (the line without a trailing `\`). All subsequent assertions reference this line, not the anchor start. This addresses multiline writer invocations like Step 8+'s 18-line `ship-pr.sh` block (FINDING_2).
2. **Shell ampersand** on the writer's logical-end line. Missing `&` is a **hard fail** (exit 1) with diagnostic `missing shell ampersand on top-level Family B writer <anchor>; tool-level run_in_background alone is insufficient — see BASH_AUTHORING.md §4`. Inline suppression `# lint-foreground-markers: ok <reason>` is honored as for existing checks (FINDING_12).
3. **PID capture** within 3 non-blank in-fence lines *after* the logical-end line. Pattern: `(local[[:space:]]+)?<IDENT>=\$!`, where `<IDENT>` matches `[A-Za-z_][A-Za-z0-9_]*`. The `local` prefix is permitted only inside shell-file function bodies; Markdown fence assignments may omit it (FINDING_17).
4. **`wait` line** matching one of `wait "$<IDENT>"`, `wait $<IDENT>`, or `wait "${<IDENT>}"`, where `<IDENT>` matches the identifier captured in (3). Position: **after** the `breadcrumb-monitor.sh` invocation, in the **same fence** (the next-fence allowance from the prior draft is **removed** — FINDING_3 — because the current Markdown scanner has no pending-anchor lookahead state and adding one is out of scope for L1).
5. **Identifier-match assertion** in (4) is strict: capture-vs-wait identifier mismatch is a hard fail with diagnostic `wait identifier <wait_ident> does not match captured PID variable <capture_ident>` (FINDING_19).

Add a sibling helper `scan_shell_file_for_family_b_wait` that applies (1)–(5) to shell-script files in `scripts/`, `skills/*/scripts/`, and `hooks/` (mirroring the existing `scan_shell_file_for_unset_before_nested_child` shape — FINDING_11). Shell-file scan respects the optional `local ` prefix (FINDING_17) and per-line suppression.

Wire both helpers into the existing per-anchor scan loops in `scan_fence_buffer_for_anchors` (Markdown) and the shell-file scan path. Nested-only Family B children (`ci-wait.sh`, `review-and-fix.sh`, `step2-implement.sh`, `dispatch-with-waterfall.sh`, `step-7a.sh`) are excluded via the existing `family_b_pid_writer_required` gate — they are invoked synchronously by parents and not backgrounded.

### UPDATED: `scripts/test-lint-foreground-markers.sh`

Add the following fixture cases registered into the harness's existing iteration:

1. **Positive — multiline ship-pr.sh** (matches `skills/implement/SKILL.md` Step 8+ shape): a fenced bash block containing a backslash-continued multi-line `ship-pr.sh` invocation ending with `&`, then `SHIP_PR_PID=$!`, then `monitor_rc=0` + monitor + `|| monitor_rc=$?`, then branch + `wait "$SHIP_PR_PID"` → must pass (FINDING_2, FINDING_15).
2. **Positive — `local` PID capture in a function** (shell-file fixture): a shell function body that backgrounds `ship-pr.sh`, captures `local SHIP_PR_PID=$!`, runs monitor, waits on `"$SHIP_PR_PID"` → must pass (FINDING_17).
3. **Positive — all three wait forms**: three sub-fixtures, identical except for `wait "$IDENT"` / `wait $IDENT` / `wait "${IDENT}"` → all must pass (FINDING_18).
4. **Negative — missing wait**: same as (1) but with `wait` line removed → must fail with `missing wait` diagnostic.
5. **Negative — missing PID capture**: same as (1) but with `SHIP_PR_PID=$!` line removed → must fail with `missing PID capture` diagnostic.
6. **Negative — wait before monitor**: must fail with `wait must follow breadcrumb-monitor.sh` diagnostic.
7. **Negative — missing `&` on writer's logical-end line**: must fail (exit 1) with `missing shell ampersand` diagnostic; verify nonzero exit (FINDING_12).
8. **Negative — identifier mismatch**: captures `SHIP_PR_PID=$!` but waits on a different identifier → must fail with `wait identifier ... does not match captured PID variable` diagnostic (FINDING_19).
9. **Positive — nested Family B child unchanged**: a fence invoking `ci-wait.sh` or `review-and-fix.sh` without `&` / PID / wait → must pass (the new check is gated by `family_b_pid_writer_required`).

Each fixture is a temp Markdown or shell file written by the harness; assertions check exit code and that the expected diagnostic substring appears in stderr.

### NEW: `scripts/test-background-monitor-wait.sh`

A focused offline regression harness simulating the orphan scenario without touching real Family B writers. Redesigned per FINDING_5 / FINDING_6 / FINDING_20 / FINDING_21:

1. Allocate a per-run tmpdir under `${TMPDIR:-/tmp}/larch-test-bgmw-XXXXXX`.
2. Write a fake-writer shell script that **stays alive in the foreground after writing the done sentinel**:
   ```sh
   printf 'EXIT_CODE=%s\n' "${FAKE_EXIT:-0}" > "$LARCH_DONE_SENTINEL"
   sleep 5
   touch "$TMPDIR_WRITER_DONE_MARKER"
   exit "${FAKE_EXIT:-0}"
   ```
   The marker file is the load-bearing assertion target — wrapper must observe its presence on completion (FINDING_5 marker-file approach is preferred over elapsed-time math).
3. Run the canonical wrapper pattern (writer `&`, PID capture, fake-monitor that exits on the early-written sentinel, branch + `wait` + writer_rc propagation) against the fake writer.
4. Assertions:
   - **Marker file exists** when the wrapper completes (proves the wrapper did NOT exit before the writer's `touch`).
   - **Wrapper exit code equals `${FAKE_EXIT}`** for `FAKE_EXIT` ∈ {0, 3, 4, 5, 6} (FINDING_13 + FINDING_21: load-bearing writer exit codes propagate).
   - **Wrapper exit code equals 2** when fake-monitor returns exit 2 (validation failure) and writer exits 0 (FINDING_6: monitor failure not masked by writer success).
   - **Wrapper completes within bounded time** (≤ 12s) when fake-monitor returns exit 4 (timeout) — proves the post-monitor reap is bounded (FINDING_20).
5. **Negative control**: run a "no wait" variant of the wrapper against the same fake writer — must observe the marker file *missing* when the wrapper completes (proves the regression harness is sensitive to the bug it's catching).
6. Clean up the tmpdir on exit. Bash 3.2 portable (no `mapfile`, no associative arrays, no `&>>`).

Register via the Makefile (`make test-background-monitor-wait`).

### NEW: `scripts/test-background-monitor-wait.md`

Sibling stub naming purpose (orphan prevention + writer-exit-code propagation + monitor-failure preservation + bounded post-monitor reap invariants), primary callers (Makefile target, `relevant-checks.sh` chain, pre-commit hook), Bash 3.2 portability note, and edit-in-sync rule.

### UPDATED: `scripts/collect-agent-results.sh`

Fix the EXIT trap composition so the quiet done trap fires on normal collector exit (FINDING_7). Two acceptable shapes — pick whichever survives review:

(a) **Compose via `LARCH_QUIET_PREV_EXIT_TRAP`**: install the WAIT_STDERR cleanup *first*, then call `larch_quiet_append_done_trap` (which captures the existing EXIT trap into `LARCH_QUIET_PREV_EXIT_TRAP` and the `larch_quiet__exit_combo` re-evaluates the saved body).
(b) **Inline composition**: rewrite the cleanup trap to invoke both the WAIT_STDERR cleanup body *and* `larch_quiet__exit_write_done "$_rc"` (the lib-quiet helper).

Add a unit assertion to `scripts/test-collect-agent-results.sh`: after a normal collector exit (no timeout), `$LARCH_DONE_SENTINEL` must contain `EXIT_CODE=0`.

### UPDATED: `scripts/test-collect-agent-results.sh`

Add the done-sentinel assertion described above and a clear test name (`assert_done_sentinel_written_on_normal_exit`).

### UPDATED: `scripts/breadcrumb-monitor.md`

Add a "Caller contract" section documenting:
1. Callers paired with a top-level Family B writer must `wait` on the captured writer PID after the monitor returns.
2. Callers must capture `monitor_rc` (non-zero monitor exit indicates infrastructure failure) and branch: on success propagate `writer_rc`, on failure propagate `monitor_rc` with a bounded reap.
3. The 1800-second timeout discipline + `larch_bm_signal_paired_pid` SIGTERM-then-SIGKILL escalation is the bounded hang-stop; the post-monitor `wait` does not extend the hang window beyond that.
4. Link to `BASH_AUTHORING.md` §4 for the canonical pattern.

### UPDATED: `Makefile`

Register the new `test-background-monitor-wait` target; chain it into whichever aggregate target the existing lint pipeline uses (mirror the existing pattern for sibling `test-*` targets). Also register a `lint-background-monitor-wait-fence` or equivalent if the new lint check needs an explicit Makefile entry (mirror the existing `lint-foreground-markers` pattern).

### UPDATED: `scripts/relevant-checks.sh`

Add the new harness and the updated lint helper to the routing logic so changes to the five top-level Family B writers, `scripts/breadcrumb-monitor.sh`, `scripts/collect-agent-results.sh`, the new harness itself, and any swept Markdown file trigger the relevant test/lint targets (FINDING_4). Mirror the existing per-path routing patterns.

### UPDATED: `docs/linting.md`

Add an entry for the new lint invariant in the canonical linter table (FINDING_16). Cross-reference `BASH_AUTHORING.md` §4, the lint helper name, the harness target, and the `relevant-checks.sh` routing.

### UPDATED: `AGENTS.md`

Add a one-line entry to the **Conventions** section noting the post-monitor wait contract (FINDING-accepted OOS_2 will file this separately, but landing the contract anchor here ensures contributors editing skills see it). Reference `BASH_AUTHORING.md` §4 for the canonical pattern. Keep this short (one bullet line); the full normative spec lives in §4.

### UPDATED: `skills/implement/SKILL.md`

Sweep every fenced bash block that invokes one of the five top-level Family B writers in the background+monitor pair pattern. Rewrite each to the explicit canonical shape (writer with shell `&`, `<pid_var>=$!`, `monitor_rc=0` + monitor + `|| monitor_rc=$?`, branch + `wait` + writer_rc propagation). Known anchors include the `ship-pr.sh` Step 8+ Invoke block around line 1450, the `run-step2-dispatch.sh` Step 2 dispatch block around line 881, the `run-step5-review.sh` Step 5 review block around line 1145, and the `collect-agent-results.sh` / `dispatch-plan-voters.sh` blocks elsewhere — confirm the exact set by grepping for the five basenames at implementation time. Preserve all surrounding env-allocation lines, comments (`# Tool JSON: run_in_background: true`, `# Background pair required: see BASH_AUTHORING.md §4`), and the `**⚠ Background required — must be paired with breadcrumb-monitor.sh.**` banner.

**Step 8+ orchestrator prose update**: revise the exit-code matrix prose around `ship-pr.sh` to (a) consult `EXIT_CODE` from `$LARCH_STATUS_FILE` for the writer status (not the wrapper exit alone), (b) recognize that the wrapper exit code is `writer_rc` on monitor success and `monitor_rc` on monitor failure, and (c) document that a non-zero `monitor_rc` should be surfaced as an infrastructure-failure stall, distinct from writer-driven bail/conflict-handoff/retry paths (FINDING_13).

### UPDATED: `skills/design/SKILL.md`

Same sweep applied to every Family B writer fence in this file (primarily `collect-agent-results.sh` invocations in Step 2a.3 sketch collection and Step 3 plan review collection). Step 3 / Step 5 prose remains unchanged — `collect-agent-results.sh`'s exit code is not routing-load-bearing in `/design` (the orchestrator reads collector status from per-output structured blocks, not from the wrapper exit), but the canonical wrapper shape still applies for consistency.

### UPDATED: `skills/design/references/dialectic-execution.md`

Sweep `collect-agent-results.sh` fences.

### UPDATED: `skills/design/references/plan-review.md`

Sweep `collect-agent-results.sh` and `dispatch-plan-voters.sh` fences.

### UPDATED: `skills/design/references/sketch-launch.md`

Sweep `collect-agent-results.sh` fences if any appear (sketch-launch.md may delegate collection to the main SKILL.md — confirm and only touch fences that actually contain the pair invocation).

### UPDATED: `skills/design/references/brainstorm.md`

Sweep `collect-agent-results.sh` fences.

### UPDATED: `skills/research/references/research-phase.md`

Sweep `collect-agent-results.sh` fences.

### UPDATED: `skills/research/references/validation-phase.md`

Sweep `collect-agent-results.sh` fences.

### UPDATED: `skills/review/references/heavy-worker.md`

Sweep `collect-agent-results.sh` fences if any (review's heavy-worker may delegate to `/review`'s own background path — confirm and touch only Family B writer pair fences).

### UPDATED: `skills/implement/references/conflict-resolution.md`

Sweep `ship-pr.sh` fences.

### UPDATED: `skills/implement/references/rebase-rebump-subprocedure.md`

Sweep `ship-pr.sh` fences.

### UPDATED: `skills/shared/external-reviewers.md`

Sweep `collect-agent-results.sh` fences (FINDING_1 — this file is already scanned by `lint-foreground-markers.sh` and would fail CI on landing if not updated).

### UPDATED: `skills/shared/dialectic-protocol.md`

Sweep `collect-agent-results.sh` fences (FINDING_1 — same rationale).

### Sweep-completeness check

At implementation time, run `grep -l -E 'ship-pr\.sh|run-step5-review\.sh|run-step2-dispatch\.sh|collect-agent-results\.sh|dispatch-plan-voters\.sh' skills/**/*.md` and verify that every file in the output appears in the list above. Any new hits indicate a missed sweep target; add to scope before commit.

## Edge cases

- **Writer exits before monitor starts**: `wait "$<pid>"` on an already-reaped PID returns immediately with the exit code. The canonical pattern still propagates `writer_rc` correctly.
- **Monitor hits its 1800-second timeout**: existing `larch_bm_signal_paired_pid` SIGTERM-then-SIGKILL escalation kills the writer; the wrapper's monitor-failure branch then waits briefly (already-reaped → immediate return) and exits with `monitor_rc` (non-zero) so the orchestrator sees the infrastructure failure (FINDING_20).
- **Done sentinel fires legitimately while writer continues briefly**: monitor exits 0, wrapper waits on writer PID, writer finishes its remaining work, wrapper propagates `writer_rc`. The orphan bug is the case this fix targets.
- **Monitor fails on argv validation (exit 2) before the writer finishes**: wrapper takes the monitor-failure branch, briefly reaps the writer (which may still be running but will be terminated by the monitor's paired-PID signaling on a subsequent invocation; in this specific scenario the writer is left running because monitor exited before signaling — accepted residual risk, this case shouldn't normally occur in CI). The wrapper exits with `monitor_rc` (2) so the failure is visible.
- **Writer is a stdout-capturing command substitution** (FINDING_14 rejected/exonerated by panel but worth noting): the canonical pattern adds `&` to a command-substitution writer, which would background the assignment in a subshell and break the parent's KV capture. The lint rule's `family_b_pid_writer_required` set is restricted to the five top-level scripts — none of which currently use `$()` capture — so no in-scope fence is at risk. If a future Family B writer needs stdout capture, that contract change is a separate design.
- **Nested Family B children invoked synchronously by a parent** (`ci-wait.sh`, `review-and-fix.sh`, `step2-implement.sh`, `dispatch-with-waterfall.sh`, `step-7a.sh`): no shell `&`, no PID capture, no wait required. Existing `family_b_pid_writer_required` gate keeps the new lint check from triggering here.
- **Stylistic PID-variable names**: lint accepts any `[A-Za-z_][A-Za-z0-9_]*` identifier; canonical examples use SCREAMING_SNAKE (`SHIP_PR_PID`, `COLLECTOR_PID`) for Markdown fences and `local snake_case` for shell-function bodies.
- **PID capture line uses `local`**: lint regex `(local[[:space:]]+)?<IDENT>=\$!` allows it (FINDING_17). Markdown fences typically omit `local`; shell-file function bodies typically include it.
- **Multiline writer invocations** (backslash continuation): lint's logical-command-end detection walks `\`-terminated lines forward until a line without trailing `\`; all subsequent assertions reference that line, not the anchor start (FINDING_2).
- **Multiple Family B writers in one fence**: the linter scans per-anchor; each anchor independently asserts shell `&`, PID capture, and wait. Identifiers must be distinct.

## Failure modes

1. **Implementer adds `wait` but drops the monitor_rc capture / branch**, so a monitor timeout silently exits 0 after the writer completes. The orchestrator misses the infrastructure-failure signal and continues into a degraded state.
   - **Signal**: lint check requires the `monitor_rc=0` initialization and `|| monitor_rc=$?` on the monitor invocation, plus a `monitor_rc`-branching `if`/`case`. Missing any of these is a hard fail.
   - **Mitigation**: lint helper asserts the presence of `monitor_rc=` initialization within 3 lines above the monitor call, an `|| monitor_rc=` on the monitor's logical-end line, and the branching exit later in the fence. (Implementation may simplify: assert just the `monitor_rc` token appears in both an assignment and a later conditional — keeps the regex tractable.)
2. **Identifier mismatch slips past the linter** because the regex captures the first `$!` assignment but the wait uses a typo'd identifier (e.g. `SHIP_PR_PD`).
   - **Signal**: `wait identifier <wait_ident> does not match captured PID variable <capture_ident>` lint diagnostic.
   - **Mitigation**: lint helper extracts the captured identifier and asserts the wait line references the same identifier (FINDING_19). Negative fixture covers this.
3. **Regression test (`test-background-monitor-wait.sh`) becomes flaky on slow CI runners** because the bounded-reap timing window is tight.
   - **Signal**: intermittent CI failures with `bounded reap exceeded 12s` assertion.
   - **Mitigation**: use generous fake-writer / fake-monitor durations (writer sleeps 5s, bounded-reap assertion 12s). If flake persists, increase to 20s — the harness is offline; CI slowness is bounded.
4. **`collect-agent-results.sh` fix introduces a new trap interaction bug** — composing the WAIT_STDERR cleanup with `larch_quiet__exit_combo` may not preserve cleanup ordering or `_rc` propagation.
   - **Signal**: `scripts/test-collect-agent-results.sh` `assert_done_sentinel_written_on_normal_exit` assertion fails, or any of the existing collector tests regress (timeout-path tests, output-paths tests).
   - **Mitigation**: extend the existing test suite; verify both the new done-sentinel assertion and that no existing tests regress before commit.
5. **Skills/shared sweep misses a Family B fence** in a `skills/shared/*.md` file beyond the two named (`external-reviewers.md`, `dialectic-protocol.md`) — CI fails on landing because the new lint runs across the same scan scope.
   - **Signal**: post-PR CI `lint-foreground-markers` failure naming a specific shared file.
   - **Mitigation**: run the **Sweep-completeness check** grep described above (the `grep -l -E ...` shell line in the Files-to-modify section) at implementation time *before* committing; any new hits indicate scope adjustments needed.

## Testing strategy

- **New harness `scripts/test-background-monitor-wait.sh`**: invariant-validates orphan prevention, writer-exit-code propagation (FAKE_EXIT in {0, 3, 4, 5, 6}), monitor-failure preservation, and bounded post-monitor reap. Includes a negative-control "no wait" path that proves the harness is sensitive to the bug.
- **Extended `scripts/test-lint-foreground-markers.sh`**: nine new fixture cases (3 positives covering canonical, `local`, all-three-wait-forms; 5 negatives covering missing-wait, missing-PID, wait-before-monitor, missing-`&`, identifier-mismatch; 1 nested-Family-B-passes check).
- **Extended `scripts/test-collect-agent-results.sh`**: new `assert_done_sentinel_written_on_normal_exit` plus preservation of existing test cases.
- **Existing test suites unchanged**: no test removal, no test rename. The fence sweep across 14+ Markdown files is verified by running existing harnesses (`make lint`, `make lint-foreground-markers`, `make lint-bash32`) — any regressions show as positive lint failures.
- **Manual smoke**: after implementation, run one low-cost `/larch:research` or `/larch:design` flow to confirm the existing background+monitor pair still streams breadcrumbs correctly. No automated end-to-end since real Family B writer runs are expensive.
- **Pre-commit hook routing** (`scripts/relevant-checks.sh`): explicit per-path routing so changes to `scripts/breadcrumb-monitor.sh`, `scripts/collect-agent-results.sh`, the five top-level Family B writers, the new harness, and any swept Markdown file all trigger the relevant test/lint targets (FINDING_4).

diff_lines: 460


## Acceptance

- BASH_AUTHORING.md §4 declares the writer-`&` + PID-capture + monitor_rc + branch + wait shape canonical, with worked example using `ship-pr.sh` and a "Why wait and propagate?" subsection citing incident `984F0AA4`.
- `scripts/lint-foreground-markers.sh` adds the `fence_has_family_b_pid_capture_and_wait` helper (Markdown) and `scan_shell_file_for_family_b_wait` helper (shell-file) that hard-fail on missing `&`, missing PID capture, missing wait, wait-before-monitor, identifier-mismatch; respects multi-line `\`-continuation logical-command end; supports optional `local ` prefix; honors `# lint-foreground-markers: ok` suppression.
- `scripts/test-lint-foreground-markers.sh` has 9 new fixtures (positives: multiline ship-pr, `local` capture, three wait forms; negatives: missing-wait, missing-PID, wait-before-monitor, missing-`&`, identifier-mismatch; passes-nested-family-B).
- `scripts/test-background-monitor-wait.sh` (new) + `.md` sibling: regression harness that asserts orphan prevention, writer_rc propagation for FAKE_EXIT ∈ {0,3,4,5,6}, monitor-failure preservation when monitor returns 2, bounded post-monitor reap (≤12s) when monitor returns 4 (timeout), plus a negative no-wait control.
- `scripts/collect-agent-results.sh` trap composition fixed so the quiet done sentinel is written on normal exit; `scripts/test-collect-agent-results.sh` asserts `assert_done_sentinel_written_on_normal_exit`.
- `scripts/breadcrumb-monitor.md` has a "Caller contract" section documenting the post-monitor wait, monitor_rc capture/branch, and bounded-reap rule.
- Markdown sweep across all SKILL.md, references/*.md, AND shared/*.md files (including `skills/shared/external-reviewers.md`, `skills/shared/dialectic-protocol.md`) rewrites every Family B background+monitor pair fence to the explicit canonical shape; `make lint-foreground-markers` passes.
- `skills/implement/SKILL.md` Step 8+ orchestrator prose for `ship-pr.sh` consults `EXIT_CODE` from `$LARCH_STATUS_FILE` AND interprets wrapper exit as writer_rc-on-monitor-success / monitor_rc-on-monitor-failure; non-zero `monitor_rc` is treated as infrastructure-failure stall, distinct from writer-driven routing.
- `scripts/relevant-checks.sh` routes changes to the five top-level Family B writers, `breadcrumb-monitor.sh`, `collect-agent-results.sh`, the new harness, and any swept Markdown file to the relevant test/lint targets.
- `docs/linting.md` and `AGENTS.md` Conventions reflect the new invariant; sweep-completeness grep returns no files outside the plan's UPDATED list.
- `make lint`, `make lint-foreground-markers`, `make lint-bash32`, and the new `test-background-monitor-wait` target all pass.

diff_lines: 460
