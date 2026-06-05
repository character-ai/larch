### FINDING_1: Archival reject message misstates bracket pattern
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The archival title-filter reject banner at `skills/design/scripts/design-route.sh:264` says `` `[...] Report` ``, implying "Report" comes after the closing bracket, but `LARCH_TITLE_ARCHIVAL_REPORT_REGEX_BASH='^\[.*[Rr]eport\] '` in `lib-title-eligibility.sh` requires "Report" inside the brackets (e.g., `[Research Report] Foo`). The older SKILL.md wording `` `[... Report]` `` matched the regex; the new message can mislead operators renaming titles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Change the message back to `` `[... Report]` `` (closing bracket after Report, matching the regex pattern).


### FINDING_10: No runtime smoke test for KV-stream isolation on cancel paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `render-final-summary.sh --post-publish-only` emits summary body on stdout while driver stdout is the KV stream. Structural pins assert `>/dev/null` presence, but no CI-runnable test invokes `design-route.sh` on a cancel-eligible title and asserts stdout contains only KV lines. If summary output escapes the redirect, SKILL.md KV parsing silently ingests garbage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add at minimum a minimal cancel fixture in `test-design-structure.sh` or a companion smoke script: mock `render-final-summary.sh` to emit a sentinel line, call `design-route.sh` with a `[IMPLEMENTING]`-prefixed title, assert stdout has no non-`KEY=VALUE` lines.


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


