### OOS_18: Migration cutover/deletion is incomplete
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Python CLI verbs were added, but live runtime callers, docs, structure tests, manifest entries, and zero-live-caller script deletion are not fully cut over, leaving Bash and Python implementations to drift and acceptance criteria unmet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.



