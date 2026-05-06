# fetch-issues.sh

Purpose: wrap the single `gh issue list` fetch used by `/analyze-issues`.

Primary callers: `run-analysis.sh`.

Invariants: perform no issue processing, do not filter duplicate titles or `[OOS]` issues, and write the GitHub JSON response to the requested output path. Keep shell scripts on `set -euo pipefail`.

Makefile wiring: none; this is a dev-only local skill helper.

Test harness: `bash -n .claude/skills/analyze-issues/scripts/*.sh`.

Edit in sync: update this contract if the fetched JSON fields, flags, or failure behavior change.
