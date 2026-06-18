### [Plan Review] FINDING_3

### FINDING_3: Custom close-equivalent gating diverges from Pylint disable semantics
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Concern**: The proposed close-equivalent gating adds custom per-file attribution semantics that Pylint 4.0.5 does not use. Pylint filters disabled R0801 lines while building `LineSet` via `line_enabled_callback`, then `close` emits one R0801 per computed cluster. If the runner suppresses or attributes clusters later using custom disabled-file rules, enabled-disabled duplicate pairs can diverge from the legacy pylint pass/fail contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Make LineSet construction through `process_tokens`/`process_module` the only per-line disable gate, mirror `close`/`add_message` behavior without extra attribution rules, and make disabled-file fixtures assert parity with the legacy pylint command rather than a new enabled-peer rule


