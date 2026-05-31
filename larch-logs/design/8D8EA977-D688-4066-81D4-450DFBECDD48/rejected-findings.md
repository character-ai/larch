### [Plan Review] FINDING_3

### FINDING_3: Agents waterfall drops rotated first-tier / first-fixer-non-health contract
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: latent
- **Concern**: The plan pins a fixed `cursor,codex,claude` order and tests against that order, but ship-pr’s CI-fix path rotates the starting tier via `start_attempt % 3` and applies `first-fixer-non-health` relative to the rotated first tier. A fixed first tier can let repeated outer attempts keep short-circuiting on the same Cursor non-health failure without giving Codex or Claude the first-fixer slot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Add a start_attempt/offset input to the agents waterfall, rotate the base tier tuple per invocation, and test that first-fixer-non-health applies to the rotated first tier.


### [Plan Review] FINDING_6

### FINDING_6: Outbound redaction not wired into `gh` bodies and logging
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The feature requires outbound `gh` bodies and logs to pass through `python/redact.py`, but the plan only creates `redact.py` and leaves `gh` issue edit/comment plus JSONL/breadcrumb text silent on redaction—allowing future issue comments or journals to leak secrets or operator paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Add an explicit contract that free-text gh body/comment fields and logging_util message/detail fields are passed through redact.redact before subprocess or journal output, with focused tests covering a token and tmpdir path.


### [Plan Review] FINDING_7

### FINDING_7: Python redactor lacks stateful streaming PEM parity with shell
- **Reviewer(s)**: Cursor-dyn-redaction-parity, Codex-dyn-redaction-parity
- **Severity**: important
- **Concern**: The proposed Python redactor only specifies `redact(text: str)`, but the current contract includes stateful streaming PEM redaction used by operator diagnostics and breadcrumb publication. A PEM private key split across logging calls can lose persisted `in_pem` state; future Python `logging_util` output could surface key body lines that the shell path currently swallows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-redaction-parity, Codex-dyn-redaction-parity: Add a minimal stateful streaming primitive and parity tests for complete/split/fresh-END PEM cases, or narrow the plan so this phase does not claim to replace the streaming side and logging_util cannot publish unredacted user-visible text.


