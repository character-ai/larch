### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:76-78; python/ship.py:536-544
- **Concern**: The proposed cap-exhaustion test expects ITERATION=49 with cap 50 to stall immediately, but the preserved loop only stalls when iteration >= cap.. Scenario: Following this test would force an off-by-one behavior change and violate the plan's no-change merge-loop-body/minimum-change contract.
- **Proposed resolution**: Keep existing cap semantics: test immediate stall with ITERATION=50, or expect one monitor call at ITERATION=49 before the next loop stalls.

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:486-524
- **Concern**: FINDING_2 fixes terminal writes only; open-pr pr-create _write_ship_state calls still default counters to 0. Scenario: On exit-3/exit-6 re-entry classified as open-pr, _resume_plan restores session counters in memory but pr-create-path _write_ship_state (phase pr-create/ci-initial/done and OOS/materialize side writes at ship.py:218-322,499) omits counter kwargs and overwrites persisted ITERATION/REBASE_COUNT/FIX_ATTEMPTS/TRANSIENT_RETRIES before the CI loop first counter-preserving write at ship.py:545; a crash/OOS re-handback between those writes leaves the state file at zero so the next process re-read loses cap progress (ITERATION=49 cap bypass)
- **Proposed resolution**: Thread resume.iteration/rebase_count/fix_attempts/transient_retries through every _write_ship_state on the open-pr path until the CI loop owns updates, or skip counter-bearing state writes until ship.py:545; extend the terminal round-trip test to assert counters survive pr-create writes on second run_ship

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:416-443,446-455
- **Concern**: Merged resume returns run_postmerge_phase directly without advancing ship state to done. Scenario: After a PHASE=postmerge or PR_CLOSED=true resume succeeds, ship-pr-state.sh can remain at postmerge, so the next re-entry repeats postmerge instead of observing completion
- **Proposed resolution**: In the merged branch, store the postmerge result; when outcome is OK, call _write_ship_state(working, phase="done", with restored counters) before returning, and add a resume test that asserts PHASE=done after successful merged resume

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:486-517
- **Concern**: Open-pr resume still calls _write_ship_state with default counter kwargs before the CI loop. Scenario: After exit-3/6, _resume_plan restores counters in memory, but pr-create-path writes (phase pr-create/ci-initial/done) persist iteration/rebase_count/fix_attempts/transient_retries as 0. A crash/OOM between those writes and the first loop _write_ship_state loses session caps; the planned terminal-counter test only covers monitor handback, not this window
- **Proposed resolution**: In the open-pr branch, thread resume.iteration/rebase_count/fix_attempts/transient_retries into every _write_ship_state until the CI loop seeds locals, or defer state writes until the loop; add a test that asserts non-zero counters in ship-pr-state.sh immediately after the first open-pr _write_ship_state

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:416-443
- **Concern**: Merged resume plan runs postmerge without refreshing ship-pr-state. Scenario: Step 18 restore-finalize-state treats ship-pr-state as authoritative; if resume is classified from gh or manifest while ship-pr-state still has PR_CLOSED=false or empty MERGE_RESULT, restore can overwrite the correct finalize-state and teardown/final reporting can see a non-merged run
- **Proposed resolution**: Write merged-resume state before postmerge and again on success, matching the normal merge path: _write_ship_state(working, phase="postmerge", restored counters) before run_postmerge_phase and _write_ship_state(working, phase="done", restored counters) after OK

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:509-515; python/pr.py:41-42
- **Concern**: Open-pr resume can drop hydrated PR identity after ensure_pr. Scenario: For repo_unavailable resumes the plan validates PR_NUMBER/PR_URL from state, but pr.ensure_pr returns number=0 and url="", and the existing working = ctx.with_(pr_number=ensured.number or None, pr_url=ensured.url) pattern would erase the restored identity before finalize/state writes
- **Proposed resolution**: Preserve resumed identity when ensure_pr returns local-only or empty: on resume.start == "open-pr", set pr_number=ensured.number or resume.pr_number and pr_url=ensured.url or resume.pr_url

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:446-460; python/run_logs.py:74-98
- **Concern**: No-state resume contract is internally inconsistent. Scenario: The plan's edge cases require ctx.state_file is None => fresh, but parse_pr_number(state_file, ctx_pr_number) can make a PR_NUMBER from argv/env enough to classify open-pr and skip checks/postbump without a durable state file
- **Proposed resolution**: In _resume_plan, short-circuit to fresh when ctx.state_file is falsy; only use ctx.pr_number as fallback after a state file exists but lacks PR_NUMBER, or remove that fallback

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/ci_monitor.py:142-153; python/ship.py:537-545
- **Concern**: Test matrix encodes an off-by-one cap. Scenario: The plan asks for ITERATION=49 + cap 50 => immediate stall, but both ci_monitor and the ship loop stall only at iteration >= 50; changing code to satisfy that test would remove the last allowed poll and break current cap semantics
- **Proposed resolution**: Change the acceptance case to ITERATION=50 for immediate stall, or assert ITERATION=49 performs one monitor pass and then stalls after increment

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:18-23
- **Concern**: Open-PR resume uses ctx.branch as the branch check and never validates the actual checked-out git branch, despite the feature requiring gh/git ground truth.. Scenario: On a stale RunContext or wrong checkout, open-pr resume can skip checks/postbump and then pr.ensure_pr's existing-PR path can push HEAD without the push_branch branch guard.
- **Proposed resolution**: Add a minimal git.try_current_branch probe in _resume_plan; require it to match the expected branch and PR head when available, otherwise classify fresh so existing guards run.

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:47
- **Concern**: Terminal CI handback preserves only the pre-monitor loop locals, not counters consumed by a terminal monitor result.. Scenario: If ci_monitor returns NEEDS_USER_INPUT after did_fixing=True, the next run restores the old FIX_ATTEMPTS value, so exit-3 handbacks can still bypass the session-wide fix-attempt cap.
- **Proposed resolution**: When writing terminal state for the ci_monitor non-OK path, persist the live counters plus the same monitor.did_fixing and monitor.transient_rerun_attempted increments used on the OK continue path; add a focused round-trip test for terminal did_fixing.

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:78
- **Concern**: The cap-exhaustion test expectation says ITERATION=49 with cap 50 should immediately stall, which is off by one for the existing loop semantics.. Scenario: Implementers may change the cap check to satisfy the proposed test and reduce the allowed iteration budget from 50 polls to 49.
- **Proposed resolution**: Keep minimum-change semantics: use ITERATION=50 for immediate stall, or assert ITERATION=49 is restored into the monitor and stalls only after the next wait iteration.

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-bash-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:3308-3323
- **Concern**: _resume_plan ignores persisted PHASE for entry point. Scenario: Bash resumes at the state PHASE (ci-initial, ci-merge, pr-create, postmerge, done). The plan’s open-pr path always skips checks/postbump and re-enters the pr-create body before the CI loop, so an exit-3/exit-6 handback at PHASE=ci-initial or ci-merge re-runs pr-create/OOS/materialize gates instead of jumping straight to CI like bash.
- **Proposed resolution**: goto_rebase and other mid-CI re-invokes can diverge (extra gh/push churn, OOS re-prompts, wrong ci-merge timing). Teach _resume_plan to read PHASE (and CI_PASSED) from state: done→no-op OK; postmerge→merged; ci-initial/ci-merge→open-pr entry at CI with pr-create skipped; only lower phases run pr-create.

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-bash-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:3324
- **Concern**: No PHASE=done fast-path in _resume_plan. Scenario: Bash exits 0 immediately when PHASE=done. The plan never checks PHASE=done; a completed merge=false run (PHASE=done, PR_NUMBER set, PR still OPEN) classifies as open-pr and re-enters CI.
- **Proposed resolution**: Spurious re-invocation after a successful PR-only run repeats CI/merge work instead of idempotent exit 0. Add a first-class done target (or treat PHASE=done as immediate ShipResult OK) before PR-identity/open-pr logic.

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-bash-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2947-2954
- **Concern**: repo_unavailable open-pr still runs CI loop. Scenario: Bash run_ci_phase skips ci-wait when REPO_UNAVAILABLE=true or PR_NUMBER is empty and advances ci-initial→ci-merge or ci-merge→postmerge without polling. The plan’s repo_unavailable branch match still classifies open-pr and seeds the CI monitor loop.
- **Proposed resolution**: Fork/OSS PR-only resume paths poll or fix CI against an unreachable repo instead of phase-skipping like bash. Mirror bash: when ctx.repo_unavailable (or empty PR_NUMBER), do not call ci_monitor.monitor; advance/synthesize the same phase transitions bash uses.

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-bash-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2956-2959
- **Concern**: FORKED_TARGET/merge=false CI short-circuit absent from open-pr resume. Scenario: Bash skips ci-merge (→postmerge) when MERGE!=true, DRAFT=true, or FORKED_TARGET=true. The plan’s open-pr branch always enters the CI loop with restored counters and does not restate these gates.
- **Proposed resolution**: Resume after a forked-target or merge=false session can enter merge polling/merge attempts that bash would bypass at ci-merge. After pr-create hydration, apply the same merge/draft/forked_target/repo_unavailable early-return gates as today’s fresh path before entering the loop.

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-bash-parity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:30-31
- **Concern**: manifest_status==DONE alone can force merged classification. Scenario: Merged is chosen when manifest status is DONE even if PHASE is still ci-initial/ci-merge and gh would show OPEN. Bash routes on PHASE, not manifest alone.
- **Proposed resolution**: Premature manifest DONE (partial postmerge, manual edit) routes to run_postmerge_phase while CI is still active in bash. Restrict manifest DONE to merged only when PHASE is postmerge/done or PR_CLOSED/MERGE_RESULT already agree; otherwise ignore manifest for routing.

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-bash-parity
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:13-19
- **Concern**: Three-value FSM replaces bash PHASE dispatch while claiming phase-resume parity. Scenario: Approach says resume matches bash session-wide counters and phase-resume logic, but bash’s normative driver is the PHASE while-loop (scripts/ship-pr.sh:3308-3327), not fresh/open-pr/merged inference.
- **Proposed resolution**: The proposed abstraction is a different FSM; parity gaps above are structural, not accidental omissions in tests. Either narrow the parity claim to counter persistence + skip checks/postbump only, or add PHASE-aware entry inside _resume_plan (minimum change: read PHASE/CI_PASSED, keep counter restore).

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-bash-parity
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: plan.txt:78
- **Concern**: “ITERATION=49 + cap 50 ⇒ immediate stall” not aligned with bash cap order. Scenario: Bash enforces iteration>=50 inside ci-decide during ci-wait (scripts/ci-decide.sh:123-125); ITERATION=49 still gets one decide cycle. Python also pre-checks iteration>=50 at loop head (python/ship.py:537) before monitor.
- **Proposed resolution**: Resume with ITERATION=49 may stall one cycle earlier/later than bash depending on whether the outer loop or decide fires first; the planned test name overstates “immediate.” Align the test with bash: assert stall on the first monitor/decide call only after ITERATION reaches 50, or document intentional double-gate behavior.

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-bash-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:48-54; scripts/ship-pr.sh:2714-2721,3275-3303
- **Concern**: The three-state resume plan drops bash's explicit ship-pr-rrr-phase14 rebase-continuation handback.. Scenario: After a non-bump conflict handback, bash validates PHASE plus ship-pr-rrr-after-phase14.flag, calls run_rebase_rebump, consumes the flag, and increments counters before returning to CI. The proposed open-pr resume skips straight through pr-create/CI and can miss the required rebase continuation.
- **Proposed resolution**: Handle RESUME_PHASE=ship-pr-rrr-phase14 before the coarse fresh/open-pr/merged decision, or refuse that resume shape until Python supports it. Keep the change narrow and add only this parity test.

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-bash-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:53-54,76-78; python/ship.py:532-538; scripts/ci-decide.sh:104-123
- **Concern**: The plan preserves Python's outer iteration-cap check, but bash evaluates pass/already_merged before safety caps.. Scenario: With ITERATION=50 and CI already pass or merged, bash returns merge/already_merged because ci-decide checks those before ITERATION >= 50. Python stalls before polling. The plan's ITERATION=49 + cap 50 immediate-stall assertion is also off by one.
- **Proposed resolution**: Move/remove the run_ship pre-monitor cap and rely on ci_monitor.decide's bash-order cap for non-merge actions. Update the planned tests to cover pass-at-cap plus non-merge cap exhaustion.

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-bash-parity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:29-32,73,93-95; scripts/ship-pr.sh:2946-2959,3308-3323; python/pr.py:41-42
- **Concern**: The gh-skip branch still requires valid PR identity before any non-fresh resume, unlike bash's repo_unavailable phase path.. Scenario: For state PHASE=ci-initial, REPO_UNAVAILABLE=true, and empty PR_NUMBER, bash advances ci-initial to ci-merge to postmerge without gh. The proposed _resume_plan returns fresh and reruns checks/postbump/pr-create. If PR_NUMBER is present, the open-pr path can call ensure_pr, which returns number=0 for repo_unavailable and can wipe the hydrated identity.
- **Proposed resolution**: For repo_unavailable, honor bash's state PHASE skip semantics before PR identity, or exclude repo_unavailable from open-pr resume and preserve the current local-only flow. Never let ensure_pr overwrite a restored PR identity with 0.

### FINDING_22:
- **Reviewer(s)**: Cursor-dyn-state-file-premises
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_ship.py (planned acceptance matrix)
- **Concern**: Cap-exhaustion resume test specifies ITERATION=49 with cap 50 for immediate stall. Scenario: Loop guard is `if iteration >= SHIP_MERGE_LOOP_MAX_ITERATIONS` (python/ship.py:537-538). With cap 50, iteration 49 still runs one more `ci_monitor.monitor` pass before incrementing to 50 and stalling; only iteration>=50 stalls at loop entry. Seeding/resuming with ITERATION=49 therefore allows an extra monitor cycle, not immediate stall.
- **Proposed resolution**: Session-wide cap test should seed/resume with ITERATION=50 (expect stall before monitor), or rename the case to assert one final monitor then stall when ITERATION=49.

### FINDING_23:
- **Reviewer(s)**: Codex-dyn-state-file-premises
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:29-31; python/ship.py:365-386
- **Concern**: Finding 1: Merged resume can bypass the branch/head mismatch gate the plan assigns to fresh. Scenario: A stale state file with PR_CLOSED=true, PHASE=postmerge, MERGE_RESULT in the post-merge set, or a done manifest can classify as merged before any BRANCH_NAME or gh head_ref match check, so postmerge can run for the wrong current branch
- **Proposed resolution**: Apply the same current-branch match before accepting merged resume from state, manifest, or gh head_ref; if it mismatches, return fresh

### FINDING_24:
- **Reviewer(s)**: Codex-dyn-state-file-premises
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:48-49; python/ship.py:657-660
- **Concern**: Finding 2: Merged resume omits the normal final ship-state done write. Scenario: The normal merge path calls run_postmerge_phase then writes PHASE=done, but the proposed merged branch returns run_postmerge_phase directly; a later invocation can keep seeing postmerge or merged state and rerun postmerge
- **Proposed resolution**: Mirror the normal path in the merged resume branch: capture the postmerge result, call _write_ship_state(working, phase="done") on success, then return the ShipResult

### FINDING_25:
- **Reviewer(s)**: Codex-dyn-state-file-premises
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:18,51,73; python/pr.py:41-42; python/ship.py:509-517,522-530
- **Concern**: Finding 3: Repo-unavailable open-pr resume can erase hydrated PR_NUMBER and PR_URL. Scenario: The plan allows open-pr resume when gh is skipped for repo_unavailable and state BRANCH_NAME matches, but ensure_pr returns number=0 and url="" in that mode; the current assignment pattern would overwrite hydrated resume identity with None and empty URL before the done state/result
- **Proposed resolution**: Preserve resume.pr_number and resume.pr_url when ensure_pr returns an empty local-only result, or skip ensure_pr for repo_unavailable open-pr resume after the required gates and write the hydrated done state

### OOS_1:
- **Description**: Three new `monitor()` outcome tests are unrelated to ship resume/counter restore. Scenario: The SIMPLE plan’s core fix is `run_ship()` resume + terminal counter threading; `test_ship.py` already stubs `ci_monitor.monitor` for handback/cap cases. Adding monitor bail/transient/local-unfixable coverage expands scope (~60+ lines) without exercising new resume code.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/test_ci_monitor.py:80-84
- **Phase**: design

### OOS_2:
- **Description**: Monitor-level outcome tests unrelated to resume/counter hardening. Scenario: Extra ~30–60 LOC and maintenance surface without protecting the stated acceptance criteria
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/test_ci_monitor.py:planned-additions
- **Phase**: design
