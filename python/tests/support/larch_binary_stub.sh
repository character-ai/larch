#!/usr/bin/env bash
# Verified-binary front end for the Python test suite's bootstrap double.
#
# `scripts/larch.sh` probes `--version` and `bootstrap self-check` before every
# dispatch. Answering both here in Bash keeps a Python interpreter start off
# two of the three spawns per command, which matters because the suite makes
# many Rust-owned command calls.
#
# Every other command delegates to `rust_agent_stub.py`, which owns the
# behavior. CI prefers the real workspace build over this double; see
# `conftest._verified_bootstrap_binary`.
set -euo pipefail

stub_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

die() {
    printf '%s\n' "larch-binary-stub: $1" >&2
    exit 2
}

plugin_root="${CLAUDE_PLUGIN_ROOT:-}"
[ -n "$plugin_root" ] || die "CLAUDE_PLUGIN_ROOT is required"

read_version() {
    local manifest="$plugin_root/.claude-plugin/plugin.json"
    [ -f "$manifest" ] || die "plugin manifest not found: $manifest"
    awk 'match($0, /"version"[[:space:]]*:[[:space:]]*"[^"]+"/) {
        row = substr($0, RSTART, RLENGTH)
        sub(/.*"version"[[:space:]]*:[[:space:]]*"/, "", row)
        sub(/".*/, "", row)
        print row
        exit
    }' "$manifest"
}

read_target() {
    case "$(uname -s):$(uname -m)" in
        Darwin:arm64 | Darwin:aarch64) printf 'aarch64-apple-darwin\n' ;;
        Darwin:x86_64 | Darwin:amd64) printf 'x86_64-apple-darwin\n' ;;
        Linux:arm64 | Linux:aarch64) printf 'aarch64-unknown-linux-gnu\n' ;;
        Linux:x86_64 | Linux:amd64) printf 'x86_64-unknown-linux-gnu\n' ;;
        *) die "unsupported host for the bootstrap double" ;;
    esac
}

case "${1:-}" in
    --version)
        printf 'larch %s\n' "$(read_version)"
        exit 0
        ;;
    bootstrap)
        [ "${2:-}" = self-check ] || die "unsupported bootstrap subcommand: ${2:-}"
        printf '{"schema_version":1,"version":"%s","target":"%s"}\n' "$(read_version)" "$(read_target)"
        exit 0
        ;;
esac

exec python3 "$stub_dir/rust_agent_stub.py" "$@"
