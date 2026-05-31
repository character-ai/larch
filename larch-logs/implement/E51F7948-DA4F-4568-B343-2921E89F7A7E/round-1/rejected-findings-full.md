### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: code-quality: skills/design/scripts/plan-review-loop.sh:206 and skills/review-and-fix/scripts/review-and-fix.sh:130
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Duplicate nit-counting awk on same branch. Convergence rule changes require editing two copies. Extract one shared counter script.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: **Grouped reuse-by-copy removed** (`reuse_slot_result`, ledger, `cp` between slot outputs). That path copied another reviewer’s file without a real `.done` sentinel (availability/DoS) and let one physical result stand in for a different slot (integrity). Deletion is a clear win; no replacement copies results between slots.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Grouped reuse-by-copy removed** (`reuse_slot_result`, ledger, `cp` between slot outputs). That path copied another reviewer’s file without a real `.done` sentinel (availability/DoS) and let one physical result stand in for a different slot (integrity). Deletion is a clear win; no replacement copies results between slots.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: **`--no-fallback` + paths-file filtering** — Only successful slot paths are written. Downstream collection no longer blocks on phantom outputs. This closes a resource-exhaustion class (31-minute sentinel waits), not an auth bypass.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **`--no-fallback` + paths-file filtering** — Only successful slot paths are written. Downstream collection no longer blocks on phantom outputs. This closes a resource-exhaustion class (31-minute sentinel waits), not an auth bypass.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: **Manifest construction** — Plan-review, decompose, voter, and assessor slots use `jq -nc --arg …` for NDJSON rows (safe embedding). Voter manifest still uses `printf` JSON for paths (pre-existing pattern; paths are under `$DESIGN_TMPDIR`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **Manifest construction** — Plan-review, decompose, voter, and assessor slots use `jq -nc --arg …` for NDJSON rows (safe embedding). Voter manifest still uses `printf` JSON for paths (pre-existing pattern; paths are under `$DESIGN_TMPDIR`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: **Both-absent generic Claude paths** — Prompts are built from repo templates / `render-plan-review-prompt.sh` and validated plan paths; launches go through existing `launch-claude-review.sh` with fixed output locations under `$DESIGN_TMPDIR`. Dynamic archetype slugs remain constrained upstream by scout validation (`^[a-z][a-z0-9-]{2,40}$` in `scout-dynamic-archetypes.sh`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **Both-absent generic Claude paths** — Prompts are built from repo templates / `render-plan-review-prompt.sh` and validated plan paths; launches go through existing `launch-claude-review.sh` with fixed output locations under `$DESIGN_TMPDIR`. Dynamic archetype slugs remain constrained upstream by scout validation (`^[a-z][a-z0-9-]{2,40}$` in `scout-dynamic-archetypes.sh`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: **`degraded-tools-gate.sh` env fallback** — Defaults now honor `CODEX_*` / `CURSOR_*` env vars before argv overwrites. This fixes misclassification when skills export probe results (documented contract). Impact is degraded **warnings**, not permission boundaries; dispatch availability still comes from the same Step 0 flags passed to dispatchers. No new shell interpolation of untrusted input.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 5. **`degraded-tools-gate.sh` env fallback** — Defaults now honor `CODEX_*` / `CURSOR_*` env vars before argv overwrites. This fixes misclassification when skills export probe results (documented contract). Impact is degraded **warnings**, not permission boundaries; dispatch availability still comes from the same Step 0 flags passed to dispatchers. No new shell interpolation of untrusted input.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_24: **No new secrets, network calls, or auth changes** in the implementation diff.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 6. **No new secrets, network calls, or auth changes** in the implementation diff. `/review` multi-phase waterfall (ungrouped phase-2/3) is unchanged except reuse removal; ReDoS/`grep -E` on caller patterns and `eval` in `collect_phase` are pre-existing. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_31: risk-integration: skills/design/scripts/dispatch-plan-review-panel.sh:90-124
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Generic Claude floor bypasses waterfall; hung launch can still block collect for COLLECT_TIMEOUT Long hang on launch-claude-review.sh still costs full collect timeout on floor path Document or add shorter timeout for generic floor launch
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: skills/design/scripts/dispatch-plan-review-panel.sh:238-245
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] COMBINED_FALLBACK_COUNT degradation logic is dead under --no-fallback. DEGRADED_ROUND never triggers from fallback cost even when panel is degraded. Remove fallback threshold or tie degradation to dispatch/collect outcomes only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: code-quality: scripts/dispatch-plan-voters.sh:192-193
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Claude fallback status labeling for voters cannot occur with --no-fallback. Misleading status values if code paths change later. Remove or guard fallback relabeling.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: code-quality: skills/design/scripts/dispatch-plan-assessors.sh:155-156
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Same stale claude fallback labeling for assessor externals under --no-fallback. Same as voter script. Remove or guard fallback relabeling.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: code-quality: skills/design/scripts/dispatch-plan-review-panel.sh:90-123
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Duplicated generic-Claude floor vs decompose-panel-dispatch.sh. Future fixes to .done shim or KV contract need two edits. Consider shared helper only if a third caller appears.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

