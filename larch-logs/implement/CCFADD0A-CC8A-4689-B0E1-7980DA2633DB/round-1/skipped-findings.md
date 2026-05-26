### FINDING_10: correctness: skills/implement/scripts/step2-implement.sh:418-435
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Rename/copy porcelain -z rows record source path only and skip destination token. Implementer renames plan/file.py to plan/file_new.py; recovery emits/commits plan/file.py (often deleted) and omits plan/file_new.py. On R/C rows set rel to the post-NUL destination path in parse(), digest capture, and recovery output; add git mv harness.
- **Suggested revision**: Address the concern above.



