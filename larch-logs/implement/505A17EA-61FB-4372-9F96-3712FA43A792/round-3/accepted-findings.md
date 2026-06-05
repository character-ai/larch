### FINDING_12: Missing unreadable `session-env.sh` is converted into explicit false values
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The `/implement` gate reads presence keys with `--default false`, so a missing or unreadable `session-env.sh` can look like four legitimate `false` inputs, suppress `PRESENCE_INPUT_EMPTY`, and trigger a misleading degraded-tools prompt instead of a loud infrastructure error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Implement gate plugin-root rehydration uses a weaker non-canonical fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash32-output.txt
- **Severity**: important
- **Concern**: The `/implement` degraded-tools gate prelude uses an `if`/`elif` plugin-root recovery pattern that can skip the session-env fallback when `plugin-root.env` exists but does not set a usable `CLAUDE_PLUGIN_ROOT`, causing helper invocations to fail or use a bad path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash32-output.txt: Address the concern above.


### FINDING_5: `degraded-tools-gate.sh` header omits conditional `PRESENCE_INPUT_EMPTY`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-kv-streams-output.txt
- **Severity**: latent
- **Concern**: The script header’s stdout contract omits the newly emitted conditional `PRESENCE_INPUT_EMPTY=true` KV, creating drift from the markdown contract and from consumers expected to parse the signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-kv-streams-output.txt: Address the concern above.


### FINDING_9: Design env partial-override test does not assert binary-found key preservation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-write-design-current-env.sh` case 14 does not verify `CODEX_BINARY_FOUND` and `CURSOR_BINARY_FOUND` survive partial override recovery, leaving resume-path gate rehydration regressions untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


