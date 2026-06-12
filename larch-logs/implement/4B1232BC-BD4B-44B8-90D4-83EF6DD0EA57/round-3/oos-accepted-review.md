### OOS_3: [OUT_OF_SCOPE] Docs still cite retired `run-external-agent.sh`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `docs/configuration-and-permissions.md` still cites `run-external-agent.sh` as the live launcher. Operators may follow retired script paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] Secret leak check covers only a few token patterns
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The context leak check covers only `sk-`, `ghp_`, and `crsr_` patterns. Other secret shapes may pass the post-redaction leak guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


