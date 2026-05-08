#!/usr/bin/env bash
# implement-fork-env.sh — Bootstrap /implement --forked repo context.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HELPER_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"

usage() {
    echo "Usage: implement-fork-env.sh --tmpdir PATH" >&2
}

TMPDIR_ARG=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tmpdir) TMPDIR_ARG="${2:?--tmpdir requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

if [[ -z "$TMPDIR_ARG" ]]; then
    echo "implement-fork-env.sh: --tmpdir required" >&2
    exit 2
fi

if ! git remote get-url upstream >/dev/null 2>&1; then
    echo "--forked requires the clone to be configured per /set-up-forked-open-source-repo: origin -> fork, upstream -> upstream" >&2
    exit 1
fi

FORK_REPO=$("$HELPER_ROOT/scripts/github-remote-repo.sh" origin)
UPSTREAM_REPO=$("$HELPER_ROOT/scripts/github-remote-repo.sh" upstream)
FORK_OWNER="${FORK_REPO%%/*}"

mkdir -p "$TMPDIR_ARG"
caller_env_tmp="$TMPDIR_ARG/caller-env.sh.tmp"
{
    printf 'REPO=%s\n' "$FORK_REPO"
} > "$caller_env_tmp"
mv -f "$caller_env_tmp" "$TMPDIR_ARG/caller-env.sh"

printf 'FORK_REPO=%s\n' "$FORK_REPO"
printf 'UPSTREAM_REPO=%s\n' "$UPSTREAM_REPO"
printf 'FORK_OWNER=%s\n' "$FORK_OWNER"
printf 'FORKED_TARGET=true\n'
printf 'SLACK_ENABLED=false\n'
