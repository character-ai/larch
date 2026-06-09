### OOS_8: [OUT_OF_SCOPE] implement NEVER #11 still names restore-finalize-state.sh
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/SKILL.md` has prose drift where NEVER #11 names the retired `restore-finalize-state.sh` while the actual flow uses the session CLI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_9: [OUT_OF_SCOPE] linting docs reference retired harnesses/scripts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` still describes removed harness targets and retired bash script names, misleading contributors about the post-migration test surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_10: [OUT_OF_SCOPE] plugin-root-only invalid value exits successfully
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Invalid `--plugin-root-only` values can exit 0 without writing the expected bootstrap env, so resume-tail callers may silently lack `plugin-root.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_11: [OUT_OF_SCOPE] pytest helper masks quiet fd-3 routing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The pytest helper forces `LARCH_QUIET_DISABLE=1` for all session CLI invocations, so fd-3/stdout quiet-mode routing regressions may not be detected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_12: [OUT_OF_SCOPE] design skill prose still names retired bash scripts
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` prose still refers to retired bash scripts even though command fences use Python session verbs, creating operator confusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_13: [OUT_OF_SCOPE] empty .PHONY line remains after harness removal
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The `Makefile` contains a stray empty `.PHONY` target after harness removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_14: [OUT_OF_SCOPE] repo-unavailable is persisted without boolean validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `REPO_UNAVAILABLE` can be written with invalid boolean-like values, which may confuse downstream boolean gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### OOS_15: [OUT_OF_SCOPE] REPO and previous tmpdir hardening gaps
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Existing parity gaps leave `REPO` format validation and previous tmpdir copy hardening weaker than desired; malformed repo values or symlinked previous tmpdir paths could affect quoting/copy semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### OOS_16: [OUT_OF_SCOPE] SECURITY.md references retired read-session-env-key.sh
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` still points operators at the retired `read-session-env-key.sh` instead of the Python session read-key surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_17: [OUT_OF_SCOPE] final-bail-reason lacks newline guard
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `final-bail-reason.txt` can be written from a multiline bail reason, which could confuse downstream parsers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


