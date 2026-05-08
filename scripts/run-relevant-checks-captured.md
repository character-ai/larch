# run-relevant-checks-captured.sh

Purpose: run the project-local `.claude/skills/relevant-checks/scripts/run-checks.sh` while capturing its verbose output to a private session log. The green path emits one bounded machine line so `/implement` and `/review` can validate without invoking the `/relevant-checks` Skill or reading the log.

Primary callers: `/implement` Step 3, Step 5.7, Step 6, Step 10, Step 12c, and `/review` Step 3e.

Inputs: `--site <label>` is a slash-free label matching `[A-Za-z0-9._-]+` with no leading dot and no `..`. `--tmpdir <path>` defaults to `${IMPLEMENT_TMPDIR:-${REVIEW_TMPDIR:-}}` and must be an absolute, existing, non-symlink session directory under `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions/` whose basename starts with `claude-implement-` or `claude-review-`.

Invariants:

- The helper uses `set -euo pipefail` and captures the underlying check exit code with an `if command; then rc=0; else rc=$?; fi` block.
- It resolves the repo root from `CLAUDE_PROJECT_DIR`, falling back to `git -C "$PWD" rev-parse --show-toplevel`.
- It creates `$tmpdir/relevant-checks/` with mode `700` under `umask 077`; log and redacted-log files are mode `600`.
- It allocates `<site>-<attempt>.log` with noclobber so concurrent attempts do not overwrite an existing log.
- On success, stdout is exactly one `RELEVANT_CHECKS_OK=true SITE=<site> COVERAGE=<value>` line, plus `WARN=agent-lint-missing` only when `run-checks.sh` reported the warning. Success never emits `LOG=`, `LOG_FILE=`, or a log path.
- On failure, stdout is a KEY=VALUE envelope containing `STATUS=fail`, `EXIT_CODE`, `LOG_FILE`, `LOG_BYTES`, `PHASE`, and `REDACTED_LOG_FILE`. The caller must read `REDACTED_LOG_FILE`, not the raw log.
- Redaction is fail-closed: if either redaction utility is unavailable or the pipeline fails, stdout is only `STATUS=fail FAILURE_REASON=redaction-failed` and no raw log path is emitted.

Coverage classification is best effort from the captured banners: `full` when both pre-commit and agent-lint banners appear, `changed-file-only` when only the changed-file phase is observed, and `post-check-only` when only the post-check phase is observed.

Harnesses: `scripts/test-relevant-checks-byte-budget.sh`, `scripts/test-relevant-checks-helper-failure.sh`, and `scripts/test-relevant-checks-validation.sh`.

Edit in sync: update this file, the three harnesses above, `skills/implement/SKILL.md`, `skills/review/SKILL.md`, and `docs/linting.md` when changing stdout grammar, tmpdir validation, coverage classification, redaction behavior, or log allocation.
