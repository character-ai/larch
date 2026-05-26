## Goal
Implement monitor timeout signaling via opt-in --paired-pid-file flag and larch_quiet_write_paired_pid_file helper; audit design-log-publish.sh/larch-log.sh breadcrumb duplication

## Implementation Plan
## Plan

# Implementation Plan — Issue #2848 (Revised after plan-review)

Address the two items in the OOS observation:
1. Audit + close any residual duplication between `design-log-publish.sh` and `larch-log.sh` / `lib-larch-log.sh` (the literal duplication in the issue body was already eliminated by #2790/#2849).
2. Make `breadcrumb-monitor.sh` signal the paired background process on timeout exit instead of leaving it orphaned. Introduce an opt-in `--paired-pid-file <PATH>` flag and a corresponding `LARCH_PAIRED_PID_FILE` env var; only **top-level** Family B scripts write their own `$$` to that file (nested children must not overwrite); on monitor timeout, send SIGTERM, wait 5 seconds, then SIGKILL — every `kill` call guarded so the monitor always reaches its `exit 4`. Update top-level callsites only, enforce the contract via `lint-foreground-markers.sh`, and document the security model in `SECURITY.md`.

## Ownership model (top-level vs nested)

The DENYLIST contains 10 basenames. Their actual nesting topology:
- **Top-level Family B (write the PID file)** — directly background-launched by SKILL.md fences with `run_in_background: true`:
  - `scripts/ship-pr.sh`
  - `scripts/run-step5-review.sh`
  - `skills/implement/scripts/run-step2-dispatch.sh`
  - `scripts/collect-agent-results.sh`
  - `scripts/dispatch-plan-voters.sh`
- **Nested Family B (do NOT write the PID file)** — always invoked synchronously from another DENYLIST parent:
  - `scripts/ci-wait.sh` — nested under `scripts/ship-pr.sh`
  - `skills/review-and-fix/scripts/review-and-fix.sh` — nested under `scripts/run-step5-review.sh`
  - `skills/implement/scripts/step2-implement.sh` — nested under `skills/implement/scripts/run-step2-dispatch.sh` (and `scripts/launch-codex-implement.sh` / `scripts/launch-cursor-implement.sh`)
  - `scripts/dispatch-with-waterfall.sh` — nested under `scripts/dispatch-plan-voters.sh` / `scripts/dispatch-code-voters.sh` / `skills/design/scripts/dispatch-plan-review-panel.sh` / `skills/design/scripts/decompose-panel-dispatch.sh` / `skills/review/scripts/dispatch-panel.sh` / `skills/review/scripts/aggregate-findings.sh`
- **Foreground-only carve-out** — `scripts/step-7a.sh` stays excluded from the new linter requirement.

**Defensive unset in parents**: each top-level script that synchronously invokes a nested DENYLIST child also `unset LARCH_PAIRED_PID_FILE` immediately before the child invocation, so even if the nested child later acquires its own `larch_quiet_write_paired_pid_file` call, the env var is unset and the helper is a no-op. This is belt-and-suspenders against future regressions.

## Files to modify/create

### UPDATED: `scripts/breadcrumb-monitor.sh`
Add `PAIRED_PID_FILE=""` near the variable declarations (~line 17-25). Extend the usage string (~line 28) to document `[--paired-pid-file PATH]`. Add a parser case `--paired-pid-file) PAIRED_PID_FILE="${2:?}"; shift 2 ;;` in the `while` argv loop (~lines 56-69). When `PAIRED_PID_FILE` is non-empty, run `larch_bm_validate_path --paired-pid-file "$PAIRED_PID_FILE"` alongside the other validation calls (~lines 77-81). Add a new helper `larch_bm_signal_paired_pid()` that: reads exactly 33 bytes from `$PAIRED_PID_FILE` via `dd bs=1 count=33` (so a 32+ byte payload is over-read and rejected), strips one optional final newline only, refuses any remaining CR/LF or non-ASCII byte under `LC_ALL=C`, validates the result is a non-empty string of ASCII digits with a positive integer value. On any validation failure (file missing, empty, too long, non-digit) emit `larch_err "WARN paired-pid-file-missing"` (the existing `WARN` channel; not a structured breadcrumb so it does not pass through `larch_quiet_bc_valid_category`) and **return 0**. Otherwise: `kill -TERM "$pid" 2>/dev/null || true`; poll up to 5 times with `kill -0 "$pid" 2>/dev/null || break; sleep 1`; then `kill -KILL "$pid" 2>/dev/null || true`. Every `kill` invocation has its own `|| true` guard so the monitor reaches `exit 4` regardless of EPERM/ESRCH/etc. The helper itself always returns 0. Insert `larch_bm_signal_paired_pid` call inside the `if (( now - START_TS > 1800 ))` branch at lines 165-168 immediately before `exit 4`; gate the call on `[[ -n "$PAIRED_PID_FILE" ]]` so default behavior is byte-compatible for callers that do not pass the flag. Also add a test-only env-var hook: when `LARCH_BM_TEST_TIMEOUT_SECONDS` is set to a positive integer, use that value in place of `1800` in the `START_TS` comparison (default still `1800`). Document the hook in `breadcrumb-monitor.md` as test-only.

### UPDATED: `scripts/breadcrumb-monitor.md`
Document the new `--paired-pid-file` flag in the contract, its validation invariant (absolute path, no `..`, no symlinks, under the session tmpdir), its opt-in semantics (no flag → no signaling, full backward compatibility), the signal sequence (SIGTERM → up to 5× `kill -0` polling at 1s each → SIGKILL, every kill guarded with `|| true`), and the missing/malformed-pid-file fallback (`WARN paired-pid-file-missing` via `larch_err` + plain `exit 4`). Document the 33-byte read cap and the "reject any CR/LF or non-ASCII byte after stripping one trailing newline" rule. Document the `LARCH_BM_TEST_TIMEOUT_SECONDS` test-only env-var hook. Note the PID-reuse caveat: the helper does not verify the target is a child of the calling shell, so a long-departed PID could theoretically be reused; the 1800-second timeout makes this rare on operator machines but it is a documented limitation. Cross-reference the new `larch_quiet_write_paired_pid_file` helper in `lib-quiet.md` and the ownership model (top-level writers only).

### UPDATED: `scripts/lib-quiet.sh`
Add a new function `larch_quiet_write_paired_pid_file` near the other `larch_quiet_*` exports (between `larch_quiet_append_done_trap` definition and the end of the file, ~line 290 region). Body: when `LARCH_PAIRED_PID_FILE` is unset/empty, return 0 (no-op). Otherwise validate the env-var value by mirroring `breadcrumb-monitor.sh`'s `larch_bm_validate_path` rules — reuse `larch_log_breadcrumbs_under_session_tmp` from `lib-larch-log.sh` for the session-tmpdir-scope check; reject `..`, non-absolute paths, symlinks (`[ -L ... ]`), and paths whose parent directory does not exist or is not a writable directory. On any validation failure, emit `larch_err "WARN paired-pid-file-invalid"` and return 0 (never abort the caller — fail open per AGENTS.md). On success: allocate a tmp file with `mktemp "${LARCH_PAIRED_PID_FILE}.tmp.XXXXXX"` in the validated parent directory (NOT the predictable `.tmp.$$`), `printf '%s\n' "$$" > "$tmp"`, then `mv -f "$tmp" "$LARCH_PAIRED_PID_FILE"`. On any write/mv failure, clean up `$tmp` (best-effort `rm -f`) and return 0 with a `larch_err` warning. Bash 3.2-safe: no associative arrays, no namerefs, no `mapfile`. Source `lib-larch-log.sh` lazily inside the helper if needed (or rely on the existing top-of-file sourcing in each caller — confirm during implementation).

### UPDATED: `scripts/lib-quiet.md`
Document the new helper, its env-var contract (`LARCH_PAIRED_PID_FILE`), the **ownership rule** (only top-level Family B entrypoints call it: `ship-pr.sh`, `run-step5-review.sh`, `run-step2-dispatch.sh`, `collect-agent-results.sh`, `dispatch-plan-voters.sh`; nested children — `ci-wait.sh`, `review-and-fix.sh`, `step2-implement.sh`, `dispatch-with-waterfall.sh` — must NOT call it), the validation invariant (absolute, no `..`, no symlinks, under session tmpdir, parent must be writable directory), the atomic `mktemp + mv -f` semantics, the no-op-when-unset opt-in, and the fail-open contract (always returns 0 even when validation/write fails — never aborts the caller under `set -e`). Cross-reference `breadcrumb-monitor.md`.

### UPDATED: `SECURITY.md`
Add a new entry near the existing breadcrumb/runtime trust model section (~lines 136-149). Document: (a) the `LARCH_PAIRED_PID_FILE` / `--paired-pid-file` pairing contract; (b) the same-UID trust assumption (the monitor signals processes accessible to the operator's UID; cross-user signaling is out of scope); (c) the path containment invariant (paired-pid paths must be absolute, under the active session tmpdir, no symlinks, no `..`); (d) the PID-reuse caveat (long-departed PIDs could be reused — known limitation, mitigated by the 1800s timeout and the same-UID assumption); (e) the signal scope (`kill -TERM` then `kill -KILL` to the file-supplied PID only; no process-group signaling, no parent-traversal); (f) the fail-open posture for both the writer (no abort on invalid path) and the signal helper (no abort on kill failure — monitor always reaches `exit 4`).

### UPDATED: `scripts/ship-pr.sh`
In `main()` (~line 2837), immediately after `larch_quiet_init` + `larch_quiet_append_done_trap`, call `larch_quiet_write_paired_pid_file`. Immediately before invoking `ci-wait.sh` (~line 2620), `unset LARCH_PAIRED_PID_FILE` so the nested ci-wait does not see the env var (defensive — even if ci-wait acquires the helper call in some future refactor, it will be a no-op).

### UPDATED: `scripts/ship-pr.md`
Add a one-line note that `ship-pr.sh` is a top-level Family B writer of `LARCH_PAIRED_PID_FILE` and unsets the env var before invoking nested `ci-wait.sh`.

### UPDATED: `scripts/ci-wait.sh`
**Do NOT add `larch_quiet_write_paired_pid_file`**. Per the `ci-wait must remain synchronous` invariant (issue #842), `ci-wait` is never paired with `breadcrumb-monitor.sh` from any current SKILL.md fence; the env var inheritance from a parent `ship-pr.sh` is defused by ship-pr's `unset`. No changes to `ci-wait.sh` are required for issue #2848.

### UPDATED: `scripts/ci-wait.md`
**Keep the "synchronous-only" wording intact.** Do NOT add Family B pairing prose. Optionally add a one-line note under an existing Invariants section that `ci-wait.sh` is intentionally synchronous and is not on the new paired-PID-file writer list; this preserves the issue #842 / `rebase-rebump-subprocedure.md` invariant and the foreground-only contract.

### UPDATED: `scripts/run-step5-review.sh`
After `larch_quiet_append_done_trap` (~line 13), call `larch_quiet_write_paired_pid_file`. (The script intentionally does not call `larch_quiet_init`; the helper does not depend on init.) Immediately before invoking `review-and-fix.sh` (~lines 186-187), `unset LARCH_PAIRED_PID_FILE` so the nested child does not clobber the parent PID.

### UPDATED: `scripts/run-step5-review.md`
Add a one-line note that `run-step5-review.sh` is a top-level Family B writer and unsets the env var before invoking nested `review-and-fix.sh`.

### UPDATED: `skills/implement/scripts/run-step2-dispatch.sh`
Preserve the **no-init contract**: do NOT call `larch_quiet_init` (the existing comment at lines 14-17 explains why — initializing quiet mode would redirect diagnostics to a log file and break the orchestrator KV contract). Add the helper call immediately after the existing `larch_quiet_append_done_trap` line only (~line 86). Before invoking `step2-implement.sh` (~line 96-97), `unset LARCH_PAIRED_PID_FILE` so the child does not clobber the parent PID.

### UPDATED: `skills/implement/scripts/run-step2-dispatch.md`
Add a one-line note that `run-step2-dispatch.sh` is a top-level Family B writer (call placed after `larch_quiet_append_done_trap`, preserving the no-init contract) and unsets the env var before invoking nested `step2-implement.sh`.

### UPDATED: `scripts/collect-agent-results.sh`
After `larch_quiet_init` + `larch_quiet_append_done_trap` (~line 184), call `larch_quiet_write_paired_pid_file`. No nested DENYLIST children — no `unset` needed.

### UPDATED: `scripts/collect-agent-results.md`
Add a one-line note that `collect-agent-results.sh` is a top-level Family B writer.

### UPDATED: `scripts/dispatch-plan-voters.sh`
After the standard `lib-quiet.sh` init pair (~line 11), call `larch_quiet_write_paired_pid_file`. Immediately before invoking `dispatch-with-waterfall.sh` (~line 138), `unset LARCH_PAIRED_PID_FILE` so the child does not clobber the parent PID.

### UPDATED: `scripts/dispatch-plan-voters.md`
Add a one-line note that `dispatch-plan-voters.sh` is a top-level Family B writer and unsets the env var before invoking nested `dispatch-with-waterfall.sh`.

### UPDATED: `scripts/dispatch-code-voters.sh`
Although not in the DENYLIST, this script also invokes `dispatch-with-waterfall.sh` (line 172). For symmetry and defense in depth: if `dispatch-code-voters.sh` is reached through a top-level Family B that has set `LARCH_PAIRED_PID_FILE`, the inherited env var should be unset before the nested `dispatch-with-waterfall.sh` invocation. Add the `unset LARCH_PAIRED_PID_FILE` immediately before line 172. No `larch_quiet_write_paired_pid_file` call — this script is not on the top-level writer list.

### UPDATED: `scripts/dispatch-code-voters.md`
Add a one-line note about the defensive `unset` before invoking nested `dispatch-with-waterfall.sh`.

### UPDATED: `scripts/lint-foreground-markers.sh`
In the per-anchor enforcement block that currently computes `has_rb` / `has_c` (~line 345 region around the `breadcrumb-monitor.sh` argv match at line 347), add two new checks: (a) `has_pid_alloc` — the fence body contains a line matching either `LARCH_PAIRED_PID_FILE="$(mktemp` (single-line capture) or a multi-line pair where `LARCH_PAIRED_PID_FILE=$(mktemp ...)` is followed by `export LARCH_PAIRED_PID_FILE` (or `export LARCH_PAIRED_PID_FILE="$(mktemp ...)"` on one line). Bare `export LARCH_PAIRED_PID_FILE` without a same-fence mktemp assignment MUST fail the check — verify by requiring the mktemp assignment to be from `$DESIGN_TMPDIR/breadcrumbs/` / `$IMPLEMENT_TMPDIR/breadcrumbs/` / `$REVIEW_TMPDIR/breadcrumbs/` / `$RESEARCH_TMPDIR/breadcrumbs/`. (b) `has_pid_flag` — the paired `breadcrumb-monitor.sh` invocation argv contains `--paired-pid-file` with a non-empty argument. When the anchor's basename is in the Family B DENYLIST set MINUS `step-7a.sh` AND MINUS the four nested-only basenames (`ci-wait.sh`, `review-and-fix.sh`, `step2-implement.sh`, `dispatch-with-waterfall.sh`), BOTH checks must be true. Maintain a small inline exclusion list inside `lint-foreground-markers.sh` documenting why the four nested-only entries are not required to carry the new tokens. Emit clear errors attaching file path, line number, basename, and the missing check name. Bash 3.2-safe (`case` over the lists, no associative arrays).

### UPDATED: `scripts/lint-foreground-markers.md`
Document the two new required tokens (`LARCH_PAIRED_PID_FILE` mktemp allocation/export under a session breadcrumbs subdirectory; `--paired-pid-file` on the monitor invocation), the `step-7a.sh` foreground-only carve-out (unchanged), and the four nested-only basenames (`ci-wait.sh`, `review-and-fix.sh`, `step2-implement.sh`, `dispatch-with-waterfall.sh`) that do NOT need the new tokens because they are never the top-level script in a paired fence. Document the exact error wording emitted for each missing check.

### UPDATED: `scripts/test-lint-foreground-markers.sh`
First, update **all existing `assert_case_clean` fences** (estimated ~22 cases that exercise the top-level Family B basenames) to include both `LARCH_PAIRED_PID_FILE=$(mktemp …)` and `export LARCH_PAIRED_PID_FILE` allocation lines AND a `--paired-pid-file "$LARCH_PAIRED_PID_FILE"` argument on the paired `breadcrumb-monitor.sh` invocation. Then add new negative fixtures (~line 100 region near the existing background-pair fixtures): (a) Family B top-level fence missing the mktemp allocation entirely — must fail with the new `missing LARCH_PAIRED_PID_FILE allocation` error; (b) Family B top-level fence with bare `export LARCH_PAIRED_PID_FILE` but no mktemp assignment — must fail; (c) Family B top-level fence with allocation but no `--paired-pid-file` on the paired monitor — must fail; (d) Family B top-level fence with both tokens — must pass; (e) `step-7a.sh` foreground-only fence — must pass without either token (carve-out preserved); (f) `ci-wait.sh` / `review-and-fix.sh` / `step2-implement.sh` / `dispatch-with-waterfall.sh` nested-only fence — must pass without the new tokens (existing background+monitor banner still required when these scripts ever appear directly in a fence, but the new tokens are NOT). Use the existing fixture format (heredoc-based temp Markdown files); do not introduce a new test harness layout.

### UPDATED: `scripts/test-lint-foreground-markers.md`
Update the harness contract description to note the six new fixture categories and the requirement that all existing passing fixtures now carry the new tokens.

### UPDATED: `scripts/test-breadcrumb-monitor.sh`
Add new test cases near the end of the file (~line 520 region, after the current last `test 15` block): (a) **TERM signaled on timeout** — set `LARCH_BM_TEST_TIMEOUT_SECONDS=2`, launch `sleep 30 &` and write `$!` to the paired pid file, invoke monitor with `--paired-pid-file`, assert the sleep PID is gone after monitor exits 4, assert the monitor stderr contains no `WARN paired-pid-file-missing`. (b) **KILL escalates after 5s grace** — set `LARCH_BM_TEST_TIMEOUT_SECONDS=2`, launch a TERM-ignoring child via `bash -c 'trap "" TERM; while sleep 1; do :; done' &` (bash builtins inherit through `bash -c` — the trap takes effect inside the child process), write `$!` to the pid file, invoke monitor, assert the child PID is gone within ~7 seconds (2 + 5s grace), assert the kill -KILL path executed. (c) **Missing pid file** — point `--paired-pid-file` at a non-existent path; assert `WARN paired-pid-file-missing` is emitted via stderr; assert exit 4. (d) **Empty pid file** — point at a 0-byte file; same expectations. (e) **Malformed pid file** — write `not-a-number\n` to the file; same expectations. (f) **Multi-line pid file** — write `12345\nstuff\n` (>32 bytes total) to the file; assert reject + WARN + exit 4. (g) **CR/LF only** — write `12345\r\n`; assert reject (CR after stripping single newline). (h) **Stale PID (process exited before TERM)** — write a PID for a process that no longer exists; assert monitor reaches `exit 4` cleanly (no `set -e` abort from the kill failure), and that the WARN path is NOT triggered (the PID was syntactically valid; the kill silently failed via `|| true`). (i) **Nested-script regression** — simulate the top-level / nested-child scenario: launch a "parent" sleep 30 process, write its PID to the file, then have a "child" sleep 5 process overwrite the same file with its own PID, wait for the child to exit (5s), then trigger monitor timeout — assert the monitor signals the now-stale child PID (matching the documented first-or-last-writer semantics; this test pins the current behavior and would catch a future regression). Use the existing harness skeleton (`SURFACED="$(mktemp ...)"`, etc.). Bash 3.2-safe.

### UPDATED: `scripts/test-breadcrumb-monitor.md`
Update the harness contract description to note all new test cases, the `LARCH_BM_TEST_TIMEOUT_SECONDS` test-only env-var hook, and the nested-script regression test.

### UPDATED: `scripts/test-lib-quiet.sh`
Add new tests for `larch_quiet_write_paired_pid_file`: (a) no-op when env var unset; (b) atomic write when set and path is valid — verify the written content is exactly `<pid>\n`, verify no `.tmp.XXXXXX` leftover; (c) write failure on unwritable parent — verify return code is 0 (fail-open) and a `larch_err` warning was emitted; (d) reject path outside session tmpdir — verify return code is 0 and no file was written; (e) reject symlinked path — create a symlink, point env var at it, verify rejection; (f) reject path with `..` — verify rejection; (g) reject non-absolute path — verify rejection; (h) parallel-write race — two subshells both call the helper with the same path; verify the final file content is one of the two PIDs (no torn write), and the lone `.tmp.XXXXXX` artifact (if any) is cleaned up. Bash 3.2-safe.

### UPDATED: `scripts/test-lib-quiet.md`
Update the harness contract description to note the new test cases.

### UPDATED: `skills/design/SKILL.md`
Update the two `collect-agent-results.sh` paired-monitor fence blocks (~lines 412 and 444 — the Step 2a.3 Regular and Quick mode fences) to allocate `LARCH_PAIRED_PID_FILE` via `mktemp` under `$DESIGN_TMPDIR/breadcrumbs/`, export it before the background launch, and pass `--paired-pid-file "$LARCH_PAIRED_PID_FILE"` to the paired `breadcrumb-monitor.sh` invocation. Mirror the same env-var allocation pattern already in use for the other five LARCH_* env vars.

### UPDATED: `skills/implement/SKILL.md`
Update the paired-monitor fence blocks at ~line 913 (run-step2-dispatch), ~lines 1175 and 1232 (run-step5-review), and ~line 1466 (ship-pr) to allocate `LARCH_PAIRED_PID_FILE`, export it before launch, and pass `--paired-pid-file` to the paired monitor. **Also update the NEVER #16 invariant text** at ~line 66 to include `LARCH_PAIRED_PID_FILE` in the list of breadcrumb env vars and to mention the `--paired-pid-file` monitor argument requirement; the current text enumerates only the five existing LARCH_* paths and would conflict with the new linter contract.

### UPDATED: `skills/implement/references/rebase-rebump-subprocedure.md`
Per FINDING_12 / FINDING_23, reconcile the prose at ~line 175-184 that pins `ci-wait.sh` as "synchronous-only" — keep the `ci-wait` synchronous invariant (issue #842) explicit and add a small forward-reference paragraph stating that `ci-wait` is intentionally excluded from the new `LARCH_PAIRED_PID_FILE` writer list for this reason. This documents the carve-out so future readers don't accidentally promote `ci-wait` to a paired-monitor pattern.

### UPDATED: `skills/shared/external-reviewers.md`
Update the paired-monitor fence at ~line 46 to include the new allocation/export and the monitor flag.

### UPDATED: `skills/shared/dialectic-protocol.md`
Update the paired-monitor fence at ~line 262 to include the new allocation/export and the monitor flag.

### UPDATED: `skills/design/references/brainstorm.md`
Update the paired-monitor fences at ~lines 84 and 113 to include the new allocation/export and the monitor flag.

### UPDATED: `skills/design/references/dialectic-execution.md`
Update the paired-monitor fences at ~lines 71 and 207 to include the new allocation/export and the monitor flag.

### UPDATED: `skills/design/references/plan-review.md`
Update the paired-monitor fences at ~lines 93 and 142 to include the new allocation/export and the monitor flag.

### UPDATED: `skills/research/references/research-phase.md`
Update the paired-monitor fence at ~line 190 to include the new allocation/export and the monitor flag.

### UPDATED: `skills/research/references/validation-phase.md`
Update the paired-monitor fence at ~line 184 to include the new allocation/export and the monitor flag.

### UPDATED: `BASH_AUTHORING.md`
Add a paragraph in §4 documenting the new `LARCH_PAIRED_PID_FILE` env var + `--paired-pid-file` flag contract. Cite it next to the existing five env vars (`LARCH_BREADCRUMB_STREAM`, `LARCH_DONE_SENTINEL`, `LARCH_STATUS_FILE`, `LARCH_QUIET_LOG_FILE`, `LARCH_BREADCRUMBS_SURFACED_FILE`) and note the new linter enforcement. Document the ownership model: only top-level Family B scripts write the PID file; nested children (`ci-wait`, `review-and-fix`, `step2-implement`, `dispatch-with-waterfall`) do NOT call the helper and parents `unset` the env var before spawning nested children. Update the "Pre-launch path allocation" paragraph to mention the new sixth env var.

### Duplication audit (item 1) — sweep notes, no file edits expected
Re-read `scripts/design-log-publish.sh` and `scripts/larch-log.sh` side-by-side. Confirm `design_publish_breadcrumbs` (lines 255-263) and `larch_log_publish_breadcrumbs` (lines 156-163) are 3-line wrappers delegating to `larch_log_publish_breadcrumbs_shared` in `scripts/lib-larch-log.sh:356`. Confirm the staging/redaction/atomic-mv logic only lives in the shared helper. Scan adjacent helpers (`design_publish_stage_file`, manifest writers, file enumerators, error callbacks) for residual line-for-line copy-paste. Per Codex's reservation, only consolidate exact shared behavior — manifest writers and file enumerators in `design-log-publish.sh` are domain-specific (design-specific `RUN_DEST="$WT_DIR/larch-logs/design/$RUN_ID"`, `plan-review` subtree handling, etc.) and over-sharing them would be a bigger risk than the residual duplication. If nothing in this sweep merits consolidation, the audit produces no file edits; document the result in the PR description rather than adding placeholder edits.

## Approach

The new pairing mechanism is **strictly opt-in and backward-compatible**. The monitor's existing argv contract grows by one optional flag (`--paired-pid-file`); existing callers that pass none of: the env var or the flag get byte-identical behavior. Top-level Family B background scripts gain a one-line call after their existing `larch_quiet_init` / `larch_quiet_append_done_trap` pair to register their PID; the helper itself is a no-op when the env var is unset.

**The critical design refinement after plan review**: PID-file ownership is restricted to top-level Family B entrypoints. Nested DENYLIST children (`ci-wait`, `review-and-fix`, `step2-implement`, `dispatch-with-waterfall`) do NOT call the helper, and their parents `unset LARCH_PAIRED_PID_FILE` before spawning them. This prevents the documented orphan-regression where a child overwrites the file with its own (short-lived) PID and the monitor signals a dead child while the long-running parent continues. The linter enforces only the top-level subset; nested basenames are explicitly carved out via an inline exclusion list in `lint-foreground-markers.sh`.

The helper itself enforces the same path-validation invariant as the monitor (absolute, no `..`, no symlinks, under the session tmpdir, parent directory must exist and be writable). It uses an atomic `mktemp` + `mv -f` write — not the predictable `.tmp.$$` pattern — and is fail-open: validation or write failures emit a `larch_err` warning and return 0 so callers do not abort under `set -e`.

The monitor's signal helper guards every `kill -TERM`, `kill -0`, and `kill -KILL` call with `|| true` so that stale/EPERM/ESRCH PIDs never abort the monitor before its `exit 4`. The 33-byte read cap and strict CR/LF/non-ASCII rejection prevent malformed PID files from being misinterpreted. The helper always returns 0.

Item (1) is handled as a quiet sweep folded into the PR diff per Round 1 Decision 7. The expected outcome is that no consolidation is needed (the prior #2790/#2849 refactor already covered the duplication). If the sweep does find a small residual block worth sharing, add it as a focused edit to `scripts/lib-larch-log.sh` plus the two callsites — keep scope tight.

The new SECURITY.md entry documents the same-UID trust assumption, the path containment invariant, the PID-reuse caveat, and the signal scope, so the security model is explicit and reviewable.

## Edge cases

- **PID reuse**: a long-departed PID could be reused by an unrelated process by the time the monitor sends SIGTERM. The signal helper does not verify the target is a child of the calling shell (cross-Bash-3.2 child-process verification is awkward and platform-specific). Accept the small reuse risk as a known limitation; document it in `breadcrumb-monitor.md` and `SECURITY.md`. The 1800-second monitor timeout already implies the script has been alive for ~30 minutes, which is uncommon for trivial PID-reuse collisions on a typical operator machine.
- **PID-file race on slow startup**: if the monitor's 1800-second timeout elapses before the background script reaches `larch_quiet_write_paired_pid_file`, the PID file is empty or missing. The WARN-and-skip fallback handles this gracefully.
- **Multi-line / over-sized PID files**: the monitor reads exactly 33 bytes via `dd bs=1 count=33`. Any payload of 33 bytes or more (after stripping one trailing newline) is rejected as malformed. Any CR/LF/non-ASCII byte in the remaining content is rejected. Empty strings are rejected. The strict reader prevents accidental matching of "12345" inside a longer corrupt file.
- **Atomic write contention**: the lib-quiet helper uses `mktemp` in the validated parent directory + `mv -f` (atomic on the same filesystem). The monitor reads after the timeout — well after the write race window. No additional locking needed. Concurrent writes from two subshells would either both succeed (last-mv-wins) or one's tmp leaks (cleaned up best-effort).
- **Nested Family B child clobber**: explicitly prevented by (a) restricting the helper call to top-level entrypoints only and (b) defensive `unset LARCH_PAIRED_PID_FILE` in parents before invoking nested children. The regression test in `test-breadcrumb-monitor.sh` (case "Nested-script regression") pins this behavior.
- **`ci-wait` synchronous invariant**: preserved. `ci-wait.sh` is never paired with a monitor in any current SKILL.md fence; the parent `ship-pr.sh` unsets the env var before invoking `ci-wait`; `ci-wait.md` retains its "synchronous-only" wording; `rebase-rebump-subprocedure.md` is updated with a forward-reference paragraph documenting the carve-out.
- **`run-step2-dispatch.sh` no-init contract**: preserved. The helper is called only after `larch_quiet_append_done_trap` (no `larch_quiet_init` introduced). The orchestrator KV contract from `step2-implement.sh` is not disturbed.
- **Stale PID kill failure**: every `kill` invocation is `|| true` guarded. The monitor reaches `exit 4` regardless of whether the kill succeeded, failed with EPERM, or failed with ESRCH.
- **Cursor sketch empty-output anomaly**: surfaced during this design session — Cursor returned EXIT_CODE=0 with no substantive content. Logged in execution-issues.md; not a code-change issue.
- **Non-existent paired-pid-file at validation**: the existing `larch_bm_validate_path` (line 49) returns 0 for paths that do not yet exist, which is the correct behavior for `--paired-pid-file` (the file is created by the background script slightly later than the monitor's argv parse). No new validation branch needed in the monitor.

## Failure modes

1. **Linter false-positive on legacy fences** — if the lint-foreground-markers update is enforced before all callsites are converted, CI fails on the conversion PR itself. Mitigation: stage the linter change in the same commit/PR that updates all callsites, the SKILL.md fences, and all existing `assert_case_clean` fixtures. Earliest warning signal: pre-commit hook failing on the implementer's machine. Simplest mitigation: edit order — SKILL.md/refs/Family B scripts/test fixtures first, lint last in the diff sequence; pre-commit runs lint against the final tree.
2. **Bash 3.2 portability regression** — the kill-loop helper, the new lib-quiet function, or the linter check accidentally uses Bash 4+ idioms (associative arrays, `mapfile`, parameter case conversion). Mitigation: keep functions plain `case`/`while`/`printf`/`mv`/`kill`/`sleep`; run `make lint-bash32` after edits. Earliest warning signal: `make lint-bash32` failing in CI.
3. **PID-file write races multi-shell launches** — if two background scripts inherit the same `LARCH_PAIRED_PID_FILE` value (operator misconfiguration), the second write clobbers the first. Mitigation: each fenced block in SKILL.md allocates a fresh `mktemp` path; document explicitly in BASH_AUTHORING.md that the env var must be allocated per-launch, never reused across two background scripts. The nested-Family-B variant of this same race is prevented by the ownership model + defensive unset in parents.

## Testing strategy

- **Unit/harness**: extend `scripts/test-breadcrumb-monitor.sh` with the nine new test cases (TERM, KILL escalation, missing/empty/malformed/multi-line/CR-LF pid file, stale PID kill-failure, and the nested-script regression). Extend `scripts/test-lib-quiet.sh` with the helper's eight no-op/atomic-write/fail-open/validation cases. Extend `scripts/test-lint-foreground-markers.sh` with the six new lint-enforcement fixtures and update all ~22 existing passing fixtures to include the new tokens.
- **Linter regression**: run `make lint-foreground-markers` (alias `make lint-foreground`) and `make lint-bash32` after the edits. Confirm the linter passes on the converted tree and fails on the new negative fixtures by construction.
- **End-to-end**: run a small `/design --simple <issue>` or `/research` invocation locally to exercise at least one of the converted fences (any `collect-agent-results.sh` paired call); confirm no behavioral regression and that `$LARCH_PAIRED_PID_FILE` is created and populated with the background script's PID.
- **Idempotency check**: re-run `bash scripts/relevant-checks.sh` (or `make lint`) per `AGENTS.md` to confirm all pre-commit hooks pass.
- **Cross-check**: grep for any remaining mention of "5 env vars" or "five env vars" in normative docs that might list the LARCH_* allocation surface; update to "six" with the new addition where appropriate.

diff_lines: 700

## Acceptance

- [ ] `scripts/breadcrumb-monitor.sh` accepts `--paired-pid-file <PATH>` flag and reads it through `larch_bm_validate_path`. On the 1800s timeout branch (or test-only `LARCH_BM_TEST_TIMEOUT_SECONDS` override), the monitor invokes `larch_bm_signal_paired_pid` before `exit 4`. Every `kill` call (TERM, -0 polling, KILL) is guarded with `|| true` so the monitor always reaches `exit 4`. PID-file read is bounded to 33 bytes; any CR/LF/non-ASCII byte or value exceeding 32 bytes after stripping one trailing newline is rejected with `larch_err "WARN paired-pid-file-missing"` (helper returns 0).
- [ ] `scripts/lib-quiet.sh` defines `larch_quiet_write_paired_pid_file` with the same path-validation invariant as the monitor (absolute, no `..`, no symlinks, under session tmpdir, writable parent). Atomic write via `mktemp` (not predictable `.tmp.$$`) + `mv -f`. Fail-open semantics: invalid path or write failure emits `larch_err` and returns 0 — never aborts caller under `set -e`.
- [ ] Only the 5 top-level Family B entrypoints (`ship-pr.sh`, `run-step5-review.sh`, `run-step2-dispatch.sh`, `collect-agent-results.sh`, `dispatch-plan-voters.sh`) call `larch_quiet_write_paired_pid_file`. The 4 nested-only basenames (`ci-wait.sh`, `review-and-fix.sh`, `step2-implement.sh`, `dispatch-with-waterfall.sh`) do NOT. Each parent `unset LARCH_PAIRED_PID_FILE` immediately before invoking its nested DENYLIST child (`ship-pr→ci-wait`; `run-step5-review→review-and-fix`; `run-step2-dispatch→step2-implement`; `dispatch-plan-voters→dispatch-with-waterfall`; `dispatch-code-voters→dispatch-with-waterfall`).
- [ ] `scripts/ci-wait.sh` and `scripts/ci-wait.md` retain the synchronous-only invariant (issue #842). No paired-monitor pattern is introduced; the env var inheritance from `ship-pr` is defused by the parent `unset`.
- [ ] `skills/implement/scripts/run-step2-dispatch.sh` retains the no-init contract (no `larch_quiet_init` call). The helper is inserted only after `larch_quiet_append_done_trap`.
- [ ] `scripts/lint-foreground-markers.sh` enforces the new contract for top-level Family B anchors only: `has_pid_alloc` (mktemp assignment under a session breadcrumbs subdirectory plus `export`; bare `export` alone fails) AND `has_pid_flag` (`--paired-pid-file` on the paired `breadcrumb-monitor.sh` invocation). `step-7a.sh` and the 4 nested-only basenames are explicitly excluded.
- [ ] `scripts/test-lint-foreground-markers.sh`: all existing `assert_case_clean` Family B fixtures (~22 cases) updated to carry both new tokens. New fixtures: missing-mktemp, bare-export-no-mktemp, missing-monitor-flag (all FAIL), happy-path (PASS), step-7a foreground-only (PASS), 4 nested-only basenames (PASS).
- [ ] `scripts/test-breadcrumb-monitor.sh`: 9 new test cases covering TERM signal, KILL escalation, missing/empty/malformed/multi-line/CR-LF pid files, stale PID (kill failure), and nested-script regression.
- [ ] `scripts/test-lib-quiet.sh`: 8 new test cases covering helper no-op, atomic write, fail-open on unwritable parent, rejection of paths outside session tmpdir / symlinks / `..` / non-absolute, parallel write race.
- [ ] All 9 paired-monitor fenced blocks in SKILL.md / references are updated: 2 in `skills/design/SKILL.md`, 4 in `skills/implement/SKILL.md`, 1 in `skills/shared/external-reviewers.md`, 1 in `skills/shared/dialectic-protocol.md`, 2 in `skills/design/references/brainstorm.md`, 2 in `skills/design/references/dialectic-execution.md`, 2 in `skills/design/references/plan-review.md`, 1 in `skills/research/references/research-phase.md`, 1 in `skills/research/references/validation-phase.md`.
- [ ] `skills/implement/SKILL.md` NEVER #16 invariant text updated to include `LARCH_PAIRED_PID_FILE` in the LARCH_* env-var list and the `--paired-pid-file` argument requirement.
- [ ] `skills/implement/references/rebase-rebump-subprocedure.md` reconciled: `ci-wait` synchronous-only invariant retained; small forward-reference paragraph documents the explicit exclusion of `ci-wait` from the new PID-file writer list.
- [ ] `SECURITY.md` extended with a paragraph documenting the paired-PID trust model: same-UID assumption, path containment invariant, PID-reuse caveat, signal scope (TERM then KILL to the file-supplied PID only, no process-group signaling), and fail-open posture for both helper and signal paths.
- [ ] `BASH_AUTHORING.md` §4 updated to list the new sixth env var `LARCH_PAIRED_PID_FILE` next to the existing five LARCH_* paths, document the ownership model (top-level writers only), and note the linter enforcement.
- [ ] Every modified `.sh` script has its sibling `.md` updated in the same PR (per `.claude/rules/script-md-siblings.md`).
- [ ] `make lint-foreground-markers` and `make lint-bash32` pass on the converted tree.
- [ ] `bash scripts/relevant-checks.sh` (or `make lint`) passes after the edits.
- [ ] Item (1) audit completed: side-by-side sweep of `design-log-publish.sh` vs `larch-log.sh` / `lib-larch-log.sh` confirms the breadcrumb-publish duplication is already eliminated via `larch_log_publish_breadcrumbs_shared`. Any residual line-for-line copy-paste found during the sweep is consolidated (or, if none, documented in the PR description with no file edits).

diff_lines: 700

## Test plan
(no test plan section in plan-file)
