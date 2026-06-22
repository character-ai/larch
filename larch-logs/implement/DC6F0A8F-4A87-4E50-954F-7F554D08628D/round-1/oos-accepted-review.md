### OOS_1: [OUT_OF_SCOPE] Missing test for nested ledger resolution via `session_env_path` alone
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Tests cover nested resolution via `IMPLEMENT_TMPDIR` env but not via `session_env_path` alone (the fallback path `review_tally._nested_implement_round` also supports).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add a test with unset `IMPLEMENT_TMPDIR` and `session_env_path=<parent>/session-env.sh` to lock the resolver contract.


### OOS_2: [OUT_OF_SCOPE] Corrupt ledger header silent history wipe (pre-existing hardening)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-dyn-ledger-roundtrip-output.txt
- **Severity**: latent
- **Concern**: If an on-disk ledger header diverges from `LEDGER_COLUMNS`, `_read_existing_rows` returns `[]` and `write_round` rewrites the file with only the current round, silently dropping prior rounds. That predates this feature's semantics but is worth hardening separately (warn/fail closed instead of discarding history).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-roundtrip-output.txt: That predates this feature's semantics but is worth hardening separately (warn/fail closed instead of discarding history).


