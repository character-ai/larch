Verifying a few source locations so merged findings stay accurate.
### FINDING_1: Archival reject message misstates bracket pattern
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The archival title-filter reject banner at `skills/design/scripts/design-route.sh:264` says `` `[...] Report` ``, implying "Report" comes after the closing bracket, but `LARCH_TITLE_ARCHIVAL_REPORT_REGEX_BASH='^\[.*[Rr]eport\] '` in `lib-title-eligibility.sh` requires "Report" inside the brackets (e.g., `[Research Report] Foo`). The older SKILL.md wording `` `[... Report]` `` matched the regex; the new message can mislead operators renaming titles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Change the message back to `` `[... Report]` `` (closing bracket after Report, matching the regex pattern).

### FINDING_2: `render_cancel_summary` captures unused `_render_rc` and hides render failures
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: In `render_cancel_summary` (`skills/design/scripts/design-route.sh:235-254`), `_render_rc` is declared, assigned from `$?`, and never read before the function unconditionally `return 0`. This is dead code (shellcheck SC2034), obscures the intentional "tolerate non-zero render rc" contract, and leaves render failures unobservable at the driver level (no WARN KV, no branch) even though stderr/FD4 may carry child diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the `_render_rc=0` from the `local` declaration and the `_render_rc=$?` assignment, replacing the capture with a comment like `# render failure tolerated; exit 0 regardless` to make the intent explicit.
  - From cursor-specialist-correctness-output.txt: Either drop the capture entirely (`render_cancel_summary() { ... ; return 0; }` with no `_render_rc`) to make intent explicit and silence shellcheck, or promote it to a `WARN` KV via `WARN_LINES+=("render-cancel-summary-failed rc=$_render_rc")` before `return 0` so CI/ops can detect render failures.
  - From cursor-specialist-testing-output.txt: Remove the `_render_rc=0` declaration and `_render_rc=$?` assignment; keep only `return 0` after `set -e`.
  - From cursor-specialist-security-output.txt: remove the `_render_rc` local declaration and assignment; leave a comment documenting that render failure is intentionally tolerated.
  - From cursor-specialist-edge-cases-output.txt: Drop the capture entirely (no _render_rc) or promote to WARN_LINES+=("render-cancel-summary-failed rc=$_render_rc") before return 0.

### FINDING_3: `route_emit_stdout_and_exit` has no guard that `ROUTE_KVS` was built
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `ROUTE_KVS` is a script-global array populated only by `route_build_kvs` inside `route_write_result_env`. `emit_route_result` and `emit_cancel_route_result` call `route_write_result_env` first, but `route_emit_stdout_and_exit` itself has no precondition check. A direct or mistaken call would silently emit zero KVs and `exit 0`, yielding an empty-looking success that downstream parses as `ROUTE=""` and fails later with an opaque "missing or invalid ROUTE" error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a brief comment on `ROUTE_KVS` noting it is always populated by `route_write_result_env` before use, or assert `[[ ${#ROUTE_KVS[@]} -gt 0 ]]` at the top of `route_emit_stdout_and_exit` to make the precondition explicit.
  - From cursor-specialist-correctness-output.txt: Add a guard: `[[ ${#ROUTE_KVS[@]} -gt 0 ]] || { larch_err 'route_emit_stdout_and_exit: ROUTE_KVS not built'; exit 2; }` at the top of `route_emit_stdout_and_exit`, or make `ROUTE_KVS` local by inlining `route_build_kvs` into `route_write_result_env`.
  - From cursor-specialist-edge-cases-output.txt: Assert `[[ ${#ROUTE_KVS[@]} -gt 0 ]]` at the top of `route_emit_stdout_and_exit` to make the precondition explicit.

### FINDING_4: `route_emit_cancel_side_effects` silently no-ops on unknown cancel routes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `route_emit_cancel_side_effects` (`skills/design/scripts/design-route.sh:257-278`) handles only `cancel-title-filter` and `cancel-reentry-guard`. Any other `ROUTE` value falls through with no reject banner and no `render-final-summary.sh` invocation. A future cancel route wired through `emit_cancel_route_result` would fail silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a `*) fail "route_emit_cancel_side_effects: unexpected ROUTE=${ROUTE}"` arm to the `case` to fail loudly if called with an unhandled cancel route.

### FINDING_5: `write-design-current-env.sh` stdout suppression lacks documented protocol assumption
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: In `design-init-runparams.sh` (resume env-refresh path), child stdout is redirected to `/dev/null` in both quiet and non-quiet branches. This is correct only if `write-design-current-env.sh` never emits parsed `WARN=` / other KVs to stdout on failure; any such stdout is now discarded with no test or comment anchoring the assumption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add an inline comment at the `>/dev/null` line stating "write-design-current-env.sh must not emit KVs to stdout; only stderr diagnostics are expected" to document the protocol assumption and make a future violation detectable.

### FINDING_6: `bare_devnull_count` threshold is a brittle count floor, not a per-branch pin
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-structure.sh` uses `bare_devnull_count=$(grep -cE '>/dev/null$' ...)` with threshold `< 2`. The check passes if unrelated `>/dev/null` lines are added while one required resume/render redirect is removed (count stays ≥ 2). An exact-count pin (`-eq 2`) would catch drift in either direction; pinning specific non-quiet branch patterns per child invocation would be tighter still.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Instead of counting bare `>/dev/null` lines globally, pin specific non-quiet branch patterns for each child invocation (similar to how the quiet branch is tested via the `[ "${LARCH_QUIET_PID:-}" = "$$" ]` grep), or document the current count as an explicit minimum and bump it when new child calls are added.
  - From cursor-specialist-edge-cases-output.txt: `[[ $(grep -cE '>/dev/null$' "$DESIGN_ROUTE_SH") -eq 2 ]] || fail ...` This fails if the count moves in either direction without an explicit test update.

### FINDING_7: Post-fence cancel handling lacks mechanical symlink-refusal enforcement
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Step 0b post-fence cancel handling in `skills/design/SKILL.md` (~line 409) is prose-only: it instructs re-reading `.design-route-result.env` with "file-first; refuse symlinks", but there is no post-fence bash fence and `scripts/test-design-structure.sh` pins only the `[ -s … ]` gate and "Cancel routes always terminate before sub-step 3", not the symlink-refusal or explicit result-env re-read wording. An orchestrator turn can reuse in-fence `ROUTE` (equivalent value) and skip symlink refusal; a future edit can drop symlink guards without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add a bash fence for the post-fence cancel handling (read `.design-route-result.env`, symlink check, `ROUTE=` parse, `[ -s ... ]` emit, unconditional abort), making it mechanical rather than instructional.
  - From cursor-specialist-testing-output.txt: Add `printf '%s\n' "$step0b_block" | grep -Fq 'refuse symlinks' || fail "post-fence result-env read must refuse symlinks"`.
  - From cursor-specialist-plan-fidelity-output.txt: Add `grep -Fq '.design-route-result.env' …` and `grep -Fq 'refuse symlinks' …` (or the equivalent wording from SKILL.md) to the `step0b_block` check block.

### FINDING_8: Missing structural pin for resume env-refresh failure before `ROUTE=resume@*`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Cancel paths have an ordering assertion (`cancel_write_line` before `cancel_side_effects_line`), but there is no equivalent check that resume env-refresh `larch_err` + `exit 1` (`design-route.sh` ~345-347) precedes `ROUTE="resume@${_step}"` (~349) and `emit_route_result`. A refactor swapping those lines would let the orchestrator see `ROUTE=resume@*` after env-refresh failure and proceed on stale env.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a line-number ordering check analogous to the cancel pattern: grep for the resume `larch_err` failure line and for `ROUTE="resume@`, then `(( fail_line < route_assign_line ))`.

### FINDING_9: `test-step0b-router-flag-recovery.sh` assumption that it never calls `design-route.sh` is unpinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `design-route.sh` now requires `--session-id` (exit 2 when missing). The plan asserts `test-step0b-router-flag-recovery.sh` only exercises `design-init-runparams.sh`, but the diff adds no structural pin confirming the harness never invokes `design-route.sh`. If it did, cases would exit 2 before exercising router-flag recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Read `scripts/test-step0b-router-flag-recovery.sh` to confirm no `design-route.sh` invocation; add a `! grep -q 'design-route.sh' "$HARNESS"` structural assertion or a code comment if the assumption is load-bearing.

### FINDING_10: No runtime smoke test for KV-stream isolation on cancel paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `render-final-summary.sh --post-publish-only` emits summary body on stdout while driver stdout is the KV stream. Structural pins assert `>/dev/null` presence, but no CI-runnable test invokes `design-route.sh` on a cancel-eligible title and asserts stdout contains only KV lines. If summary output escapes the redirect, SKILL.md KV parsing silently ingests garbage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add at minimum a minimal cancel fixture in `test-design-structure.sh` or a companion smoke script: mock `render-final-summary.sh` to emit a sentinel line, call `design-route.sh` with a `[IMPLEMENTING]`-prefixed title, assert stdout has no non-`KEY=VALUE` lines.

### FINDING_11: `TITLE_FILTER_MARKER` interpolated into `larch_err` may be unsafe if format-string semantics differ
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: At `skills/design/scripts/design-route.sh:261`, `TITLE_FILTER_MARKER` (derived from external GitHub issue title) is interpolated into the double-quoted first argument of `larch_err`. If `larch_err` treated that argument as a `printf` format string (unlike the safe `larch_errf` pattern used for reentry-guard at line 269), a `%` in the title could cause format-string injection. The reentry-guard path already uses positional `%s` args correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: verify `larch_err` uses `printf '%s'` (or equivalent) internally; if not, convert the title-filter banner to `larch_errf '...lifecycle marker %s — ...' "${TITLE_FILTER_MARKER:-<token>}"` to match the pattern already used for the reentry-guard case.

### FINDING_12: Re-entry guard KV parsing uses unsafe word-splitting
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: At `skills/design/scripts/design-route.sh:401-407`, `for _rkv in $_reentry_out` word-splits unquoted output. Embedded whitespace or newlines in a future KV value (e.g., `MARKER_PATH=...`) would split/truncate silently; the pause-load sibling uses safe `while read`. Current `MARKER_HIT` / `MARKER_AGE` / `MARKER_TTL` are single-token, but the idiom is inconsistent and fragile for extension.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Embedded whitespace: if `_reentry_out` ever contains a value with spaces (e.g., a path in a future `MARKER_PATH=...` KV), the `for` loop splits it into two tokens and the case match fails silently, leaving the variable at its default.
  - From cursor-specialist-edge-cases-output.txt: Newline-embedded values: word splitting on unquoted `$var` collapses embedded newlines to IFS whitespace. If `design_reentry_marker_hit` emits multi-word values, the parser silently truncates them. In this change the three parsed KVs (`MARKER_HIT`, `MARKER_AGE`, `MARKER_TTL`) are all numeric or boolean single-words, so the current behavior is correct. But the inconsistency with the safe `while read` idiom used everywhere else in the file is a maintenance risk: if a future KV is added to `design_reentry_marker_hit`'s output with a string value (e.g., `MARKER_PATH=...`), it would silently fail to parse.

### FINDING_13: Empty `DESIGN_REENTRY_MARKER_PATH` yields blank path in reentry-guard banner
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `DESIGN_REENTRY_MARKER_PATH="$(design_reentry_marker_path ... 2>/dev/null || true)"` (`design-route.sh:410`) can leave the variable empty; `larch_errf` at lines 269-270 then prints "…delete  to override." with a blank where the path should be. Pre-existing behavior, not introduced by this refactor, but moving the banner into the driver makes the gap less visible to editors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: a non-empty guard or fallback literal (e.g., `${DESIGN_REENTRY_MARKER_PATH:-<unknown-path>}`) would eliminate the blank.

### FINDING_14: Missing ordering pin for `larch_err` before `render_cancel_summary` inside cancel side effects
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-structure.sh` verifies `route_write_result_env` precedes `route_emit_cancel_side_effects` in `emit_cancel_route_result`, but there is no intra-function ordering check that `larch_err` / `larch_errf` precedes `render_cancel_summary` within `route_emit_cancel_side_effects`. Swapping those lines would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add an awk-based ordering check (similar to the existing `cancel_write_line`/`cancel_side_effects_line` check) that scans inside `route_emit_cancel_side_effects` for `larch_err` before `render_cancel_summary`.

### FINDING_15: Cancel-path test pins wrapper `route_write_result_env` but not underlying `phase_driver_write_result_env` on that path
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The plan called for a `$DESIGN_ROUTE_SH` pin for `phase_driver_write_result_env` before reject/render on cancel paths. The harness pins `route_write_result_env` (wrapper) for cancel ordering but not the exact underlying writer symbol on the cancel-specific path, slightly weakening contract coverage if the wrapper were replaced with a non-conforming writer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add `grep -Fq 'phase_driver_write_result_env' "$DESIGN_ROUTE_SH"` alongside the existing `route_write_result_env` check, matching the plan's stated pin list.

### OOS_1: [OUT_OF_SCOPE] `LARCH_DESIGN_REENTRY_GUARD_PPID` no longer exported before cancel render
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The old SKILL.md `cancel-reentry-guard` fence set `LARCH_DESIGN_REENTRY_GUARD_PPID="$PPID"` before `render-final-summary.sh`. The new driver's command-scoped render invocation does not forward it, and the plan does not mention preserving it. If `render-final-summary.sh` consumed that variable, reentry-guard cancels would now see an empty value. Marked out-of-scope because the plan lists no requirement to preserve it and current evidence suggests the coupling may be dormant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Verify render-final-summary.sh does not consume LARCH_DESIGN_REENTRY_GUARD_PPID; if it does add it to the command-scoped env prefix in render_cancel_summary.
