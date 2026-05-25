### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step2-implement.sh:474-476
- **Concern**: Recovery only runs after LAUNCHER_EXIT=0. Scenario: Non-zero launcher exit with a malformed manifest on disk bails with codex-runtime-failure/cursor-runtime-failure before schema validation; same lost-work scenario as manifest-schema-invalid without recovery
- **Proposed resolution**: Document as known gap or extend recovery precheck: if MANIFEST_WRITTEN=true and manifest fails schema, consider recovery before runtime-failure bail when tree/guards pass


