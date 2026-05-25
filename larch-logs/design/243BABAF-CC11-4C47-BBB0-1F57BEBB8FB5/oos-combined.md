### Phase 3/4 stubs in implement-bootstrap.sh overwrite IMPLEMENT_BAIL_REASON after phase_tracking
- **Description**: phase_plan_materialize and phase_coder_select stubs still overwrite IMPLEMENT_BAIL_REASON after phase_tracking when UP_TO_PHASE is plan, coder, or all. Scenario: Operators testing combined phases see not-yet-implemented-phase-3 tail unrelated to tracking work. Surfaced during /design review of issue #2736 (Phase 2 of umbrella #2732).
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/implement-bootstrap.sh:286-294
- **Phase**: design

### tracking-issue-read.sh --sentinel header omits RUN_ID even though implementation emits it
- **Description**: Top header of scripts/tracking-issue-read.sh says --sentinel emits ISSUE_NUMBER and ADOPTED only. Scenario: Auditors or future docs may wrongly assume RUN_ID absent from stdout despite emit_kv RUN_ID and tests covering it. Update the file header contract to list RUN_ID alongside ISSUE_NUMBER and ADOPTED.
- **Reviewer**: Cursor-dyn-sentinel-read-contract
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/tracking-issue-read.sh:21-22 vs scripts/tracking-issue-read.sh:268-278
- **Phase**: design

### Fork upstream get-issue-context failures suppressed by || true lose observability
- **Description**: SKILL.md Step 0 fork-mode best-effort context fetch redirects stderr to upstream-context.log and ignores failures via || true. Scenario: Operators lose explicit fail-closed signal on upstream context fetch flakes; any secret-bearing stderr lands in a log file rather than surfacing through the standard execution-issues channel. Add an explicit Warning entry to execution-issues.md when the fetch returns non-zero.
- **Reviewer**: Cursor-dyn-kv-emit-table-sync
- **Severity**: latent
- **Focus area**: security
- **Location**: skills/implement/SKILL.md:646-658
- **Phase**: design
