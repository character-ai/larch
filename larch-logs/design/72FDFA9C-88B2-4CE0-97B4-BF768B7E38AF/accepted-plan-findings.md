### FINDING_1: Verification grep includes historical run logs
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Cursor-dyn-ref-inventory, Codex-dyn-ref-inventory
- **Severity**: important
- **Concern**: The proposed post-edit grep is repo-wide while expecting only `CHANGELOG.md` matches. Tracked historical artifacts under `larch-logs/**` already contain the removed harness names, so a literal verification run may fail even when live surfaces are clean or may push implementers into editing archived logs outside scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Narrow the grep to live surfaces being cleaned up, or add path exclusions such as :!larch-logs/**; keep archived run-log references untouched
  - From Cursor-Pragmatic: Scope the check, e.g. `git grep -nE 'test-report-tokens-recompute|test-rate-assertions' -- Makefile agent-lint.toml docs/linting.md skills/report-tokens CHANGELOG.md` and expect matches only in `CHANGELOG.md` (historical line ~2107 plus the new `### Removed` bullet), or add `':!larch-logs'`
  - From Cursor-dyn-ref-inventory, Codex-dyn-ref-inventory: Keep the deletion scope as-is, but revise the verification command or expected output to exclude `larch-logs/**` historical artifacts, for example `git grep ... -- . ':(exclude)larch-logs/**'`, and note that committed run logs may retain historical mentions.

