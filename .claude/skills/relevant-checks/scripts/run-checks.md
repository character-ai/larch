# run-checks.sh

Purpose: run the project-local `/relevant-checks` validation pipeline for files modified on the current branch.

Primary callers: `.claude/skills/relevant-checks/SKILL.md` invokes this private helper through the Bash tool.

Invariants: keep `set -uo pipefail` without `-e` so pre-commit and agent-lint exit codes can be captured explicitly; preflight to exit 1 with a stdout line that begins with `ERROR: pre-commit not found` (the full literal carries an installation hint) when `pre-commit` is absent on `PATH`, and exit 1 with a stdout line that begins with `ERROR: not inside a git repository` when `git rev-parse --show-toplevel` fails; collect the union of branch diff, staged changes, unstaged changes, and untracked files; filter deleted paths before invoking `pre-commit run --files`; run full-repo `agent-lint --pedantic` when available after changed-file checks pass, for deletions-only changes, and when there are no modified files; exit 2 with an `ERROR:` line if zero validation phases actually ran.

Makefile wiring: `make test-run-checks` runs the automated regression harness for this dev-only local skill helper.

Test harness: `.claude/skills/relevant-checks/scripts/test-run-checks.sh` covers the zero-phase, agent-lint propagation, changed-file pre-commit, and preflight failure exit paths. Run it directly after edits, then run `make test-run-checks` to verify Makefile wiring.

Edit in sync: update this contract and `.claude/skills/relevant-checks/SKILL.md` whenever phase counting, observable banners, exit paths, warning/error text, or changed-file detection behavior changes.
