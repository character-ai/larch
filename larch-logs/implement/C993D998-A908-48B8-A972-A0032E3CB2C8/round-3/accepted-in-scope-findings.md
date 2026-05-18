### FINDING_14: correctness: scripts/hook-anti-read-poll.sh:47-64
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Negative age not handled when now < first_ts Clock skew or corrupt state can satisfy the 30s window test with negative elapsed time and skew streak resets Clamp negative age to treat as window expired or reset when first_ts > now
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: skills/implement/scripts/write-rejected-findings.sh:103-108
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Persist failure path emits REJECTED_COUNT=0 despite prior successful count from non-empty detail_file. Downstream consumers or grep-only transcripts can read REJECTED_COUNT=0 while tmpdir still holds rejected findings; Step 16 uses || true so exit status may be ignored. Emit the computed count on the failure path (or add a separate persist-failure field) and assert it in test-write-rejected-findings.sh.
- **Suggested revision**: Address the concern above.


### FINDING_28: security: scripts/hook-anti-read-poll.sh:60-61
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Hook persists tool_input.file_path into a tab-delimited state line without delimiter escaping. A file_path value containing TAB or newline corrupts TSV parsing and breaks consecutive-read detection. Strip or reject control characters in file_path before writing state, or persist state as JSON with jq.
- **Suggested revision**: Address the concern above.


### FINDING_7: code-quality: scripts/compose-review-findings.md:5-8
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract lists only round-*/rejected-findings.md while the script prefers rejected-findings-full.md when present. Operators or tests following only the markdown contract may omit full.md and see different composed output than production. Document rejected-findings-full.md first, then bare rejected-findings.md (and parent tmpdir fallback) to match compose-review-findings.sh:163-176.
- **Suggested revision**: Address the concern above.


