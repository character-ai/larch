### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:211-218,297-304,497-500; python/finalize.py:346-368
- **Concern**: Python OOS routing is moved to finalize-state even though OOS exits do not write that state. Scenario: On the Python path, oos-filing exits write OOS_PENDING and fork/repo-unavailable data to ship-pr-state only; finalize-state is absent or lacks OOS_PENDING, so the proposed Step 8/OOS checkpoint read-source change can miss continuation or skip-gate inputs
- **Proposed resolution**: Keep OOS_PENDING, FORKED_TARGET, and REPO_UNAVAILABLE as scoped ship-pr-state reads for Python OOS checkpoint routing, matching the existing helper, or explicitly add finalize-state writes/schema for every OOS exit path

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_run_logs.py:28-49
- **Concern**: Shared RecordingRunner plan drops the git_commits behavior used by test_run_logs. Scenario: The planned import-swap-only change removes runner.git_commits, but existing tests increment and assert it; make py-test will fail with AttributeError or lose the commit-count assertion
- **Proposed resolution**: Leave a tiny test_run_logs-local subclass that extends the shared queue runner with git_commits tracking, or add an explicit optional call hook/counter to test_support and update those assertions accordingly

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_run_logs.py:32-47
- **Concern**: Plan mandates bare shared RecordingRunner import but local runner defines git_commits and auto-increment on git commit argv. Scenario: Blind import swap drops git_commits; tests at :105 :121 and :597 raise AttributeError and make py-test fail
- **Proposed resolution**: Keep a thin local subclass extending test_support.RecordingRunner with git_commits (and commit argv hook), or document that field in test_support.py; do not treat test_run_logs.py as import-only

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: python/finalize.py:297-307 and python/ship.py:395-410
- **Concern**: Planned XDG cache helper accepts relative XDG_CACHE_HOME as an allowlist root. Scenario: XDG_CACHE_HOME=relative turns the cleanup and tmpdir allowlist into a cwd-relative root, contrary to XDG rules, so an unexpected repo-local larch/sessions path can pass validation and later cleanup checks
- **Proposed resolution**: Use XDG_CACHE_HOME only when it is non-empty and absolute; otherwise fall back to Path.home() / ".cache"

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:425-435
- **Concern**: Gap-fill tests omit post-merge flush-skip stale-ctx regression. Scenario: run_postmerge_phase writes finalize-state with STALL_TRACKING=false then returns STALLED on flush skip while main() ctx still lacks in-run PR_NUMBER; naive gap-fill write_finalize_state(ctx) can erase PR_NUMBER (failure mode 5)
- **Proposed resolution**: Add test_ship regression for post-merge flush-skip stall asserting STALL_TRACKING=true and PR_NUMBER preserved; gap-fill must read-merge-write existing finalize-state and prefer result.pr_number/pr_url/merge_result over main ctx

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_run_logs.py:27-52
- **Concern**: The plan says test_run_logs.py gets a shared-runner import swap only, but its local RecordingRunner has a git_commits counter used by existing assertions.. Scenario: The proposed swap to python/test_support.py would remove runner.git_commits, so tests at python/test_run_logs.py:105, python/test_run_logs.py:121, and python/test_run_logs.py:597 would fail or lose their assertion target.
- **Proposed resolution**: Keep this file's tiny local subclass over test_support.RecordingRunner with git_commits, or replace those assertions with direct call-list checks during the swap.

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: python/logging_util.py:45-62; python/run_logs.py:960-975; python/ship.py:100-102; python/ci_monitor.py:192-193
- **Concern**: quiet_init redirects stderr but the plan leaves operator warnings on quiet=False call sites. Scenario: After quiet_init, ship.py breadcrumbs, CI progress, and the secret-scrub warning write to the redirected stderr log only instead of caller-visible fd4; the Python ship path loses bash-parity progress and can hide the credential-rotation warning
- **Proposed resolution**: Route operator-visible Python breadcrumbs and warnings through the quiet-aware path: remove quiet=False from progress/security warning call sites or add a dedicated fd4 warning helper; add a regression that a secret-scrub warning or ship breadcrumb reaches original stderr after self-initialized quiet

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_run_logs.py:27-52,99-121,597
- **Concern**: Shared RecordingRunner import swap omits test_run_logs git_commits behavior. Scenario: test_run_logs asserts runner.git_commits and increments it in a fake commit path; the proposed generic calls/responses helper has no git_commits attribute or git commit counter, so an import-swap-only change breaks these tests
- **Proposed resolution**: Keep a small local subclass or fixture in test_run_logs that extends test_support.RecordingRunner with git_commits counting, or leave this file's runner local; avoid expanding the shared helper unless needed

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:116-118; python/test_run_logs.py:27-52,105,121,597
- **Concern**: Shared RecordingRunner migration lists test_run_logs.py as import-swap-only but its local runner tracks git_commits. Scenario: Blind import of test_support.RecordingRunner drops git_commits; flush_logs_pre/post tests that assert runner.git_commits fail or lose commit-count coverage
- **Proposed resolution**: Exclude test_run_logs.py from consolidation (keep local runner with git_commits) or extend test_support with optional git_commits counting; update the nine-file count and acceptance wording accordingly

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_run_logs.py:27-52,576-597
- **Concern**: FINDING_1: Shared RecordingRunner plan omits test_run_logs git_commits contract. Scenario: After the import swap, tests that assert runner.git_commits either fail with a missing attribute or lose the current git commit counting behavior
- **Proposed resolution**: Add git_commits to test_support.RecordingRunner with the same git commit argv increment semantics before migrating test_run_logs.py, or leave test_run_logs.py on its local runner

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-quiet-fd-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_ship.py (planned tests) / python/ship.py:680-686
- **Concern**: Acceptance, edge-case, and journal-failure test prose say contract JSON reaches stdout, but B4 routes post-quiet_init JSON through contract_stream() to FD 3 (lib-quiet caller-visible stream), not FD 1. Scenario: Journal-failure regression exercised via main() after quiet_init will pass capsys.stdout (the quiet log) while orchestrator-visible FD 3 receives no JSON; the swallowed-contract failure quiet_init is meant to fix can ship undetected
- **Proposed resolution**: Rename acceptance/edge language to caller-visible contract stream via contract_stream() (FD 3 after quiet_init, sys.stdout before); add an explicit test that dup-captures FD 3 after quiet_init for journal-failure and happy-path emit_result

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-stall-gap-fill-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:344-378
- **Concern**: Plan names finalize.read_finalize_state but finalize.py has no read helper and the finalize.py file section omits it. Scenario: Gap-fill cannot use the documented API; implementer may duplicate run_logs._read_finalize_kv or skip reads
- **Proposed resolution**: Add read_finalize_state (thin key-based wrapper, no sourcing) under ### UPDATED: python/finalize.py alongside cache_sessions_root()

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-stall-gap-fill-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:597-606
- **Concern**: Gap-fill merge rules omit PR metadata sources for exception-path STALLED exits. Scenario: Merge-loop rebase Stalled leaves finalize-state absent and ShipResult without pr_number; Step 18 stall routing loses PR_NUMBER despite ship-pr-state.sh
- **Proposed resolution**: In _persist_stall_metadata_if_needed populate PR_NUMBER/PR_URL/MERGE_RESULT from non-empty ShipResult fields then key-parse ship-pr-state.sh (ctx.state_file) when finalize-state lacks them; add one regression for rebase Stalled without pre-existing finalize-state.sh

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-stall-gap-fill-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:32-37,186,202; python/ship.py:462,488,510,597-606,667-668; python/pr_body.py:256-260; python/pr.py:43-65
- **Concern**: The gap-fill plan names early pr.ensure_pr ShipError as the true gap example but does not make the true-gap set exhaustive. Current run_ship also converts other pre-finalize exceptions to STALLED without finalize-state, including checks.run_checks_phase ShipError, pr_body.compose_pr_body ShipError, and rebase_and_push Stalled after the rebase phase state write.. Scenario: An implementer could special-case only ensure_pr and leave other valid-tmpdir STALLED exits without STALL_TRACKING=true, so Step 18 can miss stall recovery.
- **Proposed resolution**: Define the rule generically: for any Outcome.STALLED after run_ship/exception conversion with an allowed tmpdir and no existing STALL_TRACKING=true, write merged stall metadata, with invalid-tmpdir as the explicit no-write exception. Add at least one regression outside ensure_pr.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-stall-gap-fill-boundary
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:35,49-52; python/finalize.py:344-378; python/run_logs.py:79-92
- **Concern**: The plan tells ship.py to use finalize.read_finalize_state, but finalize.py currently has only write_finalize_state and the finalize.py update section only adds cache_sessions_root. A private key reader exists in run_logs.py, not finalize.py.. Scenario: Calling the named helper fails, or using write_finalize_state from a stale RunContext rewrites the file and can drop preserved keys the same bullet requires.
- **Proposed resolution**: Either add read_finalize_state plus an atomic dict writer to finalize.py, or change the plan to require a local key-based parser/writer in ship.py and test preservation of existing keys.

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-stall-gap-fill-boundary
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:33-36,135,142,150-151,176,189-194; python/ship.py:454-455
- **Concern**: The invalid-tmpdir edge is described correctly in ship.py prose and SKILL.md prose as JSON-only, but the test strategy only pins generic Exit 4 finalize-state reads and does not pin the JSON fallback/no-write contract.. Scenario: A structural test could pass after removing the invalid-tmpdir fallback prose, leaving Step 8+ to require finalize-state on a path where ship.py deliberately refuses to write it.
- **Proposed resolution**: Add a minimal structural pin for “finalize-state absent → JSON detail fallback” on the Python Exit 4 path, and a unit test that invalid tmpdir returns STALLED JSON without writing finalize-state.
