### [rejected] FINDING_10

### FINDING_10: correctness: skills/review-and-fix/scripts/review-and-fix.sh:700-715
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Process-env tier uses non-empty test for LARCH_DYNAMIC_ARCHETYPES_MAX instead of the plan's set-vs-unset guard. An exported empty LARCH_DYNAMIC_ARCHETYPES_MAX skips the env tier and falls through to session-env or default cap 4 in implement mode rather than binding tier-2 then failing validation per the plan snippet. Replace the elif with [[ ${LARCH_DYNAMIC_ARCHETYPES_MAX+x} ]] and assign LARCH_DYNAMIC_ARCHETYPES="$LARCH_DYNAMIC_ARCHETYPES_MAX" before the session_get branch or document and test the chosen empty-export semantics.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_11

### FINDING_11: correctness: skills/review-and-fix/scripts/review-and-fix.sh:704-705
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Empty `LARCH_DYNAMIC_ARCHETYPES_MAX` export is treated as unset vs plan’s `+x` set-detection. Empty export + session-env=3: code uses 3; strict `+x` empty-bind would differ. Confirm intended semantics in spec or align implementation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_12

### FINDING_12: risk-integration: scripts/test-run-step5-review.md:12-14
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Contract doc overstates that forwarding alone makes operator flags override all ambient env. Env-only cap with empty session-env: no argv forwarding; process env still affects `review-and-fix.sh`. Narrow wording to persisted-key + CLI override, or document env-only path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_16

### FINDING_16: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:700-715
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Empty-string LARCH_DYNAMIC_ARCHETYPES_MAX in the process environment is treated as unset (falls through to session-env/defaults). Profile exports LARCH_DYNAMIC_ARCHETYPES_MAX= to clear; session-env still supplies a cap; behavior differs from a literal reading of process-env priority. Document non-empty-only semantics or use set-test if empty should override session-env.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_17

### FINDING_17: security: skills/review-and-fix/scripts/test-review-and-fix.sh:new harness (~CURSOR_API_KEY line)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Literal CURSOR_API_KEY=test-cursor-key in committed test. False positives from gitleaks/trufflehog-style scanners or org secret policies on CI. Use a clearly non-credential dummy value, external fixture, or scanner allowlist comment per repo policy.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

