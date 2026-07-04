### OOS_1: [OUT_OF_SCOPE] duplicate `LARCH_PANEL_PAYLOAD_BYTES` parsing in launchers
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: Separate launcher-side parsers for `LARCH_PANEL_PAYLOAD_BYTES` can drift and compute different payload telemetry unless the parsing logic is shared.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Import tokens._panel_payload_bytes at launcher boundaries.
  - From cursor-specialist-testing: Extract shared helper in larch.report.tokens or larch.agents shared module

### OOS_2: [OUT_OF_SCOPE] raw file bytes overstate scaffold parity
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Using raw file bytes for the scope anchor and feature payload can overstate scaffold bytes relative to the wrapped prompt, especially around untrusted blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Count emitted wrapper block bytes if exact parity is needed.

### OOS_3: [OUT_OF_SCOPE] competition notice bytes are not counted
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Competition-notice file bytes are not counted into specialist payload helpers, so review rounds with notices can still understate payload and inflate scaffold rankings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Count competition notice file bytes as payload when --competition-notice is set if future density work needs it

### OOS_4: [OUT_OF_SCOPE] `realized_bytes` double-counts prompt and agent bytes
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `realized_bytes` currently sums `prompt_bytes` and `agent_bytes`, which can double-count embedded agent markdown and skew realized ranking totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address separately if realized ranking accuracy becomes a goal

