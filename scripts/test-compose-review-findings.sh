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
#   (e) inline ↔ archive switchover at the configured threshold, with no
#       leftover same-directory archive tempfile
#   (f) archive content shape (JSONL — one record per line, valid JSON)
#   (g) category derivation maps reviewer-name fragments to canonical tags
#   (h) JSON escaping handles control bytes, carriage returns, quotes, and newlines
#   (i) missing jq fails closed before writing an archive
#   (j) archive mode redacts token-shaped secrets
#   (k) inline mode also redacts token-shaped secrets
#   (l) redactor failure surfaces the documented failure envelope
#
# Self-contained: creates fixtures under a fresh tmpdir and cleans up.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE="$SCRIPT_DIR/compose-review-findings.sh"
BASH_BIN=$(command -v bash || true)
REAL_JQ=$(command -v jq || true)

[ -x "$COMPOSE" ] || { echo "FAIL: $COMPOSE not executable" >&2; exit 1; }
if [ -z "$BASH_BIN" ] || [ ! -x "$BASH_BIN" ]; then
    echo "FAIL: bash not found on PATH" >&2
    exit 1
fi
if [ -z "$REAL_JQ" ] || [ ! -x "$REAL_JQ" ]; then
    echo "FAIL: jq not found on PATH" >&2
    exit 1
fi

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
archive_entries=("$TMP/e-archive"/*)
if [ "${#archive_entries[@]}" -ne 1 ] || [ "${archive_entries[0]}" != "$TMP/e-archive/issue-99.jsonl" ]; then
    fail "(e) archive directory should contain only the published JSONL"
fi
grep -q 'Inline payload exceeded' "$out_e" || fail "(e) pointer text missing"
grep -q 'Archive path' "$out_e" || fail "(e) archive path bullet missing"
[ "$FAILS" -eq 0 ] && pass "(e) archive switchover"

# --------------------------------------------------------------------------
# (f) Archive content shape: one JSON object per line, parseable
# --------------------------------------------------------------------------
echo "=== (f) Archive content shape ==="
line_count=$(wc -l < "$TMP/e-archive/issue-99.jsonl" | tr -d ' ')
[ "$line_count" -gt 0 ] || fail "(f) archive empty"
while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] || continue
    printf '%s\n' "$line" | "$REAL_JQ" -e '
        has("id") and has("phase") and has("outcome") and
        has("reviewer") and has("category") and has("prose_body")
    ' >/dev/null || fail "(f) JSONL parse/key failure"
done < "$TMP/e-archive/issue-99.jsonl"
[ "$FAILS" -eq 0 ] && pass "(f) JSONL shape"

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
mkdir -p "$TMP/h-design" "$TMP/h-impl" "$TMP/h-archive"
{
    # FINDING ids are constrained by FINDING_[0-9A-Za-z_]+, so quote/control
    # coverage belongs in pending_title, reviewer, and prose_body rather than id.
    printf '### FINDING_1: title with "quote", newline coverage, and carriage\rreturn\n'
    printf -- '- **Concern**: controls \001 \007 \033, CR\r, and quote "hello".\n'
    printf -- '- **Resolution**: line one\nline two with backslashes \\\\foo\\\\bar\n'
} > "$TMP/h-design/accepted-plan-findings.md"
{
    printf '### [Code Review] Cursor-Generic "quoted" \007\n'
    printf '**Finding**: code-review body with escape \033 and carriage\rreturn.\n'
    printf '**Reason not implemented**: second line with "quote".\n'
} > "$TMP/h-impl/rejected-findings.md"
out_h="$TMP/h-out.md"
"$COMPOSE" \
    --design-artifacts-dir "$TMP/h-design" \
    --implement-tmpdir "$TMP/h-impl" \
    --issue 7 \
    --output "$out_h" \
    --archive-dir "$TMP/h-archive" \
    --archive-threshold 1 >/dev/null 2>&1 || fail "(h) compose failed"
[ -f "$TMP/h-archive/issue-7.jsonl" ] || fail "(h) archive missing"
while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] || continue
    printf '%s\n' "$line" | "$REAL_JQ" -e . >/dev/null || fail "(h) JSONL line is not parseable"
done < "$TMP/h-archive/issue-7.jsonl"
"$REAL_JQ" -s -e '
    any(.[]; .id == "FINDING_1"
        and (.prose_body | contains("title with \"quote\""))
        and (.prose_body | contains("\u0001"))
        and (.prose_body | contains("\u0007"))
        and (.prose_body | contains("\u001b"))
        and (.prose_body | contains("\r"))
        and (.prose_body | contains("line one\nline two"))
        and (.prose_body | contains("\\\\foo\\\\bar")))
    and
    any(.[]; .id == "REJ_C1"
        and (.reviewer | contains("\"quoted\""))
        and (.reviewer | contains("\u0007"))
        and (.prose_body | contains("\u001b"))
        and (.prose_body | contains("\r")))
' "$TMP/h-archive/issue-7.jsonl" >/dev/null || fail "(h) escaped fields did not round-trip"
[ "$FAILS" -eq 0 ] && pass "(h) JSON escaping"

# --------------------------------------------------------------------------
# (i) jq unavailable fails closed
# --------------------------------------------------------------------------
echo "=== (i) Missing jq fails closed ==="
mkdir -p "$TMP/i-design" "$TMP/i-impl" "$TMP/i-archive" "$TMP/i-bin"
out_i="$TMP/i-out.md"
stdout_i="$TMP/i-stdout.txt"
stderr_i="$TMP/i-stderr.txt"
EXIT_I=0
env PATH="$TMP/i-bin" "$BASH_BIN" "$COMPOSE" \
    --design-artifacts-dir "$TMP/i-design" \
    --implement-tmpdir "$TMP/i-impl" \
    --issue 8 \
    --output "$out_i" \
    --archive-dir "$TMP/i-archive" \
    --archive-threshold 1 >"$stdout_i" 2>"$stderr_i" || EXIT_I=$?
[ "$EXIT_I" -eq 2 ] || fail "(i) expected exit 2 without jq, got $EXIT_I"
grep -qxF 'FAILED=true' "$stdout_i" || fail "(i) missing FAILED=true"
grep -q 'jq is required for compose-review-findings.sh' "$stdout_i" || fail "(i) missing jq-required error"
[ ! -e "$TMP/i-archive/issue-8.jsonl" ] || fail "(i) archive was written despite missing jq"
[ "$FAILS" -eq 0 ] && pass "(i) missing jq fail-closed"

# --------------------------------------------------------------------------
# (j) Archive mode redacts token-shaped secrets
# --------------------------------------------------------------------------
echo "=== (j) Archive mode redacts token-shaped secrets ==="
SK_PREFIX='sk-'
SK_MID='ant-api03-'
SK_TOKEN="${SK_PREFIX}${SK_MID}FAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKE"
printf '%s' "$SK_TOKEN" | "$SCRIPT_DIR/redact-secrets.sh" | grep -qxF '<REDACTED-TOKEN>' \
    || fail "(j) fixture token did not match redact-secrets.sh"
mkdir -p "$TMP/j-design" "$TMP/j-impl" "$TMP/j-archive"
{
    printf '### [Code Review] Cursor-Security\n'
    printf '**Finding**: token fixture %s\n' "$SK_TOKEN"
    for _ in $(seq 1 12); do
        printf 'Filler line to force archive mode while carrying the secret fixture through redaction.\n'
    done
    printf '**Reason not implemented**: regression fixture.\n'
} > "$TMP/j-impl/rejected-findings.md"
out_j="$TMP/j-out.md"
stdout_j=$("$COMPOSE" \
    --design-artifacts-dir "$TMP/j-design" \
    --implement-tmpdir "$TMP/j-impl" \
    --issue 9 \
    --output "$out_j" \
    --archive-dir "$TMP/j-archive" \
    --archive-threshold 100 2>&1)
grep -qxF 'MODE=archive' <<<"$stdout_j" || fail "(j) expected archive mode"
grep -Fq '<REDACTED-TOKEN>' "$TMP/j-archive/issue-9.jsonl" || fail "(j) archive missing redacted token"
! grep -Fq "$SK_TOKEN" "$TMP/j-archive/issue-9.jsonl" || fail "(j) archive leaked raw token"
! grep -Fq "$SK_TOKEN" "$out_j" || fail "(j) inline pointer leaked raw token"
[ "$FAILS" -eq 0 ] && pass "(j) archive redaction"

# --------------------------------------------------------------------------
# (k) Inline mode also redacts token-shaped secrets
# --------------------------------------------------------------------------
echo "=== (k) Inline mode redacts token-shaped secrets ==="
mkdir -p "$TMP/k-design" "$TMP/k-impl"
{
    printf '### [Code Review] Cursor-Security\n'
    printf '**Finding**: inline token fixture %s\n' "$SK_TOKEN"
    printf '**Reason not implemented**: regression fixture.\n'
} > "$TMP/k-impl/rejected-findings.md"
out_k="$TMP/k-out.md"
stdout_k=$("$COMPOSE" \
    --design-artifacts-dir "$TMP/k-design" \
    --implement-tmpdir "$TMP/k-impl" \
    --issue 10 \
    --output "$out_k" 2>&1)
grep -qxF 'MODE=inline' <<<"$stdout_k" || fail "(k) expected inline mode"
grep -Fq '<REDACTED-TOKEN>' "$out_k" || fail "(k) inline output missing redacted token"
! grep -Fq "$SK_TOKEN" "$out_k" || fail "(k) inline output leaked raw token"
[ "$FAILS" -eq 0 ] && pass "(k) inline redaction"

# --------------------------------------------------------------------------
# (l) Redactor failure surfaces FAILED envelope
# --------------------------------------------------------------------------
echo "=== (l) Redactor failure surfaces FAILED envelope ==="
mkdir -p "$TMP/l-bin" "$TMP/l-design" "$TMP/l-impl"
cp "$COMPOSE" "$TMP/l-bin/compose-review-findings.sh"
cp "$SCRIPT_DIR/redact-tmpdir-paths.sh" "$TMP/l-bin/redact-tmpdir-paths.sh"
cat > "$TMP/l-bin/redact-secrets.sh" <<'EOF_REDACTOR_FAIL'
#!/bin/sh
exit 1
EOF_REDACTOR_FAIL
chmod +x "$TMP/l-bin/compose-review-findings.sh" "$TMP/l-bin/redact-tmpdir-paths.sh" "$TMP/l-bin/redact-secrets.sh"
cat > "$TMP/l-impl/rejected-findings.md" <<'EOF_L'
### [Code Review] Cursor-Security
**Finding**: body
**Reason not implemented**: reason
EOF_L
out_l="$TMP/l-out.md"
stdout_l="$TMP/l-stdout.txt"
stderr_l="$TMP/l-stderr.txt"
EXIT_L=0
"$BASH_BIN" "$TMP/l-bin/compose-review-findings.sh" \
    --design-artifacts-dir "$TMP/l-design" \
    --implement-tmpdir "$TMP/l-impl" \
    --issue 11 \
    --output "$out_l" >"$stdout_l" 2>"$stderr_l" || EXIT_L=$?
[ "$EXIT_L" -eq 2 ] || fail "(l) expected exit 2 on redactor failure, got $EXIT_L"
grep -qxF 'FAILED=true' "$stdout_l" || fail "(l) missing FAILED=true"
grep -q 'redaction failed for prose_body' "$stdout_l" || fail "(l) missing redaction failure error"
[ "$FAILS" -eq 0 ] && pass "(l) redactor failure envelope"

if [ "$FAILS" -eq 0 ]; then
    echo "PASS: all compose-review-findings tests passed"
    exit 0
else
    echo "FAIL: $FAILS test(s) failed" >&2
    exit 1
fi
