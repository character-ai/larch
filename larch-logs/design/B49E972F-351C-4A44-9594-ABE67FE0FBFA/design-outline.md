## Proposed Design Outline

### Goals
- Drop n-gram duplication score for `--run-id` flag docs from score 42-48 (8 occurrences, 8 files) to near-zero.
- Drop n-gram duplication score for session-setup parse prose (~5 occurrences in 4 files).
- No behavior change; anti-halt/NEVER/continuation blocks unchanged.

### Non-goals
- Don't create any `MANDATORY — READ ENTIRE FILE` loads for the new shared files.
- Don't touch `design/SKILL.md` session-setup (complex launcher machinery).
- Don't touch compaction-resilience duplication (#5788).

### Approach sketch
- Create `skills/shared/run-id-flag.md` as the normative one-line `--run-id` description.
- In each of 7 SKILL.md files, replace the full flag doc with a short cited anchor pointing to the shared file.
- In `skills/block-issue/SKILL.md`, shorten the inline `--run-id` mention to the short form.
- Create `skills/shared/session-setup-output.md` listing the standard session-setup output keys with a one-sentence semantic note each.
- In `skills/research/SKILL.md` `### 0a`, replace the verbose key list with a compact form that cites the shared file.

### Surfaces in scope
- `skills/shared/` (2 new files: `run-id-flag.md`, `session-setup-output.md`)
- `skills/report-tokens/SKILL.md`
- `skills/set-up-forked-open-source-repo/SKILL.md`
- `skills/issue/SKILL.md`
- `skills/research/SKILL.md`
- `skills/upgrade-larch/SKILL.md`
- `skills/alias/SKILL.md`
- `skills/cleanup/SKILL.md`
- `skills/block-issue/SKILL.md`

### Open questions
- Should `skills/review/SKILL.md` Step 0 prose also reference the shared session-setup file? It's more complex (adds token session fields, timing ledger). Low risk to leave as-is.
