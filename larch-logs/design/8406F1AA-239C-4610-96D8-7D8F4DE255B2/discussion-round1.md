## Decision 1: repair-loop internalizes lint-fix + re-check loop
- **Question**: Does the verb re-run checks internally after lint-fix applied, so NEXT_ACTION=continue means checks passed?
- **Resolution**: Yes. The verb wraps the dispatch-first run_check_fix_loop path (lint-fix first, then checks, loop until clean or exhausted). NEXT_ACTION=continue is only emitted after checks are verified passing.
- **Source**: codebase (run_check_fix_loop with dispatch_first=True already implements this loop)

## Decision 2: STDERR_TAIL_PATH and CODER_LOG_FILE emitted for main-agent-edit
- **Question**: Should repair-loop emit auxiliary KVs alongside NEXT_ACTION=main-agent-edit?
- **Resolution**: Yes. The current SKILL.md prose at Steps 3 and 6 reads STDERR_TAIL_PATH / CODER_LOG_FILE for operator-visible tails on main-agent-required. The collapsed SKILL.md for main-agent-edit still needs these. Steps 5 sites reference Step 3's behavior, so all sites need them.
- **Source**: codebase (SKILL.md lines 511, 701 parse STDERR_TAIL_PATH from lint-fix envelope)

## Decision 3: no-changes maps to stall internally
- **Question**: When lint-fix returns no-changes and a re-check still fails, should repair-loop emit stall?
- **Resolution**: Yes. run_check_fix_loop already handles this: no-changes → re-check; if still failing → no-changes-stale → maps to stall.
- **Source**: codebase (run_check_fix_loop lines 2392-2400, LoopResult status no-changes-stale)

## Decision 4: SKILL.md prose collapses at all 5 sites uniformly
- **Question**: Are all 5 sites equivalent in behavior?
- **Resolution**: Yes. Step 5 sites at lines 587, 639, 643 reference Step 3's loop; they all use the same dispatch-first pattern with repair-loop replacing the duplicated 4-way dispatch.
- **Source**: codebase (SKILL.md lines 587, 639, 643 reference Step 3 loop behavior)

## Decision 5: fence-shape test unaffected
- **Question**: Does changing prose at the 5 sites affect EXPECTED_OLD / EXPECTED_NEW fence counts?
- **Resolution**: No. The prose paragraphs change but bash fences (run-step-checks.sh calls) stay. EXPECTED_OLD=4, EXPECTED_NEW=36 remain valid.
- **Source**: codebase (scripts/test-implement-fence-shape.sh counts fence wrappers, not prose)
