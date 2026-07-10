### OOS_2: Module docstring still states all non-zero codex/cursor launch maps to `main-agent-required`
- **Description**: Module docstring still states all non-zero codex/cursor launch maps to `main-agent-required`. Scenario: Post-change pre-ship recoverable dispatch failures advance inside the waterfall and stall at exhaustion; the stale doc misleads readers of the checks package entrypoint
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/implement/checks.py:1-6
- **Phase**: design

### OOS_9: The checks.py module docstring still claims all non-zero codex/cursor launch outcomes map to main-agent-required. Pre-ship behavior after this piece will stall on delegated exhaustion instead.
- **Description**: The checks.py module docstring still claims all non-zero codex/cursor launch outcomes map to main-agent-required. Pre-ship behavior after this piece will stall on delegated exhaustion instead.. Scenario: The package-level doc misleads readers and contradicts the post-change repair-loop contract.
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/implement/checks.py:3-5
- **Phase**: design

