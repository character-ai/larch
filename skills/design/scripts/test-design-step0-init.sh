#!/usr/bin/env bash
# test-design-step0-init.sh — feature-description materialization on already-planned route
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
INIT="$ROOT/skills/design/scripts/design-step0-init.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

D=$(mktemp -d "${TMPDIR:-/tmp}/test-step0-init.XXXXXX")
trap 'rm -rf "$D"' EXIT
FAKE="$D/fake-plugin"
mkdir -p "$FAKE/scripts" "$FAKE/skills/design/scripts"
ln -sf "$ROOT/scripts/read-result-env.sh" "$FAKE/scripts/read-result-env.sh"
ln -sf "$ROOT/scripts/lib-quiet.sh" "$FAKE/scripts/lib-quiet.sh"
ln -sf "$ROOT/python" "$FAKE/python"

printf 'ROUTE=already-planned\n' >"$D/.design-route-result.env"
printf 'replace-path feature body\n' >"$D/issue-body.txt"
cat >"$D/session-env.sh" <<EOF
export DESIGN_TMPDIR="$D"
export ISSUE_NUMBER=42
export ISSUE_TITLE='[DESIGNED] Replace planned'
export SESSION_ID=test-session
export CLAUDE_PLUGIN_ROOT="$FAKE"
EOF

set +e
env CLAUDE_PLUGIN_ROOT="$FAKE" bash "$INIT" --session-env-path "$D/session-env.sh" --claude-pid 1 --plugin-root "$FAKE" 2>"$D/stderr.log"
init_rc=$?
set -e
[[ "$init_rc" -eq 0 ]] || fail "step0 init rc=$init_rc stderr=$(cat "$D/stderr.log")"
grep -Fq 'replace-path feature body' "$D/feature-description.txt" || fail 'already-planned route must populate feature-description.txt'
grep -Fq '[DESIGNED] Replace planned' "$D/feature-description.txt" || fail 'feature-description must include issue title prefix'
pass 'Step 0 init writes feature-description.txt on already-planned route'

pass 'design-step0-init.sh checks passed'
