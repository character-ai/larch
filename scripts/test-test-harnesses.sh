#!/usr/bin/env bash
# test-test-harnesses.sh — Regression test for scripts/test-harnesses.sh.
#
# Builds a temp project with a small fake Makefile and three fake harness
# scripts (two that pass with controlled output, one that fails). Runs the
# parallel runner with MAX_JOBS=2 and asserts:
#   - exit code is 1 (one harness failed)
#   - all three output blocks are present
#   - each block's body lines appear contiguously, immediately after that
#     block's header (no interleaving across blocks)
#   - blocks appear in submission order
#   - the final summary line reports "1 of 3" failed

set -uo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
RUNNER="$REPO_ROOT/scripts/test-harnesses.sh"

# Use `bash "$RUNNER"` rather than relying on the exec bit so the meta-harness
# is portable across checkouts that may not preserve the +x mode (some CI
# checkouts, archive extractions, scrubbed worktrees).
if [ ! -f "$RUNNER" ]; then
    echo "FAIL: runner not present at $RUNNER" >&2
    exit 1
fi

WORKDIR=$(mktemp -d -t test-test-harnesses.XXXXXX)
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT INT TERM

mkdir -p "$WORKDIR/scripts"

# Three fake harnesses. Each emits a unique marker line so we can identify
# which block its output belongs to. The "slow" one sleeps briefly so the
# parallel runner has a real chance to interleave (and we can prove it does
# not).
cat >"$WORKDIR/scripts/h1.sh" <<'EOF'
#!/usr/bin/env bash
echo "H1-LINE-A"
echo "H1-LINE-B"
exit 0
EOF
cat >"$WORKDIR/scripts/h2.sh" <<'EOF'
#!/usr/bin/env bash
sleep 0.3
echo "H2-LINE-A"
echo "H2-LINE-B"
exit 0
EOF
cat >"$WORKDIR/scripts/h3.sh" <<'EOF'
#!/usr/bin/env bash
echo "H3-LINE-A"
echo "H3-LINE-B" >&2
exit 7
EOF
chmod +x "$WORKDIR/scripts/"*.sh

cat >"$WORKDIR/Makefile" <<'EOF'
.PHONY: _test-harnesses-list test-h1 test-h2 test-h3

_test-harnesses-list: test-h1 test-h2 test-h3

test-h1:
	bash scripts/h1.sh

test-h2:
	bash scripts/h2.sh

test-h3:
	bash scripts/h3.sh
EOF

# Run the runner from inside the fake repo. The runner cds to its own
# repo root via $0, so we copy it into the fake project to keep it self-
# contained for the test.
cp "$RUNNER" "$WORKDIR/scripts/test-harnesses.sh"

OUTPUT=$(MAX_JOBS=2 bash "$WORKDIR/scripts/test-harnesses.sh" 2>&1)
RC=$?

fail() {
    echo "FAIL: $1" >&2
    echo "----- captured runner output -----" >&2
    printf '%s\n' "$OUTPUT" >&2
    echo "----- end captured output -----" >&2
    exit 1
}

# 1. Exit code must be 1 (one harness failed).
if [ "$RC" -ne 1 ]; then
    fail "expected exit code 1, got $RC"
fi

# 2. All three blocks present, in submission order.
H1_HDR=$(printf '%s\n' "$OUTPUT" | grep -n '^===== bash scripts/h1.sh — PASS =====$' | head -1 | cut -d: -f1)
H2_HDR=$(printf '%s\n' "$OUTPUT" | grep -n '^===== bash scripts/h2.sh — PASS =====$' | head -1 | cut -d: -f1)
H3_HDR=$(printf '%s\n' "$OUTPUT" | grep -n '^===== bash scripts/h3.sh — FAIL (exit 7) =====$' | head -1 | cut -d: -f1)

[ -z "$H1_HDR" ] && fail "missing H1 PASS header"
[ -z "$H2_HDR" ] && fail "missing H2 PASS header"
[ -z "$H3_HDR" ] && fail "missing H3 FAIL header"

if [ "$H1_HDR" -ge "$H2_HDR" ] || [ "$H2_HDR" -ge "$H3_HDR" ]; then
    fail "blocks out of submission order: H1=$H1_HDR H2=$H2_HDR H3=$H3_HDR"
fi

# 3. Contiguity check: each H<i>-LINE-* line must appear AFTER its block
# header and BEFORE the next block's header. (No marker line for one
# harness may appear inside another's block.)
check_contiguous() {
    local prefix="$1" hdr="$2" next_hdr="$3"
    local lineno
    while IFS= read -r lineno; do
        [ -z "$lineno" ] && continue
        if [ "$lineno" -le "$hdr" ]; then
            fail "$prefix line at $lineno appears at/before its header (line $hdr)"
        fi
        if [ -n "$next_hdr" ] && [ "$lineno" -ge "$next_hdr" ]; then
            fail "$prefix line at $lineno bleeds into the next block (header at $next_hdr)"
        fi
    done <<EOF2
$(printf '%s\n' "$OUTPUT" | grep -n "^${prefix}-LINE-" | cut -d: -f1)
EOF2
}

check_contiguous "H1" "$H1_HDR" "$H2_HDR"
check_contiguous "H2" "$H2_HDR" "$H3_HDR"
check_contiguous "H3" "$H3_HDR" ""

# 4. Final summary line.
if ! printf '%s\n' "$OUTPUT" | grep -q '^FAILED: 1 of 3 harness(es) failed$'; then
    fail "missing or wrong summary line"
fi

# Validation tests below verify the runner FAILS FAST on bad input — they
# exit 2 before any worker is launched, so no real timeout is needed (a
# regression that hung would be caught by the harness suite's per-target
# timeout in CI). For local portability we don't depend on `timeout(1)`,
# which is GNU coreutils-only on macOS.

# 5. MAX_JOBS=0 must fail loudly, not hang.
RC5=0
OUT5=$(MAX_JOBS=0 bash "$WORKDIR/scripts/test-harnesses.sh" 2>&1) || RC5=$?
[ "$RC5" -eq 2 ] || { echo "FAIL: MAX_JOBS=0 expected exit 2, got $RC5" >&2; exit 1; }
printf '%s\n' "$OUT5" | grep -q 'MAX_JOBS must be >= 1' || { echo "FAIL: MAX_JOBS=0 missing diagnostic" >&2; exit 1; }

# 6. MAX_JOBS=abc (non-numeric) must fail loudly.
RC6=0
OUT6=$(MAX_JOBS=abc bash "$WORKDIR/scripts/test-harnesses.sh" 2>&1) || RC6=$?
[ "$RC6" -eq 2 ] || { echo "FAIL: MAX_JOBS=abc expected exit 2, got $RC6" >&2; exit 1; }
printf '%s\n' "$OUT6" | grep -q "MAX_JOBS must be a positive integer" || { echo "FAIL: MAX_JOBS=abc missing diagnostic" >&2; exit 1; }

# 7. Empty _test-harnesses-list must fail loudly (not exit 0 silent-green).
WORKDIR2=$(mktemp -d -t test-test-harnesses-empty.XXXXXX)
trap 'rm -rf "$WORKDIR" "$WORKDIR2"' EXIT INT TERM
mkdir -p "$WORKDIR2/scripts"
cp "$RUNNER" "$WORKDIR2/scripts/test-harnesses.sh"
cat >"$WORKDIR2/Makefile" <<'EOF'
.PHONY: _test-harnesses-list
_test-harnesses-list:
EOF
RC7=0
OUT7=$(bash "$WORKDIR2/scripts/test-harnesses.sh" 2>&1) || RC7=$?
[ "$RC7" -eq 2 ] || { echo "FAIL: empty harness list expected exit 2, got $RC7" >&2; printf '%s\n' "$OUT7" >&2; exit 1; }
printf '%s\n' "$OUT7" | grep -q 'zero harness commands' || { echo "FAIL: empty list missing diagnostic" >&2; exit 1; }

# 8. Non-conforming recipe (multi-statement) must be rejected.
WORKDIR3=$(mktemp -d -t test-test-harnesses-malformed.XXXXXX)
trap 'rm -rf "$WORKDIR" "$WORKDIR2" "$WORKDIR3"' EXIT INT TERM
mkdir -p "$WORKDIR3/scripts"
cp "$RUNNER" "$WORKDIR3/scripts/test-harnesses.sh"
cat >"$WORKDIR3/scripts/h-ok.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$WORKDIR3/scripts/h-ok.sh"
cat >"$WORKDIR3/Makefile" <<'EOF'
.PHONY: _test-harnesses-list test-bad
_test-harnesses-list: test-bad
test-bad:
	bash scripts/h-ok.sh && echo chained
EOF
RC8=0
OUT8=$(bash "$WORKDIR3/scripts/test-harnesses.sh" 2>&1) || RC8=$?
[ "$RC8" -eq 2 ] || { echo "FAIL: chained recipe expected exit 2, got $RC8" >&2; printf '%s\n' "$OUT8" >&2; exit 1; }
printf '%s\n' "$OUT8" | grep -q "did not match the expected" || { echo "FAIL: chained recipe missing diagnostic" >&2; exit 1; }

echo "PASS: test-test-harnesses.sh (8 cases: contiguity, exit code, summary, MAX_JOBS=0, MAX_JOBS=abc, empty list, malformed recipe)"
