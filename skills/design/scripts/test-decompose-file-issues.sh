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
grep -Fq 'DECOMPOSE_PARTITION_CYCLE_WITNESS=' "$D2/decompose/prepare-python.log" || fail "expected cycle witness in prepare log"
[[ ! -f "$D2/decompose/partition-input.txt" ]] || fail "partition-input should not exist on cycle"

echo "=== prepare multi-blocker comma list ==="
D2c="$TMP/p2c"
mkdir -p "$D2c"
printf 'feat' >"$D2c/feature-description.txt"
cat >"$D2c/part.md" <<'MD'
## Recommendation
split

## Pieces

### Piece 1: Alpha
- Scope: a
- Dependencies: none
- Diff_lines estimate: 1
- Why: x

### Piece 2: Beta
- Scope: b
- Dependencies: none
- Diff_lines estimate: 1
- Why: x

### Piece 3: Gamma
- Scope: c
- Dependencies: none
- Diff_lines estimate: 1
- Why: x

### Piece 4: Delta
- Scope: d
- Dependencies: none
- Diff_lines estimate: 1
- Why: x

### Piece 5: Epsilon
- Scope: e
- Dependencies: blocked-by Piece 1, Piece 2, Piece 3, Piece 4
- Diff_lines estimate: 5
- Why: y
MD
_out2c=$("$DFI" prepare --design-tmpdir "$D2c" --partition-file "$D2c/part.md" --issue-number 99 2>/dev/null || true)
printf '%s\n' "$_out2c" | grep -Fq 'DECOMPOSE_PARTITION_STATUS=ok' || fail "multi-blocker ok status missing"
[[ -f "$D2c/decompose/partition-deps.tsv" ]] || fail "multi-blocker deps tsv missing"
grep -Fq $'1\t5' "$D2c/decompose/partition-deps.tsv" || fail "expected edge 1->5 in multi-blocker"
grep -Fq $'2\t5' "$D2c/decompose/partition-deps.tsv" || fail "expected edge 2->5 in multi-blocker"
grep -Fq $'3\t5' "$D2c/decompose/partition-deps.tsv" || fail "expected edge 3->5 in multi-blocker"
grep -Fq $'4\t5' "$D2c/decompose/partition-deps.tsv" || fail "expected edge 4->5 in multi-blocker"
_edges2c=$(wc -l <"$D2c/decompose/partition-deps.tsv" | tr -d ' ')
[[ "$_edges2c" == "4" ]] || fail "expected 4 edges in multi-blocker tsv got $_edges2c"

echo "=== prepare bad-ref inside multi list ==="
D2d="$TMP/p2d"
mkdir -p "$D2d"
printf 'f' >"$D2d/feature-description.txt"
cat >"$D2d/part.md" <<'MD'
## Recommendation
split

## Pieces

### Piece 1: A
- Scope: a
- Dependencies: none
- Diff_lines estimate: 1
- Why: x

### Piece 2: B
- Scope: b
- Dependencies: blocked-by Piece 1, Piece 99
- Diff_lines estimate: 1
- Why: y
MD
set +e
_out2d=$("$DFI" prepare --design-tmpdir "$D2d" --partition-file "$D2d/part.md" 2>/dev/null)
_rc2d=$?
set -e
[[ "$_rc2d" -eq 2 ]] || fail "expected exit 2 on bad-ref in multi list got $_rc2d"
printf '%s\n' "$_out2d" | grep -Fq 'DECOMPOSE_PARTITION_STATUS=bad-dependency-ref' || fail "expected bad-dependency-ref status"
[[ ! -f "$D2d/decompose/partition-input.txt" ]] || fail "partition-input must not exist on bad-ref"
[[ ! -f "$D2d/decompose/partition-deps.tsv" ]] || fail "partition-deps must not exist on bad-ref"

echo "=== prepare and-separator multi-blocker ==="
D2e="$TMP/p2e"
mkdir -p "$D2e"
printf 'feat' >"$D2e/feature-description.txt"
cat >"$D2e/part.md" <<'MD'
## Recommendation
split

## Pieces

### Piece 1: Alpha
- Scope: a
- Dependencies: none
- Diff_lines estimate: 1
- Why: x

### Piece 2: Beta
- Scope: b
- Dependencies: none
- Diff_lines estimate: 1
- Why: x

### Piece 3: Gamma
- Scope: c
- Dependencies: blocked-by Piece 1 and Piece 2
- Diff_lines estimate: 2
- Why: y
MD
_out2e=$("$DFI" prepare --design-tmpdir "$D2e" --partition-file "$D2e/part.md" --issue-number 99 2>/dev/null || true)
printf '%s\n' "$_out2e" | grep -Fq 'DECOMPOSE_PARTITION_STATUS=ok' || fail "and-separator ok status missing"
[[ -f "$D2e/decompose/partition-deps.tsv" ]] || fail "and-separator deps tsv missing"
grep -Fq $'1\t3' "$D2e/decompose/partition-deps.tsv" || fail "expected edge 1->3 in and-separator"
grep -Fq $'2\t3' "$D2e/decompose/partition-deps.tsv" || fail "expected edge 2->3 in and-separator"
_edges2e=$(wc -l <"$D2e/decompose/partition-deps.tsv" | tr -d ' ')
[[ "$_edges2e" == "2" ]] || fail "expected 2 edges in and-separator tsv got $_edges2e"

echo "=== prepare duplicate-blocker idempotency ==="
D2f="$TMP/p2f"
mkdir -p "$D2f"
printf 'feat' >"$D2f/feature-description.txt"
cat >"$D2f/part.md" <<'MD'
## Recommendation
split

## Pieces

### Piece 1: Alpha
- Scope: a
- Dependencies: none
- Diff_lines estimate: 1
- Why: x

### Piece 2: Beta
- Scope: b
- Dependencies: blocked-by Piece 1, Piece 1
- Diff_lines estimate: 1
- Why: y
MD
_out2f=$("$DFI" prepare --design-tmpdir "$D2f" --partition-file "$D2f/part.md" --issue-number 99 2>/dev/null || true)
printf '%s\n' "$_out2f" | grep -Fq 'DECOMPOSE_PARTITION_STATUS=ok' || fail "dup-blocker ok status missing"
[[ -f "$D2f/decompose/partition-deps.tsv" ]] || fail "dup-blocker deps tsv missing"
grep -Fq $'1\t2' "$D2f/decompose/partition-deps.tsv" || fail "expected edge 1->2 in dup-blocker"
_edges2f=$(wc -l <"$D2f/decompose/partition-deps.tsv" | tr -d ' ')
[[ "$_edges2f" == "1" ]] || fail "expected 1 deduped edge in dup-blocker tsv got $_edges2f"

echo "=== prepare neutralizes embedded ^### in feature excerpt ==="
D2b="$TMP/p2b"
mkdir -p "$D2b"
printf $'intro\n\n### Not a batch item\n\nmore\n' >"$D2b/feature-description.txt"
cat >"$D2b/part.md" <<'MD'
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
"$DFI" prepare --design-tmpdir "$D2b" --partition-file "$D2b/part.md" --issue-number 1 >/dev/null 2>&1 || true
python3 - "$D2b" <<'PY' || fail "expected neutralized ### in batch body"
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
text = (root / "decompose" / "partition-input.txt").read_text(encoding="utf-8")
if "\u200b### Not a batch item" not in text:
    sys.exit(1)
PY

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

echo "=== annotate partial batch: no filing sentinel ==="
D3p="$TMP/p3p"
mkdir -p "$D3p/decompose"
cat >"$D3p/issue.stdout" <<'OUT'
ISSUES_CREATED=1
ISSUES_FAILED=2
ISSUE_1_URL=https://example.com/1
OUT
"$DFI" annotate --design-tmpdir "$D3p" --issue-stdout-file "$D3p/issue.stdout"
[[ -f "$D3p/decompose/partition-filed.md" ]] || fail "partition-filed missing for partial"
grep -Fq '**ISSUES_FAILED**: 2' "$D3p/decompose/partition-filed.md" || fail "expected ISSUES_FAILED in record"
[[ ! -f "$D3p/.decompose-issues-filed" ]] || fail "sentinel must not exist when ISSUES_FAILED>0"

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
set +e
PATH="$BIN:$PATH" \
    GH_STUB_LOG="$TMP/gh2.log" \
    GH_STUB_RC=1 \
    REDACT_TOUCH="$TMP/redact2.touch" \
    DECOMPOSE_REDACT_SH="$BIN/redact-stub.sh" \
    "$DFI" close-original --design-tmpdir "$D5" --original-issue 7 --repo "o/r" >"$D5/close.kv" 2>/dev/null
_close_rc=$?
set -e
[[ "$_close_rc" != 0 ]] || fail "expected close-original to fail when gh returns non-zero"
grep -Fq 'CLOSE_ORIGINAL_STATUS=failed' "$D5/close.kv" || fail "expected failed close status"
BIN2="$TMP/bin2"
mkdir -p "$BIN2"
cat >"$BIN2/gh" <<'GH2'
#!/usr/bin/env bash
set -euo pipefail
log="${GH_STUB_LOG:?}"
printf '%s\n' "gh $*" >>"$log"
if [[ "$*" == issue\ comment\ * ]]; then
  exit "${GH_COMMENT_RC:-0}"
fi
if [[ "$*" == issue\ close\ * ]]; then
  exit "${GH_CLOSE_RC:-0}"
fi
exit 0
GH2
chmod +x "$BIN2/gh"

echo "=== close-original skips duplicate comment after close failure ==="
D6="$TMP/p6"
mkdir -p "$D6/decompose"
cp "$D4/decompose/partition-filed.md" "$D6/decompose/partition-filed.md"
: >"$D6/execution-issues.md"
: >"$TMP/gh3.log"
hash -r
set +e
PATH="$BIN2:$PATH" \
    GH_STUB_LOG="$TMP/gh3.log" \
    GH_COMMENT_RC=0 \
    GH_CLOSE_RC=1 \
    REDACT_TOUCH="$TMP/redact3.touch" \
    DECOMPOSE_REDACT_SH="$BIN/redact-stub.sh" \
    "$DFI" close-original --design-tmpdir "$D6" --original-issue 99 --repo "o/r" >/dev/null 2>&1
set -e
[[ ! -f "$D6/.decompose-original-closed" ]] || fail "expected no close sentinel when gh close fails"
grep -Fq 'gh issue close' "$TMP/gh3.log" || fail "expected close attempt"
_c0=$(grep -c 'issue comment' "$TMP/gh3.log" || true)
[[ "$_c0" -eq 1 ]] || fail "expected single comment invocation before close failure"

hash -r
PATH="$BIN2:$PATH" \
    GH_STUB_LOG="$TMP/gh3.log" \
    GH_COMMENT_RC=0 \
    GH_CLOSE_RC=0 \
    REDACT_TOUCH="$TMP/redact3b.touch" \
    DECOMPOSE_REDACT_SH="$BIN/redact-stub.sh" \
    "$DFI" close-original --design-tmpdir "$D6" --original-issue 99 --repo "o/r" >/dev/null
[[ -f "$D6/.decompose-original-closed" ]] || fail "close sentinel after retry"
_c1=$(grep -c 'issue comment' "$TMP/gh3.log" || true)
[[ "$_c1" -eq 1 ]] || fail "expected no second gh issue comment on retry got $_c1"
grep -Fq 'gh issue close' "$TMP/gh3.log" || fail "expected close on retry"

echo "PASS: test-decompose-file-issues.sh"
