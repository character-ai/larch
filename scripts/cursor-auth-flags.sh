#!/usr/bin/env bash
# cursor-auth-flags.sh — Cursor auth preflight gate for runtime skill markdown
# templates.
#
# Historically this script printed `--api-key <CURSOR_API_KEY>` argv elements
# for the markdown blocks to splice into the `cursor agent` command line. That
# leaked the key into run-external-agent.sh `.meta` CMD_JSON, `ps` listings,
# and any captured command line (issue #3375). Cursor now authenticates via the
# CURSOR_API_KEY *environment variable* (see scripts/lib-cursor-auth.sh), which
# the orchestrator already exports and the `cursor agent` child inherits — so
# no `--api-key` argv element is needed and this script no longer prints one.
#
# It is retained as the Darwin-gated preflight GATE for the markdown templates
# that cannot conveniently `source` a library
# (skills/shared/voting-protocol.md, skills/shared/dialectic-protocol.md,
# skills/research/references/validation-phase.md): it runs the same
# cursor_auth_preflight the launchers use and exits non-zero with an actionable
# message when neither CURSOR_API_KEY nor a cursor keychain entry is available,
# so those blocks abort with the same exit code and stderr message as the
# launchers instead of letting `cursor agent` emit the cryptic
# `Security process exited with code: 45`.
#
# Output: nothing on stdout on any path. Exit 0 when the launch should proceed;
# exit 2 when the Darwin preflight fails; exit 1 on library source failure.
#
# Bash 3.2-safe: no Bash 4+ features.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

# Source the lib. Hard fail (exit 1) on missing/unsourceable library — the
# runtime markdown blocks rely on this gate firing correctly; degrading
# silently would reintroduce the keychain bug at exactly the call sites this
# script was added to fix.
# shellcheck source=scripts/lib-cursor-auth.sh
if ! . "$SCRIPT_DIR/lib-cursor-auth.sh" 2>/dev/null; then
    larch_err "cursor-auth-flags.sh: failed to source lib-cursor-auth.sh"
    exit 1
fi

# Run the same Darwin-gated preflight the launchers use (lib-cursor-auth.sh
# `cursor_auth_preflight`). The runtime markdown templates that invoke this
# script (skills/shared/voting-protocol.md, skills/shared/dialectic-protocol.md,
# skills/research/references/validation-phase.md) had no preflight gate before
# — operators hitting voting / dialectic / research-validation paths could see
# the cryptic `Security process exited with code: 45` while script-owned
# launches got the actionable preflight error. Fail closed via exit 2 so the
# markdown-template Bash blocks abort with the same actionable stderr message
# and consistent exit code as the launchers.
#
# Cursor authenticates from CURSOR_API_KEY in the environment (issue #3375);
# this script prints no argv flags and the markdown blocks pass no `--api-key`.
cursor_auth_preflight || exit 2
