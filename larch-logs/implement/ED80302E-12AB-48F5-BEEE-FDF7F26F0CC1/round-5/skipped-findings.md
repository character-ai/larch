### FINDING_6: Align SECURITY breadcrumb-source semantics
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` still documents removed directory-level breadcrumb source rejection/fail-closed behavior. The current code treats an out-of-tmpdir source hint as a silent no-op or only rejects at per-file staging, so auditors and maintainers get the wrong security contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.



