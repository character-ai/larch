### FINDING_1: Duplicate state-format validation scans
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `validate_ship_pr_state` and `check_ship_pr_state_format` duplicate malformed-line validation, risking drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Implement validate_ship_pr_state as a thin wrapper around check_ship_pr_state_format plus larch_err/exit 3.

### FINDING_2: Duplicate clear/seed guard and commit plumbing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `cmd_clear_stall` and `cmd_seed_terminal_state` repeat guard, temp-write, `mv`, and reread-assert logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared guard and commit helpers used by both subcommands.

### FINDING_3: [OUT_OF_SCOPE] Unsafe awk rewrite value interpolation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-state-output.txt
- **Severity**: important
- **Concern**: `rewrite_ship_pr_state_keys` embeds update values into awk source; malformed `PHASE`/`STALL_STEP` values can break rewriting or execute unintended awk code on the seed-terminal-state rewrite path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pass key updates via awk -v assignments instead of embedding values in the script string.
  - From cursor-specialist-security-output.txt: Always apply safe_step_value/safe_phase_value to step/phase before rewrite, or pass updates via awk -v with allowlisted tokens only.
  - From cursor-specialist-edge-cases-output.txt: Escape values or use a safer rewriter if arbitrary ship-pr-state values must be rewritten later.
  - From dyn-shell-state-output.txt: Always normalize before rewrite, e.g. `step=$(safe_step_value "$(kv_get …)")` and `phase=$(safe_phase_value "$(kv_get …)")`, then call `rewrite_ship_pr_state_keys` with those sanitized values (same pattern as classify/report subcommands).

### FINDING_4: Unused token-report return variable
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `token_rc` is assigned on token-report failure but never read or emitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove token_rc or emit TOKEN_REPORT_RC for operators.
  - From cursor-specialist-edge-cases-output.txt: Remove token_rc or emit TOKEN_REPORT_RC if orchestrators need visibility.

### FINDING_5: clear-stall symlink rejection lacks harness coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: important
- **Concern**: `clear-stall` symlink rejection is not tested, while `seed-terminal-state` symlink rejection is covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add case22-clear-symlink expecting CLEARED=false and exit 3.
  - From cursor-specialist-testing-output.txt: Add case22-clear-symlink expecting exit 3 and CLEARED=false
  - From dyn-harness-wiring-output.txt: Add a `case22-clear-symlink` block mirroring `case22-seed-symlink` (symlinked `ship-pr-state.sh` → expect `CLEARED=false` and exit 3).

### FINDING_6: seed-terminal-state rewrite test misses preserved keys
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The rewrite-path test does not assert `EXIT_CODE` and `BAIL_REASON` survive rewrite.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Assert EXIT_CODE and BAIL_REASON unchanged after rewrite.

### FINDING_7: [OUT_OF_SCOPE] STEP17_EMITTED_PRESENT parsed but unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-emit-boundary-output.txt
- **Severity**: nit
- **Concern**: `STEP17_EMITTED_PRESENT` is parsed from wrapper stdout but does not affect orchestrator branching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Omit from the fence or document as debug-only.

### FINDING_8: [OUT_OF_SCOPE] Snapshot/cmp I/O failure can force duplicate emit
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Snapshot copy or `cmp` I/O failures can be treated as “body changed,” causing `EMIT_BODY=true` and duplicate summary emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pre-existing; consider failing closed or retaining last-good snapshot (separate change).
  - From cursor-specialist-edge-cases-output.txt: Ensure readable snapshot before cmp; only treat cmp exit 1 as changed, or fail closed to EMIT_BODY=false.

### FINDING_9: [OUT_OF_SCOPE] plugin-root.env-only rehydration untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The Step 18b harness always exports `CLAUDE_PLUGIN_ROOT`, so direct wrapper invocation relying only on `plugin-root.env` is not covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a harness case with only plugin-root.env set.

### FINDING_10: [OUT_OF_SCOPE] Step 18 --print-stdout removal affects operator visibility
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-state-output.txt, dyn-emit-boundary-output.txt, dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Step 18 no longer prints the report body in collapsible Bash stdout; the body appears only through orchestrator top-chat emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document for operators; no fix unless dual-channel output is required.

### FINDING_11: [OUT_OF_SCOPE] Post-mv assert failure can route to stale terminal seeding
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: If `mv` succeeds but the post-`mv` assertion fails, disk may already have `STALL_TRACKING=false` while terminal recovery can re-assert stall state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Dangling ship-pr-state symlink treated as absent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: A dangling `ship-pr-state.sh` symlink follows the absent-file path instead of symlink rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_13: Step 18 structure test omits non-empty summary pin
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Structural tests do not require the `-s "$IMPLEMENT_TMPDIR/summary-final.md"` guard for Step 18 emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend awk or grep to require [ -s "$IMPLEMENT_TMPDIR/summary-final.md" ] in emit prose

### FINDING_14: stall-recovery.md structure pins do not require helper delegation
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Structural tests can pass if Steps 7–8 revert from `stall-recovery-report.sh clear-stall` / `seed-terminal-state` to manual state-file edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Grep -Fq for clear-stall and seed-terminal-state invocations in stall-recovery.md
  - From dyn-harness-wiring-output.txt: Add `grep -Fq 'stall-recovery-report.sh clear-stall'` and `grep -Fq 'stall-recovery-report.sh seed-terminal-state'` (or equivalent literal pins) next to the existing terminal-shape pins in `scripts/test-implement-structure.sh`.

### FINDING_15: seed-fresh harness misses canonical EXIT_CODE/BAIL_REASON
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: nit
- **Concern**: Fresh seed tests do not assert `EXIT_CODE=4` and empty `BAIL_REASON=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert EXIT_CODE=4 and empty BAIL_REASON= on fresh seed output
  - From dyn-harness-wiring-output.txt: Assert `EXIT_CODE=4` via `read-session-env-key.sh` and `grep -q '^BAIL_REASON=$'` (or equivalent) on the seeded file in `case22-seed-fresh`.

### FINDING_16: WFR failure log not asserted
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The write-final-report failure path does not assert `step18-write-final-report.failure.log` exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert failure log exists in case-wfr-fail like token-report case

### FINDING_17: [OUT_OF_SCOPE] Missing summary-final.md success case untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Harness coverage includes empty `summary-final.md` but not a successful renderer that creates no `summary-final.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub mode with no summary-final.md and expect EMIT_BODY=false

### FINDING_18: Non-atomic regular-file check before mv
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ship-pr-state.sh` can be replaced with a symlink between the regular-file check and the subsequent `mv`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Use directory-fd + renameat / O_NOFOLLOW-style writes, or document single-runner + strict tmpdir permissions as the only control.

### FINDING_19: Helpers accept arbitrary implement tmpdirs
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `clear-stall`, `seed-terminal-state`, and `step-18b-final-report` accept any existing directory as `--implement-tmpdir`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reuse canonical_dir + validate_tmpdir_path (or session resolver binding) before touching paths under tmpdir.

### FINDING_20: Orchestrator KV parsing is not strict
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: First-match `awk -F=` parsing of `EMIT_BODY` / `WFR_RC` can be skewed by duplicate or malformed contract lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Parse with anchored patterns (e.g. ^EMIT_BODY=(true|false)$) or a shared strict KV parser.

### FINDING_21: [OUT_OF_SCOPE] plugin-root.env provenance is trusted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Sourcing `plugin-root.env` from tmpdir can redirect helpers to an attacker-controlled plugin tree under the existing trust model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Harden plugin-root.env provenance or refuse source when path is not under the installed plugin root.

### FINDING_22: PLUGIN_ROOT stays stale after sourcing plugin-root.env
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-shell-state-output.txt
- **Severity**: important
- **Concern**: `step-18b-final-report.sh` sources `plugin-root.env` but does not refresh `PLUGIN_ROOT`, so standalone or mis-invoked runs can call helpers from the wrong plugin tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After sourcing plugin-root.env, set PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}" before helper calls (mirror step-7a.sh).
  - From dyn-shell-state-output.txt: After sourcing `plugin-root.env`, set `PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}"` (or drop the redundant source and require callers to export `CLAUDE_PLUGIN_ROOT`, matching other implement helpers).

### FINDING_23: Empty ship-pr-state.sh passes format check
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A zero-byte `ship-pr-state.sh` can pass validation and be rewritten into a state missing canonical keys needed by downstream classify/rename gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Treat empty state as malformed (CLEARED=false exit 3) or require minimum canonical keys before rewrite.

### FINDING_24: mv failure leaves orphan tmp files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Failed `mv` after successful temp write can leave `.tmp` files in `IMPLEMENT_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: rm -f "$tmp" in mv failure handlers before emit_cleared_false_exit / emit_seeded_false_exit.

### FINDING_25: SKILL prose still references old Step 18 dual-condition guard
- **Reviewer(s)**: dyn-emit-boundary-output.txt
- **Severity**: latent
- **Concern**: Step 18 bridge/NEVER prose still describes the old dual-condition guard instead of the authoritative wrapper `EMIT_BODY` / `WFR_RC` / non-empty-summary contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-emit-boundary-output.txt: Rewrite line 1363 to name the machine contract explicitly (parse `EMIT_BODY` / `WFR_RC` from `step-18b-final-report.sh`; emit only when `EMIT_BODY=true`, `WFR_RC=0`, and `summary-final.md` is non-empty), and drop “Step 17 did not print” / snapshot wording in favor of a pointer to Step 18b prose.
  - From dyn-emit-boundary-output.txt: Update the NEVER #20 “How to apply” tail to say Step 18 verbatim emission is allowed only when `EMIT_BODY=true` from `step-18b-final-report.sh` (plus the existing `WFR_RC=0` and non-empty `summary-final.md` checks in Step 18b), and retain the prompt-side `.step17-emitted` write-after-emit rule.

### FINDING_26: Structure test does not require WFR_RC capture
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: `test-implement-structure.sh` pins `EMIT_BODY` parsing and `WFR_RC=0` prose, but not actual `WFR_RC=$(printf …)` capture from wrapper stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Extend the Step 18 awk (or a `grep -Fq`) to require `WFR_RC=$(printf` (and optionally `STEP17_EMITTED_PRESENT=$(printf`) alongside `EMIT_BODY=$(printf`, mirroring the existing `EMIT_BODY` pin.

### FINDING_27: Wrapper no-write sentinel check is not universal
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: The Step 18b harness only checks `.step17-emitted` is not written in one case, not across the full wrapper matrix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: After each `run_wrapper`, assert `[ ! -f "$tmpdir/.step17-emitted" ]` (or centralize that check in `run_wrapper`).

### FINDING_28: [OUT_OF_SCOPE] Quiet-mode KV capture lacks end-to-end wrapper coverage
- **Reviewer(s)**: dyn-emit-boundary-output.txt
- **Severity**: nit
- **Concern**: `test-step-18b-final-report.sh` disables quiet mode, so wrapper FD-3 KV capture is not exercised end-to-end there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-emit-boundary-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] linting docs list stale harness shard
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` documents `test-stall-recovery-report` under shard 5 while Makefile places it on shard 6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Address the concern above.
