### OOS_1: [OUT_OF_SCOPE] docs risk=low contract contradicts launch-review with_effort=True
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `docs/configuration-and-permissions.md:187` claims Codex omits `--with-effort` when `risk=low`, but `launch-review` always passes `with_effort=True`. Docs-only or test-only diffs classified low risk still run Codex at full configured effort, contrary to the documented `--risk low` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Either implement risk-gated with_effort in launch-review or narrow the documented contract.


