### FINDING_1: Validate PR identity before open-pr resume
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: Resume classification can treat invalid or unsafe PR identity as an open PR, allowing checks/postbump to be skipped for non-numeric, closed, or wrong-branch PRs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define identity only when state/ctx PR_NUMBER is a base-10 int (same rule as counters); otherwise treat as no identity → fresh
  - From Codex-Innovation: Only classify open-pr when the PR is OPEN and its head_ref matches the current branch, or when gh is skipped require matching state-file branch; otherwise use fresh or stall


### FINDING_2: Terminal CI handbacks overwrite restored counters with zero
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-state-contract
- **Severity**: important
- **Concern**: CI-loop counters are restored and persisted during the loop, but terminal handback/stall writes call the state writer without those counters, overwriting ITERATION/REBASE_COUNT/FIX_ATTEMPTS/TRANSIENT_RETRIES with zeros and resetting session-wide caps on the next invocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Thread the current counters into terminal state writes in the CI loop, or add a small loop-local state writer that preserves them; cover a handback path by asserting the state file keeps the seeded counters
  - From Cursor-Edge: In _write_terminal_state (or equivalent), preserve counters from the state file via read_resume_counters before writing; add a handback test that runs run_ship once to NEEDS_USER_INPUT, then asserts the second run seeds ci_monitor with non-zero counters without manually rewriting the state file.
  - From Codex-Edge: Carry iteration, rebase_count, fix_attempts, and transient_retries into terminal writes from the CI loop, either by extending _write_terminal_state or writing state explicitly. Add a test that inspects the state file after exit-3 and exit-6 handbacks.
  - From Codex-Innovation: Extend _write_terminal_state to accept counter values, and pass the live loop counters on CI handback and cap paths
  - From Codex-Pragmatic: Thread the current counters into _write_terminal_state or add a preserve-counters path before every CI handback/stall write; add a resume test that inspects the state file after an exit-3/exit-6 monitor result, not only the monitor kwargs on the next run.
  - From Codex-Requirements: Thread current counters into the terminal write path for CI-loop exits, or add optional counter args to _write_terminal_state. Add a regression that inspects the state file after a NEEDS_USER_INPUT or TRANSIENT return.
  - From Cursor-dyn-state-contract: Extend `_write_terminal_state` to accept optional counter kwargs and forward them from merge-loop call sites (`ship.py:538`, `568`, `592`); document in the `python/ship.py` plan section (minimal change to call sites, not `_write_ship_state` semantics)


### FINDING_3: Open-pr resume can erase PR metadata before context hydration
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: The open-pr resume path can fall through to pr-create state writes using the original context before PR_NUMBER/PR_URL are restored, so early gates or handbacks can erase persisted PR identity and cause the next resume to classify as fresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Use an active context for open-pr resume with pr_number/pr_url/merge_result restored before the pr-create state write, and pass it through gates, ensure_pr, and state writes
  - From Codex-Innovation: Build a resume-aware context with resume.pr_number/resume.pr_url before pr-create, and use it for pr-create state writes and gates


### FINDING_4: Merged resume can run postmerge with empty merge_result
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: When merged classification comes from gh state, manifest status, or phase rather than MERGE_RESULT, postmerge can receive an empty merge_result, write an empty sentinel, fail to finalize the manifest, and omit the merge classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: In _resume_plan, when any merged predicate holds, set resume.merge_result to a persisted post-merge value if present, otherwise default to config.MERGE_RESULT_MERGED; hydrate pr_url from gh when available
  - From Codex-Edge: When _resume_plan classifies merged, default an empty or non-postmerge MERGE_RESULT to config.MERGE_RESULT_DRIVER_ALREADY_MERGED or config.MERGE_RESULT_MERGED before calling run_postmerge_phase. Add coverage for gh MERGED with empty state MERGE_RESULT.
  - From Codex-Innovation, Codex-Requirements: When _resume_plan classifies merged without a post-merge merge_result, set merge_result to already_merged or another POST_MERGE_MERGE_RESULTS value before postmerge


### FINDING_6: Fresh resume can inherit stale counters
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The fresh path is supposed to start counters at zero, but the approach seeds the CI loop from restored resume counters for every branch, so stale state without PR identity can enter CI near a cap and immediately stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `_resume_plan`, zero `ResumePlan` counters when `start == "fresh"` (or use literal zeros in the `fresh` branch only); keep state-file restore for `open-pr`/`merged` only


