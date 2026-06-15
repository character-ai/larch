### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step-prelude.sh:24-29
- **Concern**: [SCOPE-REDUCTION] Plan omits the shared generated-wrapper prelude that still binds CODEX_AVAILABLE/CURSOR_AVAILABLE from CODEX_PRESENT/CURSOR_PRESENT defaults. Scenario: ~35 design-step*.sh wrappers duplicate this block and call design_source_env_optional after setting CODEX_AVAILABLE=false; once durable session env drops probe-health keys, sourced env can set CODEX_BINARY_FOUND=true while CODEX_AVAILABLE stays false, so downstream revise-waterfall/panel paths still skip external tiers despite installed binaries
- **Proposed resolution**: Add ### UPDATED: skills/design/scripts/design-step-prelude.sh to remove probe-health defaults, derive routing only from CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND after source, and sync every generated wrapper that duplicates the prelude header (not only the handful named individually)

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step-prelude.sh:24-27
- **Concern**: [SCOPE-REDUCTION] Plan omits the shared generated-wrapper env-default block that still binds CODEX_AVAILABLE/CURSOR_AVAILABLE from CODEX_PRESENT/CURSOR_PRESENT. Scenario: After session_env stops persisting probe-health keys, every design wrapper that sources source-env.sh will default both vendors to false and downstream revise-waterfall/panel argv will skip externals even when CODEX_BINARY_FOUND=true
- **Proposed resolution**: Add ### UPDATED: skills/design/scripts/design-step-prelude.sh (and regenerate all Generated /design wrapper headers) to drop probe-health defaults and derive attempt flags only from CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND; drop per-script one-off edits where prelude regen covers them
