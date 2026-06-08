### FINDING_1:
- **Reviewer(s)**: Codex-dyn-quiet-contract-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:60,177; scripts/lib-quiet.md:18-19; scripts/lib-quiet.sh:166-172; python/logging_util.py:98-105
- **Concern**: [SCOPE-REDUCTION] Plan promotes emit_kv CR/LF rejection into a lint/CLI exit-2 mapping, but the existing shell spec only defines the shell helper returning 2 and the current Python API has no error mapper. Scenario: Implementer may add a broad ValueError-to-exit-2 wrapper around migration_lint even though its planned KV values are static counts/status; an internal bug would be reported as a usage/manifest error and the feature gains behavior not required by the fd-3 contract
- **Proposed resolution**: Add emit and emit_kv to logging_util with CR/LF ValueError coverage, but remove the lint maps ValueError to exit 2 edge case and any generic CLI caller mapping unless a concrete subcommand emits user-supplied KV values
