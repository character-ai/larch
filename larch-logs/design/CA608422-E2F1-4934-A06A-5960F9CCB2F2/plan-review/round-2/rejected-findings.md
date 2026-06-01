### [Plan Review] FINDING_1

### FINDING_1: SECURITY.md Step 0 still documents Cursor-first omitted-`--coder` routing
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The Step 0 paragraph in `SECURITY.md` still describes a Cursor-first reversal and tells operators to pin `--coder=codex` for Codex. After #3337, Codex is the omitted-`--coder` default; unchanged text misstates product direction and instructs operators to pin the tool they already get by default.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the ~105 edit, replace Cursor-first reversal wording with Codex-first (#3337), update the availability arrow to Codex then Cursor then Claude, and invert pin guidance (e.g. operators who want Cursor pin --coder=cursor); keep explicit-pin fail-closed sentences


### [Plan Review] FINDING_4

### FINDING_4: `scripts/ship-pr.md` still Cursor-centric for tier order and `first-fixer-non-health`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan covers arrow-order edits but not first-fixer tier-name literals tied to cursor-first. After a codex-first flip, prose at line 72 (and related waterfall lines) can still name the Cursor CI-fix launcher / first tier (`cursor`) for `first-fixer-non-health`, disagreeing with codex-first base order and rotation-aware `first_tier` from `start_attempt % 3`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add explicit ship-pr.md edits: line 72 Codex (or first-tier) CI-fix launcher; line 118 first tier (codex) and codex→cursor→claude launch order; line 154 drop literal cursor tier (first tier of rotated list)
  - From Cursor-Pragmatic: Extend the `ship-pr.md` grep/sync pass to line 72 (and any similar first-fixer sentences): first-tier launcher wording, not Cursor-only


