### OOS_1:
- **Description**: Item 6 text mentions validation Codex lanes but the plan only adds ingestion prose to research-phase.md. Scenario: Validation still collects Codex outputs via `collect-agent-results.sh` with no matching append-record / record-vendor-sidecar instructions; validation Codex usage can remain absent from NDJSON and the active ledger
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/research/references/validation-phase.md:180-190
- **Phase**: design

### OOS_2:
- **Description**: Plan reimplements sidecar ingestion in `python/checks.py` instead of extending the existing helper. Scenario: `ingest_launcher_token_sidecar` still omits stale-env clearing and failure warnings, so CI/rebase ingestion paths keep diverging from the new lint-fix contract
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/agents.py:2817-2855
- **Phase**: design

