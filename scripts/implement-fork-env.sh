#!/usr/bin/env bash
# implement-fork-env.sh — Bootstrap /implement --forked repo context.
#
# Allocates a bootstrap tmpdir (via mktemp), writes
# `caller-env.sh` containing only `REPO=<fork-owner>/<fork-repo>` into
# it, and emits the bootstrap path plus fork metadata on stdout. This
# ordering decouples fork bootstrap from `session-setup.sh`'s tmpdir
# (which does not exist yet at this point in /implement Step 0) so the
# helper can run as the single permitted pre-Step-0 exception.
#
# Stdout (KEY=value lines, one per line):
#   BOOTSTRAP_TMPDIR=<absolute-path>
#   CALLER_ENV_PATH=<absolute-path>
#   FORK_REPO=<owner/repo>
#   UPSTREAM_REPO=<owner/repo>
#   FORK_OWNER=<owner>
#   FORKED_TARGET=true
#   SLACK_ENABLED=false
#
# Exit codes:
#   0  Success
#   1  No `upstream` remote configured (fork prereq)
#   2  Argument or remote-URL parse failure
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HELPER_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"

usage() {
    echo "Usage: implement-fork-env.sh [--tmpdir PATH]" >&2
    echo "  --tmpdir PATH (optional): use this directory for caller-env.sh." >&2
    echo "                            When omitted, allocates via mktemp." >&2
}

TMPDIR_ARG=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tmpdir) TMPDIR_ARG="${2:?--tmpdir requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

if ! git remote get-url upstream >/dev/null 2>&1; then
    echo "--forked requires the clone to be configured for the fork-PR workflow:" >&2
    echo "  origin -> your fork; upstream -> the upstream repo." >&2
    echo "See docs/installation-and-setup.md (Fork CI dry-runs) for the full" >&2
    echo "remote-add walkthrough; the minimum is:" >&2
    echo "  git remote add upstream <https-or-ssh-url-of-upstream-repo>" >&2
    exit 1
fi

FORK_REPO=$("$HELPER_ROOT/scripts/github-remote-repo.sh" origin)
UPSTREAM_REPO=$("$HELPER_ROOT/scripts/github-remote-repo.sh" upstream)
FORK_OWNER="${FORK_REPO%%/*}"

if [[ -n "$TMPDIR_ARG" ]]; then
    BOOTSTRAP_TMPDIR="$TMPDIR_ARG"
    mkdir -p "$BOOTSTRAP_TMPDIR"
else
    BOOTSTRAP_TMPDIR="$(mktemp -d "${TMPDIR:-/tmp}/larch-fork-bootstrap.XXXXXX")"
fi

caller_env_tmp="$BOOTSTRAP_TMPDIR/caller-env.sh.tmp"
{
    printf 'REPO=%s\n' "$FORK_REPO"
} > "$caller_env_tmp"
mv -f "$caller_env_tmp" "$BOOTSTRAP_TMPDIR/caller-env.sh"

printf 'BOOTSTRAP_TMPDIR=%s\n' "$BOOTSTRAP_TMPDIR"
printf 'CALLER_ENV_PATH=%s/caller-env.sh\n' "$BOOTSTRAP_TMPDIR"
printf 'FORK_REPO=%s\n' "$FORK_REPO"
printf 'UPSTREAM_REPO=%s\n' "$UPSTREAM_REPO"
printf 'FORK_OWNER=%s\n' "$FORK_OWNER"
printf 'FORKED_TARGET=true\n'
printf 'SLACK_ENABLED=false\n'
