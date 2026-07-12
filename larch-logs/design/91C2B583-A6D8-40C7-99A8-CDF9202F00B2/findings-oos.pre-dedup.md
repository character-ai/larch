### OOS_1: Defer Codex CODEX_HOME configuration context to a later partition piece
- **Description**: Defer Codex CODEX_HOME configuration context to a later partition piece. Scenario: Piece 1 scope names Cursor config isolation only; Codex launchers already wrap _prepare_codex_home and _temporary_env in _ci_launcher.py and _review_launcher.py and do not need a third copy in inactive foundation yet
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/agents/_run_external.py:865-910
- **Phase**: design



