### OOS_1: [OUT_OF_SCOPE] correctness: dispatch.lock OSError misreports permission failures as contention
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The `run_dispatch_main` dispatch-lock `except OSError` path reports contention for all `OSError`s, including permission failures when opening `dispatch.lock`. A tmpdir with a non-writable `dispatch.lock` path makes `run_dispatch_main` exit 2 with "another dispatch is already running" even though no concurrent dispatch exists; operators may misdiagnose a permissions problem as lock contention (`python/implement_dispatch.py:1509-1513`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Branch on errno or separate open vs flock failures so only EAGAIN/EWOULDBLOCK emits the concurrent-dispatch message


### OOS_2: [OUT_OF_SCOPE] security: oos.py is_security_tagged misses space-separated Focus area
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/oos.py` `is_security_tagged` still uses a `focus-area`-only `_FOCUS_AREA_FIELD_RE`, while `voting.is_security_block` was updated for space-separated `Focus area`. The `oos serialize` path can misclassify `- **Focus area**: security` blocks as non-security and write them to public output (`python/oos.py:19-21`, `python/oos.py:47-61`). `oos.py` is unchanged on this branch; the plan targets `voting.is_security_block` / `plan_review_tally`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Align `_FOCUS_AREA_FIELD_RE` with `focus[- ]area` (or delegate to `voting.is_security_block`) and add a matching regression test.
  - From cursor-specialist-testing-output.txt: Align `oos.py` with the `voting.py` regex and add a serialize regression test mirroring `test_is_security_block_space_separated_focus_area`.
  - From codex-specialist-testing-output.txt: Update _FOCUS_AREA_FIELD_RE in python/oos.py to match the same space-separated form and add an oos_serialize regression test.


