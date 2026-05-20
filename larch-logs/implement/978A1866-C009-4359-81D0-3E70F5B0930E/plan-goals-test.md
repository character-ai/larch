## Goal
Remove --no-fix-issues from /audit-runs; always file report, print to chat, ask 3-way question about findings

## Implementation Plan

Goal: Rework `/audit-runs` so it never auto-files bug issues at scan time; instead it always files the audit report, prints it to chat, and asks the user a 3-way question about what to do with findings. Remove the `--no-fix-issues` flag.

### Files to modify

**1. `.claude/skills/audit-runs/SKILL.md`**

- Usage line: remove `[--no-fix-issues]`
- `### Args`: remove the `--no-fix-issues` entry entirely
- `## Bug Issue Handling` → rename to `## Proposed bug-issue actions`; rewrite to:
  - At scan time, ONLY record findings as proposals (never auto-file or auto-augment)
  - `proposed_new_issues`: findings with no matching open issue (always present, possibly empty)
  - `proposed_augmentations`: findings matching an existing issue (always present, possibly empty)
  - Add subsection `### Post-report user prompt` describing:
    - Print full audit-report body verbatim to chat, then audit-report URL
    - Zero-findings short-circuit: if `proposed_new_issues` and `proposed_augmentations` both empty, state "No findings — no bug issues to file." and exit (do NOT ask the 3-way question)
    - Otherwise ask 3-way question: "(1) file/augment all, (2) discuss specific findings first, (3) skip filing." Act on user response:
      - file/augment all: file new via `/larch:issue` (dedup ON); post augmentation comments via `gh issue comment`
      - discuss first: wait for user direction; file/augment per-finding as user approves
      - skip filing: exit cleanly; audit report captures proposed findings for historical record
    - The audit report is NEVER edited after creation (chain-of-history property preserved)
- Frontmatter in audit report section:
  - Rename `proposed_issues_no_filing` → split into `proposed_new_issues: [...]` (always present) and `proposed_augmentations: [...]` (always present)
  - Drop `issues_filed_this_audit` and `issues_augmented_this_audit` (actions happen post-filing in chat, not at scan time)
- Add `## Output to chat` section near end:
  - Full audit-report body, verbatim
  - Audit-report URL
  - Zero-findings short-circuit OR the 3-way question
- Anti-patterns additions:
  - "Do NOT auto-file or auto-augment bug issues — only file the audit report itself. Bug-issue actions require explicit user direction in chat."
  - "Do NOT ask the 3-way question when there are zero findings — state and exit."

**2. `.claude/skills/audit-runs/scripts/test-audit-runs.sh`**

- Replace Test 13 (current `--no-fix-issues` behavior) with:
  - **Test 13a**: argparse rejects `--no-fix-issues` with usage error (flag removed)
  - **Test 13b**: scan-time always records in `proposed_new_issues` / `proposed_augmentations`; no auto-filing path
- Test 14 (existing title-exclusion test): keep unchanged
- Add **Test 15**: zero-findings short-circuit:
  - Assert that when `proposed_new_issues` and `proposed_augmentations` are both empty arrays, the chat output contains "No findings — no bug issues to file."
  - Assert that report body frontmatter has `proposed_new_issues: []` and `proposed_augmentations: []`
  - Assert 3-way question is NOT generated
- Update script header comment to reflect new test set

**3. `.claude/skills/audit-runs/scripts/test-audit-runs.md`**

- Update "What is tested" section: drop `--no-fix-issues` mention; add description of 13a, 13b, and 15
- No other changes needed

**4. `docs/linting.md`**

- Update the `make test-audit-runs` row description: drop `--no-fix-issues behavior`; add "always-proposal-only behavior" and "zero-findings short-circuit"

### Edge cases

- The frontmatter schema change only applies to newly-filed reports; existing audit-report issues remain valid
- The `## Output to chat` section is instructional (for the orchestrator); no scripted enforcement needed
- Test 15 is purely behavioral (no network calls); it tests the parsing/routing logic inline


## Test plan

Run `make test-audit-runs` — should pass with all new assertions green.
Run `/relevant-checks` — pre-commit + agent-lint on modified files.
