### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: .claude/skills/audit-runs/SKILL.md
- **Concern**: Bugs-backlog nudge is wired only after the scan loop, so the default since-last-audit zero-PR exit never reaches it. Scenario: On the common default cadence (empty positional or explicit since last audit), resolve-prs returns ERROR=no new PRs merged after prior audit and the skill exits cleanly before scanning; the plan places bugs-backlog-nudge after scan-run completes, so acceptance criterion 2 (/audit-runs prints the nudge when backlog exceeds threshold) fails whenever the operator has no new merged PRs but more than 25 closed [BUG] issues since the marker
- **Proposed resolution**: Run bugs-backlog-nudge after preflight succeeds (repo and root are known) and before resolve-prs fail-fast handling, or add an explicit zero-PR clean-exit branch that runs the same nudge fence before exit; keep the nudge chat-only and non-fatal on gh failure in both placements



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/learn-from-bugs/SKILL.md
- **Concern**: Marker commit failure cleanup remains prose-only despite round-1 commit-wiring acceptance. Scenario: After write-state succeeds, a first-run marker file is untracked; if the isolated git commit --only fence fails, the skill only says delete or restore with no concrete command, so an implementer may run git checkout (no-op on untracked) or skip cleanup and leave a live uncommitted marker that local read_state and a same-session retry can treat as durable even though acceptance requires a committed marker
- **Proposed resolution**: Add a post-commit failure fence: rm -f the marker path when the file was newly created, otherwise git checkout HEAD -- <marker-relpath>; stop before Step 5 after reporting commit failure



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: .claude/skills/audit-runs/SKILL.md:346-365
- **Concern**: Revised Orchestrator Flow still omits bugs-backlog-nudge after the scan loop. Scenario: The accepted round-1 placement fix adds a prose subsection but leaves the ASCII orchestrator flow as scan-run → compute-counters with no nudge step, so implementers following that flow can ship without ever calling audit-runs bugs-backlog-nudge
- **Proposed resolution**: Insert bugs-backlog-nudge in Revised Orchestrator Flow immediately after the scan-run loop and before compute-counters, matching the plan’s stated execution order



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/audit_runs.py
- **Concern**: Local closedAt filtering lacks a guard for missing or unparseable timestamps. Scenario: The plan requires closedAt > run_date but does not say to skip rows with absent or invalid closedAt; comparing None or raw strings can raise and turn the advisory into a hard CLI failure despite audit-runs treating it as non-fatal
- **Proposed resolution**: Skip rows whose closedAt fails parse_iso (or equivalent); only count rows with closedAt strictly after run_date in UTC



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/learn-from-bugs/SKILL.md
- **Concern**: Marker commit-failure rollback is required but not mechanically specified. Scenario: Edge cases require delete or restore on commit failure so uncommitted marker state is not observable, yet no fence names the recovery action, so a failed commit can leave a dirty marker file that the next read-state or nudge could treat as live
- **Proposed resolution**: Add an explicit rollback fence after failed git commit --only (for example git restore --staged --worktree on the marker path when tracked, otherwise rm the new file) before stopping before Step 5



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: .claude/skills/audit-runs/SKILL.md:46-54
- **Concern**: Early resolve-prs exits still skip bugs-backlog-nudge (FINDING_4 incomplete). Scenario: The plan places the nudge only after the scan-run loop. Default `since last audit` (empty positional) fail-fasts at resolve-prs when `ERROR=no new PRs merged after prior audit` (python/larch/issue/audit_runs.py:515-516; skill lines 54 and 203), so the run never reaches Scanning or the nudge. The same gap hits other resolve-prs ERROR exits before scan. The advisory never fires on a common periodic cadence even though the host skill ran.
- **Proposed resolution**: Run `audit-runs bugs-backlog-nudge` once after `PREFLIGHT_OK=true`, before resolve-prs fail-fast and independent of PR_COUNT. Keep chat-only and non-fatal (`|| true`). On resolve-prs ERROR paths that exit early (including zero new PRs), print any nudge stdout, then fail-fast as today. Optionally note this in the Revised Orchestrator Flow.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/learn-from-bugs/SKILL.md
- **Concern**: Failed marker commit cleanup is still not mechanical (FINDING_2 partial). Scenario: The plan stops before Step 5 and says delete or restore the marker on commit failure, but gives no concrete rollback. If `write-state` succeeds and `git commit --only` fails, an uncommitted marker can remain on disk. `read_state` will treat it as the last run, suppressing or skewing the backlog nudge relative to the acceptance criterion that only committed markers count.
- **Proposed resolution**: After non-zero commit, rollback explicitly: `git restore --staged --worktree -- <config.LEARN_FROM_BUGS_STATE_RELPATH>` when the path was tracked, else `rm -f` the resolved path; then stop before Step 5. ## Findings ### 1. Early resolve-prs exits still skip bugs-backlog-nudge (correctness, major) Round 1 FINDING_4 added the nudge after the scan loop, but the default audit path often stops earlier. With an empty positional (`since last audit`), `resolve-prs` returns `ERROR=...` when no new PRs merged (`audit_runs.py` around lines 515–516). The skill fail-fasts on non-empty `ERROR` (lines 54–55) and explicitly allows a clean exit without filing (line 203). The nudge subsection sits after Scanning, so those runs never invoke it. That leaves a hole in the feature goal: an advisory on an operator cadence that frequently produces “nothing to audit.” **Suggested revision:** Run `bugs-backlog-nudge` once after successful preflight, before resolve-prs branching. Keep it chat-only and non-fatal. On early ERROR exits, emit any nudge line first, then fail-fast as today. ### 2. Failed marker commit cleanup still underspecified (risk-integration, minor) Round 1 FINDING_2 fixed isolated `--only` commit wiring, but rollback remains hand-wavy (“delete or restore”). A failed commit after a successful `write-state` can leave a fresh marker on disk. Readers use filesystem state, not “committed only,” so the nudge can behave as if a durable run happened when it did not. **Suggested revision:** Pin rollback in the skill: `git restore --staged --worktree -- <path>` when tracked, otherwise `rm -f` the resolved marker path, then stop before Step 5.



### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py:251-260
- **Concern**: Accepted marker-frontier fix still captures the nudge time boundary after the issue scan. Scenario: `learn-from-bugs prepare` lists closed bugs at T1, report drafting finishes at T2, and a [BUG] closes between T1 and T2. The marker records T2, and `audit-runs bugs-backlog-nudge` excludes `closedAt <= T2`, so that unscanned bug is not counted toward the backlog.
- **Proposed resolution**: Have prepare emit a scan-start boundary captured immediately before `gh issue list`; store it in the marker while keeping `run_date` as the success timestamp, and make the nudge compare against that scan boundary with a fallback for older markers.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: .claude/skills/audit-runs/SKILL.md:86-235
- **Concern**: [SCOPE-REDUCTION] bugs-backlog-nudge is still wired only after the scan-run loop, so default early exits never invoke it. Scenario: Round 1 moved the hook to after scanning, but `resolve-prs` still fail-fast exits before any scan on common paths such as implicit `since last audit` with zero new PRs (`no new PRs merged after prior audit`) and missing prior audit-report. Those runs never reach compute-counters, so the advisory never prints and acceptance criterion "/audit-runs prints the nudge when the backlog exceeds the threshold" fails on the default cadence.
- **Proposed resolution**: Run the nudge once immediately after successful preflight (repo and root are already known; no scan NDJSON required), before `resolve-prs`, with the same chat-only non-fatal semantics. Keep the CLI unchanged; only move the skill hook earlier. ### 1. correctness — `.claude/skills/audit-runs/SKILL.md:86-235` The plan places `bugs-backlog-nudge` after the scan loop and before `compute-counters`. That only runs when `resolve-prs` returns a non-empty PR list and the scan loop completes. The default audit invocation is empty positional → `since last audit`. When no PRs merged since the prior audit, `resolve_prs_main` returns an error and the skill exits before scanning: if not nums: return _kv_error(f"no new PRs merged after prior audit (last PR: #{last_pr}, skill={args.skill})") The skill documents the same early exit: Always file an audit report after the scan, EXCEPT when the scope is `since last audit` (including an empty/omitted positional normalized to that form per **Verbal-Description Resolution**) and the query yields zero new PRs (exit cleanly without filing). The nudge does not need scan artifacts. The plan already says it only needs `--repo` and `--root`. Running it after preflight covers every operator touchpoint, including zero-PR exits, with less coupling than post-scan placement.



### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py:261-266
- **Concern**: Explicit learn-from-bugs searches still bypass the shared bug title predicate. Scenario: The stated acceptance requires selection through the shared predicate, but an explicit search can mine non-[BUG] issues and then commit a marker as if bug mining ran, which can suppress future audit-runs nudges
- **Proposed resolution**: Revise the plan so run_prepare always filters selected digests through bug_title_match after gh returns rows; let explicit search only change the upstream query, keep HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED from raw_issues, and add explicit-search coverage



