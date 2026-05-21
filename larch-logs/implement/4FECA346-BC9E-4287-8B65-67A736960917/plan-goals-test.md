## Goal
Remove the GO-marker convention and auto-pick from /issue and /fix-issue

## Implementation Plan

Goal: Remove the GO-marker convention and auto-pick from /issue and /fix-issue.

### 1. skills/issue/SKILL.md

- Line 3: Remove `--go` from the description field.
- Line 4: Remove `[--go]` from the argument-hint.
- Remove the `--go` flag entry in the flags section.
- Step 6: Remove the "Post-create GO comment" block (the `gh issue comment ... GO` invocation, go-stderr-$i.txt capture, stderr-redaction, and `ISSUE_<i>_GO_POSTED=true|false` emission).
- Step 6: Remove the single-mode duplicate + `--go` pre-flight block.
- Step 6: Remove the dry-run + `--go` interaction sentence from the `--dry-run` flag description.
- Step 6: Remove all `--go` references from duplicate-handling paths ("Do NOT post GO").
- Step 6/output: Remove `ISSUE_<i>_GO_POSTED` from the channel-discipline section (stdout) and from the Step 8 single-mode human summary (both GO-succeeded and GO-failed variants).
- Dependency Analysis section: Remove the entire "GO timing" paragraph.

### 2. skills/fix-issue/scripts/issue-lifecycle.sh

In `cmd_comment()`:
- Remove `--lock` parsing (`--lock) lock=true; shift ;;`).
- Remove `--lock-no-go) lock_no_go=true; shift ;;` and rename to `--lock) lock=true; shift ;;`.
- Remove the mutual-exclusion check.
- Remove the GO-delete code block (the `--lock: verify last comment is "GO"` block, lines ~120-160).
- Rename `--lock-no-go` label to `--lock` in the post-check comment and all references.
- Update usage string in the `larch_err "Usage: ..."` line.
- Update header comments at top of file.

### 3. skills/fix-issue/scripts/issue-lifecycle.md

- Update the command usage: remove `[--lock]` (old GO-delete) and rename `--lock-no-go` to `--lock`.
- Remove description of the GO-delete behavior.

### 4. skills/fix-issue/scripts/find-lock-issue.sh

- Remove `has_archival_prefix()` function.
- Arg parsing: After the while loop, if `ISSUE_ARG` is empty, emit error "Usage: find-lock-issue.sh <issue-number-or-url>" and exit 2.
- Remove the deprecated `--issue` flag handling block.
- Remove `lock_and_rename_then_emit` function (old GO-delete path using `--lock`).
- Rename `lock_no_go_and_rename_then_emit` → `lock_and_rename_then_emit`; update it to use `--lock` instead of `--lock-no-go`.
- In `lock_no_go_and_rename_then_emit_for_child` (umbrella child): rename to `lock_and_rename_then_emit_for_child` (or update in place) and change `--lock-no-go` to `--lock`.
- Update the `handle_umbrella` function call from `lock_no_go_and_rename_then_emit_for_child` to `lock_and_rename_then_emit_for_child`.
- Explicit-issue path (around line 870-913): Remove the GO-check conditional (`if [ "$TRIMMED" = "GO" ]`); always call `lock_and_rename_then_emit "$ISSUE_NUM" "$ISSUE_TITLE"`. Remove the comment about which lock mode to use.
- Remove the entire auto-pick section (lines 916-1069): ISSUES_JSONL query, SORTED jq sort, while loop with all filters.
- Update exit-code table in header comment: remove "1 — no eligible issues (auto-pick mode only)".
- Update header description: script is now explicit-target only.
- Update mentions of archival prefix, urgent prioritization, and auto-pick throughout comments.

### 5. skills/fix-issue/scripts/find-lock-issue.md

- Update description: explicit-target-only; no auto-pick.
- Update exit codes: remove exit 1 (auto-pick no candidate).
- Remove mentions of GO, auto-pick, urgency ordering, archival filter.

### 6. skills/fix-issue/SKILL.md

- Update description header: "scans for open issues (or targets a specific one)" → "processes the named issue".
- Update argument-hint: `[<number-or-url>]` → `<number-or-url>` (mandatory positional).
- Remove the `--issue <number-or-url>` deprecated flag entry (or change to refusal).
- Step 0 description of `find-lock-issue.sh`:
  - Remove mention of "eligibility scan" and "auto-pick" modes.
  - Remove Urgent-first ordering description.
  - Remove archival-title filter description.
  - Remove GO-comment requirement text.
  - Simplify lock acquisition: just "posts IN PROGRESS, post-checks for duplicate races".
  - Remove the "--lock when GO is present / --lock-no-go otherwise" choice text.
- Exit code 1 handling block: Remove (was auto-pick only).
- Known Limitations: Remove "Stale IN PROGRESS lock" sub-bullet about GO deletion mid-Step-0. Remove "archival title prefixes are auto-pick-only exclusions" known limitation. Update "Single-runner assumption" if it mentions auto-pick. Remove auto-pick-related text from umbrella limitations.
- Mindset section, candidates description, auto-pick section references: Remove all.

### 7. skills/fix-issue/scripts/test-find-lock-issue.sh

Remove auto-pick-only fixtures (these become unreachable):
- Fixture 6 (auto-pick, no eligible candidates)
- Fixture 7 (auto-pick + Urgent preference)
- Fixture 8 (auto-pick + oldest-first)
- Fixture 12 (auto-pick skips umbrella)
- Fixture 14 (auto-pick skips archival titles)
- Fixture 15 (auto-pick treats [ROUND-TRIP] as pickable)
- Fixture 17 (auto-pick + dirty tree)
- Fixture 20 (auto-pick skips [UMBRELLA] prefix)
- Fixture 21 (auto-pick no-GO path)
- Fixture 23 (auto-pick skips audit-report label)

Update remaining fixtures that use `make_comments_json GO`:
- Change `make_comments_json GO` to `make_comments_json ""` (or another non-special body) throughout explicit-target tests, since --lock no longer requires GO.
- Update descriptions/assertions that mention GO or lock-no-go.
- Fixture 22 (explicit-target no-GO path): Update description to "explicit-target uses --lock" and verify still passes.

Add new Fixture N: no-arg invocation → exit 2 with ERROR containing "Usage:".

Update test index comment at top of file.

### 8. skills/fix-issue/scripts/test-find-lock-issue.md

- Update to list the revised fixture set (removing auto-pick fixtures).
- Remove mentions of GO, auto-pick, archival filter, urgent preference.

### 9. README.md

- In the /fix-issue section: Remove "Scans open issues (GO-flagged)" or similar phrasing.
- Remove mentions of `--go` flag from /issue section.
- Remove any auto-pick documentation.

### 10. docs/workflow-lifecycle.md

- In /fix-issue description: Remove "with `GO` sentinel comment as last comment" from the eligibility criteria.
- Remove "auto-pick mode (no positional argument)" text and replace with "positional argument is mandatory".
- Remove "auto-pick scan keeps its GO-tail invariant unchanged" and related text.

### 11. docs/skills.md

- /fix-issue entry: Update to reflect mandatory argument, no GO requirement.
- /issue entry: Remove `--go` flag description.
- /umbrella entry: Remove `--go` reference.


## Test plan

After implementation:
- `make lint` and `agent-lint` pass.
- `make test-find-lock-issue` passes (run the regression harness).
- `grep -r "\bGO\b" skills/issue/SKILL.md skills/fix-issue/SKILL.md docs/workflow-lifecycle.md README.md` returns no user-facing GO references (outside CHANGELOG.md).
- `/fix-issue` (no arg) refusal: `find-lock-issue.sh` with no args exits 2 with usage error.
