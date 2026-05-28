### FINDING_11: Copy-plan failure can prevent emergency bypass audit persistence
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `copy-plan` runs before emergency bypass log append, so under `--emergency` a copy-plan failure exits before `append_emergency_bypass_log_if_present`, leaving `execution-issues.md` without the bypass entry despite a Preflight warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: post-tracking-issue invalid emergency flag is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `post-tracking-issue` lacks a harness case for invalid `--emergency-requested` values, so bad argv could be silently accepted or produce wrong metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: render-run-summary invalid emergency flag is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `render-run-summary` lacks a harness case for invalid `--emergency-requested` values, so invalid flags may reach summary rendering without exercising the guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: SECURITY.md overstates invalid bypass log fail-closed behavior
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` says invalid `emergency-bypass.log` lines fail closed at bootstrap, but `implement-bootstrap` warns, redacts, and continues, which can mislead operators about whether malformed bypass logs halt the run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_20: Resume-plan-tail does not refresh emergency metadata
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `--resume-plan-tail` does not refresh `larch:metadata` after emergency state changes, so dirty-tree recovery can set `EMERGENCY_REQUESTED=true` in run flags while the metadata comment remains stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_22: Structure test pins stale Preflight item 6 heading
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-implement-structure.sh` still greps the old AUDIT=pass-only Preflight item 6 heading, while `SKILL.md` uses the new emergency-bypassed AUDIT=refuse variant, so `make lint` fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Audit-refuse emergency bypass grammar is not pinned in Preflight item 5
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Preflight item 5 says to append a structured bypass entry but does not repeat the exact `BYPASS kind=audit-refuse issue=<N>` grammar, so an orchestrator may write non-canonical text and bootstrap will record an invalid-format warning instead of a structured audit-refuse bypass trail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_9: Non-emergency missing-plan refusal is not grep-pinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-plan-adequacy-audit.sh` does not pin the non-emergency `BLOCK_PRESENT=false` exit-2 refusal message or `emergency_requested=false` branch, so `/implement` without `--emergency` could stop enforcing “run /design first” while emergency checks still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


