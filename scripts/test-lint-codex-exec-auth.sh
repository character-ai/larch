#!/usr/bin/env bash
# test-lint-codex-exec-auth.sh — regression harness for lint-codex-exec-auth.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LINT="$REPO_ROOT/scripts/lint-codex-exec-auth.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-lint-codex-exec-auth.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0

reset_tree() {
    find "$TMPROOT" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    mkdir -p "$TMPROOT/scripts" "$TMPROOT/skills/foo"
}

write_file() {
    local path="$1"
    shift
    mkdir -p "$(dirname "$path")"
    printf '%s\n' "$@" >"$path"
}

run_lint() {
    set +e
    bash "$LINT" --root "$TMPROOT" 2>"$1"
    local rc=$?
    set -e
    printf '%s\n' "$rc"
}

stderr_file="$(mktemp)"
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -eq 0 ]]; then echo "PASS clean tree"; PASS=$((PASS+1)); else echo "FAIL clean tree"; FAIL=$((FAIL+1)); fi

reset_tree
write_file "$TMPROOT/scripts/bad.sh" '#!/bin/bash' 'codex exec --full-auto -C . hi'
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -ne 0 ]]; then echo "PASS unwired shell fails"; PASS=$((PASS+1)); else echo "FAIL unwired shell fails"; FAIL=$((FAIL+1)); fi

reset_tree
write_file "$TMPROOT/scripts/launch-codex-exec.sh" '#!/bin/bash' 'codex exec --full-auto -C . hi'
chmod +x "$TMPROOT/scripts/launch-codex-exec.sh"
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -eq 0 ]]; then echo "PASS allowlisted basename"; PASS=$((PASS+1)); else echo "FAIL allowlisted basename"; FAIL=$((FAIL+1)); fi

reset_tree
write_file "$TMPROOT/scripts/pragma.sh" 'codex exec --full-auto -C . hi # lint-codex-exec-auth: ok fixture'
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -eq 0 ]]; then echo "PASS pragma suppression"; PASS=$((PASS+1)); else echo "FAIL pragma suppression"; FAIL=$((FAIL+1)); fi

reset_tree
write_file "$TMPROOT/scripts/embedded-pragma.sh" 'printf "%s\n" "# lint-codex-exec-auth: ok fixture"; codex exec --full-auto -C . hi'
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -ne 0 ]]; then echo "PASS embedded pragma does not suppress"; PASS=$((PASS+1)); else echo "FAIL embedded pragma does not suppress"; FAIL=$((FAIL+1)); fi

reset_tree
write_file "$TMPROOT/scripts/mixed-auth.sh" '#!/bin/bash' '/repo/scripts/launch-codex-exec.sh --output /tmp/out --timeout 60 --prompt ok' 'codex exec --full-auto -C . hi'
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -ne 0 ]]; then echo "PASS mixed helper plus raw exec fails"; PASS=$((PASS+1)); else echo "FAIL mixed helper plus raw exec fails"; FAIL=$((FAIL+1)); fi

reset_tree
write_file "$TMPROOT/scripts/comment-only.sh" '#!/bin/bash' '# codex exec --full-auto -C . hi'
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -eq 0 ]]; then echo "PASS shell comments ignored"; PASS=$((PASS+1)); else echo "FAIL shell comments ignored"; FAIL=$((FAIL+1)); fi

reset_tree
write_file "$TMPROOT/scripts/continued.sh" '#!/bin/bash' "codex \\" '  exec --full-auto -C . hi'
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -ne 0 ]]; then echo "PASS shell continuation fails"; PASS=$((PASS+1)); else echo "FAIL shell continuation fails"; FAIL=$((FAIL+1)); fi

reset_tree
write_file "$TMPROOT/scripts/env-value.sh" '#!/bin/bash' 'B=codex exec --full-auto -C . hi'
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -ne 0 ]]; then echo "PASS env value codex fails"; PASS=$((PASS+1)); else echo "FAIL env value codex fails"; FAIL=$((FAIL+1)); fi

reset_tree
write_file "$TMPROOT/scripts/env-value-chain.sh" '#!/bin/bash' 'A=1 B=codex exec --full-auto -C . hi'
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -ne 0 ]]; then echo "PASS chained env value codex fails"; PASS=$((PASS+1)); else echo "FAIL chained env value codex fails"; FAIL=$((FAIL+1)); fi

reset_tree
write_file "$TMPROOT/scripts/env-prefix.sh" '#!/bin/bash' 'CODEX_HOME=/tmp/codex codex exec --full-auto -C . hi'
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -ne 0 ]]; then echo "PASS env prefix raw codex fails"; PASS=$((PASS+1)); else echo "FAIL env prefix raw codex fails"; FAIL=$((FAIL+1)); fi

reset_tree
write_file "$TMPROOT/scripts/env-prefix-multi.sh" '#!/bin/bash' 'CODEX_HOME=/tmp/codex OTHER=1 codex exec --full-auto -C . hi'
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -ne 0 ]]; then echo "PASS multi env prefix raw codex fails"; PASS=$((PASS+1)); else echo "FAIL multi env prefix raw codex fails"; FAIL=$((FAIL+1)); fi

reset_tree
write_file "$TMPROOT/scripts/negotiation-pragma.sh" '#!/bin/bash' "CODEX_HOME=\"\$codex_home\" codex exec --full-auto -C \"\$workspace\" -c \"projects.\\\"\$workspace\\\".trust_level=\\\"trusted\\\"\" --output-last-message \"\$output\" --json -- \"\$prompt\" # lint-codex-exec-auth: ok auth prepared by external_prepare_codex_auth"
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -eq 0 ]]; then echo "PASS negotiation pragma suppression"; PASS=$((PASS+1)); else echo "FAIL negotiation pragma suppression"; FAIL=$((FAIL+1)); fi

reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" '```bash' "codex \\" '  exec --full-auto -C . hi' '```'
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -ne 0 ]]; then echo "PASS markdown continuation fails"; PASS=$((PASS+1)); else echo "FAIL markdown continuation fails"; FAIL=$((FAIL+1)); fi

reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" '```bash' 'codex exec --full-auto -C . hi' '```'
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -ne 0 ]]; then echo "PASS one-line markdown fence fails"; PASS=$((PASS+1)); else echo "FAIL one-line markdown fence fails"; FAIL=$((FAIL+1)); fi

reset_tree
mkdir -p "$TMPROOT/docs" "$TMPROOT/hooks"
write_file "$TMPROOT/docs/out-of-scope.md" '```bash' 'codex exec --full-auto -C . hi' '```'
write_file "$TMPROOT/hooks/out-of-scope.sh" '#!/bin/bash' 'codex exec --full-auto -C . hi'
rc="$(run_lint "$stderr_file")"
if [[ "$rc" -eq 0 ]]; then echo "PASS out-of-scope paths ignored"; PASS=$((PASS+1)); else echo "FAIL out-of-scope paths ignored"; FAIL=$((FAIL+1)); fi

set +e
bash "$LINT" --root /no/such 2>"$stderr_file"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then echo "PASS invalid --root"; PASS=$((PASS+1)); else echo "FAIL invalid --root"; FAIL=$((FAIL+1)); fi

echo "Results: $PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]]
