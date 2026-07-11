#!/usr/bin/env bash
# shellcheck disable=SC2016 # single-quoted strings are intentional source literals.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
WRAPPER="$SCRIPT_DIR/step-8-ci-fixer.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/larch-ci-fixer-test.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

contains() {
  command grep -Fq -- "$2" "$1" || { printf 'missing %s in %s\n' "$2" "$1" >&2; exit 1; }
}
not_contains() {
  if ( command grep -Fq -- "$2" "$1" ); then printf 'unexpected %s in %s\n' "$2" "$1" >&2; exit 1; fi
}

# Shared Git-backed fixture for --start route-handoff parsing.
# --start runs git -C "$REPO_ROOT" rev-parse HEAD before reading the handoff.
setup_route_fixture() {
  local name=$1
  local fixture="$TMP/$name"
  local checkout="$fixture/checkout"
  local impl="$fixture/impl"
  mkdir -p "$checkout" "$impl" "$TMP/plugin/python"
  (
    cd "$checkout"
    git init >/dev/null
    git config user.email 'ci-fixer-test@example.com'
    git config user.name 'ci-fixer-test'
    printf 'seed\n' >README
    git add README
    git commit -m 'seed' >/dev/null
  )
  printf 'REPO_ROOT=%s\n' "$checkout" >"$impl/session-env.sh"
  printf 'REPO=owner/repo\nPR_NUMBER=42\n' >"$impl/ship-pr-state.sh"
  FIXTURE_IMPL=$impl
}

run_start() {
  local out_file=$1
  set +e
  IMPLEMENT_TMPDIR="$FIXTURE_IMPL" CLAUDE_PLUGIN_ROOT="$TMP/plugin" \
    bash "$WRAPPER" --start >"$out_file" 2>&1
  local rc=$?
  set -e
  [ "$rc" -eq 0 ]
}

bash -n "$WRAPPER"
contains "$WRAPPER" 'python/cli.py" bgjob start'
not_contains "$WRAPPER" 'bgjob wait'
contains "$WRAPPER" 'ci fixer-lane'
contains "$WRAPPER" '--merge-result-env "$MERGE_ENV"'
contains "$WRAPPER" '--bgjob-result-env "$MERGE_ENV"'
not_contains "$WRAPPER" 'distilled-failure.md'
not_contains "$WRAPPER" 'gh run'
contains "$REPO_ROOT/skills/implement/SKILL.md" 'step-8-ci-fixer.sh'
not_contains "$REPO_ROOT/skills/implement/scripts/step-8-ship.sh" 'step-8-ci-fixer.sh'
not_contains "$REPO_ROOT/python/larch/implement/ship.py" 'step-8-ci-fixer.sh'

mkdir -p "$TMP/impl" "$TMP/plugin/python"
set +e
OUT=$(IMPLEMENT_TMPDIR="$TMP/impl" CLAUDE_PLUGIN_ROOT="$TMP/plugin" bash "$WRAPPER" --start 2>&1)
RC=$?
set -e
[ "$RC" -eq 0 ]
printf '%s\n' "$OUT" | command grep -Fq 'RESULT=operator-bail'
printf '%s\n' "$OUT" | command grep -Fq 'REASON=missing-repo-root'

mkdir -p "$TMP/unsafe-impl"
ln -s "$TMP" "$TMP/unsafe-impl/ci-fixer"
set +e
OUT=$(IMPLEMENT_TMPDIR="$TMP/unsafe-impl" CLAUDE_PLUGIN_ROOT="$TMP/plugin" bash "$WRAPPER" --start 2>&1)
RC=$?
set -e
[ "$RC" -eq 0 ]
printf '%s\n' "$OUT" | command grep -Fq 'REASON=unsafe-handoff-dir'

# Lowercase ledger_* keys must be ignored so uppercase routing fields still parse.
# Invalid CI_FAILURE_SCOPE stops after route parsing (before tier/bgjob).
setup_route_fixture lowercase-ledger
cat >"$FIXTURE_IMPL/.ship-route-exit-handoff.env" <<'EOF'
NEEDS_USER_REASON=first-fixer-non-health
CI_FAILURE_SCOPE=bogus
FAILED_RUN_ID=29145966394
ledger_ready=true
ledger_site=ship-pr
ledger_trigger=ci-failure
ledger_step=8
ledger_phase=ship
ledger_dispatcher=ship
ledger_exit_code=0
ledger_failure_detail_log=
EOF
run_start "$TMP/lowercase-ledger.out"
contains "$TMP/lowercase-ledger.out" 'REASON=unknown-ci-failure-scope'
not_contains "$TMP/lowercase-ledger.out" 'REASON=invalid-route-handoff'

# Duplicate uppercase keys still fail closed.
setup_route_fixture duplicate-uppercase
cat >"$FIXTURE_IMPL/.ship-route-exit-handoff.env" <<'EOF'
NEEDS_USER_REASON=first-fixer-non-health
CI_FAILURE_SCOPE=bogus
FAILED_RUN_ID=29145966394
NEEDS_USER_REASON=duplicate
EOF
run_start "$TMP/duplicate-uppercase.out"
contains "$TMP/duplicate-uppercase.out" 'REASON=invalid-route-handoff'

# Control characters in an uppercase-key value still fail closed.
setup_route_fixture control-char-value
printf 'NEEDS_USER_REASON=first-fixer-non-health\nCI_FAILURE_SCOPE=bogus\nFAILED_RUN_ID=29145966394\nDETAIL=bad\x01value\n' \
  >"$FIXTURE_IMPL/.ship-route-exit-handoff.env"
run_start "$TMP/control-char-value.out"
contains "$TMP/control-char-value.out" 'REASON=invalid-route-handoff'

printf '%s\n' 'step-8-ci-fixer harness: ok'
