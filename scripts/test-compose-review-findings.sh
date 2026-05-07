#!/usr/bin/env bash
# test-compose-review-findings.sh — regression harness for
# scripts/compose-review-findings.sh.
#
# Covers:
#   (a) empty inputs → fragment with "no findings" placeholder, exit 0
#   (b) accepted plan-review parsing → finding emitted with correct id, phase,
#       outcome, category, prose body
#   (c) rejected plan-review parsing → finding emitted under [Plan Review]
#       header with synthetic id REJ_P1
#   (d) rejected code-review parsing → finding emitted under [Code Review]
#       header with synthetic id REJ_C1
#   (e) inline ↔ archive switchover at the configured threshold
#   (f) archive content shape (JSONL — one record per line, valid JSON)
#   (g) category derivation maps reviewer-name fragments to canonical tags
#   (h) JSON escaping handles backslash, double-quote, and embedded newlines
#
# Self-contained: creates fixtures under a fresh tmpdir and cleans up.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE="$SCRIPT_DIR/compose-review-findings.sh"

[ -x "$COMPOSE" ] || { echo "FAIL: $COMPOSE not executable" >&2; exit 1; }

TMP=$(mktemp -d /tmp/test-compose-review-findings.XXXXXX)
trap 'rm -rf "$TMP"' EXIT

FAILS=0

fail() { echo "FAIL: $1" >&2; FAILS=$((FAILS + 1)); }
pass() { echo "  ok: $1"; }

# --------------------------------------------------------------------------
# (a) Empty inputs
# --------------------------------------------------------------------------
echo "=== (a) Empty inputs → stable empty section ==="
mkdir -p "$TMP/a-design" "$TMP/a-impl"
out_a="$TMP/a-out.md"
stdout_a=$("$COMPOSE" \
    --design-artifacts-dir "$TMP/a-design" \
    --implement-tmpdir "$TMP/a-impl" \
    --issue 1 \
    --output "$out_a" 2>&1)
grep -qxF 'COMPOSED=true' <<<"$stdout_a" || fail "(a) expected COMPOSED=true; got: $stdout_a"
grep -qxF 'FINDINGS_TOTAL=0' <<<"$stdout_a" || fail "(a) expected FINDINGS_TOTAL=0"
grep -qxF 'MODE=inline' <<<"$stdout_a" || fail "(a) expected MODE=inline"
grep -q '## Review Findings' "$out_a" || fail "(a) section header missing"
grep -q 'No review findings captured' "$out_a" || fail "(a) empty placeholder missing"
[ "$FAILS" -eq 0 ] && pass "(a) empty inputs"

# --------------------------------------------------------------------------
# (b) Accepted plan-review parsing
# --------------------------------------------------------------------------
echo "=== (b) Accepted plan-review parsing ==="
mkdir -p "$TMP/b-design" "$TMP/b-impl"
cat > "$TMP/b-design/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Layer boundary violation in foo.sh
- **Concern**: scripts/foo.sh:42 leaks tmpdir paths into stderr without redaction.
- **Resolution**: Pipe stderr through redact-secrets.sh before emitting.
EOF
out_b="$TMP/b-out.md"
"$COMPOSE" \
    --design-artifacts-dir "$TMP/b-design" \
    --implement-tmpdir "$TMP/b-impl" \
    --issue 2 \
    --output "$out_b" >/dev/null 2>&1 || fail "(b) compose failed"
grep -q '^### FINDING_1 — ' "$out_b" || fail "(b) FINDING_1 heading missing"
grep -q '^- \*\*Phase\*\*: plan-review$' "$out_b" || fail "(b) Phase bullet missing"
grep -q '^- \*\*Outcome\*\*: accepted$' "$out_b" || fail "(b) Outcome bullet missing"
grep -q '^> .*foo.sh:42' "$out_b" || fail "(b) prose body not blockquoted"
[ "$FAILS" -eq 0 ] && pass "(b) accepted plan-review"

# --------------------------------------------------------------------------
# (c) Rejected plan-review parsing → synthetic id
# --------------------------------------------------------------------------
echo "=== (c) Rejected plan-review parsing ==="
mkdir -p "$TMP/c-design" "$TMP/c-impl"
cat > "$TMP/c-design/rejected-findings.md" <<'EOF'
### [Plan Review] Cursor-Architecture
**Finding**: The plan misses the assemble-anchor.sh seed-only placeholder rule.
**Reason not implemented**: Out of scope; tracked separately as #1402.
EOF
out_c="$TMP/c-out.md"
"$COMPOSE" \
    --design-artifacts-dir "$TMP/c-design" \
    --implement-tmpdir "$TMP/c-impl" \
    --issue 3 \
    --output "$out_c" >/dev/null 2>&1 || fail "(c) compose failed"
grep -q '^### REJ_P1 — architecture$' "$out_c" || fail "(c) REJ_P1 architecture heading missing"
grep -q '^- \*\*Phase\*\*: plan-review$' "$out_c" || fail "(c) Phase plan-review missing"
grep -q '^- \*\*Outcome\*\*: rejected$' "$out_c" || fail "(c) Outcome rejected missing"
[ "$FAILS" -eq 0 ] && pass "(c) rejected plan-review"

# --------------------------------------------------------------------------
# (d) Rejected code-review parsing → synthetic id
# --------------------------------------------------------------------------
echo "=== (d) Rejected code-review parsing ==="
mkdir -p "$TMP/d-design" "$TMP/d-impl"
cat > "$TMP/d-impl/rejected-findings.md" <<'EOF'
### [Code Review] Cursor-Edge-Cases (round 1)
**Finding**: scripts/redact-secrets.sh:88 may emit a stale match on a 0-byte input.
**Reason not implemented**: Existing test coverage proves this branch is unreachable in practice.
EOF
out_d="$TMP/d-out.md"
"$COMPOSE" \
    --design-artifacts-dir "$TMP/d-design" \
    --implement-tmpdir "$TMP/d-impl" \
    --issue 4 \
    --output "$out_d" >/dev/null 2>&1 || fail "(d) compose failed"
grep -q '^### REJ_C1 — edge-cases$' "$out_d" || fail "(d) REJ_C1 edge-cases heading missing"
grep -q '^- \*\*Phase\*\*: code-review$' "$out_d" || fail "(d) Phase code-review missing"
grep -q '^- \*\*Outcome\*\*: rejected$' "$out_d" || fail "(d) Outcome rejected missing"
[ "$FAILS" -eq 0 ] && pass "(d) rejected code-review"

# --------------------------------------------------------------------------
# (e) Inline ↔ archive switchover at threshold
# --------------------------------------------------------------------------
echo "=== (e) Archive switchover at threshold ==="
mkdir -p "$TMP/e-design" "$TMP/e-impl" "$TMP/e-archive"
# Build a large rejected-findings file with many entries to push past a small threshold.
{
    for i in $(seq 1 6); do
        printf '### [Code Review] Cursor-Security (round %s)\n' "$i"
        printf '**Finding**: scripts/redact-secrets.sh:%s — concern body filler line one.\n' "$i"
        # ~200 chars per filler line, 5 lines → ~1000 chars per entry, 6 entries → ~6000 chars
        for _ in $(seq 1 5); do
            printf 'Filler line for size — repeat to push past threshold AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.\n'
        done
        printf '**Reason not implemented**: short justification.\n\n'
    done
} > "$TMP/e-impl/rejected-findings.md"
out_e="$TMP/e-out.md"
stdout_e=$("$COMPOSE" \
    --design-artifacts-dir "$TMP/e-design" \
    --implement-tmpdir "$TMP/e-impl" \
    --issue 99 \
    --output "$out_e" \
    --archive-dir "$TMP/e-archive" \
    --archive-threshold 3000 2>&1)
grep -qxF 'MODE=archive' <<<"$stdout_e" || fail "(e) expected MODE=archive; got: $stdout_e"
grep -qxF "ARCHIVE_PATH=$TMP/e-archive/issue-99.jsonl" <<<"$stdout_e" || fail "(e) archive path missing"
[ -f "$TMP/e-archive/issue-99.jsonl" ] || fail "(e) archive file not created"
grep -q 'Inline payload exceeded' "$out_e" || fail "(e) pointer text missing"
grep -q 'Archive path' "$out_e" || fail "(e) archive path bullet missing"
[ "$FAILS" -eq 0 ] && pass "(e) archive switchover"

# --------------------------------------------------------------------------
# (f) Archive content shape: one JSON object per line, parseable
# --------------------------------------------------------------------------
echo "=== (f) Archive content shape ==="
if command -v python3 >/dev/null 2>&1; then
    line_count=$(wc -l < "$TMP/e-archive/issue-99.jsonl" | tr -d ' ')
    [ "$line_count" -gt 0 ] || fail "(f) archive empty"
    python3 - "$TMP/e-archive/issue-99.jsonl" <<'PY' || fail "(f) JSONL parse failure"
import json, sys
path = sys.argv[1]
with open(path) as f:
    for n, line in enumerate(f, 1):
        line = line.rstrip("\n")
        if not line:
            continue
        obj = json.loads(line)
        for key in ("id", "phase", "outcome", "reviewer", "category", "prose_body"):
            if key not in obj:
                raise SystemExit(f"line {n} missing key {key}")
PY
    [ "$FAILS" -eq 0 ] && pass "(f) JSONL shape"
else
    pass "(f) skipped (no python3)"
fi

# --------------------------------------------------------------------------
# (g) Category derivation
# --------------------------------------------------------------------------
echo "=== (g) Category derivation ==="
mkdir -p "$TMP/g-design" "$TMP/g-impl"
cat > "$TMP/g-impl/rejected-findings.md" <<'EOF'
### [Code Review] Cursor-Correctness (round 1)
**Finding**: a body
**Reason not implemented**: a reason

### [Code Review] Cursor-Security (round 1)
**Finding**: a body
**Reason not implemented**: a reason

### [Code Review] Generic-Codex (round 4)
**Finding**: a body
**Reason not implemented**: a reason
EOF
out_g="$TMP/g-out.md"
"$COMPOSE" \
    --design-artifacts-dir "$TMP/g-design" \
    --implement-tmpdir "$TMP/g-impl" \
    --issue 5 \
    --output "$out_g" >/dev/null 2>&1 || fail "(g) compose failed"
grep -q '^### REJ_C1 — correctness$' "$out_g" || fail "(g) correctness mapping missing"
grep -q '^### REJ_C2 — security$' "$out_g" || fail "(g) security mapping missing"
grep -q '^### REJ_C3 — generic$' "$out_g" || fail "(g) generic mapping missing"
[ "$FAILS" -eq 0 ] && pass "(g) category derivation"

# --------------------------------------------------------------------------
# (h) JSON escaping
# --------------------------------------------------------------------------
echo "=== (h) JSON escaping ==="
if command -v python3 >/dev/null 2>&1; then
    mkdir -p "$TMP/h-design" "$TMP/h-impl" "$TMP/h-archive"
    cat > "$TMP/h-impl/rejected-findings.md" <<'EOF'
### [Code Review] Cursor-Generic
**Finding**: A path with backslashes \\foo\\bar and quotes "hello" embedded
**Reason not implemented**: line one
line two with a tab	character
EOF
    out_h="$TMP/h-out.md"
    "$COMPOSE" \
        --design-artifacts-dir "$TMP/h-design" \
        --implement-tmpdir "$TMP/h-impl" \
        --issue 7 \
        --output "$out_h" \
        --archive-dir "$TMP/h-archive" \
        --archive-threshold 1 >/dev/null 2>&1 || fail "(h) compose failed"
    [ -f "$TMP/h-archive/issue-7.jsonl" ] || fail "(h) archive missing"
    python3 - "$TMP/h-archive/issue-7.jsonl" <<'PY' || fail "(h) JSON escape parse failure"
import json, sys
with open(sys.argv[1]) as f:
    for line in f:
        line = line.rstrip("\n")
        if not line:
            continue
        obj = json.loads(line)
        body = obj["prose_body"]
        if "\\\\foo\\\\bar" not in body and "\\foo\\bar" not in body:
            raise SystemExit("backslash content lost in escape: " + repr(body))
        if '"hello"' not in body:
            raise SystemExit("quote content lost in escape: " + repr(body))
        # Embedded newlines must round-trip as actual \n.
        if "line one" not in body or "line two" not in body:
            raise SystemExit("newline content lost: " + repr(body))
PY
    [ "$FAILS" -eq 0 ] && pass "(h) JSON escaping"
else
    pass "(h) skipped (no python3)"
fi

if [ "$FAILS" -eq 0 ]; then
    echo "PASS: all compose-review-findings tests passed"
    exit 0
else
    echo "FAIL: $FAILS test(s) failed" >&2
    exit 1
fi
