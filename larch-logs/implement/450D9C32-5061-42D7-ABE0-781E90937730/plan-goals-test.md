## Goal
Eliminate duplicate CI run per PR by removing the post-PR-create push from ship-pr.sh

## Implementation Plan

Goal: Eliminate the duplicate CI run triggered by ship-pr.sh's post-PR-create push by restructuring run_pr_create_phase.

### Files to change
- scripts/ship-pr.sh — run_pr_create_phase function
- skills/implement/SKILL.md — update Step 7a prose (~line 1680)
- docs/run-logs.md — add note to larch:final-summary section

### 1. scripts/ship-pr.sh — restructure run_pr_create_phase

**1a. Update `local` declarations (line 937)**
Remove `flush_run_id manifest_rc push_output` from the local vars list — they belong to the blocks being deleted. Keep `final_report_output`.

**1b. First `write-final-report.sh` call — BEFORE create-pr.sh**
Insert BEFORE the `create-pr.sh` invocation. Uses existing pattern (fail_file, rc, exit_stall 9b on failure). At this point PR_URL is not yet known; write-final-report.sh defaults missing PR_URL to "N/A". This writes final-summary.md to the tmpdir and upserts the larch:final-summary tracking-issue comment with placeholder PR.

**1c. Pre-PR `larch-log.sh commit` — AFTER 1b, BEFORE create-pr.sh**
Gated on `[ "${LARCH_NO_LOGS_COMMIT:-false}" != "true" ]`. Captures final-summary.md (and any other artifacts) into a commit that rides in Push #1. On failure: `record_failure pr-create "larch-log.sh commit (pre-pr-create)" "$rc" "$fail_file" Warnings` and continue (do NOT exit_stall). Resolve flush_run_id locally (not as a function-wide local).

**1d. create-pr.sh call (existing line 952) — unchanged**

**1e. Parse pr_number, pr_url, pr_status; state_set_many (existing lines 967-970) — unchanged**

**1f. Second `write-final-report.sh` call — AFTER state_set_many (AFTER create-pr.sh)**
Best-effort: on non-zero rc, `record_failure pr-create "write-final-report.sh post" "$rc" "$fail_file" Warnings` and continue (do NOT exit_stall). This updates larch:final-summary comment with live PR_URL via API, but does NOT commit the updated final-summary.md (so PR tree keeps "PR: N/A" per the trade-off).

**1g. Keep `pr_status=existing` body-update branch (lines 980-985) — unchanged**

**1h. Delete lines 990-1025** — the entire pr_number manifest update + larch-log.sh commit + git-push.sh block. The `flush_run_id` resolution (lines 986-989) is only used in this block; remove it too.

**1i. advance_phase ci-initial — unchanged**

### 2. skills/implement/SKILL.md — update Step 7a prose

In the paragraph at ~line 1680 containing:
  "ship-pr.sh then pushes the post-create log-refresh commit before CI wait begins so the remote PR tip includes that summary."

Replace that sentence with:
  "ship-pr.sh writes `final-summary.md` with placeholder PR fields and folds it into the pre-PR larch-log commit so `create-pr.sh`'s push includes it on the remote PR tip. After PR creation, `write-final-report.sh` is re-run to update the tracking-issue `larch:final-summary` comment with the live PR URL via API only — no second commit, no second push."

### 3. docs/run-logs.md — larch:final-summary section

After the existing content ("Content: final run status (STALL_TRACKING value), PR URL, and log directory path."), add a sentence:
  "The committed `final-summary.md` in the PR tree may carry placeholder `PR: N/A`; the tracking-issue comment is the canonical live source for the PR URL."

### Edge cases / verification
- `LARCH_NO_LOGS_COMMIT=true`: pre-PR larch-log.sh commit is skipped; PR tree has no chore(larch-logs) commit for this phase.
- The second write-final-report.sh failure must not stall: the PR was already created; a tracking-issue comment update failure is recoverable.
- The `pr_status=existing` branch still runs after the second write-final-report.sh call.
- No callers read `pr_number` from a committed manifest (confirmed by issue author grep).
- Acceptance: `make lint` passes, test harnesses pass, no lint regressions.

### Testing strategy
Run `make lint` and `make test-harnesses` before committing. Verify no variable references to `flush_run_id`, `manifest_rc`, or `push_output` remain in the surviving function body.

## Test plan
(no test plan section in plan-file)
