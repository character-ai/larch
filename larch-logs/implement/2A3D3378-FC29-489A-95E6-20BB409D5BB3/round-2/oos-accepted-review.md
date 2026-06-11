### OOS_2: [OUT_OF_SCOPE] Redaction parity fixtures reference deleted scripts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Bash parity fixtures in `python/test_redact.py` still reference deleted redaction scripts. Tests may skip when helpers are absent, reducing regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


