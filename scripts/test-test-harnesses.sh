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

if [ ! -x "$RUNNER" ]; then
    echo "FAIL: runner not executable at $RUNNER" >&2
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
chmod +x "$WORKDIR/scripts/test-harnesses.sh"

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

echo "PASS: test-test-harnesses.sh"
