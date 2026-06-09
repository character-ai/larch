### OOS_1: [OUT_OF_SCOPE] deferred four-lib follow-up issue not filed or wired
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-parity-drift-output.txt, dyn-module-boundary-output.txt
- **Severity**: important
- **Concern**: `docs/python-migration.md` still records the deferred four-lib follow-up as pending, and reviewers note the acceptance/process follow-up issue and blocker DAG wiring are missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-parity-drift-output.txt, dyn-module-boundary-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] planned pytest parity coverage is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-parity-drift-output.txt
- **Severity**: important
- **Concern**: `python/test_session_env.py` lacks multiple plan-named parity replacements for deleted bash harnesses, including setup, local-cleanup, design-env refresh preservation, bootstrap, writer guards, and entry-gate failure capture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-parity-drift-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] SECURITY.md still documents read-session-env-key.sh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-parity-drift-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` still references the retired `read-session-env-key.sh` reader instead of `python/cli.py session read-key`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-parity-drift-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] retired-script lint misses basename variants
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: migration lint matches full retired paths but can miss `$SCRIPTS_DIR/read-session-env-key.sh`-style basename references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] design skill prose still names retired bash scripts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` prose still refers to retired session bash scripts even though runtime fences use the session CLI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### OOS_6: [OUT_OF_SCOPE] fd-3 read-key routing untested without quiet disable
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `run_cli` always sets `LARCH_QUIET_DISABLE=1`, leaving fd-3 routing for `read-key` without that escape hatch untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_7: [OUT_OF_SCOPE] setup copies previous larch logs without validating source root
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `setup` copies `PREV_IMPLEMENT_TMPDIR/larch-logs` without validating that `PREV_IMPLEMENT_TMPDIR` is under an allowed session root; reviewer marked this as bash-parity/out-of-scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


