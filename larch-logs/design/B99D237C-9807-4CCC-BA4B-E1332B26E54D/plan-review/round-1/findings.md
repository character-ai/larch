### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:22-25
- **Concern**: PR identity from PR_NUMBER lacks a digit-parse contract. Scenario: Non-numeric PR_NUMBER (e.g. PR_NUMBER=abc) is treated as identity; open-pr resume can skip checks/postbump yet hand ci_monitor pr=0 or a bogus ensure_pr path
- **Proposed resolution**: Define identity only when state/ctx PR_NUMBER is a base-10 int (same rule as counters); otherwise treat as no identity → fresh

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:339-345,545-572
- **Concern**: The plan restores counters at loop entry but leaves _write_terminal_state writing default 0 counters. Scenario: On a NEEDS_USER_INPUT or TRANSIENT CI handback, the loop first persists restored counters, then _write_terminal_state overwrites ITERATION/REBASE_COUNT/FIX_ATTEMPTS/TRANSIENT_RETRIES with zeros, so the next invocation still resets the session caps
- **Proposed resolution**: Thread the current counters into terminal state writes in the CI loop, or add a small loop-local state writer that preserves them; cover a handback path by asserting the state file keeps the seeded counters

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:486-507
- **Concern**: The open-pr branch falls through to pr-create without first hydrating ctx with resume.pr_number/pr_url. Scenario: Early pr-create gates write ship state before ensure_pr; if materialize, security, or OOS returns NEEDS_USER_INPUT, those writes erase PR_NUMBER and the next resume classifies fresh, rerunning checks/postbump
- **Proposed resolution**: Use an active context for open-pr resume with pr_number/pr_url/merge_result restored before the pr-create state write, and pass it through gates, ensure_pr, and state writes

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:416-443
- **Concern**: Merged resume can enter postmerge with an empty merge_result when the predicate came from gh state, manifest status, or phase rather than MERGE_RESULT. Scenario: run_postmerge_phase writes an empty MERGE_RESULT and flush_logs_post receives an empty merge_result, so the final manifest may stay partial and the ShipResult omits the merge classification for an already-merged PR
- **Proposed resolution**: In _resume_plan, when any merged predicate holds, set resume.merge_result to a persisted post-merge value if present, otherwise default to config.MERGE_RESULT_MERGED; hydrate pr_url from gh when available

### FINDING_5:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:339-345
- **Concern**: persisted counters zeroed on CI handback exits. Scenario: Each merge-loop iteration writes ITERATION/REBASE_COUNT/etc. at ship.py:545-552, but _write_terminal_state calls _write_ship_state with default counter args (0), overwriting the file before exit 3/6/4. Re-entry read_resume_counters then reads zeros, so caps and fix-attempt limits reset despite the new reader.
- **Proposed resolution**: In _write_terminal_state (or equivalent), preserve counters from the state file via read_resume_counters before writing; add a handback test that runs run_ship once to NEEDS_USER_INPUT, then asserts the second run seeds ci_monitor with non-zero counters without manually rewriting the state file.

### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:339-345,537-578
- **Concern**: Terminal CI handbacks still overwrite counters with defaults. Scenario: The loop writes current counters before monitor, but NEEDS_USER_INPUT or TRANSIENT then calls _write_terminal_state, which calls _write_ship_state without counters. The state file stores zeros, so the next orchestrator re-entry resumes at 0 and the session-wide caps remain per-process.
- **Proposed resolution**: Carry iteration, rebase_count, fix_attempts, and transient_retries into terminal writes from the CI loop, either by extending _write_terminal_state or writing state explicitly. Add a test that inspects the state file after exit-3 and exit-6 handbacks.

### FINDING_7:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:416-433
- **Concern**: Merged resume can run postmerge with an empty merge_result. Scenario: If gh reports MERGED or the manifest is done but MERGE_RESULT is absent in the state file, the proposed merged branch passes merge_result="". run_postmerge_phase writes an empty post-merge sentinel, flush_logs_post does not mark the manifest done, and the final result loses the merge classification.
- **Proposed resolution**: When _resume_plan classifies merged, default an empty or non-postmerge MERGE_RESULT to config.MERGE_RESULT_DRIVER_ALREADY_MERGED or config.MERGE_RESULT_MERGED before calling run_postmerge_phase. Add coverage for gh MERGED with empty state MERGE_RESULT.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:460-461
- **Concern**: Resume plan gates checks/postbump blocks but not the pre-checks state write. Scenario: An open-pr handback still runs _write_ship_state(phase=checks) and the checks breadcrumb before the skip, regressing PHASE and misleading downstream readers
- **Proposed resolution**: Move _resume_plan before any phase-specific _write_ship_state/_breadcrumb, or guard those two lines so they run only when resume.start == fresh

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:339-345,545-573
- **Concern**: Terminal handback still resets counters to zero. Scenario: The plan restores counters on entry, but monitor NEEDS_USER_INPUT or TRANSIENT calls _write_terminal_state, which rewrites the state file without iteration/rebase/fix/transient values; the next resume reads zeros and the session caps still reset
- **Proposed resolution**: Extend _write_terminal_state to accept counter values, and pass the live loop counters on CI handback and cap paths

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:486-517
- **Concern**: Open-PR resume falls through with the original ctx. Scenario: Before ensure_pr refreshes PR data, _write_ship_state(ctx, phase="pr-create") can erase state-file PR_NUMBER/PR_URL and reset counters; if OOS or materialization blocks, the next run misclassifies as fresh
- **Proposed resolution**: Build a resume-aware context with resume.pr_number/resume.pr_url before pr-create, and use it for pr-create state writes and gates

### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:460-510
- **Concern**: Resume trusts any non-merged PR identity as open-pr. Scenario: The plan skips checks and postbump even if gh reports the PR is CLOSED unmerged or the PR head does not match the current branch; ensure_pr can then create a new PR without the skipped prep
- **Proposed resolution**: Only classify open-pr when the PR is OPEN and its head_ref matches the current branch, or when gh is skipped require matching state-file branch; otherwise use fresh or stall

### FINDING_12:
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:416-443
- **Concern**: merged resume may enter postmerge with empty merge_result. Scenario: If gh or manifest says merged but state MERGE_RESULT is empty, run_postmerge_phase writes an empty sentinel and flush_logs_post does not mark the manifest done
- **Proposed resolution**: When _resume_plan classifies merged without a post-merge merge_result, set merge_result to already_merged or another POST_MERGE_MERGE_RESULTS value before postmerge

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:16-20,43
- **Concern**: `fresh` says counters from 0 but Approach says counters always restored and `run_ship` seeds the CI loop from `resume.*` for every branch. Scenario: Stale/partial state with empty `PR_NUMBER` but high `ITERATION` classifies as `fresh`, runs full checks, then enters CI at iteration 49 and can immediately hit the merge-loop cap
- **Proposed resolution**: In `_resume_plan`, zero `ResumePlan` counters when `start == "fresh"` (or use literal zeros in the `fresh` branch only); keep state-file restore for `open-pr`/`merged` only

### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:339-345,545-573
- **Concern**: Finding 1: terminal handback still overwrites restored CI-loop counters with zero. Scenario: After monitor returns NEEDS_USER_INPUT or TRANSIENT, run_ship writes the current counters at the CI poll, then _write_terminal_state calls _write_ship_state without counter args, so the state file saved for the next invocation has ITERATION/REBASE_COUNT/FIX_ATTEMPTS/TRANSIENT_RETRIES reset to 0 and the session-wide caps remain per-process.
- **Proposed resolution**: Thread the current counters into _write_terminal_state or add a preserve-counters path before every CI handback/stall write; add a resume test that inspects the state file after an exit-3/exit-6 monitor result, not only the monitor kwargs on the next run.

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:486-510 python/pr.py:45-47
- **Concern**: open-pr resume still runs full pr.ensure_pr which calls _push_existing_pr on OPEN PRs. Scenario: After exit-3/6 handback with an open PR, skipping checks/postbump but re-entering pr-create can still git push (and force-push recovery), partially reproducing the redundant push/CI churn the plan targets
- **Proposed resolution**: For open-pr with state PR_NUMBER, hydrate ctx from ResumePlan and jump to the CI loop (or add a resume-only ensure_pr path that reuses PR metadata without push); add a resume test asserting no git push argv in runner.calls

### FINDING_16:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:339-345,545-578
- **Concern**: 1. Terminal CI exits still overwrite restored counters with zero. Scenario: After monitor returns NEEDS_USER_INPUT or TRANSIENT, _write_terminal_state calls _write_ship_state without iteration/rebase/fix/transient values, so the next resume reads zeros despite the plan's counter restore work.
- **Proposed resolution**: Thread current counters into the terminal write path for CI-loop exits, or add optional counter args to _write_terminal_state. Add a regression that inspects the state file after a NEEDS_USER_INPUT or TRANSIENT return.

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-state-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:339-345
- **Concern**: `_write_terminal_state` rewrites the state file without passing loop counters, so `_write_ship_state` defaults `ITERATION`/`REBASE_COUNT`/`FIX_ATTEMPTS`/`TRANSIENT_RETRIES` to 0. Scenario: On exit-3/exit-6 (and merge-loop STALLED) from the CI loop, the last state write overwrites counters that were persisted at the start of the iteration (`ship.py:545-552`), so `read_resume_counters` restores zeros and session caps reset despite the plan’s goal
- **Proposed resolution**: Extend `_write_terminal_state` to accept optional counter kwargs and forward them from merge-loop call sites (`ship.py:538`, `568`, `592`); document in the `python/ship.py` plan section (minimal change to call sites, not `_write_ship_state` semantics)
