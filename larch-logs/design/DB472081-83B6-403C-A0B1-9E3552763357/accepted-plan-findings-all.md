### FINDING_1: Learn-from-bugs state capture can crash on empty selections or record the wrong frontier
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-dyn-State Nudge Correctness, Codex-dyn-State Nudge Correctness
- **Severity**: major
- **Concern**: `run_prepare` and the marker state contract do not consistently define `HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED`, so empty runs can crash, the Step 2 contract can omit required bindings, and the committed marker can understate the real scan frontier by using the wrong issue source or capturing metadata too late.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In run_prepare emit HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED=0 when ISSUES_SELECTED=0; document the same in Edge cases and test it
  - From Cursor-Innovation: Define HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED as 0 when no issues were selected otherwise max digest number and add a prepare test for the empty-selection path
  - From Cursor-Innovation: Extend Step 2 parse list with SEARCH STATE ISSUES_SELECTED and HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED and pass them verbatim into write-state
  - From Codex-Innovation: Capture RUN_DATE once when the /learn-from-bugs report finishes and pass it through to write-state; do not synthesize it inside the commit step.
  - From Codex-Innovation: Compute highest_closed_issue_number_scanned from the unfiltered closed-issue list before local bug filtering, and keep selected_count as a separate field.
  - From Cursor-dyn-State Nudge Correctness: Add HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED to the Step 2 parse list and retain it through Step 4
  - From Codex-dyn-State Nudge Correctness: Compute `HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED` from `raw_issues` before the bug-title filter, or rename the field if selection is the intended meaning.


### FINDING_2: Marker commit and post-Step-4 wiring are underspecified and can sweep unrelated staged files
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-State Nudge Correctness, Codex-dyn-State Nudge Correctness
- **Severity**: major
- **Concern**: The skill text does not precisely define the automatic marker write/commit sequence after Step 4, does not clearly require an isolated single-path commit, and still frames the workflow as report-only until Step 5, so implementers can skip the durable marker, mix in unrelated staged changes, or leave a live uncommitted state behind on failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin a one-line fence to python/cli.py git commit -m chore(larch-logs): update learn-from-bugs state --only <marker-relpath>; on non-zero exit stop before Step 5 as already specified
  - From Codex-Arch: Stage only the marker path first, then commit that file alone and fail if the add-commit pair does not land it.
  - From Cursor-Innovation: Rewrite the Contract intro to carve out the marker-only commit as required durable state while keeping Step 5 follow-ups approval-gated
  - From Cursor-Innovation: Pin marker commit to python/cli.py git commit -m ... --only <marker-relpath> or --pathspec-from-file rather than ad-hoc git
  - From Codex-Innovation: Use git commit --only for the marker path, or an equivalent isolate-then-commit flow that cannot include pre-staged unrelated files.
  - From Codex-Pragmatic: On commit failure, restore or delete the just-written marker before exiting so only committed state can be observed
  - From Cursor-Requirements: Extend Step 2 to parse and retain SEARCH, STATE, REPO, ISSUES_SELECTED, and HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED from prepare stdout; add a post-Step-4 fence that calls learn-from-bugs write-state with those values, then git-add/commit only config.LEARN_FROM_BUGS_STATE_RELPATH (pathspec-only, no -a); update Contract to allow this one marker commit; on write or commit failure stop before Step 5.
  - From Codex-Requirements: Update the contract text to carve out the mandatory marker commit after the report is written, and keep Step 5 as the gate for all other repository or GitHub mutations.
  - From Cursor-dyn-State Nudge Correctness: Add explicit post-Step-4 fences: learn-from-bugs write-state with KV bindings, then git commit --only on config.LEARN_FROM_BUGS_STATE_RELPATH, with stop-before-Step-5 on either failure
  - From Codex-dyn-State Nudge Correctness: Stage only the marker path before the commit, preferably by reusing python/cli.py git commit --pathspec-from-file <marker-list> or a single git add -- <marker> followed by a pathspec-limited commit.


### FINDING_4: Revised audit-runs flow still misplaces or omits bugs-backlog-nudge
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-State Nudge Correctness
- **Severity**: major
- **Concern**: The orchestrator flow still does not consistently place `bugs-backlog-nudge` in the normal audit path, so the advisory can be skipped on the default cadence or conflated with report composition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Insert python/cli.py audit-runs bugs-backlog-nudge after the scan loop and before compute-counters/report compose; note chat-only non-fatal failure handling
  - From Cursor-Innovation: Run bugs-backlog-nudge after preflight succeeds (and on zero-new-PR resolve exits before fail-fast) because it needs no scan NDJSON
  - From Cursor-dyn-State Nudge Correctness: Insert python/cli.py audit-runs bugs-backlog-nudge after the scan-run loop and before compute-counters, with a chat-only note that stdout must not enter report body/YAML/counters/NDJSON


### FINDING_5: Marker read/write paths need symlink and ancestor rejection
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The shared marker file can be redirected through symlinks on write or read, which can push the durable state outside the repo or make the nudge trust forged JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Reject symlinked path and ancestors before atomic_write, and set nofollow=True.
  - From Codex-Arch: Reject symlinked path and ancestors on read, and treat the marker as unusable.


### FINDING_1: Bugs backlog nudge is skipped on early exits
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The bugs-backlog nudge is only placed after the scan loop, so early `resolve-prs` exits—including the common zero-new-PR path—can bypass the advisory entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Run bugs-backlog-nudge after preflight succeeds (repo and root are known) and before resolve-prs fail-fast handling, or add an explicit zero-PR clean-exit branch that runs the same nudge fence before exit; keep the nudge chat-only and non-fatal on gh failure in both placements
  - From Cursor-Innovation: Insert bugs-backlog-nudge in Revised Orchestrator Flow immediately after the scan-run loop and before compute-counters, matching the plan’s stated execution order
  - From Cursor-Pragmatic: Run `audit-runs bugs-backlog-nudge` once after `PREFLIGHT_OK=true`, before resolve-prs fail-fast and independent of PR_COUNT. Keep chat-only and non-fatal (`|| true`). On resolve-prs ERROR paths that exit early (including zero new PRs), print any nudge stdout, then fail-fast as today. Optionally note this in the Revised Orchestrator Flow.


### FINDING_2: Marker commit rollback is still underspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The post-commit failure path for the durable marker is still prose-only, so a failed isolated commit can leave an uncommitted marker on disk that later reads may treat as durable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a post-commit failure fence: rm -f the marker path when the file was newly created, otherwise git checkout HEAD -- <marker-relpath>; stop before Step 5 after reporting commit failure
  - From Cursor-Innovation: Add an explicit rollback fence after failed git commit --only (for example git restore --staged --worktree on the marker path when tracked, otherwise rm the new file) before stopping before Step 5
  - From Cursor-Pragmatic: After non-zero commit, rollback explicitly: `git restore --staged --worktree -- <config.LEARN_FROM_BUGS_STATE_RELPATH>` when the path was tracked, else `rm -f` the resolved path; then stop before Step 5. ## Findings ### 1. Early resolve-prs exits still skip bugs-backlog-nudge (correctness, major) Round 1 FINDING_4 added the nudge after the scan loop, but the default audit path often stops earlier. With an empty positional (`since last audit`), `resolve-prs` returns `ERROR=...` when no new PRs merged (`audit_runs.py` around lines 515–516). The skill fail-fasts on non-empty `ERROR` (lines 54–55) and explicitly allows a clean exit without filing (line 203). The nudge subsection sits after Scanning, so those runs never invoke it. That leaves a hole in the feature goal: an advisory on an operator cadence that frequently produces “nothing to audit.” **Suggested revision:** Run `bugs-backlog-nudge` once after successful preflight, before resolve-prs branching. Keep it chat-only and non-fatal. On early ERROR exits, emit any nudge line first, then fail-fast as today. ### 2. Failed marker commit cleanup still underspecified (risk-integration, minor) Round 1 FINDING_2 fixed isolated `--only` commit wiring, but rollback remains hand-wavy (“delete or restore”). A failed commit after a successful `write-state` can leave a fresh marker on disk. Readers use filesystem state, not “committed only,” so the nudge can behave as if a durable run happened when it did not. **Suggested revision:** Pin rollback in the skill: `git restore --staged --worktree -- <path>` when tracked, otherwise `rm -f` the resolved marker path, then stop before Step 5.


### FINDING_4: The marker boundary is captured too late for the audit nudge
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The marker records the post-scan success time, so bugs closed after the scan starts but before the marker is written can be excluded from the backlog count even though they were never scanned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Have prepare emit a scan-start boundary captured immediately before `gh issue list`; store it in the marker while keeping `run_date` as the success timestamp, and make the nudge compare against that scan boundary with a fallback for older markers.


### FINDING_5: Explicit learn-from-bugs searches bypass the shared bug predicate
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Explicit searches can select non-[BUG] issues before the shared title predicate runs, which can make the durable marker reflect the wrong population and suppress later nudges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Revise the plan so run_prepare always filters selected digests through bug_title_match after gh returns rows; let explicit search only change the upstream query, keep HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED from raw_issues, and add explicit-search coverage


### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: .claude/skills/audit-runs/SKILL.md:86-235
- **Concern**: [SCOPE-REDUCTION] bugs-backlog-nudge is still wired only after the scan-run loop, so default early exits never invoke it. Scenario: Round 1 moved the hook to after scanning, but `resolve-prs` still fail-fast exits before any scan on common paths such as implicit `since last audit` with zero new PRs (`no new PRs merged after prior audit`) and missing prior audit-report. Those runs never reach compute-counters, so the advisory never prints and acceptance criterion "/audit-runs prints the nudge when the backlog exceeds the threshold" fails on the default cadence.
- **Proposed resolution**: Run the nudge once immediately after successful preflight (repo and root are already known; no scan NDJSON required), before `resolve-prs`, with the same chat-only non-fatal semantics. Keep the CLI unchanged; only move the skill hook earlier. ### 1. correctness — `.claude/skills/audit-runs/SKILL.md:86-235` The plan places `bugs-backlog-nudge` after the scan loop and before `compute-counters`. That only runs when `resolve-prs` returns a non-empty PR list and the scan loop completes. The default audit invocation is empty positional → `since last audit`. When no PRs merged since the prior audit, `resolve_prs_main` returns an error and the skill exits before scanning: if not nums: return _kv_error(f"no new PRs merged after prior audit (last PR: #{last_pr}, skill={args.skill})") The skill documents the same early exit: Always file an audit report after the scan, EXCEPT when the scope is `since last audit` (including an empty/omitted positional normalized to that form per **Verbal-Description Resolution**) and the query yields zero new PRs (exit cleanly without filing). The nudge does not need scan artifacts. The plan already says it only needs `--repo` and `--root`. Running it after preflight covers every operator touchpoint, including zero-PR exits, with less coupling than post-scan placement.


