### DECISION_1: metadata-summary upsert failure handling
- **Chosen**: `DEFERRED=true`, continue (sentinel not written; `post-tracking-issue.sh` already writes the sentinel only after success).
- **Alternative**: Skip to Step 18 (per current `skills/implement/SKILL.md` L622 inline prose "Aborting").
- **Tension**: The issue body explicitly overrides the inline SKILL.md prose. SKILL.md L563-565 (higher-level summary) ALSO says `deferred=true, proceed`, so the contradiction is internal to SKILL.md itself. Cursor flagged this divergence; the issue body resolves it.
- **Impact**: Medium
- **Affected files**: scripts/implement-bootstrap.sh, skills/implement/SKILL.md (L622-623 needs rewrite in the moderate-collapse update).

### DECISION_2: phase_tracking failure on get-issue-state FAILED=true (non-bail-listed)
- **Chosen**: Treat `get-issue-state.sh FAILED=true` (gh transient or permanent failure) as `IMPLEMENT_BAIL_REASON=tracking-init-failed` + `STALL_TRACKING=true`, return 0 (lets emit_final_tail run so the orchestrator can route to Step 18 cleanup with `[STALLED]` rename intact).
- **Alternative**: emit `STEP_FAILED=get-issue-state`, exit 2 (treat as infra failure, same as Phase 1's session-setup failure handling).
- **Tension**: The issue body enumerates three bails (`adopted-issue-closed`, `adopted-issue-is-pr`, `tracking-init-failed`). Mapping a transient gh failure to `tracking-init-failed` reuses an enumerated token but blurs cause; mapping to STEP_FAILED matches Phase 1's infra-class handling but adds a new exit-2 path the issue body did not explicitly authorize.
- **Impact**: Low (well-formed gh failures are uncommon and the symptom — STALL_TRACKING=true + bail to Step 18 — is equivalent under either choice)
- **Affected files**: scripts/implement-bootstrap.sh, scripts/implement-bootstrap.md (bail-table entry).
