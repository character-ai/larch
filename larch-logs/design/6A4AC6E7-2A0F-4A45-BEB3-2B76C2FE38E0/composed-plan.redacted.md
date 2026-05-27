## Plan


Mechanical fixes for three distinct voter failure modes plus one Codex-wide stdin contract. Per Round 1 Decision 1, the deeper breadcrumb-monitor early-exit cascade is filed as an OOS follow-up in Step 5b, not implemented here. Per Round 1 Decision 3, the Codex stdin fix lands once in the shared spawn layer so every background-Codex launch benefits.

This revision (Gate B "Apply all") addresses 6 panel findings: FINDING_1 (wait-barrier position vs size checks), FINDING_2 (capture wait stdout / parse TIMEOUT), FINDING_3 (test coverage across spawn branches), FINDING_4 (launcher-layer test hooks), FINDING_5 (set -e safety on the wait branch), FINDING_6 (single implementation path for the stdin redirect).

## Files to modify/create

### UPDATED: `scripts/run-external-agent.sh`

Apply the Codex stdin guard at the actual spawn site. Per FINDING_6, the **direct per-branch shell-redirection** pattern is authoritative; the previous plan's "string-variable" alternative is discarded.

Authoritative structure: at each of the three background spawn branches around `scripts/run-external-agent.sh:206-212`, wrap the spawn line in a `case "$TOOL_NAME" in codex)` block that appends `< /dev/null` for Codex spawns and otherwise preserves the existing behavior:

1. **Default branch** (line ~213, `"$@" &`):
   ```bash
   case "$TOOL_NAME" in
       codex) "$@" < /dev/null & ;;
       *)     "$@" & ;;
   esac
   ```

2. **`--capture-stdout` branch** (line ~209, `"$@" > "$OUTPUT_FILE" 2>&1 &`):
   ```bash
   case "$TOOL_NAME" in
       codex) "$@" > "$OUTPUT_FILE" 2>&1 < /dev/null & ;;
       *)     "$@" > "$OUTPUT_FILE" 2>&1 & ;;
   esac
   ```

3. **`--capture-stdout-only` branch** — fix lands INSIDE `_launch_capture_stdout_only` so **both** of its spawn arms (stdbuf-enabled and the fallback) apply `< /dev/null` for Codex. The outer caller (`elif [ "$CAPTURE_STDOUT_ONLY" = true ]; then _launch_capture_stdout_only "$@"`) is unchanged. The helper is rewritten:
   ```bash
   _launch_capture_stdout_only() {
       case "$TOOL_NAME" in
           codex)
               if [[ "${RUN_EXTERNAL_AGENT_CAPTURE_STDOUT_STDBUF:-}" == "1" ]] && command -v stdbuf >/dev/null 2>&1; then
                   stdbuf -o0 -e0 "$@" > "$OUTPUT_FILE" 2> "${OUTPUT_FILE}.diag" < /dev/null &
               else
                   "$@" > "$OUTPUT_FILE" 2> "${OUTPUT_FILE}.diag" < /dev/null &
               fi
               ;;
           *)
               if [[ "${RUN_EXTERNAL_AGENT_CAPTURE_STDOUT_STDBUF:-}" == "1" ]] && command -v stdbuf >/dev/null 2>&1; then
                   stdbuf -o0 -e0 "$@" > "$OUTPUT_FILE" 2> "${OUTPUT_FILE}.diag" &
               else
                   "$@" > "$OUTPUT_FILE" 2> "${OUTPUT_FILE}.diag" &
               fi
               ;;
       esac
   }
   ```

4. **Contract comment** above the first patched branch:
   ```
   # Codex CLI: stdin is redirected to /dev/null because the CLI keeps stdin open
   # expecting interactive input. Without this redirect, when the parent shell
   # exits while a background Codex subprocess is still running, the subprocess
   # sees stdin EOF and emits "write_stdin failed: stdin is closed for this
   # session" (issue #2962 / #2973 Voter A). Documented at the Codex-named layer
   # in lib-codex-launcher-common.sh.
   ```

### UPDATED: `scripts/lib-codex-launcher-common.sh`

Add a 6-line comment block after the existing `source "${BASH_SOURCE[0]%/*}/lib-external-launcher-common.sh"` line documenting the Codex stdin contract and pointing at `scripts/run-external-agent.sh` lines 206-213 (the actual spawn site). No functional change.

### UPDATED: `scripts/lib-codex-launcher-common.md`

One-paragraph addition: "Codex stdin contract" subsection noting the `< /dev/null` redirect for all background Codex spawns and the literal landing site in `scripts/run-external-agent.sh`. Cross-reference `scripts/run-external-agent.md`.

### UPDATED: `scripts/dispatch-code-voters.sh`

Add an explicit `wait-for-reviewers.sh` invocation covering all three voter `.done` sentinels, **positioned before any size-based status assignments** (FINDING_1) **with stdout captured and TIMEOUT records parsed** (FINDING_2) **and `set -e`-safe error handling** (FINDING_5).

Changes:
1. **Re-order the existing status block**: split the current lines 198-210 so that path bindings happen before the wait and size-based status checks happen after. The new order is:
   - Line ~198: `VOTER_1_TOOL="claude"`; `VOTER_1_STATUS="launched"` (unchanged).
   - Line ~199-200: bind `VOTER_2_PATH`, `VOTER_3_PATH`, `VOTER_2_TOOL`, `VOTER_3_TOOL` from `outputs_arr`/`tools_arr` (move the existing lines 201-204 up).
   - Line ~201-202: `VOTER_2_STATUS="launched"`, `VOTER_3_STATUS="launched"`; the existing `claude` → `fallback` checks for voter 2/3 (lines 207-208).
   - Insert the **wait barrier** here (see point 2 below).
   - After the wait: **recompute** the size-based status checks (the existing lines 200, 209, 210):
     ```bash
     # FINDING_1: re-evaluate size-based statuses AFTER the wait barrier so a
     # voter whose output became visible during the wait is correctly classified.
     [[ "$voter1_rc" -eq 0 && -s "$VOTER_1_PATH" ]] || VOTER_1_STATUS="failed"
     [[ "$VOTER_2_STATUS" == "skipped" ]] || [[ -s "$VOTER_2_PATH" ]] || VOTER_2_STATUS="failed"
     [[ -s "$VOTER_3_PATH" ]] || VOTER_3_STATUS="failed"
     ```

2. **Wait barrier** (inserted between path/launched-status assignment and size-based status checks):
   ```bash
   # FINDING_2: capture stdout — wait-for-reviewers.sh emits TIMEOUT rows on
   # stdout and exits 0 even when sentinels never appear, so an exit-only check
   # would silently miss timeouts. FINDING_5: use if/fi (not arithmetic && cmd)
   # because the arithmetic test returns 1 on the normal zero-exit path and would
   # abort dispatch-code-voters.sh under set -e before parse-rate/tally.
   wait_sentinels=()
   [[ -n "$VOTER_1_PATH" ]] && wait_sentinels+=("${VOTER_1_PATH}.done")
   [[ "$VOTER_2_STATUS" != "skipped" && -n "$VOTER_2_PATH" ]] && wait_sentinels+=("${VOTER_2_PATH}.done")
   [[ -n "$VOTER_3_PATH" ]] && wait_sentinels+=("${VOTER_3_PATH}.done")
   if (( ${#wait_sentinels[@]} > 0 )); then
       _wait_out_file=$(mktemp "${REVIEW_TMPDIR}/voter-wait.XXXXXX")
       set +e
       "$PLUGIN_ROOT/scripts/wait-for-reviewers.sh" \
           --timeout "${LARCH_VOTER_WAIT_TIMEOUT:-60}" \
           "${wait_sentinels[@]}" >"$_wait_out_file" 2>&1
       _wait_rc=$?
       set -e
       # FINDING_2: detect TIMEOUT rows on stdout (wait-for-reviewers exits 0
       # even when sentinels never appear).
       if grep -q '^TIMEOUT ' "$_wait_out_file" 2>/dev/null; then
           while IFS= read -r _to_line; do
               larch_err "dispatch-code-voters.sh: voter sentinel $_to_line"
           done < <(grep '^TIMEOUT ' "$_wait_out_file")
       fi
       # FINDING_5: rc=1 is a usage error (not a sentinel timeout); log distinctly.
       if (( _wait_rc != 0 )); then
           larch_err "dispatch-code-voters.sh: wait-for-reviewers.sh exited $_wait_rc (usage/config error) — proceeding with whatever state exists"
       fi
       rm -f "$_wait_out_file"
       unset _wait_out_file _wait_rc
   fi
   ```

3. **Timeout default** unchanged: `LARCH_VOTER_WAIT_TIMEOUT=60`. The launchers themselves block until completion, so the wait is normally a no-op (sentinel-poll-first-pass per `wait-for-reviewers.sh` line 116 detects pre-existing sentinels immediately). The 60s budget is for the rare race window where the launcher just returned but the `.done` write is still pending.

4. **Non-blocking on failure**: timeouts surface via the captured stdout grep; usage errors via the `_wait_rc` check; both log via `larch_err` but do NOT abort. The existing `VOTER_*_STATUS=failed` checks (now after the wait, per FINDING_1) handle whatever state exists. Pragmatic regression-risk callout from Cursor-Pragmatic addressed.

### UPDATED: `scripts/dispatch-code-voters.md`

Update the sibling .md to reflect the new wait barrier. Add a section "Voter `.done` sentinel barrier" documenting:
- **Position**: between path/launched-status assignment and size-based status checks (re-evaluation of `-s` happens AFTER the wait).
- **Stdout capture**: TIMEOUT rows are detected and logged via `larch_err`; align with `wait-for-reviewers.md` contract that timeouts return exit 0 (not non-zero).
- **rc=1 semantics**: documented as usage/config error, logged distinctly from timeouts.
- **Timeout default**: 60s; `LARCH_VOTER_WAIT_TIMEOUT` env override.
- **Failure semantics**: non-blocking; preserves degraded-quorum behavior; `set -e`-safe (uses `if/fi`, not `(( … )) && cmd`).
- Cross-reference to `scripts/wait-for-reviewers.md` and issue #2973.

### UPDATED: `scripts/launch-review.sh`

Cursor sidecar population (Round 1 Decision 5). Verified: the existing `_launch_cursor` body initializes `SIDECAR=${OUTPUT}.sidecar` at line 855, `: > "$SIDECAR"` at line 899, redirects cursor agent stderr there via `2>>"$_STDERR_TARGET"` at line 928. The sidecar can legitimately remain 0 bytes when cursor agent exits without emitting stderr — the current "empty" behavior is normal but indistinguishable from "never wrote anything." Issue #2973 Voter C flags this as a visibility gap.

Change: after the `wait "$WRAPPER_PID"` block (around line 932), if `EXIT_CODE == 0` AND the sidecar exists AND is empty, write a single status marker line:

```bash
if (( EXIT_CODE == 0 )) && [[ "$SIDECAR" != "/dev/null" && -f "$SIDECAR" && ! -s "$SIDECAR" ]]; then
    printf 'cursor-status: ok (no stderr emitted during agent run)\n' > "$SIDECAR" 2>/dev/null || true
fi
```

Apply the same marker write to `_launch_codex` for parity, after the successful `EXIT_CODE=0` path. The marker prefix (`cursor-status:` / `codex-status:`) is distinctive and easily skippable by future sidecar parsers; existing `external_is_auth_failure` / `external_is_transient_infra_failure` matchers do not look for these tokens.

### UPDATED: `scripts/launch-review.md`

Add a "Sidecar status marker" subsection documenting the post-success marker writes for cursor and codex branches. Note that the marker is informational only — no consumer parses it; existing `tally-code-votes.sh` reads only `.txt` outputs.

### UPDATED: `scripts/run-external-agent.md`

Add a "Codex stdin contract" subsection documenting the `< /dev/null` redirect for `--tool codex` spawns across all three spawn branches. Note the implementation lives at `scripts/run-external-agent.sh:206-212` (default + `--capture-stdout`) and inside `_launch_capture_stdout_only` (both stdbuf and non-stdbuf arms). Include the issue references (#2962, #2973) and explain why other tools (cursor) don't need the redirect.

### UPDATED: `scripts/test-run-external-agent.sh` (FINDING_3)

Add direct stdin-probe coverage for **all three spawn branches** and a **non-Codex control**:

1. **TOOL_NAME=codex default branch**: run `run-external-agent.sh --tool codex --output ... -- <stub>` where the stub probes its own fd 0. On Linux use `readlink /proc/$$/fd/0`; on macOS use `lsof -p $$ -a -d 0 -F n` and parse the `n` line. Assert the result names `/dev/null`. The test wrapper provides a non-/dev/null stdin (e.g., a temp file or FIFO) before invoking the wrapper so the assertion proves the production redirect happens — without that, the test would tautologically pass on ambient stdin.

2. **TOOL_NAME=codex with `--capture-stdout`**: same stub, same probe, with `--capture-stdout` set. Assert fd 0 is `/dev/null`.

3. **TOOL_NAME=codex with `--capture-stdout-only`** (default arm, no stdbuf): same stub, same probe, with `--capture-stdout-only` set. Assert fd 0 is `/dev/null`.

4. **TOOL_NAME=codex with `--capture-stdout-only` + RUN_EXTERNAL_AGENT_CAPTURE_STDOUT_STDBUF=1** (stdbuf arm; gated on `command -v stdbuf` succeeding): same stub, same probe with stdbuf available. Assert fd 0 is `/dev/null`. If stdbuf is not on PATH, skip this test case with an explicit `printf 'SKIP: stdbuf not on PATH\n'` so the harness coverage gap is visible.

5. **TOOL_NAME=cursor control**: same wrapper with `--tool cursor`. Assert fd 0 is the wrapper's parent stdin (NOT `/dev/null`) so the test proves Codex-specific behavior is gated correctly and Cursor still inherits stdin.

Each test sets `LARCH_ALLOW_TEST_HOOKS=1` if needed (the stdin probe itself is harmless), creates the wrapper-input as a `mktemp` file, invokes `run-external-agent.sh` via the wrapper, and asserts on stdout from the stub.

### UPDATED: `scripts/test-run-external-agent.md`

Update the sibling .md to list the five new test cases under "Coverage" and reference issue #2973.

### UPDATED: `scripts/test-dispatch-code-voters.sh` (FINDING_4)

Add three new test cases inside the existing harness pattern:

1. **Voter `.done` wait gate (delayed `.done` for voter 2 or 3 via launcher hook)**: per FINDING_4, the prior plan's Claude-stub approach cannot create the race because `launch-claude-review.sh` synchronously writes its own `.done` after the subprocess returns and launcher scripts backfill `.done` on completion. Instead, exercise the race at **voter 2 or 3** (codex/cursor path) using the existing launcher-layer hook:
   - Set `LARCH_ALLOW_TEST_HOOKS=1` and create a temp shell-snippet file path bound to `LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE` (per `scripts/launch-review.sh:976-989`).
   - The snippet writes the final `.txt` content but delays the `.done` move (the snippet runs after `${OUTPUT}.inner.done` is written but before it is renamed to `${OUTPUT}.done`).
   - Set `WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05` for fast polling in the harness.
   - Invoke `dispatch-code-voters.sh` with stub manifests; assert that the dispatcher waits past the `.txt`-visible-but-`.done`-pending point before VOTER_*_STATUS is finalized, and that the final VOTER_*_STATUS reflects the post-wait `-s` re-evaluation (FINDING_1) — i.e., the voter is `launched`, not `failed`, after the race resolves.

2. **Voter 1 (Claude) delayed-`.done` race via direct `launch-claude-review.sh` stub** (mirroring `scripts/test-dispatch-plan-voters.sh:58-86`): build a stub `launch-claude-review.sh` that writes the output and `.done` with a fixed delay between them. Place the stub on PATH via `PLUGIN_ROOT_STUB`. Run `dispatch-code-voters.sh` and assert via `mtime` comparison that the dispatcher's progression past the wait barrier happens after `.done` is written, not before.

3. **`set -e` survival under normal `_wait_rc=0` path** (FINDING_5 regression coverage): run a happy-path scenario (all stubs cleanly exit 0 and write their `.done` files immediately). Assert dispatch-code-voters.sh completes normally — it must NOT abort on the line `if (( _wait_rc != 0 )); then ...; fi` due to set -e. This regression coverage would fail if the implementer reverts to `(( _wait_rc != 0 )) && larch_err "..."`.

Each test case adds ~30-40 lines (manifest setup, stub env vars, hook file or stub binary, dispatcher invocation, assertions).

### UPDATED: `scripts/test-dispatch-code-voters.md`

Update the sibling .md to list the three new test cases under "Coverage" with cross-references to FINDING_1, FINDING_4, FINDING_5, and issue #2973.

### UPDATED: `scripts/test-launch-review.sh`

Add one parity assertion for the Cursor sidecar marker: after a successful Cursor launch with no stderr, the sidecar contains `cursor-status: ok` line. Add corresponding Codex parity assertion. Each addition is ~15 lines.

### UPDATED: `scripts/test-launch-review.md`

Update the sibling .md to list the two new sidecar marker assertions.

## Approach

The three voter failures share one structural fix (wait for `.done` before tally) and one launcher-specific fix per failure mode (Codex stdin redirect; Cursor sidecar marker). All four changes land in the smallest correct layer:

- **Voter race (B + C)**: `dispatch-code-voters.sh` is the boundary between voter launch and tally. The wait is positioned BEFORE size-based status assignments (FINDING_1) so a voter whose output appears during the wait window is correctly classified. Stdout is captured so TIMEOUT records surface in execution logs (FINDING_2). The branch uses `if/fi` form for `set -e` safety (FINDING_5).
- **Codex stdin (A)**: the documented "stdin closed" failure pattern is parent-shell-exit + inherited-stdin. `< /dev/null` neutralizes it directly. Single implementation pattern (direct per-branch `case "$TOOL_NAME" in codex)` blocks at the spawn site, plus updated `_launch_capture_stdout_only` helper applying the redirect on both spawn arms; FINDING_6).
- **Cursor sidecar (C)**: a 1-line marker write after successful exit makes empty-sidecar distinguishable from "never ran." Parity applied to Codex.

The wider Codex stdin fix scope (Round 1 Decision 3: "all background-Codex launches") means the fix automatically benefits voters, reviewers, implementer, and research without per-caller edits — `run-external-agent.sh` is the single entry point for all `--tool codex` invocations, and `_launch_capture_stdout_only` covers all stdbuf/non-stdbuf capture-only variants.

Test scope (Round 1 Decision 6: offline regression tests only) adds bash-stub-based test cases that simulate each failure mode. Per FINDING_3, three test files participate: `test-run-external-agent.sh` covers the stdin redirect across all spawn branches; `test-dispatch-code-voters.sh` covers the wait barrier race via launcher-layer hooks (FINDING_4) and Claude-stub direct delay; `test-launch-review.sh` covers the sidecar marker assertions.

## Edge cases

- **`launch-claude-review.sh` synchrony**: the launcher writes its own `.done` at line 180-182 after `launch-claude-subprocess.sh` returns synchronously. The new `wait-for-reviewers.sh` call may sometimes see all sentinels already present at first poll — that's the expected fast path and `wait-for-reviewers.sh` handles it (line 116-117 comment: "Check before first sleep — detect pre-existing sentinels immediately"). The 60s timeout is purely a defensive ceiling.
- **`VOTER_2_STATUS=skipped`**: when Codex is unavailable and the waterfall fallback path skips voter 2, do NOT include its `.done` in the wait list. The conditional `[[ "$VOTER_2_STATUS" != "skipped" && -n "$VOTER_2_PATH" ]]` filters it out (mirrors the existing pattern at line 254-256).
- **Cross-platform stdin probing**: the `Codex stdin redirect` test cases differ between macOS (`lsof -p $$ -a -d 0 -F n`) and Linux (`readlink /proc/$$/fd/0`). The stub detects the platform via `uname -s` and runs the appropriate probe. CI runs on Linux; manual macOS runs by developers should still pass. The non-Codex Cursor control proves Codex behavior is gated correctly.
- **Stdbuf availability**: the `_launch_capture_stdout_only` stdbuf arm only fires when `command -v stdbuf` succeeds. The test for the stdbuf arm uses an explicit `printf 'SKIP: stdbuf not on PATH\n'` when stdbuf is unavailable so the coverage gap is visible.
- **Sidecar marker file mode**: `printf` to `$SIDECAR` is best-effort (`|| true`) — if the file is `/dev/null` (the fallback when initial `: > "$SIDECAR"` failed at line 904), the marker write silently no-ops. No new failure surface.
- **`run-external-agent.sh` spawn-branch parity**: all three spawn branches (default, CAPTURE_STDOUT, CAPTURE_STDOUT_ONLY) must apply the `< /dev/null` redirect when `TOOL_NAME=codex` — partial coverage would re-introduce the failure mode for any branch that's not patched. The test cases per FINDING_3 enforce this.
- **`wait-for-reviewers.sh` exit semantics**: timeouts emit `TIMEOUT <idx> <basename>` lines on stdout with exit 0. Usage errors exit 1. The new caller captures both, parses TIMEOUT lines via `grep '^TIMEOUT '`, and distinguishes the usage error in its `larch_err` text. The wait does NOT abort on either condition; existing `VOTER_*_STATUS=failed` (post-wait re-evaluation) handles the missing-output state.
- **`LARCH_VOTER_WAIT_TIMEOUT` validation**: the env override goes to `wait-for-reviewers.sh --timeout` which validates positive-integer via its own grammar. No new validation needed in `dispatch-code-voters.sh`.
- **Set -e and arithmetic tests**: `if (( ... )); then ...; fi` is `set -e` safe regardless of the arithmetic test result; the bare form `(( ... )) && cmd` returns the arithmetic result's status when the `&&` short-circuits, which trips `set -e` on the false branch. FINDING_5 regression test (case 3 in test-dispatch-code-voters.sh) protects this invariant.
- **Test hook file path safety**: `LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE` must point at a regular non-symlink file (per `scripts/launch-review.sh:986-989`). The new test cases use `mktemp` for the hook file path and clean up via `trap`.

## Failure modes

1. **Codex stdin redirect breaks an interactive Codex path**. Today no larch code path launches Codex interactively (verified: every `codex exec` call uses `--full-auto` or `--sandbox read-only` with prompt argv), but a future caller could expect stdin to be inherited (e.g., `codex chat` style flows). Earliest signal: a new Codex caller's harness fails because the CLI hangs or errors waiting for input. Mitigation: the redirect is gated on `TOOL_NAME=codex` AND a comment block in `lib-codex-launcher-common.sh` documents the contract; future authors see it before adding interactive code paths. The non-Codex control case in `test-run-external-agent.sh` (per FINDING_3) detects accidental gate breakage.

2. **`wait-for-reviewers.sh` 60s timeout is too aggressive on slow filesystems**. On a heavily loaded CI runner or a slow disk, the `.done` write may legitimately lag the launcher return by >60s. The new gate would emit `larch_err` warnings via the captured TIMEOUT lines and proceed with whatever state exists; the post-wait `-s` re-evaluation marks affected voters `failed`, and degraded-quorum tally takes over. Earliest signal: CI logs show `dispatch-code-voters.sh: voter sentinel TIMEOUT N <basename>` lines. Mitigation: operators can override via `LARCH_VOTER_WAIT_TIMEOUT=300` on slow hosts; the existing parse-rate / status logic already handles missing voter outputs gracefully.

3. **Launcher-layer test hook does not reliably create the dispatcher-layer race**. The `LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE` hook is exercised inside `launch-review.sh`, not at the dispatch-code-voters.sh boundary. If the hook fires AFTER the launcher has already promoted `${OUTPUT}.inner.done` to `${OUTPUT}.done` (line 798), the race window collapses and the test passes trivially. Earliest signal: the FINDING_4 regression test (case 1) does NOT fail on `main` (before the production fix), or both pass and fail orderings produce identical outcomes. Mitigation: the harness verifies via timestamp comparison (`mtime` of `.txt` vs `.done` vs the dispatcher's stdout marker) that the wait actually blocked; if the race window is degenerate, the harness emits a SKIP rather than a false-pass.

## Testing strategy

- **`bash scripts/test-dispatch-code-voters.sh`** runs to completion with all existing tests still passing plus the three new test cases (delayed-`.done` via launcher hook for voter 2/3, delayed-`.done` Claude stub for voter 1, `set -e` survival on normal path).
- **`bash scripts/test-launch-review.sh`** runs to completion with the two new sidecar marker assertions.
- **`bash scripts/test-run-external-agent.sh`** runs to completion with five new stdin-probe test cases (default + capture-stdout + capture-stdout-only + capture-stdout-only-stdbuf for codex, plus non-codex cursor control).
- **`bash scripts/relevant-checks.sh`** (or `make lint`) passes — covers shellcheck, sibling .md presence, foreground markers, etc.
- **Project-wide**: no live `/implement` re-run required (Round 1 Decision 6).
- **Regression coverage discipline**: verify each new test case FAILS on `main` (without the production fix) and PASSES after. This confirms the test actually covers the bug rather than passing trivially. For FINDING_4's launcher-hook test: also verify the race window is non-degenerate by inspecting the captured timestamps in the test output.

## Acceptance

- The Codex stdin redirect lands in `scripts/run-external-agent.sh` via three direct per-branch `case "$TOOL_NAME" in codex)` blocks at the default and `--capture-stdout` spawn sites, and inside `_launch_capture_stdout_only` covering both its stdbuf and non-stdbuf spawn arms. No `_codex_stdin_redirect_args` string-variable pattern (FINDING_6).
- `scripts/dispatch-code-voters.sh` invokes `wait-for-reviewers.sh` exactly once, positioned BEFORE size-based status assignments (FINDING_1), with stdout captured to a tmp file and TIMEOUT records logged per-sentinel via `larch_err` (FINDING_2), with `if/fi` form (FINDING_5), and with `LARCH_VOTER_WAIT_TIMEOUT` defaulting to 60s.
- The size-based `VOTER_*_STATUS` checks (`-s "$VOTER_*_PATH"`) are re-run AFTER the wait completes, so voters whose output became visible during the wait window are correctly classified (FINDING_1).
- `scripts/launch-review.sh` writes a `cursor-status:` / `codex-status:` marker to the sidecar after successful exit when the sidecar is empty.
- All sibling `.md` files for the changed `.sh` files are updated in the same PR (per `.claude/rules/script-md-siblings.md`).
- `bash scripts/test-dispatch-code-voters.sh` passes with three new test cases (one via launcher hook, one via Claude stub, one `set -e` survival).
- `bash scripts/test-run-external-agent.sh` passes with five new test cases (FINDING_3).
- `bash scripts/test-launch-review.sh` passes with two new sidecar marker assertions.
- `bash scripts/relevant-checks.sh` (or `make lint`) passes.
- The Step 5b OOS filing creates a follow-up issue tracking "Investigate breadcrumb-monitor early-exit cascade in /implement Step 5 (sentinel inheritance / `LARCH_BREADCRUMBS_SURFACED_FILE` non-empty)."
- No changes to `scripts/wait-for-reviewers.sh` (reuse only; its contract is unchanged).
- No changes to `scripts/dispatch-with-waterfall.sh` (its `wait $pid` already provides per-phase synchrony; the new wait is the cross-phase barrier).
- No changes to `scripts/tally-code-votes.sh` (it reads only `.txt` outputs, not sidecars — verified).


diff_lines: 280
