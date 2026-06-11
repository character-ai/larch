### OOS_3: [OUT_OF_SCOPE] fetched issue content can break trust-boundary envelope
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Fetched issue content can contain delimiter-shaped closing tags like `</external_issue_N>` that are written unescaped inside the trust-boundary envelope. This can visually break out of the intended data region for downstream LLM readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


