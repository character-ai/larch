### OOS_1: [OUT_OF_SCOPE] Exact-value exemption tests are incomplete
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The harness only pins `0` versus `1`; it still lacks a deny case for malformed non-`1` values, and the default-deny assertion can false-pass if `LARCH_CLAUDE_SUBPROCESS_HOOK_EXEMPT` is inherited from the shell.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: "Address the concern above."
  - From cursor-specialist-edge-cases: "Address the concern above."
  - From cursor-specialist-testing: "Address the concern above."

### OOS_2: [OUT_OF_SCOPE] Drafter subprocess still bypasses the exemption path
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-hook-boundary
- **Severity**: latent
- **Concern**: `launch_claude_drafter` still spawns `claude --print` via bare `subprocess.run` without the exemption env. It is unlikely to overlap the current bg-wait timeline, but it is the same collateral-denial class if that timing ever changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: "Address the concern above."
  - From cursor-specialist-testing: "Out of scope for this PR; consider routing drafter through `_run_claude_with_stdin` or setting the same child env in a follow-up."
  - From dyn-dyn-hook-boundary: "Address the concern above."

### OOS_3: [OUT_OF_SCOPE] Operator-shell export can bypass the guard
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Exporting `LARCH_CLAUDE_SUBPROCESS_HOOK_EXEMPT=1` in the operator shell bypasses the guard for the top-level orchestrator process too, because the hook exits before marker scans.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: "Address the concern above."

### OOS_4: [OUT_OF_SCOPE] Exact-value contract is not pinned for junk exports
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The plan's exact-`1` contract is still not regression-locked for junk or empty values, so a future truthiness check could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: "Add one harness case with `LARCH_CLAUDE_SUBPROCESS_HOOK_EXEMPT=yes` (or empty export) and assert deny alongside the existing `=0` case."

