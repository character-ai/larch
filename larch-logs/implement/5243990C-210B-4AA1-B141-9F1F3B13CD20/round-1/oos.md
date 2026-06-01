### FINDING_10: [OUT_OF_SCOPE] Step 18 --print-stdout removal affects operator visibility
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-state-output.txt, dyn-emit-boundary-output.txt, dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Step 18 no longer prints the report body in collapsible Bash stdout; the body appears only through orchestrator top-chat emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document for operators; no fix unless dual-channel output is required.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_11: [OUT_OF_SCOPE] Post-mv assert failure can route to stale terminal seeding
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: If `mv` succeeds but the post-`mv` assertion fails, disk may already have `STALL_TRACKING=false` while terminal recovery can re-assert stall state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_12: [OUT_OF_SCOPE] Dangling ship-pr-state symlink treated as absent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: A dangling `ship-pr-state.sh` symlink follows the absent-file path instead of symlink rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] Missing summary-final.md success case untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Harness coverage includes empty `summary-final.md` but not a successful renderer that creates no `summary-final.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub mode with no summary-final.md and expect EMIT_BODY=false


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] plugin-root.env provenance is trusted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Sourcing `plugin-root.env` from tmpdir can redirect helpers to an attacker-controlled plugin tree under the existing trust model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Harden plugin-root.env provenance or refuse source when path is not under the installed plugin root.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_28: [OUT_OF_SCOPE] Quiet-mode KV capture lacks end-to-end wrapper coverage
- **Reviewer(s)**: dyn-emit-boundary-output.txt
- **Severity**: nit
- **Concern**: `test-step-18b-final-report.sh` disables quiet mode, so wrapper FD-3 KV capture is not exercised end-to-end there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-emit-boundary-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_29: [OUT_OF_SCOPE] linting docs list stale harness shard
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` documents `test-stall-recovery-report` under shard 5 while Makefile places it on shard 6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_3: [OUT_OF_SCOPE] Unsafe awk rewrite value interpolation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-state-output.txt
- **Severity**: important
- **Concern**: `rewrite_ship_pr_state_keys` embeds update values into awk source; malformed `PHASE`/`STALL_STEP` values can break rewriting or execute unintended awk code on the seed-terminal-state rewrite path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pass key updates via awk -v assignments instead of embedding values in the script string.
  - From cursor-specialist-security-output.txt: Always apply safe_step_value/safe_phase_value to step/phase before rewrite, or pass updates via awk -v with allowlisted tokens only.
  - From cursor-specialist-edge-cases-output.txt: Escape values or use a safer rewriter if arbitrary ship-pr-state values must be rewritten later.
  - From dyn-shell-state-output.txt: Always normalize before rewrite, e.g. `step=$(safe_step_value "$(kv_get …)")` and `phase=$(safe_phase_value "$(kv_get …)")`, then call `rewrite_ship_pr_state_keys` with those sanitized values (same pattern as classify/report subcommands).


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] STEP17_EMITTED_PRESENT parsed but unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-emit-boundary-output.txt
- **Severity**: nit
- **Concern**: `STEP17_EMITTED_PRESENT` is parsed from wrapper stdout but does not affect orchestrator branching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Omit from the fence or document as debug-only.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] Snapshot/cmp I/O failure can force duplicate emit
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Snapshot copy or `cmp` I/O failures can be treated as “body changed,” causing `EMIT_BODY=true` and duplicate summary emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pre-existing; consider failing closed or retaining last-good snapshot (separate change).
  - From cursor-specialist-edge-cases-output.txt: Ensure readable snapshot before cmp; only treat cmp exit 1 as changed, or fail closed to EMIT_BODY=false.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] plugin-root.env-only rehydration untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The Step 18b harness always exports `CLAUDE_PLUGIN_ROOT`, so direct wrapper invocation relying only on `plugin-root.env` is not covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a harness case with only plugin-root.env set.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

