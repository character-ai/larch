### FINDING_13: [OUT_OF_SCOPE] legacy single-pass mode is not documented as direct-script-only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `SKILL.md` always passes `--round-cap`, making legacy single-pass behavior harness/direct-script-only, but operators may infer it is available through normal SKILL invocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_14: [OUT_OF_SCOPE] revise.env allowlist entry appears unused
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `revise.env` is allowlisted although `revise-plan-with-waterfall.sh` does not create it, creating stale or misleading artifact policy surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

