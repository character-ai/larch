#!/usr/bin/env bash
# test-step-8-ship.sh — offline harness for step-8-ship.sh contracts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/step-8-ship.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
SKILL_MD="$SCRIPT_DIR/../SKILL.md"
EXIT_MATRIX="$SCRIPT_DIR/../references/ship-pr-exit-matrix.md"
SHIP_PR="$REPO_ROOT/scripts/ship-pr.sh"

PASS=0
FAIL=0
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-step-8-ship.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

pass() {
    PASS=$((PASS + 1))
    printf 'PASS: %s\n' "$1"
}

fail() {
    FAIL=$((FAIL + 1))
    printf 'FAIL: %s\n' "$1" >&2
}

assert_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -Fq -- "$needle"; then
        pass "$label"
    else
        fail "$label (missing: $needle)"
    fi
}

assert_rc() {
    local actual=$1 expected=$2 label=$3
    if [ "$actual" -eq "$expected" ]; then
        pass "$label"
    else
        fail "$label (expected rc=$expected got rc=$actual)"
    fi
}

# Case 1: static pins for Python 3.11 guard, STALLED JSON, exit 4, bash32 resume args.
assert_contains 'sys.version_info >= (3, 11)' "$(cat "$HELPER")" 'static: python 3.11 guard present'
assert_contains '"outcome":"STALLED"' "$(cat "$HELPER")" 'static: stalled JSON present'
assert_contains 'exit 4' "$(cat "$HELPER")" 'static: exit 4 present'
assert_contains 'SHIP_PR_LEDGER_READY' "$(cat "$EXIT_MATRIX")" 'static: bash ledger contract documented in exit matrix'
assert_contains 'SHIP_PR_LEDGER_*' "$(cat "$SKILL_MD")" 'static: bash ledger parse contract documented in SKILL'
SHIP_PR_LEDGER_SNIPPET="$(grep -E 'ship-pr-internal-lint-fix|ci-local-unfixable|emit_ship_pr_ledger_ready' "$SHIP_PR")"
assert_contains 'BAIL_REASON ship-pr-internal-lint-fix' "$SHIP_PR_LEDGER_SNIPPET" 'static: step6 lint-fix handoff sets ship-pr-internal token'
assert_contains 'emit_ship_pr_ledger_ready ship-pr-internal-lint-fix ci-initial' "$SHIP_PR_LEDGER_SNIPPET" 'static: step6 lint-fix handoff emits ledger before exit 3'
assert_contains "emit_ship_pr_ledger_ready \"ci-local-unfixable:\${sanitized}\" \"\$phase\" \"\$detail_file\"" "$SHIP_PR_LEDGER_SNIPPET" 'static: ci-local exit3 emits ledger'
# shellcheck disable=SC2016
if grep -q '"\${_resume_args\[@\]+"\${_resume_args\[@\]}"}"' "$HELPER"; then
    pass 'static: bash32-safe resume args expansion'
else
    fail 'static: bash32-safe resume args expansion missing'
fi

# Case 2: stale-python STALLED JSON + exit 4 via stubbed python3 on default path.
IMPL_TMP="$TMP_ROOT/implement"
mkdir -p "$IMPL_TMP"
printf 'BRANCH_NAME=test-branch\nISSUE_NUMBER=42\nRUN_ID=run-ship-guard\nREPO=owner/repo\n' >"$IMPL_TMP/ship-pr-state.sh"
printf 'export CLAUDE_PLUGIN_ROOT=%s\n' "$REPO_ROOT" >"$IMPL_TMP/plugin-root.env"
printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$REPO_ROOT" >"$IMPL_TMP/session-env.sh"
printf 'session-id\n' >"$IMPL_TMP/session-id"

REAL_PYTHON=$(command -v python3)
STUB_BIN="$TMP_ROOT/bin"
mkdir -p "$STUB_BIN"
cat >"$STUB_BIN/python3" <<EOF
#!/usr/bin/env bash
if [ "\$1" = "-c" ] && printf '%s\n' "\$2" | grep -Fq 'sys.version_info >= (3, 11)'; then
  exit 1
fi
exec "$REAL_PYTHON" "\$@"
EOF
chmod +x "$STUB_BIN/python3"

set +e
OUT=$(
    PATH="$STUB_BIN:$PATH" \
    IMPLEMENT_TMPDIR="$IMPL_TMP" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    LARCH_SHIP_PR_IMPL=python \
    bash "$HELPER" 2>"$TMP_ROOT/stderr.txt"
)
RC=$?
set -e
STDERR=$(cat "$TMP_ROOT/stderr.txt" 2>/dev/null || true)

assert_rc "$RC" 4 'dynamic: stale python exits 4'
assert_contains '"outcome":"STALLED"' "$OUT" 'dynamic: stale python emits STALLED JSON'
assert_contains '"ledger_ready":false' "$OUT" 'dynamic: stale python emits ledger keys'
assert_contains 'Python ship driver requires Python 3.11 or newer' "$STDERR" 'dynamic: stale python stderr message'

# Case 3: bash mode with empty RESUME_PHASE must not abort under nounset.
set +e
(
    IMPLEMENT_TMPDIR="$IMPL_TMP" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    LARCH_SHIP_PR_IMPL=bash \
    bash -c 'set -u; exec "$@"' _ "$HELPER"
) 2>"$TMP_ROOT/bash-stderr.txt"
BASH_RC=$?
set -e
BASH_STDERR=$(cat "$TMP_ROOT/bash-stderr.txt" 2>/dev/null || true)
if [ "$BASH_RC" -eq 127 ] || printf '%s' "$BASH_STDERR" | grep -Fq 'unbound variable'; then
    fail "dynamic: bash mode empty resume args nounset (rc=$BASH_RC)"
else
    pass 'dynamic: bash mode empty resume args nounset-safe'
fi

if [ "$FAIL" -eq 0 ]; then
    printf 'PASS: test-step-8-ship.sh (%d assertions)\n' "$PASS"
    exit 0
fi
printf 'FAIL: test-step-8-ship.sh (%d passed, %d failed)\n' "$PASS" "$FAIL" >&2
exit 1
