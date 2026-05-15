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
#
# Exit codes:
#   0  Success
#   1  No `upstream` remote configured (fork prereq)
#   2  Argument or remote-URL parse failure
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
HELPER_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"

usage() {
    larch_err "Usage: implement-fork-env.sh [--tmpdir PATH]"
    larch_err "  --tmpdir PATH (optional): use this directory for caller-env.sh."
    larch_err "                            When omitted, allocates via mktemp."
}

TMPDIR_ARG=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tmpdir) TMPDIR_ARG="${2:?--tmpdir requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "Unknown option: $1"; usage; exit 2 ;;
    esac
done

if ! git remote get-url upstream >/dev/null 2>&1; then
    larch_err "--forked requires the clone to be configured for the fork-PR workflow:"
    larch_err "  origin -> your fork; upstream -> the upstream repo."
    larch_err "See docs/installation-and-setup.md (Fork CI dry-runs) for the full"
    larch_err "remote-add walkthrough; the minimum is:"
    larch_err "  git remote add upstream <https-or-ssh-url-of-upstream-repo>"
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

emit_kv BOOTSTRAP_TMPDIR "$BOOTSTRAP_TMPDIR"
emit_kv CALLER_ENV_PATH "$BOOTSTRAP_TMPDIR/caller-env.sh"
emit_kv FORK_REPO "$FORK_REPO"
emit_kv UPSTREAM_REPO "$UPSTREAM_REPO"
emit_kv FORK_OWNER "$FORK_OWNER"
emit_kv FORKED_TARGET true
