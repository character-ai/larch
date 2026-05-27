# relevant-checks.sh

Purpose: run the project-local relevant-checks validation pipeline for files modified on the current branch (pre-commit scoped to changed files, direct relevant Make targets, contains-pin verification, then full-repo `agent-lint` when available).

Primary callers: `scripts/run-relevant-checks-captured.sh` invokes this script from the consumer repo root after validating the session tmpdir.

Invariants: keep `set -uo pipefail` without `-e` so pre-commit, direct relevant Make targets, contains-pin verification, and agent-lint exit codes can be captured explicitly; preflight to exit 1 with a stdout line that begins with `ERROR: pre-commit not found` (the full literal carries an installation hint) when `pre-commit` is absent on `PATH`, and exit 1 with a stdout line that begins with `ERROR: not inside a git repository` when `git rev-parse --show-toplevel` fails; collect the union of branch diff, staged changes, unstaged changes, and untracked files; filter via `[ -f "$f" ]` to existing regular files (drops deleted paths, directories, and other non-regular paths) before invoking `pre-commit run --files`; run `test-design-structure` as a direct relevant target when `skills/design/SKILL.md` or `skills/design/references/*.md` changes; do not run `npm ci` or other implicit Node installs (see `docs/linting.md`); run `scripts/check-contains-pins.sh --changed-files <tmpfile>` when the verifier exists, or print a warning when it is missing; run full-repo `agent-lint --pedantic` when available after changed-file checks pass, when `files[]` is empty but `MODIFIED_FILES` is non-empty (every path was rejected by the regular-file filter — typically deletions, but also directories or other non-regular paths), and when there are no modified files; exit 2 with an `ERROR:` line if zero validation phases actually ran.

Makefile wiring: `make test-relevant-checks` runs the automated regression harness `scripts/test-relevant-checks.sh`.

Test harness: `scripts/test-relevant-checks.sh` covers the zero-phase, agent-lint propagation, changed-file pre-commit, direct-target routing, contains-pin phase, and preflight failure exit paths. Run it directly after edits, then run `make test-relevant-checks` to verify Makefile wiring.

Edit in sync: update this contract and `docs/linting.md` whenever phase counting, observable banners, exit paths, warning/error text, or changed-file detection behavior changes.
