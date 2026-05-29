### FINDING_11: [OUT_OF_SCOPE] discussion-rounds.md omits gate-b-dedup-plan.sh mechanical authority
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `discussion-rounds.md` describes prompt-side trailer guards without naming `gate-b-dedup-plan.sh`, unlike `SKILL.md` / `approval-gates.md`. Operators following discussion-rounds only might skip the mechanical snapshot helper. Align `discussion-rounds.md` with `gate-b-dedup-plan.sh` when touching that file (separate change).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_14: [OUT_OF_SCOPE] check-plan-size --plan-file not constrained to design tmpdir
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--plan-file` is not restricted to the design tmpdir. Orchestrator misconfiguration could point the size check at an arbitrary local file (read-only). Constrain `plan-file` to `DESIGN_TMPDIR/plan.txt` or a resolved path under a validated tmpdir if multi-tenant risk matters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_15: [OUT_OF_SCOPE] LARCH_DEDUP_PLAN_LINES_PY enables hostile dedup script injection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_DEDUP_PLAN_LINES_PY` selects the dedup script path. Hostile env injection could run attacker-chosen Python as the invoking user during dedup. Document trusted-env requirement; ignore in single-user dev plugin context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_7: [OUT_OF_SCOPE] lib-plan-optional-trailers repeated plan reads per helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Each helper re-reads the plan file for `trailer_nr` before awk. Extra I/O on large plans during validation loops. Pre-existing; cache `trailer_nr` within a single validation call if optimizing later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_8: [OUT_OF_SCOPE] plan-review-loop uses three awk passes for advisory fields
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Three awk passes parse `size_out` for advisory fields. Minor inefficiency only; combine into one awk block in a future cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


