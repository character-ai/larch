### OOS_1: [OUT_OF_SCOPE] Unused `snapshot_optional_trailer_values` expands untested API surface
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `snapshot_optional_trailer_values()` is unused dead code on a new shared library—not a regression risk from current callers, but expands untested API surface and suggests incomplete value-validation design.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_2: [OUT_OF_SCOPE] `LARCH_DEDUP_PLAN_LINES_PY` env override — arbitrary script execution
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_DEDUP_PLAN_LINES_PY` in `plan-review-loop.sh` can point `python3` at an attacker-chosen script; malicious env in the design process could achieve code execution during dedup (pre-existing).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] `check-plan-size` exit 2 skips threshold enforcement
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `check-plan-size` exit 2 proceeds without threshold enforcement when `diff_lines` is missing/malformed; documented operational risk vs fail-closed (pre-existing, `SKILL.md` ~883).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

