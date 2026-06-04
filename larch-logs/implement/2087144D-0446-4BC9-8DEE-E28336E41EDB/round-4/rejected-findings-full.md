### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: LARCH_EXPECTED_STABLE_VERSION override lacks test/trust-boundary hardening
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The expected-stable override can bypass GitHub stable-release verification and its release-only coupling is not covered by harnesses or clearly bounded for non-release callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Manual /upgrade-larch can still use stale cached script during release window
- **Reviewer(s)**: dyn-sparse-cone-output.txt
- **Severity**: important
- **Concern**: `/release` runs the working-tree upgrade script, but the operator-facing `/upgrade-larch` skill still uses `${CLAUDE_PLUGIN_ROOT}`, so pre-restart manual upgrades can execute stale cached sparse-dir logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-cone-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

