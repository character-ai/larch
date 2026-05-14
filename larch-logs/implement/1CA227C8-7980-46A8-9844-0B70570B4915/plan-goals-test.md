## Goal
Fix zero-duration Step 8a timing row and missing vendor task averages in timing-report.md

## Implementation Plan
## Implementation Plan

Fix two timing-report quirks in larch-logs/implement/<RUN_ID>/timing-report.md.

### Quirk A — zero-duration Step 8a changelog row

File: scripts/implement-finalize.sh, function maybe_update_changelog()

Problem: postbump_mark("Step 8a — changelog") is called unconditionally at function entry (line 708), before any skip checks. When the function exits early (no changelog present, forked, no bump, no bullets), postbump_report_since_mark() is called immediately after, producing a zero-duration row.

Fix: Remove postbump_mark from the top. Move it to just before the actual write begins (after changelog_categories_to_markdown() confirms there are bullets to write). Remove postbump_report_since_mark() calls from all skip/early-exit paths that precede the mark. Keep postbump_report_since_mark() on all paths after the mark (success and failure writes).

Paths that no longer call postbump_report_since_mark:
- rc != 0 from check-changelog-present.sh (CHANGELOG absent)
- forked_target=true
- has_bump != true || bump_type = NONE (no bump commit)
- collect_changelog_bullets failure
- changelog_categories_to_markdown returns false (no bullets)

Paths that keep postbump_report_since_mark (these have the mark):
- write_changelog_entry rc=4 (multiple headings)
- write_changelog_entry rc!=0 (no anchor)
- mv failure
- git-amend-add failure
- git status dirty after amend
- success path

### Quirk B — missing Vendor Task Averages

Root cause: timing-ledger.sh record-vendor-task in launch-review.sh cannot find the timing ledger because LARCH_TIMING_LEDGER, IMPLEMENT_TMPDIR, SESSION_ENV_PATH, and REVIEW_TMPDIR are not in the environment when launch-review.sh runs as a subprocess.

Fix 1 — skills/review/SKILL.md Step 0 prose:
Add LARCH_TIMING_LEDGER to the rehydration list alongside LARCH_TOKEN_SESSION_ID and LARCH_CLAUDE_SOURCE_FILE. The session-env.sh file already contains LARCH_TIMING_LEDGER (written by write-session-env.sh --timing-ledger). After reading, export it. This makes it available to all subsequent Bash calls within the review subagent session, including dispatch-panel.sh calls.

Fix 2 — skills/review/scripts/dispatch-panel.sh:
After SESSION_ENV_PATH is parsed from --session-env-path CLI arg (around line 41), add "export SESSION_ENV_PATH". This exports it so launch-review.sh child processes can inherit it, enabling timing-ledger.sh to resolve the ledger via the SESSION_ENV_PATH fallback (dirname(SESSION_ENV_PATH)/timing-ledger.tsv).

### Verification
- /relevant-checks clean
- review timing-report.sh rendering for zero-row suppression

## Test plan
(no test plan section in plan-file)
