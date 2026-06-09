### OOS_18: [OUT_OF_SCOPE] SECURITY.md still references retired read-session-env-key.sh
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: SECURITY.md still points operators/security reviewers at deleted `read-session-env-key.sh` instead of the `python/cli.py session read-key` CLI after the migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_19: [OUT_OF_SCOPE] external-reviewers prose still references session-setup.sh
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `skills/shared/external-reviewers.md` still names `session-setup.sh` even though callers use the `session setup` CLI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_20: [OUT_OF_SCOPE] plugin-root.env is not refreshed when stale
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `plugin-root.env` is only created when missing, so resume can retain a stale plugin root if `LARCH_CLAUDE_PLUGIN_ROOT` changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_21: [OUT_OF_SCOPE] design skill prose still names retired bash scripts
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` prose still references retired bash scripts while fenced examples use session CLI calls, creating operator copy-paste risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_22: [OUT_OF_SCOPE] relevant-checks misses implement-bootstrap for session_env.py changes
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/relevant-checks.sh` does not map `session_env.py` changes to `test-implement-bootstrap`, so local checks may miss bootstrap/resume-tail regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_23: [OUT_OF_SCOPE] Remaining plan-listed session-env pytest parity cases are absent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Several plan-listed pytest replacements remain missing, including entry-gate failure paths, design-tmpdir rejection, CR/LF writer guard coverage, write-id failure, and absent run-id handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


