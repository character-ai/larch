### OOS_3: DIGEST_CHARS still ignores non-section digest fields
- **Description**: DIGEST_CHARS still ignores non-section digest fields. Scenario: Even after adding `origin`, token sizing will still omit `title`, `number`, and other fields the synthesis reads, understating `DIGEST_TOKENS_EST`.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/issue/learn_from_bugs.py
- **Phase**: design

