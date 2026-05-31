#!/usr/bin/env bash
# test-degraded-tools-gate.sh — offline regression for scripts/degraded-tools-gate.sh (#3207).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATE="$SCRIPT_DIR/degraded-tools-gate.sh"

PASS=0
FAIL=0

assert_contains() {
    local haystack=$1 needle=$2 label=$3
    if printf '%s\n' "$haystack" | grep -Fq -- "$needle"; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
        printf 'FAIL: %s — expected to contain: %s\n' "$label" "$needle" >&2
        printf '----- output -----\n%s\n------------------\n' "$haystack" >&2
    fi
}

assert_not_contains() {
    local haystack=$1 needle=$2 label=$3
    if printf '%s\n' "$haystack" | grep -Fq -- "$needle"; then
        FAIL=$((FAIL + 1))
        printf 'FAIL: %s — expected NOT to contain: %s\n' "$label" "$needle" >&2
    else
        PASS=$((PASS + 1))
    fi
}

assert_rc() {
    local got=$1 want=$2 label=$3
    if [ "$got" = "$want" ]; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
        printf 'FAIL: %s — rc=%s want=%s\n' "$label" "$got" "$want" >&2
    fi
}

# --- Case 1: all healthy → not degraded, no explanation block ---
out=$(bash "$GATE" --codex-binary-found true --codex-present true \
    --cursor-binary-found true --cursor-present true --skill design 2>&1) && rc=$? || rc=$?
assert_not_contains "$out" "WARNING:" "all-healthy must not emit WARNING"
assert_rc "$rc" 0 "all-healthy exit 0"
assert_contains "$out" "DEGRADED=false" "all-healthy DEGRADED=false"
assert_contains "$out" "CODEX_STATE=ok" "all-healthy codex ok"
assert_contains "$out" "CURSOR_STATE=ok" "all-healthy cursor ok"
assert_not_contains "$out" "DEGRADED_EXPLANATION_BEGIN" "all-healthy no explanation"

# --- Case 2: codex probe-failed, cursor ok → degraded, probe-failed phrasing ---
out=$(bash "$GATE" --codex-binary-found true --codex-present false \
    --cursor-binary-found true --cursor-present true --skill design) && rc=$? || rc=$?
assert_rc "$rc" 0 "codex-probe-failed exit 0"
assert_contains "$out" "DEGRADED=true" "codex-probe-failed degraded"
assert_contains "$out" "CODEX_STATE=probe-failed" "codex-probe-failed state"
assert_contains "$out" "CURSOR_STATE=ok" "codex-probe-failed cursor ok"
assert_contains "$out" "BOTH_DOWN=false" "codex-probe-failed BOTH_DOWN=false"
assert_contains "$out" "DEGRADED_EXPLANATION_BEGIN" "codex-probe-failed explanation begin"
assert_contains "$out" "DEGRADED_EXPLANATION_END" "codex-probe-failed explanation end"
assert_contains "$out" "runtime health probe failed" "codex-probe-failed phrasing"
assert_contains "$out" "/design run" "codex-probe-failed skill label"

# --- Case 3: cursor binary-missing, codex ok → degraded, binary-missing phrasing ---
out=$(bash "$GATE" --codex-binary-found true --codex-present true \
    --cursor-binary-found false --cursor-present false --skill implement) && rc=$? || rc=$?
assert_rc "$rc" 0 "cursor-binary-missing exit 0"
assert_contains "$out" "DEGRADED=true" "cursor-binary-missing degraded"
assert_contains "$out" "CURSOR_STATE=binary-missing" "cursor-binary-missing state"
assert_contains "$out" "CODEX_STATE=ok" "cursor-binary-missing codex ok"
assert_contains "$out" "BOTH_DOWN=false" "cursor-binary-missing BOTH_DOWN=false"
assert_contains "$out" "CLI binary not found" "cursor-binary-missing phrasing"
assert_contains "$out" "/implement run" "cursor-binary-missing skill label"

# --- Case 4: both unavailable (binary present, probes failed) → degraded ---
out=$(bash "$GATE" --codex-binary-found true --codex-present false \
    --cursor-binary-found true --cursor-present false --skill review) && rc=$? || rc=$?
assert_rc "$rc" 0 "both-probe-failed exit 0"
assert_contains "$out" "DEGRADED=true" "both-probe-failed degraded"
assert_contains "$out" "CODEX_STATE=probe-failed" "both-probe-failed codex"
assert_contains "$out" "CURSOR_STATE=probe-failed" "both-probe-failed cursor"
assert_contains "$out" "BOTH_DOWN=true" "both-probe-failed BOTH_DOWN=true"

# --- Case 5: empty binary-found + empty present → generic `unavailable` ---
out=$(bash "$GATE" --codex-binary-found "" --codex-present "" \
    --cursor-binary-found true --cursor-present true) && rc=$? || rc=$?
assert_rc "$rc" 0 "empty-codex exit 0"
assert_contains "$out" "DEGRADED=true" "empty-codex degraded"
assert_contains "$out" "CODEX_STATE=unavailable" "empty-codex → generic unavailable"
assert_contains "$out" "/this run" "default skill label"

# --- Case 6: present=true but binary-found=false is still binary-missing (binary gate wins) ---
out=$(bash "$GATE" --codex-binary-found false --codex-present true \
    --cursor-binary-found true --cursor-present true) && rc=$? || rc=$?
assert_contains "$out" "CODEX_STATE=binary-missing" "binary-false-present-true → binary-missing"
assert_contains "$out" "DEGRADED=true" "binary-false-present-true degraded"

# --- Case 7: present-only wiring (binary-found omitted, as /design/review/research call it) ---
out=$(CODEX_BINARY_FOUND='' CURSOR_BINARY_FOUND='' bash "$GATE" --codex-present true --cursor-present false --skill review) && rc=$? || rc=$?
assert_rc "$rc" 0 "present-only exit 0"
assert_contains "$out" "DEGRADED=true" "present-only degraded (cursor down)"
assert_contains "$out" "CODEX_STATE=ok" "present-only codex ok without binary-found"
assert_contains "$out" "CURSOR_STATE=unavailable" "present-only cursor generic unavailable"

# --- Case 8: env-var cursor-ok (no flags) ---
out=$(CODEX_BINARY_FOUND=true CODEX_PRESENT=false CURSOR_BINARY_FOUND=true CURSOR_PRESENT=true \
    bash "$GATE" --skill implement 2>&1) && rc=$? || rc=$?
assert_rc "$rc" 0 "env-var cursor-ok exit 0"
assert_contains "$out" "CURSOR_STATE=ok" "env-var cursor-ok cursor state"
assert_contains "$out" "CODEX_STATE=probe-failed" "env-var cursor-ok codex probe-failed"
assert_contains "$out" "DEGRADED=true" "env-var cursor-ok degraded"
assert_contains "$out" "WARNING: --codex-binary-found omitted" "env-var cursor-ok codex-binary warning"
assert_contains "$out" "WARNING: --codex-present omitted" "env-var cursor-ok codex-present warning"
assert_contains "$out" "WARNING: --cursor-binary-found omitted" "env-var cursor-ok cursor-binary warning"
assert_contains "$out" "WARNING: --cursor-present omitted" "env-var cursor-ok cursor-present warning"

# --- Case 9: env-var codex-ok (no flags) ---
out=$(CODEX_BINARY_FOUND=true CODEX_PRESENT=true CURSOR_BINARY_FOUND=true CURSOR_PRESENT=false \
    bash "$GATE" --skill implement 2>&1) && rc=$? || rc=$?
assert_rc "$rc" 0 "env-var codex-ok exit 0"
assert_contains "$out" "CODEX_STATE=ok" "env-var codex-ok codex state"
assert_contains "$out" "CURSOR_STATE=probe-failed" "env-var codex-ok cursor probe-failed"
assert_contains "$out" "DEGRADED=true" "env-var codex-ok degraded"
assert_contains "$out" "WARNING: --codex-binary-found omitted" "env-var codex-ok codex-binary warning"
assert_contains "$out" "WARNING: --codex-present omitted" "env-var codex-ok codex-present warning"
assert_contains "$out" "WARNING: --cursor-binary-found omitted" "env-var codex-ok cursor-binary warning"
assert_contains "$out" "WARNING: --cursor-present omitted" "env-var codex-ok cursor-present warning"

# --- Case 7b: present-only with cleared binary env must not WARN ---
out=$(CODEX_BINARY_FOUND='' CURSOR_BINARY_FOUND='' bash "$GATE" --codex-present true --cursor-present false --skill review 2>&1) && rc=$? || rc=$?
assert_rc "$rc" 0 "present-only no-warn exit 0"
assert_not_contains "$out" "WARNING:" "present-only with flags must not emit WARNING"

# --- Case 10: flag-over-env precedence (contradictory env, explicit flags win) ---
out=$(CODEX_BINARY_FOUND=false CODEX_PRESENT=false CURSOR_BINARY_FOUND=false CURSOR_PRESENT=false \
    bash "$GATE" \
        --codex-binary-found true --codex-present true \
        --cursor-binary-found true --cursor-present true \
        --skill design 2>&1) && rc=$? || rc=$?
assert_rc "$rc" 0 "flag-over-env exit 0"
assert_contains "$out" "DEGRADED=false" "flag-over-env not degraded"
assert_contains "$out" "CODEX_STATE=ok" "flag-over-env codex ok"
assert_contains "$out" "CURSOR_STATE=ok" "flag-over-env cursor ok"
assert_not_contains "$out" "WARNING: --codex-binary-found omitted" "flag-over-env no codex-binary warning"
assert_not_contains "$out" "WARNING: --codex-present omitted" "flag-over-env no codex-present warning"
assert_not_contains "$out" "WARNING: --cursor-binary-found omitted" "flag-over-env no cursor-binary warning"
assert_not_contains "$out" "WARNING: --cursor-present omitted" "flag-over-env no cursor-present warning"

# --- Case 11: stale env with flag omission misclassifies without stderr WARNING visibility on stdout ---
out=$(CODEX_BINARY_FOUND=true CODEX_PRESENT=true CURSOR_BINARY_FOUND=true CURSOR_PRESENT=true \
    bash "$GATE" --skill review 2>&1) && rc=$? || rc=$?
assert_rc "$rc" 0 "stale-env omission exit 0"
assert_contains "$out" "DEGRADED=false" "stale-env omission uses inherited env"
assert_contains "$out" "WARNING: --codex-present omitted" "stale-env omission warns on codex-present"

# --- Case 12: unknown flag → exit 2 ---
out=$(bash "$GATE" --bogus 2>&1) && rc=$? || rc=$?
assert_rc "$rc" 2 "unknown-flag exit 2"
assert_contains "$out" "unknown argument" "unknown-flag message"

# --- Case 13: single tool down → auto-proceed notice, not Continue-or-abort question ---
out=$(bash "$GATE" --codex-binary-found true --codex-present false \
    --cursor-binary-found true --cursor-present true --skill design) && rc=$? || rc=$?
assert_rc "$rc" 0 "single-down-explanation exit 0"
assert_contains "$out" "proceeding automatically" "single-down-explanation auto-proceed notice"
assert_not_contains "$out" "Continue in this degraded mode" "single-down-explanation no Continue prompt"

# --- Case 14: both tools down → Continue-or-abort question, not auto-proceed notice ---
out=$(bash "$GATE" --codex-binary-found true --codex-present false \
    --cursor-binary-found true --cursor-present false --skill design) && rc=$? || rc=$?
assert_rc "$rc" 0 "both-down-explanation exit 0"
assert_contains "$out" "Continue in this degraded mode" "both-down-explanation Continue prompt"
assert_not_contains "$out" "proceeding automatically" "both-down-explanation no auto-proceed notice"

printf 'test-degraded-tools-gate: PASS=%d FAIL=%d\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
