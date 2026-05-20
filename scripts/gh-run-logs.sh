#!/usr/bin/env bash
# gh-run-logs.sh — View failed CI run logs (last 100 lines).
#
# Wraps `gh run view --log-failed` for diagnostic purposes.
# Output is capped at the last 100 lines to prevent arbitrarily large logs
# from flooding the orchestrator context. A pointer to the full log artifact
# is prepended on stdout so callers can fetch more lines when needed.
#
# Usage:
#   gh-run-logs.sh --run-id <id> --repo <owner/repo>
#
# Arguments:
#   --run-id — GitHub Actions workflow run ID
#   --repo   — Owner/repo identifier (e.g., "myorg/myrepo")
#
# Exit codes:
#   0 — success (logs printed to stdout)
#   1 — usage/argument error or gh command failure
#   3 — run still in progress (transient; logs not yet available)

set -euo pipefail

usage() { echo "Usage: gh-run-logs.sh --run-id <id> --repo <owner/repo>" >&2; }

RUN_ID=""
REPO=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
        --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
    esac
done

if [[ -z "$RUN_ID" ]] || [[ -z "$REPO" ]]; then
    echo "ERROR: --run-id and --repo are required" >&2
    usage; exit 1
fi

printf -- '--- CI log (run %s, repo %s) — last 100 lines shown. Full log: https://github.com/%s/actions/runs/%s ---\n' \
    "$RUN_ID" "$REPO" "$REPO" "$RUN_ID"
gh_rc=0
log_file=$(mktemp "${TMPDIR:-/tmp}/gh-run-logs.XXXXXX")
cleanup() {
    rm -f "$log_file"
}
trap cleanup EXIT

gh run view "$RUN_ID" --repo "$REPO" --log-failed >"$log_file" 2>&1 || gh_rc=$?
if [ "$gh_rc" -ne 0 ] && grep -Fq "is still in progress; logs will be available" "$log_file"; then
    tail -100 "$log_file"
    exit 3
fi
tail -100 "$log_file"
[ "$gh_rc" -eq 0 ] || exit 1
