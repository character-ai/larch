### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Reduced multi-vendor security review when externals absent or down
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Availability-gated panels and the both-absent generic Claude floor reduce independent multi-vendor security review before implement. Codex or Cursor down (or both absent) can let security archetype feedback come from one model family; correlated blind spots or prompt-influenced omissions may reach implement without a second vendor on the same lens. Keep as accepted policy but surface reduced review depth clearly at Step 0 and treat degraded panel / empty collector exits as high-risk for security-sensitive plans unless the operator explicitly continues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Both-absent generic Claude may not use Opus tier per plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan specifies generic Claude (Opus) for both-absent floor; implementation uses `launch-claude-review.sh` without an Opus-specific agent or model flag. If the session default model is not Opus, the both-absent reviewer floor does not match the plan’s stated model tier. Pass explicit Opus agent/model args consistent with other plan-review Claude launches, or update plan/docs to session-default Claude.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: COMBINED_FALLBACK_COUNT degradation dead under --no-fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `COMBINED_FALLBACK_COUNT > floor_half` checks are dead under `--no-fallback`. Design panels always pass `--no-fallback` so `COMBINED_FALLBACK_COUNT` is 0; operators may think fallback volume drives `DEGRADED_*` when only path-count logic matters. Remove or gate fallback-count degradation behind non-no-fallback dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Unreachable CODEX/CURSOR fallback status branches on assessors
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: CODEX/CURSOR fallback status branches in `dispatch-plan-assessors.sh` (~142–143) are unreachable under `--no-fallback`. `*_TOOL` never becomes claude; fallback status labels confuse readers auditing assessor flow. Remove dead branches or restrict to legacy multi-phase paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

