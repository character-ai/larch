### OOS_1:
- **Description**: Legacy env-key strip case overlaps lib harness. Scenario: test-lib-external-launcher-common.sh already exercises strip/retain contracts on copied configs; probe-path case adds ~30+ lines and a new capture env unless trimmed
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/test-check-reviewers.sh:27-401
- **Phase**: design

### OOS_2:
- **Description**: /tmp snapshot helper duplicates STUB_CODEX_HOME_FILE. Scenario: Happy path already records CODEX_HOME via STUB_CODEX_HOME_FILE; before/after ls snapshot adds harness surface for the same invariant
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-codex-implementer.sh:312-353
- **Phase**: design

