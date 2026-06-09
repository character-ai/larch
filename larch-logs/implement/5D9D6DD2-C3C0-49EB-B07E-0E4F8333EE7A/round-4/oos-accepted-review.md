### OOS_24: [OUT_OF_SCOPE] SECURITY.md references retired session-env reader
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: SECURITY.md still references the retired read-session-env-key.sh after the Python cutover, which can mislead operators auditing session-env trust boundaries away from the real read-key CLI surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### OOS_25: [OUT_OF_SCOPE] Sanitize cleanup audit log dir input
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: cleanup-tmpdir audit logging does not sanitize newlines in --dir before append. Newline-bearing paths could forge audit log lines if ever accepted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


