### FINDING_13: [OUT_OF_SCOPE] `--repo` token validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `--repo` is not validated like other PR-list tokens; malformed values rely on `gh` handling—pre-existing surface.
- **Suggested revision**: Harden only if tightening the `gh` invocation contract is desired.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_14: [OUT_OF_SCOPE] `manifest_field` hides JSON parse failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Helper can surface corrupt `manifest.json` as empty fields, silently skipping `pr_number`/status-driven gates.
- **Suggested revision**: Harden separately if desired.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_15: [OUT_OF_SCOPE] SKILL summary vs v2 cross-cutting wording
- **Reviewer(s)**: dyn-schema-v2-consumer-coverage-output.txt
- **Concern**: Skill-level summary still describes cross-cutting as flagging empty `ended_at`/`pr_number` without v2 `has(...)` nuance, easier to misread with default omit-key v2 manifests.
- **Suggested revision**: Align the bullet with v1/v2 distinction after script-level docs are corrected.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_16: [OUT_OF_SCOPE] Historical dyn-* prompts in committed run logs
- **Reviewer(s)**: dyn-schema-v2-consumer-coverage-output.txt
- **Concern**: Frozen captured prompts still teach “grep manifest for pr_number first” while live tooling order has moved.
- **Suggested revision**: Treat as frozen run-log content unless explicitly refreshed; update only if maintained as living templates elsewhere.
```

Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] Ordering invariant: final-summary vs Step 9a.1 artifacts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Step 9a.1 gating that treats `final-summary.md` as a reach signal assumes implement ordering not shown in this diff; future paths could reorder writes vs artifacts.
- **Suggested revision**: Confirm ordering invariant in implement skill docs or add an ordering-sensitive test outside this diff review.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

