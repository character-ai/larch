### [Plan Review] FINDING_14

### FINDING_14: Fallback/waterfall operator docs need the conditional review matrix
- **Reviewer(s)**: Cursor-dyn-operator-doc-sync, Codex-dyn-operator-doc-sync
- **Severity**: important
- **Concern**: Operator-facing docs can still imply skipped slots in degraded modes or universal Phase 2/Phase 3 fallback, contradicting the planned conditional behavior: both-vendor no-fallback peer drops versus single-vendor/both-down Claude waterfall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-operator-doc-sync: Spell out replacement matrix text: both-vendor → up to 8 static (4×2) + dynamic twins; single-vendor → 4 static on available vendor; both-down → 4 Cursor-primary rows with per-slot Claude waterfall (not /design’s combined generic pass); point detail to `dispatch-panel.md`
  - From Codex-dyn-operator-doc-sync: Update these surfaces to the conditional matrix: both vendors available means peer rows plus `--no-fallback` and drop accounting; single-vendor or both-down keeps waterfall to Claude. Link details to `skills/review/scripts/dispatch-panel.md`.


