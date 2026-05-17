# run-relevant-checks-captured.sh

Purpose: run the project-local `.claude/skills/relevant-checks/scripts/run-checks.sh` while capturing its verbose output to a private session log. The green path emits one bounded machine line so `/implement` and `/review` can validate without invoking the `/relevant-checks` Skill or reading the log.

Primary callers: `/implement` Step 3, Step 5 accepted-fix loop, Step 6, Step 10, Step 12c, and `/review` Step 3e.

Inputs: `--site <label>` is a slash-free label matching `[A-Za-z0-9._-]+` with no leading dot and no `..`. `--tmpdir <path>` defaults to `${IMPLEMENT_TMPDIR:-${REVIEW_TMPDIR:-}}` and must be an absolute, existing, non-symlink session directory whose basename starts with `claude-implement-` or `claude-review-`. Accepted parent locations: (a) any descendant of `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions/` (canonical larch session root), or (b) a DIRECT child of `/tmp` or `/private/tmp` (the fallback root `session-setup.sh` uses when the cache root is unwritable; macOS resolves `/tmp` to `/private/tmp`). Nested paths under `/tmp` like `/tmp/foo/claude-implement-bar` are rejected — only direct `/tmp` children matching the basename grammar are accepted, because `session-setup.sh` only ever creates fallback session dirs as direct `/tmp` children.

Invariants:

- The helper uses `set -euo pipefail` and captures the underlying check exit code with an `if command; then rc=0; else rc=$?; fi` block.
- It resolves the repo root from `CLAUDE_PROJECT_DIR`, falling back to `git -C "$PWD" rev-parse --show-toplevel`.
- After tmpdir validation, `--site step3` and `--site step6` mark `Step 3 — checks first pass` and `Step 6 — checks second pass` respectively through `scripts/token-ledger.sh` and `scripts/timing-ledger.sh`, using the canonical session tmpdir as `IMPLEMENT_TMPDIR`. These audit marks are best-effort and do not change the checks result. The `step5-review-fixes` site is intentionally not marked here because Step 5 is marked by the parent `/implement` Step 5 preamble before `scripts/run-step5-review.sh` dispatches `review-and-fix.sh`.
- It creates `$tmpdir/relevant-checks/` with mode `700` under `umask 077`; log and redacted-log files are mode `600`. After `mkdir -p`, the helper rejects a pre-existing symlink at the log dir with `STATUS=fail FAILURE_REASON=log-dir-symlink-rejected`.
- It allocates `<site>-<attempt>.log` with noclobber. The allocation loop distinguishes two failure modes: a noclobber collision (file exists at this attempt index) bumps the counter and retries, while any other create failure (read-only mount, quota, ENOSPC) emits `STATUS=fail FAILURE_REASON=log-allocation` and exits 1. Attempts cap at 100 to prevent unbounded retry loops.
- On success, stdout is exactly one `RELEVANT_CHECKS_OK=true SITE=<site> COVERAGE=<value>` line, plus `WARN=agent-lint-missing` only when `run-checks.sh` reported the warning. Success never emits `LOG=`, `LOG_FILE=`, or a log path.
- On a checks failure (the wrapped `run-checks.sh` exited non-zero), stdout is a KEY=VALUE envelope containing `STATUS=fail`, `EXIT_CODE`, `LOG_FILE`, `LOG_BYTES`, `PHASE`, and `REDACTED_LOG_FILE`. The caller must read `REDACTED_LOG_FILE`, not the raw log.
- On a structural failure (validation, repo-root-unresolved, missing check script, log-dir issues, log-allocation, redaction-failed), stdout is a shorter envelope containing `STATUS=fail` and `FAILURE_REASON=<token>` ONLY — no `LOG_FILE` / `REDACTED_LOG_FILE` fields. Callers branch on `FAILURE_REASON` first; only when it is absent should they read `REDACTED_LOG_FILE`. The full `FAILURE_REASON` enum is: `site-validation`, `tmpdir-validation`, `repo-root-unresolved`, `missing-check-script`, `log-dir-create-failed`, `log-dir-symlink-rejected`, `log-dir-chmod-failed`, `log-file-chmod-failed`, `log-allocation`, `log-allocation-attempt-cap`, `redaction-failed`.
- Redaction is fail-closed: if either redaction utility is unavailable or the pipeline fails, stdout is only `STATUS=fail FAILURE_REASON=redaction-failed` and no raw log path is emitted.

Coverage classification is best effort from the captured banners: `full` when both pre-commit and agent-lint banners appear, `changed-file-only` when only the changed-file phase is observed, and `post-check-only` when only the post-check phase is observed.

Harnesses: `scripts/test-relevant-checks-byte-budget.sh`, `scripts/test-relevant-checks-helper-failure.sh`, and `scripts/test-relevant-checks-validation.sh`.

Edit in sync: update this file, the three harnesses above, `skills/implement/SKILL.md`, `skills/review/SKILL.md`, and `docs/linting.md` when changing stdout grammar, tmpdir validation, coverage classification, redaction behavior, or log allocation.
