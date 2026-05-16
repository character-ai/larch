#!/usr/bin/env bash
# test-session-setup-health-defaults.sh — regression harness for the
# fail-closed `:-false` defaults in session-setup.sh's `.health` sidecar
# write block.
#
# Wired into: make test-harnesses (test-harnesses-6 shard).
# Sibling contract: scripts/test-session-setup-health-defaults.md
# Exit codes: 0 all pass, 1 any failure.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$REPO_ROOT/scripts/session-setup.sh"

[[ -x "$SCRIPT" ]] || { echo "FAIL: $SCRIPT not executable" >&2; exit 1; }

PASS=0
FAIL=0
SANDBOX=$(mktemp -d /tmp/larch-session-setup-health-test.XXXXXX)
trap 'rm -rf "$SANDBOX"' EXIT

assert_health_value() {
    local file=$1 key=$2 expected=$3 label=$4
    local actual
    actual=$(awk -F= -v k="$key" '$1==k{print $2; exit}' "$file" 2>/dev/null || true)
    if [[ "$actual" == "$expected" ]]; then
        PASS=$((PASS + 1))
        echo "PASS: $label ($key=$actual)"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (expected $key=$expected, got $key=${actual:-<missing>})"
    fi
}

run_session_setup() {
    local label=$1 caller_env=$2 health=$3
    shift 3
    local logfile="$SANDBOX/log.${label}"
    if ! "$SCRIPT" \
        --prefix "test-health-${label}" \
        --skip-preflight \
        --skip-repo-check \
        --caller-env "$caller_env" \
        --write-health "$health" \
        "$@" >"$logfile" 2>&1; then
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (session-setup.sh exited non-zero)"
        echo "----- session-setup.sh output ($logfile, last 50 lines) -----"
        tail -50 "$logfile" >&2 || true
        echo "----- end output -----"
        return 1
    fi
    return 0
}

# ---------------------------------------------------------------------------
# Test 1 — Empty caller-env.
# Regression for #1336: empty FINAL_CODEX_HEALTHY / FINAL_CURSOR_HEALTHY MUST
# by session-setup.sh regardless of caller-env (#1720 Part 1).
# ---------------------------------------------------------------------------
ENV1="$SANDBOX/env1.txt"
HEALTH1="$SANDBOX/health1.txt"
: > "$ENV1"  # empty file: no *_HEALTHY keys
if run_session_setup "empty-caller-env" "$ENV1" "$HEALTH1"; then
    assert_health_value "$HEALTH1" "CODEX_HEALTHY" "false" \
        "empty caller-env: CODEX defaults fail-closed"
    assert_health_value "$HEALTH1" "CURSOR_HEALTHY" "false" \
        "empty caller-env: CURSOR defaults fail-closed"
fi

# ---------------------------------------------------------------------------
# Test 3 — Sanity: explicit caller-env true values pass through for CODEX/CURSOR.
# ---------------------------------------------------------------------------
ENV3="$SANDBOX/env3.txt"
HEALTH3="$SANDBOX/health3.txt"
cat > "$ENV3" <<'EOF'
CODEX_HEALTHY=true
CURSOR_HEALTHY=true
EOF
if run_session_setup "explicit-true" "$ENV3" "$HEALTH3"; then
    assert_health_value "$HEALTH3" "CODEX_HEALTHY" "true" \
        "explicit caller-env true: CODEX passes through"
    assert_health_value "$HEALTH3" "CURSOR_HEALTHY" "true" \
        "explicit caller-env true: CURSOR passes through"
fi

# ---------------------------------------------------------------------------
# Test 4 — Sanity: explicit caller-env `false` values pass through unchanged.
# ---------------------------------------------------------------------------
ENV4="$SANDBOX/env4.txt"
HEALTH4="$SANDBOX/health4.txt"
cat > "$ENV4" <<'EOF'
CODEX_HEALTHY=false
CURSOR_HEALTHY=false
EOF
if run_session_setup "explicit-false" "$ENV4" "$HEALTH4"; then
    assert_health_value "$HEALTH4" "CODEX_HEALTHY" "false" \
        "explicit caller-env false: CODEX passes through"
    assert_health_value "$HEALTH4" "CURSOR_HEALTHY" "false" \
        "explicit caller-env false: CURSOR passes through"
fi

# ---------------------------------------------------------------------------
# Test 5 — --check-reviewers with caller-env true: health sidecar must echo
# caller value, not check-reviewers.sh's initial 'false'. Regression for the
# inverted skip-probe fix (== "false" → -n check).
# ---------------------------------------------------------------------------
ENV5="$SANDBOX/env5.txt"
HEALTH5="$SANDBOX/health5.txt"
cat > "$ENV5" <<'EOF'
CODEX_HEALTHY=true
CURSOR_HEALTHY=true
EOF
if run_session_setup "check-reviewers-caller-true" "$ENV5" "$HEALTH5" \
    --check-reviewers; then
    assert_health_value "$HEALTH5" "CODEX_HEALTHY" "true" \
        "--check-reviewers + caller true: CODEX passes through"
    assert_health_value "$HEALTH5" "CURSOR_HEALTHY" "true" \
        "--check-reviewers + caller true: CURSOR passes through"
fi

echo
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] || exit 1
exit 0
