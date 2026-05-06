# run-checks.sh

Purpose: run the project-local `/relevant-checks` validation pipeline for files modified on the current branch.

Primary callers: `.claude/skills/relevant-checks/SKILL.md` invokes this private helper through the Bash tool.

Invariants: keep `set -uo pipefail` without `-e` so pre-commit and agent-lint exit codes can be captured explicitly; collect the union of branch diff, staged changes, unstaged changes, and untracked files; filter deleted paths before invoking `pre-commit run --files`; run full-repo `agent-lint --pedantic` when available after changed-file checks pass, for deletions-only changes, and when there are no modified files; exit 2 with an `ERROR:` line if zero validation phases actually ran.

Makefile wiring: none; this is a dev-only local skill helper.

Test harness: run `.claude/skills/relevant-checks/scripts/run-checks.sh` through `/relevant-checks` after edits, and use direct shell invocations for zero-phase edge cases when needed.

Edit in sync: update this contract and `.claude/skills/relevant-checks/SKILL.md` whenever phase counting, observable banners, exit paths, warning/error text, or changed-file detection behavior changes.
