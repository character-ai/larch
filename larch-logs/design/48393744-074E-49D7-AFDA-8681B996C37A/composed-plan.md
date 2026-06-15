## Plan

## Approach

Add `/bug` as a small stateful orchestrator skill that investigates a user-described bug inline and files a detailed GitHub issue via `/issue`.

1. Treat all `$ARGUMENTS` as the bug description. No flags. Abort on empty or whitespace-only input.
2. Create `$BUG_TMPDIR` under canonical `/tmp`: `BUG_TMPDIR=$(mktemp -d "${TMPDIR:-/tmp}/claude-bug-XXXXXX")`. All scratch artifacts and the sentinel file live under this path (required by the `deny-edit-write.sh` Write hook which restricts prompt-side writes to `/tmp`).
3. Investigate inline using `Read`, `Grep`, `Glob`, and safe `Bash` discovery. No repo edits, no external agents.
4. Compose `$BUG_TMPDIR/bug-issue-body.md` with ten headings: Summary, Original report, Reproduction scenario, Expected behavior, Observed behavior, Root cause analysis, Evidence, Affected files, Suggested fix(es), Open questions. If root cause is uncertain, say so with evidence and next steps.
5. Derive a descriptive title from the bug report (not from the body file). Invoke `/issue` via the Skill tool with `--body-file "$BUG_TMPDIR/bug-issue-body.md" --sentinel-file "$BUG_TMPDIR/issue-completed.sentinel" "<descriptive-title>"`. Do not pass `--no-dedup`.
6. Parse `/issue` stdout for `ISSUES_CREATED`, `ISSUES_FAILED`, `ISSUES_DEDUPLICATED`, `ISSUE_1_URL` (created path), and `ISSUE_1_DUPLICATE_OF_URL` (deduplicated path). Run `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" verify skill-called --sentinel-file "$BUG_TMPDIR/issue-completed.sentinel"`. Treat created and deduplicated outcomes as success when `ISSUES_FAILED=0` and `VERIFIED=true`.
7. Remove `$BUG_TMPDIR` and report the issue URL (prefer `ISSUE_1_URL`, fall back to `ISSUE_1_DUPLICATE_OF_URL`).

## Files to modify/create

### NEW: skills/bug/SKILL.md

Public exported skill. Frontmatter:
- `name: bug`
- `description:` triggers on filing/reporting/root-causing a bug; answers WHAT/WHEN/KEYWORDS per Section V of skill-design-principles
- `argument-hint: "<bug description>"`
- `allowed-tools: Bash, Read, Grep, Glob, Write, Skill`
- Skill-scoped Write hook using `scripts/deny-edit-write.sh` (restricts prompt-side writes to canonical `/tmp`)

Body: anti-halt banner, no-flags contract (all args = bug description, no `--no-dedup` forwarded), 7 numbered steps matching the approach above, micro-reminder adjacent to the `/issue` Skill-tool call, compact 10-heading body template. Keep under 500 lines. Use Pattern B inline invocation text that satisfies `lint skill-invocations`.

### UPDATED: scripts/test-anti-halt-banners.sh

Add `skills/bug/SKILL.md` to `ORCHESTRATORS` (not `BANNER_ONLY_ORCHESTRATORS`). Rationale: `/bug` invokes `/issue` and continues afterward to parse stdout, verify sentinel, clean up, and report.

### UPDATED: skills/shared/subskill-invocation.md

Add `skills/bug/SKILL.md` to the orchestrator scope list. Required by `scripts/test-orchestrator-scope-sync.sh` lint that enforces exact sync between `ORCHESTRATORS` in `test-anti-halt-banners.sh` and the scope list in this doc.

## Edge cases

- Empty description: abort before creating tmpdir.
- Description starts with `--`: treat as prose, not a flag.
- Root cause uncertain: file with honest evidence and open questions rather than invented certainty.
- `/issue` deduplicates: success when sentinel verifies and `ISSUES_FAILED=0`; report `ISSUE_1_DUPLICATE_OF_URL`.
- `/issue` fails: surface failure, do not claim an issue was filed.
- Write hook denies non-`/tmp` writes: all Write paths stay under `$BUG_TMPDIR`.

## Failure modes

- **False root cause confidence**: mitigated by requiring concrete evidence under ## Evidence and hedging uncertain causal claims.
- **Silent child halt**: mitigated by anti-halt banner, micro-reminder, stdout parsing, and sentinel verification.
- **Wrong issue title (## Summary)**: mitigated by requiring explicit trailing positional title in the `/issue` invocation — do not rely on body-first-line title derivation.
- **Lint drift**: mitigated by syncing `scripts/test-anti-halt-banners.sh` with `skills/shared/subskill-invocation.md`.

## Testing strategy

```bash
python3 python/cli.py lint skill-invocations
bash scripts/test-anti-halt-banners.sh
bash scripts/test-orchestrator-scope-sync.sh
bash scripts/relevant-checks.sh
```

## Acceptance

Plan review: 1 round. Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements reviewed. Codex timed out (degraded panel). Zero findings applied. Three unimplemented suggestions noted: FINDING_1 (blocking — explicit title for /issue), FINDING_2 (important — dedup URL parse), FINDING_3 (blocking — BUG_TMPDIR under /tmp). All three incorporated into the plan above. Approved at Gate C.

diff_lines: 132
