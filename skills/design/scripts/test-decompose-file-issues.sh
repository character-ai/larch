#!/usr/bin/env bash
# test-decompose-file-issues.sh — offline harness for decompose-file-issues.sh.
# Topology composition: offline prepare annotate close-original harness
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
DFI="$REPO_ROOT/skills/design/scripts/decompose-file-issues.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-decompose-dfi.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

[[ -x "$DFI" ]] || fail "decompose-file-issues.sh not executable"

BIN="$TMP/bin"
mkdir -p "$BIN"
cat >"$BIN/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail
log="${GH_STUB_LOG:?}"
printf '%s\n' "gh $*" >>"$log"
exit "${GH_STUB_RC:-0}"
GH
chmod +x "$BIN/gh"

cat >"$BIN/redact-stub.sh" <<'R'
#!/usr/bin/env bash
set -euo pipefail
touch "${REDACT_TOUCH:?}"
cat
R
chmod +x "$BIN/redact-stub.sh"

echo "=== prepare happy path ==="
D="$TMP/p1"
mkdir -p "$D"
printf 'feat' >"$D/feature-description.txt"
cat >"$D/part.md" <<'MD'
## Recommendation
split

## Pieces

### Piece 1: Alpha
- Scope: a
- Dependencies: none
- Diff_lines estimate: 1
- Why independently mergeable: x

### Piece 2: Beta
- Scope: b
- Dependencies: blocked-by Piece 1
- Diff_lines estimate: 2
- Why independently mergeable: y
MD
_out=$("$DFI" prepare --design-tmpdir "$D" --partition-file "$D/part.md" --issue-number 99 2>/dev/null || true)
printf '%s\n' "$_out" | grep -Fq 'DECOMPOSE_PARTITION_STATUS=ok' || fail "prepare ok status missing"
[[ -f "$D/decompose/partition-input.txt" ]] || fail "partition-input missing"
[[ -f "$D/decompose/partition-deps.tsv" ]] || fail "partition-deps missing"
grep -Fq $'1\t2' "$D/decompose/partition-deps.tsv" || fail "expected edge 1 blocks 2"

echo "=== prepare cycle ==="
D2="$TMP/p2"
mkdir -p "$D2"
printf 'f' >"$D2/feature-description.txt"
cat >"$D2/bad.md" <<'MD'
## Recommendation
split

## Pieces

### Piece 1: A
- Scope: a
- Dependencies: blocked-by Piece 2
- Diff_lines estimate: 1
- Why: x

### Piece 2: B
- Scope: b
- Dependencies: blocked-by Piece 1
- Diff_lines estimate: 1
- Why: y
MD
_out2=$("$DFI" prepare --design-tmpdir "$D2" --partition-file "$D2/bad.md" 2>/dev/null || true)
printf '%s\n' "$_out2" | grep -Fq 'DECOMPOSE_PARTITION_STATUS=cycle-detected' || fail "expected cycle"
[[ ! -f "$D2/decompose/partition-input.txt" ]] || fail "partition-input should not exist on cycle"

echo "=== annotate + idempotent second run ==="
D3="$TMP/p3"
mkdir -p "$D3/decompose"
cat >"$D3/issue.stdout" <<'OUT'
ISSUES_CREATED=2
ISSUES_FAILED=0
ISSUE_1_URL=https://example.com/1
ISSUE_2_URL=https://example.com/2
OUT
"$DFI" annotate --design-tmpdir "$D3" --issue-stdout-file "$D3/issue.stdout"
[[ -f "$D3/decompose/partition-filed.md" ]] || fail "partition-filed missing"
[[ -f "$D3/.decompose-issues-filed" ]] || fail "sentinel missing"
before=$(wc -c <"$D3/decompose/partition-filed.md")
"$DFI" annotate --design-tmpdir "$D3" --issue-stdout-file "$D3/issue.stdout"
after=$(wc -c <"$D3/decompose/partition-filed.md")
[[ "$before" == "$after" ]] || fail "annotate idempotency broke file size"

echo "=== close-original redaction + gh body-file ==="
D4="$TMP/p4"
mkdir -p "$D4/decompose"
cp "$D3/decompose/partition-filed.md" "$D4/decompose/partition-filed.md"
: >"$D4/execution-issues.md"
: >"$TMP/gh.log"
: >"$TMP/redact.touch"
PATH="$BIN:$PATH" \
    GH_STUB_LOG="$TMP/gh.log" \
    GH_STUB_RC=0 \
    REDACT_TOUCH="$TMP/redact.touch" \
    DECOMPOSE_REDACT_SH="$BIN/redact-stub.sh" \
    "$DFI" close-original --design-tmpdir "$D4" --original-issue 42 --repo "o/r" >"$D4/close.kv"
grep -Fq 'CLOSE_ORIGINAL_STATUS=ok' "$D4/close.kv" || fail "close status"
grep -Fq 'gh issue comment 42' "$TMP/gh.log" || fail "gh comment not logged"
grep -Fq -- '--body-file' "$TMP/gh.log" || fail "gh missing --body-file"
grep -Fq 'close-comment.redacted.md' "$TMP/gh.log" || fail "gh body-file not redacted path"
[[ -f "$TMP/redact.touch" ]] || fail "redact stub not invoked"
[[ -f "$D4/.decompose-original-closed" ]] || fail "close sentinel missing"

echo "=== close-original gh failure ==="
D5="$TMP/p5"
mkdir -p "$D5/decompose"
cp "$D4/decompose/partition-filed.md" "$D5/decompose/partition-filed.md"
: >"$D5/execution-issues.md"
: >"$TMP/gh2.log"
PATH="$BIN:$PATH" \
    GH_STUB_LOG="$TMP/gh2.log" \
    GH_STUB_RC=1 \
    REDACT_TOUCH="$TMP/redact2.touch" \
    DECOMPOSE_REDACT_SH="$BIN/redact-stub.sh" \
    set +e
"$DFI" close-original --design-tmpdir "$D5" --original-issue 7 --repo "o/r" >"$D5/close.kv" 2>/dev/null
_close_rc=$?
set -e
[[ "$_close_rc" != 0 ]] || fail "expected close-original to fail when gh returns non-zero"
grep -Fq 'CLOSE_ORIGINAL_STATUS=failed' "$D5/close.kv" || fail "expected failed close status"
[[ ! -f "$D5/.decompose-original-closed" ]] || fail "close sentinel should not exist on gh failure"

echo "PASS: test-decompose-file-issues.sh"
