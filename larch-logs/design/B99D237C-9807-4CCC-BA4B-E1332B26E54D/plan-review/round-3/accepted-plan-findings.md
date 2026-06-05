### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:54-57
- **Concern**: manifest_status path omits ctx.tmpdir prefix. Scenario: Plan text points at larch-logs/implement/<run_id>/manifest.json; implementers may read the wrong file or always see absent manifest, breaking restricted manifest-DONE routing
- **Proposed resolution**: Specify manifest_status reads Path(ctx.tmpdir) / larch-logs / implement / effective_run_id(ctx) / manifest.json (same contract as _manifest_path)


### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:365-388; scripts/ship-pr.sh:3291-3302
- **Concern**: 1. Blocked rebase-continuation refusal can erase the handoff state. Scenario: The plan says RESUME_PHASE=ship-pr-rrr-phase14 should write terminal state, but _write_ship_state rewrites PHASE and always clears RESUME_PHASE/CALLER_KIND. Bash continuation requires PHASE ci-initial or ci-merge plus the resume marker, so one Python refusal can make the next retry look like a normal resume.
- **Proposed resolution**: On the blocked path, do not rewrite ship state, or add explicit preservation for original PHASE, RESUME_PHASE, and CALLER_KIND while updating only counters/finalize detail. Add a two-invocation regression test.


### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:446-568
- **Concern**: 2. gh failure fallback conflicts with PR-head validation. Scenario: The plan says gh failures degrade to state validation, but open-pr resume is only safe with state-only validation when gh is intentionally skipped. A transient gh.pr_view failure for a closed or head-moved PR could skip checks/postbump using stale state.
- **Proposed resolution**: Treat gh.pr_view exceptions as fresh for normal repos. Reserve state-only open-pr classification for repo_unavailable, forked, or forked_target, and test that gh failure on a non-skipped repo returns fresh.


### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:460-474
- **Concern**: Resume dispatch is not ordered before the existing checks entrypoint. Scenario: The plan places `_resume_plan` after repo/tmpdir setup but never requires moving or guarding the unconditional `_write_ship_state(..., phase="checks")` and checks/postbump block that currently run first. An implementer can insert resume handling below that block so `done`/`merged`/`blocked-rebase-continuation` still run checks, `open-pr` persists zero counters and `PHASE=checks` before hydration, and counter restoration fails the core handback fix.
- **Proposed resolution**: State resume counters and phase before any `_write_ship_state`; compute `_resume_plan` immediately after tmpdir validation; return early for `done`, `merged`, and `blocked-rebase-continuation`; branch `open-pr`/`fresh` before the checks write.


### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:74,105; python/ship.py:387-388
- **Concern**: Blocked rebase continuation preserves counters but not the RESUME_PHASE/CALLER_KIND handoff token. Scenario: The proposed blocked-rebase-continuation path writes terminal ship state; existing _write_ship_state always emits empty RESUME_PHASE and CALLER_KIND, so the Python refusal can erase ship-pr-rrr-phase14 and leave the orchestrator without the bash continuation token after NEEDS_USER_INPUT
- **Proposed resolution**: Avoid rewriting ship-pr-state.sh on this path, or extend _write_terminal_state/_write_ship_state to preserve resume_phase and caller_kind; add the planned test assertion for those keys as well as counters


### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:460-461
- **Concern**: Plan orders resume after tmpdir setup but does not require _resume_plan before the first _write_ship_state. Scenario: Open-pr handback with restored counters hits _write_ship_state(ctx, phase="checks") with default iteration/rebase/fix/transient zeros and wipes persisted caps before _resume_plan runs
- **Proposed resolution**: Compute _resume_plan immediately after tmpdir validation; branch all paths before any _write_ship_state; on open-pr/merged/done/blocked never emit a pre-resume write with zero counters


### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:352-388
- **Concern**: Blocked rebase-continuation state can be overwritten through _write_ship_state, which currently blanks RESUME_PHASE and CALLER_KIND; the plan only says to preserve counters.. Scenario: A run stopped with RESUME_PHASE=ship-pr-rrr-phase14 returns NEEDS_USER, but the terminal write erases the handoff marker, so a retry or bash fallback loses the required continuation context.
- **Proposed resolution**: For blocked-rebase-continuation, leave the ship state file untouched or extend _write_ship_state to preserve the original RESUME_PHASE and CALLER_KIND; add a test that the marker remains.


### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:387-388
- **Concern**: Proposed blocked-rebase handoff still uses _write_ship_state which always blanks RESUME_PHASE and CALLER_KIND. Scenario: Plan requires write/preserve terminal state then NEEDS_USER_INPUT for RESUME_PHASE=ship-pr-rrr-phase14; any _write_terminal_state/_write_ship_state call clears handoff keys so a follow-up run_ship can classify open-pr and enter CI while conflict-resolution is still expected
- **Proposed resolution**: Fix plan: on blocked-rebase-continuation do not zero RESUME_PHASE/CALLER_KIND (read existing values and write them back); or skip state write and return NEEDS_USER_INPUT with counters only


### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:16-22
- **Concern**: Resume-kind precedence is listed with blocked-rebase-continuation after open-pr/merged/done. Scenario: An implementer following narrative order can run open-pr (skip checks, restore counters, call monitor) when state still has RESUME_PHASE=ship-pr-rrr-phase14 and an open PR
- **Proposed resolution**: Fix plan: state explicitly that _resume_plan evaluates blocked-rebase-continuation before open-pr and merged (and document relative order vs done)


### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:522-530
- **Concern**: Open-pr resume path does not require the same merge/draft/forked/repo_unavailable short-circuit as the fresh path after ensure_pr. Scenario: Fresh run_ship returns OK without CI when not merge or draft or forked or repo_unavailable; open-pr as written only skips checks/postbump then seeds CI, so a resumed PR-only or forked dry-run session can wrongly enter the merge loop
- **Proposed resolution**: Fix plan: after open-pr hydration read MERGE/DRAFT/FORKED_TARGET/REPO_UNAVAILABLE from state (or ctx) and reuse the existing early-exit branch before seeding CI counters


### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:365-388
- **Concern**: Blocked rebase-continuation writes can erase RESUME_PHASE and CALLER_KIND because _write_ship_state hardcodes both fields empty. Scenario: The plan says RESUME_PHASE=ship-pr-rrr-phase14 should return NEEDS_USER_INPUT, but if that branch writes terminal state it can delete the handoff marker that bash needs to resume the required continuation
- **Proposed resolution**: Avoid writing ship state in the blocked branch, or extend the writer to preserve existing RESUME_PHASE and CALLER_KIND for that branch; add a test that the markers remain, not only the counters


### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:352-388
- **Concern**: Blocked-rebase refusal write clears RESUME_PHASE/CALLER_KIND. Scenario: After NEEDS_USER_INPUT for ship-pr-rrr-phase14, state may show RESUME_PHASE empty and a later run mis-classifies as open-pr/fresh instead of refusing continuation
- **Proposed resolution**: Preserve existing RESUME_PHASE/CALLER_KIND on blocked writes (or skip the write); add a repeat-invocation test that still returns NEEDS_USER_INPUT


### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:352-388
- **Concern**: Unsupported rebase-continuation refusal does not require preserving RESUME_PHASE/CALLER_KIND; the current state writer clears both keys. Scenario: After RESUME_PHASE=ship-pr-rrr-phase14 returns NEEDS_USER_INPUT once, the state can be rewritten with RESUME_PHASE empty, so the next run may resume as open-pr/fresh and skip the required continuation work
- **Proposed resolution**: Specify that the blocked-rebase-continuation write must retain RESUME_PHASE=ship-pr-rrr-phase14 and CALLER_KIND or another re-detectable blocked marker, and add a repeat-invocation test that it still refuses rather than progressing


### FINDING_14:
- **Reviewer(s)**: Codex-dyn-ci-monitor-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:123-125; python/ship.py:554-578; python/ci_monitor.py:1324-1345; python/test_ci_monitor.py:1238-1321,1590-1601
- **Concern**: Plan excludes python/test_ci_monitor.py while claiming monitor-outcome acceptance can be exercised through python/test_ship.py stubs. Scenario: python/test_ship.py can only verify run_ship forwards a prebuilt monitor.result; it cannot prove ci_monitor maps local-unfixable to NEEDS_USER_INPUT or transient bail reasons to TRANSIENT. Existing python/test_ci_monitor.py covers timeout stalled but not those two monitor routing branches.
- **Proposed resolution**: Add only two narrow python/test_ci_monitor.py tests for monitor local-unfixable routing and transient bail-to-TRANSIENT routing; keep the existing stalled test and avoid expanding unrelated ship/resume scope.


### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-state-schema
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:460-460
- **Concern**: Entry checks-phase state write not gated to fresh-only. Scenario: Unconditional _write_ship_state before _resume_plan zeroes ITERATION/REBASE_COUNT/FIX_ATTEMPTS/TRANSIENT_RETRIES and clears RESUME_PHASE; resume/counter/rebase-continuation logic reads stale zeros
- **Proposed resolution**: Run _resume_plan first; move _write_ship_state(..., phase="checks") into the fresh branch only; pass restored counters on every non-fresh pre-CI write


### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-state-schema
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:68-68
- **Concern**: _resume_plan branch probe helper unspecified. Scenario: Using git.current_branch raises on detached HEAD; violates never-raise contract and can abort instead of returning fresh
- **Proposed resolution**: Specify git.try_current_branch (or equivalent non-raising probe) for checkout validation in _resume_plan


### FINDING_17:
- **Reviewer(s)**: Codex-dyn-state-schema
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:74-75; python/ship.py:339-345,352-388; scripts/ship-pr.sh:3291-3303
- **Concern**: Blocked rebase-continuation refusal can erase RESUME_PHASE. Scenario: The plan says to write terminal state for RESUME_PHASE=ship-pr-rrr-phase14, but _write_ship_state rewrites the whole state and clears RESUME_PHASE and CALLER_KIND. Bash needs that token to run the special continuation. A Python refusal followed by a bash handback could skip required continuation work.
- **Proposed resolution**: For blocked-rebase-continuation, avoid the full terminal state rewrite or extend the state writer to preserve RESUME_PHASE=ship-pr-rrr-phase14 and CALLER_KIND while updating counters. Add the existing planned test to assert the token survives, not just counters.


### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-bash-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:460-474
- **Concern**: Resume classification is ordered after the unconditional entry `_write_ship_state(ctx, phase="checks")`, which writes default-zero counters. Scenario: The plan places `_resume_plan` after repo/tmpdir setup but does not require relocating it before the existing checks-phase write. A literal insert leaves `ITERATION`/`REBASE_COUNT`/`FIX_ATTEMPTS`/`TRANSIENT_RETRIES` and `PHASE=checks` clobbered before `open-pr`/`merged`/`done` branches run, reproducing the counter-reset bug on the first resume handback
- **Proposed resolution**: Branch on `_resume_plan` immediately after tmpdir validation and before any `_write_ship_state`; only the `fresh` path may emit `phase="checks"`


### FINDING_19:
- **Reviewer(s)**: Codex-dyn-bash-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:446-460; scripts/ship-pr.sh:2870-2892,3275-3303
- **Concern**: RESUME_PHASE=ship-pr-rrr-phase14 refusal has no required precedence before fresh fallback. Scenario: The plan says any failed validation returns fresh, while bash records this handoff in state and requires explicit continuation; a branch or PR validation failure could make Python overwrite the handoff and restart fresh instead of refusing unsupported continuation
- **Proposed resolution**: In _resume_plan, classify ship-pr-rrr-phase14 as blocked immediately after reading state and counters, before branch/PR validation or any fresh fallback


