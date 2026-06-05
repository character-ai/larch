### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:352-392
- **Concern**: Open-pr resume validates the git branch but persists ctx.branch_name/ctx.branch in _write_ship_state. Scenario: _resume_plan can admit open-pr when git.try_current_branch and gh/state agree while RunContext still carries a stale or empty --branch; pre-CI writes then set BRANCH_NAME to the wrong value and later ship/finalize guards or a bash re-entry can fail despite a valid resume classification
- **Proposed resolution**: After branch validation succeeds, hydrate working with the probed branch (or matched state BRANCH_NAME) before any open-pr/merged _write_ship_state; add a test that stubs git head feat with mismatched ctx.branch and asserts state writes feat

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:427-651
- **Concern**: Merged resume can trust stale state over reachable GitHub PR state. Scenario: If ship-pr-state.sh has PR_CLOSED=true, MERGE_RESULT=merged, or PHASE=postmerge from a prior or partial run but gh.pr_view now returns OPEN for the same PR/head, the proposed rule 8 still permits the merged path and run_postmerge_phase before the PR is actually merged.
- **Proposed resolution**: In _resume_plan, make successful gh.pr_view authoritative for normal repos: MERGED routes to merged, OPEN routes only to open-pr when the head matches, and CLOSED non-merged routes fresh; reserve state-only merged predicates for gh-skipped contexts.

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:211-327
- **Concern**: python/ship.py:494-507. Scenario: Open-pr resume plan does not require bypassing pr-create OOS helpers
- **Proposed resolution**: Re-entering `_materialize_manifest_oos`, the security-oos file gate, or `_oos_gate` on open-pr resume calls `_write_ship_state` with default-zero counter kwargs and can erase restored `ITERATION`/`REBASE_COUNT`/`FIX_ATTEMPTS`/`TRANSIENT_RETRIES` before CI despite the counter-preservation contract State `PHASE=ci-initial` with restored counters `10/3/4/1` and stale `oos-accepted-*.md` or `security-oos-observations.md` in tmpdir Route open-pr directly to hydrated `ensure_pr` → PR-only early exits → CI seeding; never invoke the three OOS helpers on non-fresh resumes; add a test that open-pr with restored counters plus leftover OOS artifacts still seeds monitor with restored values

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:75
- **Concern**: Resume-start list evaluates open-pr before merged with no tie-break when both predicates can match. Scenario: Under `repo_unavailable`/`forked`/`forked_target` (no `gh pr_view`), state `PHASE=postmerge` satisfies merged rule 8 while also matching open-pr rule 7 via branch match; open-pr-first routing re-enters CI instead of `run_postmerge_phase`
- **Proposed resolution**: Forked resume interrupted after writing `PHASE=postmerge` but before postmerge completes; next `run_ship()` classifies `open-pr` and skips postmerge Evaluate `done` and `merged` before `open-pr` in `_resume_plan`, or add explicit open-pr exclusions for `PHASE=postmerge`, `PR_CLOSED=true`, and `MERGE_RESULT` in `POST_MERGE_MERGE_RESULTS`; add a forked/state-only test for `PHASE=postmerge` → postmerge-only path

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:planned _resume_plan
- **Concern**: State merged predicates can override reachable GitHub PR state. Scenario: The plan says normal repos call gh.pr_view and closed-not-merged PRs are fresh, but rule 8 also accepts PR_CLOSED=true, postmerge phase, or persisted merge result as merged. If gh returns CLOSED without merged or OPEN while stale state has one of those flags, run_ship can run postmerge or return done for an unmerged PR.
- **Proposed resolution**: In _resume_plan, make reachable gh state authoritative: MERGED/merged_at may route to merged; OPEN may route only to open-pr; CLOSED without merged must route fresh regardless of state flags. Use state-only merged predicates only when gh is intentionally skipped, and add a focused closed-not-merged stale-state test.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:_resume_plan
- **Concern**: Positive resume-kind precedence among done/open-pr/merged is unspecified and the Resume starts narrative lists open-pr before done while run_ship dispatch lists done before open-pr. Scenario: PHASE=done after a merge=false PR-only exit still leaves an open PR; if _resume_plan classifies open-pr first, resume re-enters pr-create ensure/OOS (ensure_pr pushes and may edit the PR body) instead of the idempotent done short-circuit
- **Proposed resolution**: In _resume_plan, after blocked-rebase and failed-validation fresh fallback, evaluate done (PHASE=done + branch OK) before merged/open-pr; align the Resume starts section with that order; add a test: PHASE=done, open PR, merge=false → no checks/postbump/ensure/OOS/CI

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:416-443; python/ship.py:620-666
- **Concern**: Merged-resume rules let state-only PR_CLOSED/PHASE override a reachable unmerged PR. Scenario: With gh available, stale state containing PR_CLOSED=true or PHASE=postmerge for a PR that gh reports CLOSED but not MERGED would run postmerge and write done/flush logs as if merged, contradicting the closed-not-merged fresh fallback
- **Proposed resolution**: Treat gh.pr_view as ground truth when it succeeds: MERGED may resume postmerge, OPEN may resume open-pr, CLOSED unmerged must fall back fresh; use PR_CLOSED/MERGE_RESULT/PHASE only when gh is intentionally skipped or as supporting evidence after gh MERGED

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:509-515; python/pr.py:45-62
- **Concern**: Open-PR resume validates a branch but does not carry that branch into the context used by ensure_pr. Scenario: If the rerun argv/env has ctx.branch empty or stale while state BRANCH_NAME/current checkout/PR head are valid, _resume_plan can classify open-pr but pr.ensure_pr then looks up, pushes, or creates against the stale ctx.branch
- **Proposed resolution**: Hydrate working.branch and working.branch_name from the validated resume branch before OOS/ensure/CI, or require ctx.branch to equal the validated branch before classifying open-pr

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:38,158
- **Concern**: Merged-resume rule conflicts with the closed-not-merged fresh requirement and has no focused test. Scenario: Rule 8 allows stale state PR_CLOSED, MERGE_RESULT, or PHASE=postmerge to classify as merged; if gh.pr_view is reachable and reports CLOSED rather than MERGED, the resume path could run postmerge instead of falling back to fresh despite line 158
- **Proposed resolution**: Clarify _resume_plan so reachable gh CLOSED/non-MERGED is a hard fresh result before state/manifest merged predicates; add a narrow test for CLOSED plus stale merged-looking state flags

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-state-contracts
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:352-392; plan.txt open-pr/merged hydrate bullets
- **Concern**: Resume validation reads BRANCH_NAME from ship-pr-state.sh but open-pr/merged hydration only sets pr_number/pr_url (and merge fields); _write_ship_state still emits BRANCH_NAME from ctx.branch_name or ctx.branch. Scenario: Argv/env branch can disagree with the state file while git matches state; a resume write can persist the wrong BRANCH_NAME and break forked state-only open-pr checks or the next resume classification
- **Proposed resolution**: On non-fresh paths, hydrate working from persisted state keys used in validation (at least BRANCH_NAME; REPO/RUN_ID/MANIFEST_PATH/MERGE/DRAFT/FORKED_TARGET/REPO_UNAVAILABLE when present) before any _write_ship_state, or teach _write_ship_state to preserve keys not supplied

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-state-contracts
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:339-345, python/ship.py:365-392, skills/implement/SKILL.md:972-984, scripts/ship-pr.sh:3250-3264, skills/implement/scripts/stall-recovery-report.sh:589-603
- **Concern**: Planned state writes preserve counters but still replace the canonical ship-pr state with a shortened Python field set. Scenario: Any proposed terminal or resume `_write_ship_state` call can erase `STALL_TRACKING`, `STALL_STEP`, `BAIL_*`, `FAILED_RUN_ID`, `NO_LOGS_COMMIT`, `CI_FIX_REBASE_PENDING`, and other keys that the orchestrator seeds and bash validates; Step 18 can then misclassify Python stalls or a later bash fallback can reject the state
- **Proposed resolution**: Keep `_write_ship_state` as a narrow key-rewrite that preserves unknown existing keys, or expand it to the canonical key set and have `_write_terminal_state` write bash-compatible stall metadata and exit code

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-resume-routing
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:446-530 (planned _resume_plan)
- **Concern**: _resume_plan precedence is underspecified relative to the Resume starts list. Scenario: Merged/postmerge recovery can lose to open-pr: e.g. PHASE=postmerge or PR_CLOSED=true with gh still OPEN matches rule 7 before rule 8, skips postmerge, re-enters CI, and can report OK on the wrong lifecycle
- **Proposed resolution**: Document and implement fixed classification order in _resume_plan: blocked-rebase → done (PHASE=done) → merged (rule 8, including PHASE=postmerge/PR_CLOSED/MERGE_RESULT/gh MERGED) → open-pr (rule 7) → fresh; add a test with PHASE=postmerge + OPEN PR asserting start=merged

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-resume-routing
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:339-346,567-572,537-544 (planned)
- **Concern**: Terminal and cap stall paths still call _write_terminal_state without counter kwargs today; plan extends the helper but does not pin every early-return site. Scenario: Exit-3/6 or cap handback can persist ITERATION/REBASE_COUNT/FIX_ATTEMPTS/TRANSIENT_RETRIES=0 and the next run_ship seeds the loop at zero despite restored session counters
- **Proposed resolution**: In _write_terminal_state pass through optional counter kwargs; on every terminal/cap return (monitor non-OK, merge-loop cap after monitor, pre-rebase stall) compute post-monitor values (apply did_fixing/transient_rerun_attempted before write) and thread resume-restored baselines on open-pr

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-resume-routing
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:446-535; python/pr.py:41-77; skills/implement/SKILL.md:1009-1024; plan.txt:21,34,151-155
- **Concern**: Branch mismatch is routed to fresh even though the fresh path still uses ctx.branch while git commands run on the current HEAD. Scenario: If state or argv expects feature-a but checkout is feature-b, the proposed fresh fallback can run checks/postbump and ensure/create a PR using stale branch metadata while pushing or reading HEAD from the wrong checkout
- **Proposed resolution**: For state-present branch mismatch, detached HEAD, or ctx.branch/current mismatch, safe-refuse with STALLED/NEEDS_USER_INPUT instead of fresh; only use fresh after a verified current branch matches the requested branch

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-resume-routing
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:625-659; python/gh.py:204-215; plan.txt:36-38,83
- **Concern**: Normal-repo merged routing can let stale state override live gh OPEN evidence. Scenario: The plan says to call gh.pr_view for normal repos but then accepts PR_CLOSED=true, MERGE_RESULT, or PHASE=postmerge as merged predicates; a stale state file with PR_CLOSED=true while GitHub reports OPEN could skip CI/merge, run postmerge, and write done
- **Proposed resolution**: When gh is reachable, make gh state authoritative: route merged only on gh state MERGED; route OPEN with matching head to open-pr; treat CLOSED-not-MERGED or contradictions as fresh/refuse. Reserve state-only merged predicates for gh-skipped repo_unavailable/forked contexts

### OOS_1:
- **Description**: Merged/postmerge stall still writes PHASE=done on the main CI success path. Scenario: When run_postmerge_phase returns STALLED, the existing loop still calls _write_ship_state(phase="done"), which can contradict stall/finalize metadata (prior edge review); the plan only guards the new merged-resume branch
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/ship.py:658-659
- **Phase**: design
