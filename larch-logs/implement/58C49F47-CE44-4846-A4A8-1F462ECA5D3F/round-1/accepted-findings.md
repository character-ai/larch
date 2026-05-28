### FINDING_1: emit-design-plan-preview skips allowlist validation before early exits and sentinel writes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/emit-design-plan-preview.sh` validates too late for `step3`/`gatec` early exits. Missing or empty `plan.txt` can exit successfully before allowlist validation, and `step3` can create `.step3-entry-plan-printed` under a disallowed existing directory. The existing sentinel short-circuit can also skip validation on later runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: SECURITY.md overstates tmpdir validation ordering
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` claims all consumers validate before any tmpdir read/write, but `emit-design-plan-preview.sh` can still write the step3 sentinel before validation until the script ordering is fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: revise-plan-with-waterfall doc overstates validation timing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/revise-plan-with-waterfall.md` says validation runs immediately after the required argument check, but the script validates only after directory and other precondition checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


