## Decision 1: Fix 5 hook-clean-emission breadth
- **Question**: Should the "exactly one trailing newline" fix be targeted to the two named offenders' writer helpers, or a broad sweep of larch run-log text emitters?
- **Resolution**: Broad class-elimination — normalize at the write boundary so all larch run-log text emitters emit exactly one trailing newline, eliminating the whole hook-fixer class (not just round-1/oos.md and round-1/review-round-summary.md). Still keep the Fix 5 byte-compare normalization audit in ship.py.
- **Source**: user

## Decision 2: Scope = all five operator-approved fixes in one design
- **Question**: What is in-scope for this design?
- **Resolution**: Fix 1 (hook-tolerant `_commit_run` retry-once), Fix 2 (de-terminalize ship state at drive re-entry), Fix 3 (distinct refresh-skip reason for the pre-terminal refusal + mirror at all membership/branching sites), Fix 4 (actionable remedy in the surfaced detail when the retry also fails), Fix 5 (broad hook-clean emission + byte-compare audit). Parts A (Fix 1) and B (Fix 2) are both required; 3/4/5 are coupled to them.
- **Source**: issue (operator-approved "Required fix" direction)

## Decision 3: Out of scope (explicit non-goals — must NOT be touched)
- **Question**: What related changes does the user NOT want?
- **Resolution**: (a) Step 2 dispatcher implementation-commit retry (`dispatch_commit_route.py`, `implementation-commit-failed`) — file separately. (b) Preflight detect-and-warn for client hook configs — Fix 4 replaces it. (c) Any change to pre-terminal guard semantics or labels (`_check_preterminal_commit_blocked`, `_preterminal_outcome_commit_blocked`, `config.PRETERMINAL_FORBIDDEN_OUTCOME_LABELS`) — no bypass flag.
- **Source**: issue (Out of scope)

## Decision 4: Hard constraints (must not break)
- **Question**: What behavior must remain?
- **Resolution**:
  - Do NOT use `git commit --no-verify` — larch is a guest in the client repo; adopt the client's hook fixes.
  - Fix 1 lands once in `_commit_run` (single live choke point); leave the test-only `_larch_log_commit` unchanged (verified: only re-exported via run_logs.py:144, no live production callers).
  - Fix 2 reset lives in the Python driver only; prompt-side orchestrator code must never write `finalize-state.sh` or session env (AGENTS.md).
  - The two ship-driver flush callsites (`_flush_guideline_outcome_before_pr`, `_flush_invariant_outcome_before_pr`) keep failing closed — they must keep stalling on the new refresh-skip reason. Only `no-logs-commit`, `run-log-incomplete`, and matching `volatile-only` warn-and-continue.
  - Fix 3 must be behavior-preserving: mirror the new reason at every `REFRESH_SKIP_COMMIT_FAILED` membership/branching site (`config.REFRESH_SKIP_MERGE_OK`, `run_log_flush.py:1180`, `step_7a.py:155` `_refresh_skip_blocks_direct_commit`, and check `state/_classify.py`).
  - Sequencing dependency #6788 already landed on main (`a85d84476`); this run is unblocked.
- **Source**: issue + codebase verification
