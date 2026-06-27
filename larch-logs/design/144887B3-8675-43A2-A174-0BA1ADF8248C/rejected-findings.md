### [Plan Review] FINDING_2

### FINDING_2: Pin immediate abort when `_prepare_step2b_drafter_run` fails
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Orchestration must abort before steps 2-10 when step 1 prepare fails. Production returns immediately at parse rc 2, missing tmpdir rc 1, invalid tmpdir rc 2, folded Step 2a rc 1, and plugin-root failure before pause seeding, artifact reset, or launch (3644-3664). The plan pins handler `return` propagation at step 10 but not this immediate exit; a thin main that always continues can seed `.step2b-postplan-fallback-used`, unlink artifacts, or launch after a failed prepare, breaking `test_step2a_rejects_missing_design_tmpdir`, `test_step2a_rejects_relative_design_tmpdir`, conflicting-sentinel refusal, and pause-before-seed tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add orchestration rule: if prepare returns a non-success int, `step2b_drafter_main` must return that code immediately and must not run steps 2-10; pin the existing rc mapping for parse, tmpdir, Step 2a, and plugin-root failures.
  - From Cursor-Innovation: Add an orchestration contract: `prep = _prepare_step2b_drafter_run(argv); if isinstance(prep, int): return prep` (or equivalent explicit early-int union). Enumerate preserved rc values per gate in the prepare helper spec.
  - From Cursor-Pragmatic: Add an explicit orchestration contract: `_prepare_step2b_drafter_run` returns either an `int` exit code or a prepared tuple, and `step2b_drafter_main` must `return` that `int` immediately before step 2. Pin the rc mapping to production lines 3648-3664 (including rc 1 vs 2 distinctions and no `DRAFTER_NEXT_ACTION` on prepare failures).


