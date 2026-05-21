#!/usr/bin/env bash
# test-plan-block.sh — offline harness for plan-block-read.sh / plan-block-write.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
READ="$REPO_ROOT/scripts/plan-block-read.sh"
WRITE="$REPO_ROOT/scripts/plan-block-write.sh"

if ! [ -x "$READ" ] || ! [ -x "$WRITE" ]; then
    echo "FAIL: plan-block scripts not executable" >&2
    exit 1
fi

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-plan-block.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

ORIG_PATH="$PATH"
STUB="$TMP/stub"
mkdir -p "$STUB"
BODY_FILE="$TMP/issue-body.txt"
EDIT_CAPTURE="$TMP/edit-body.txt"
export BODY_FILE EDIT_CAPTURE

cat > "$STUB/gh" <<'GHSTUB'
#!/usr/bin/env bash
set -euo pipefail
if [ "$1" = "repo" ] && [ "$2" = "view" ]; then
    printf '%s\n' 'owner/repo'
    exit 0
fi
if [ "$1" = "issue" ] && [ "$2" = "view" ]; then
    if [ ! -f "$BODY_FILE" ]; then
        echo "stub: missing BODY_FILE" >&2
        exit 2
    fi
    jq -n --rawfile b "$BODY_FILE" '{body: $b}' | jq -c .
    exit 0
fi
if [ "$1" = "issue" ] && [ "$2" = "edit" ]; then
    i=1
    while [ "$i" -le "$#" ]; do
        eval "a=\${$i}"
        if [ "$a" = "--body-file" ]; then
            n=$((i + 1))
            eval "bf=\${$n}"
            cp "$bf" "$EDIT_CAPTURE"
            exit 0
        fi
        i=$((i + 1))
    done
    echo "stub: no --body-file" >&2
    exit 2
fi
if [ "$1" = "issue" ] && [ "$2" = "comment" ]; then
    echo "https://github.com/owner/repo/issues/99#issuecomment-1"
    exit 0
fi
echo "stub: unhandled $*" >&2
exit 2
GHSTUB

chmod +x "$STUB/gh"
export PATH="$STUB:$ORIG_PATH"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

echo "=== read: well-formed block ==="
cat > "$BODY_FILE" <<'B'
Intro line

<!-- larch:plan:start -->
INNER LINE
<!-- larch:plan:end -->

tail
B
OUT="$TMP/out1.txt"
PATH="$STUB:$ORIG_PATH" "$READ" --issue 1 --output "$OUT" --repo owner/repo >"$TMP/read.out" || fail "read exit $?"
grep -q 'BLOCK_PRESENT=true' "$TMP/read.out" || fail "missing BLOCK_PRESENT=true"
grep -q "OUTPUT=$OUT" "$TMP/read.out" || fail "missing OUTPUT="
[ "$(cat "$OUT")" = "$(printf 'INNER LINE\n')" ] || fail "inner content wrong: $(cat -A "$OUT")"

echo "=== read: no markers ==="
printf 'plain\n' > "$BODY_FILE"
OUT="$TMP/out2.txt"
: >"$OUT"
PATH="$STUB:$ORIG_PATH" "$READ" --issue 1 --output "$OUT" --repo owner/repo >"$TMP/read2.out" || fail "read2 exit"
grep -q 'BLOCK_PRESENT=false' "$TMP/read2.out" || fail "expected false"
[ ! -s "$OUT" ] || fail "output should be empty"

echo "=== read: start without end ==="
cat > "$BODY_FILE" <<'B'
<!-- larch:plan:start -->
only start
B
OUT="$TMP/out3.txt"
set +e
PATH="$STUB:$ORIG_PATH" "$READ" --issue 1 --output "$OUT" --repo owner/repo >"$TMP/read3.out"
rc=$?
set -e
[ "$rc" = "1" ] || fail "start-without-end exit $rc"
grep -q 'MALFORMED=start-without-end' "$TMP/read3.out" || fail "missing malformed token"

echo "=== read: end without start ==="
cat > "$BODY_FILE" <<'B'
<!-- larch:plan:end -->
B
set +e
PATH="$STUB:$ORIG_PATH" "$READ" --issue 1 --output "$OUT" --repo owner/repo >"$TMP/read4.out"
rc=$?
set -e
[ "$rc" = "1" ] || fail "end-without-start exit $rc"
grep -q 'MALFORMED=end-without-start' "$TMP/read4.out" || fail "missing end-without-start"

echo "=== read: multiple start ==="
cat > "$BODY_FILE" <<'B'
<!-- larch:plan:start -->
a
<!-- larch:plan:end -->
<!-- larch:plan:start -->
b
<!-- larch:plan:end -->
B
set +e
PATH="$STUB:$ORIG_PATH" "$READ" --issue 1 --output "$OUT" --repo owner/repo >"$TMP/read5.out"
rc=$?
set -e
[ "$rc" = "1" ] || fail "multiple start exit $rc"
grep -q 'MALFORMED=multiple-start' "$TMP/read5.out" || fail "multiple-start"

echo "=== read: multiple end ==="
cat > "$BODY_FILE" <<'B'
<!-- larch:plan:start -->
x
<!-- larch:plan:end -->
<!-- larch:plan:end -->
B
set +e
PATH="$STUB:$ORIG_PATH" "$READ" --issue 1 --output "$OUT" --repo owner/repo >"$TMP/read5b.out"
rc=$?
set -e
[ "$rc" = "1" ] || fail "multiple end exit $rc"
grep -q 'MALFORMED=multiple-end' "$TMP/read5b.out" || fail "multiple-end"
[ ! -s "$OUT" ] || fail "malformed read should truncate --output"

echo "=== read: malformed truncates stale --output ==="
printf 'STALE_INNER\n' > "$OUT"
cat > "$BODY_FILE" <<'B'
<!-- larch:plan:start -->
only start
B
set +e
PATH="$STUB:$ORIG_PATH" "$READ" --issue 1 --output "$OUT" --repo owner/repo >"$TMP/read3b.out"
rc=$?
set -e
[ "$rc" = "1" ] || fail "stale truncate exit $rc"
grep -q 'MALFORMED=start-without-end' "$TMP/read3b.out" || fail "stale truncate token"
[ ! -s "$OUT" ] || fail "stale inner markdown should be cleared"

echo "=== read: end before start ==="
cat > "$BODY_FILE" <<'B'
<!-- larch:plan:end -->
mid
<!-- larch:plan:start -->
B
set +e
PATH="$STUB:$ORIG_PATH" "$READ" --issue 1 --output "$OUT" --repo owner/repo >"$TMP/read6.out"
rc=$?
set -e
[ "$rc" = "1" ] || fail "end-before-start exit $rc"
grep -q 'MALFORMED=end-before-start' "$TMP/read6.out" || fail "end-before-start"

echo "=== read: leading whitespace markers ==="
cat > "$BODY_FILE" <<'B'
  <!-- larch:plan:start -->
inner
  <!-- larch:plan:end -->
B
OUT="$TMP/out7.txt"
PATH="$STUB:$ORIG_PATH" "$READ" --issue 1 --output "$OUT" --repo owner/repo >"$TMP/read7.out" || fail "read ws exit"
grep -q 'BLOCK_PRESENT=true' "$TMP/read7.out" || fail "ws true"
[ "$(cat "$OUT")" = "$(printf 'inner\n')" ] || fail "ws inner"

echo "=== write: append (no markers) ==="
printf 'hello' > "$BODY_FILE"
CONTENT="$TMP/newcontent.txt"
printf 'NEWBODY\n' > "$CONTENT"
rm -f "$EDIT_CAPTURE"
PATH="$STUB:$ORIG_PATH" "$WRITE" --issue 99 --content-file "$CONTENT" --repo owner/repo >"$TMP/w1.out" || fail "write append"
grep -q 'MODE=appended' "$TMP/w1.out" || fail "append mode"
grep -q 'MARKERS_PRESENT=false' "$TMP/w1.out" || fail "markers absent"
[ -f "$EDIT_CAPTURE" ] || fail "no edit capture"
grep -q 'hello' "$EDIT_CAPTURE" || fail "lost hello"
grep -q '<!-- larch:plan:start -->' "$EDIT_CAPTURE" || fail "no start marker"
grep -q 'NEWBODY' "$EDIT_CAPTURE" || fail "no new body"
grep -q '<!-- larch:plan:end -->' "$EDIT_CAPTURE" || fail "no end marker"

echo "=== write: replace inner ==="
cat > "$BODY_FILE" <<'B'
before
<!-- larch:plan:start -->
OLD
<!-- larch:plan:end -->
after
B
printf 'REPLACED\n' > "$CONTENT"
rm -f "$EDIT_CAPTURE"
PATH="$STUB:$ORIG_PATH" "$WRITE" --issue 99 --content-file "$CONTENT" --repo owner/repo >"$TMP/w2.out" || fail "write replace"
grep -q 'MODE=replaced' "$TMP/w2.out" || fail "replaced"
grep -q 'MARKERS_PRESENT=true' "$TMP/w2.out" || fail "markers were present"
grep -q '^before$' "$EDIT_CAPTURE" || fail "lost before"
grep -q '^after$' "$EDIT_CAPTURE" || fail "lost after"
grep -q 'REPLACED' "$EDIT_CAPTURE" || fail "no replaced"
! grep -q '^OLD$' "$EDIT_CAPTURE" || fail "OLD still present"

echo "=== write: malformed refuses ==="
cat > "$BODY_FILE" <<'B'
<!-- larch:plan:start -->
no end
B
set +e
PATH="$STUB:$ORIG_PATH" "$WRITE" --issue 99 --content-file "$CONTENT" --repo owner/repo >"$TMP/w3.out"
rc=$?
set -e
[ "$rc" = "1" ] || fail "write malformed exit $rc"
grep -q 'MALFORMED=start-without-end' "$TMP/w3.out" || fail "write malformed token"

echo "=== write: multiple end ==="
cat > "$BODY_FILE" <<'B'
<!-- larch:plan:start -->
x
<!-- larch:plan:end -->
<!-- larch:plan:end -->
B
set +e
PATH="$STUB:$ORIG_PATH" "$WRITE" --issue 99 --content-file "$CONTENT" --repo owner/repo >"$TMP/w3b.out"
rc=$?
set -e
[ "$rc" = "1" ] || fail "write multiple-end exit $rc"
grep -q 'MALFORMED=multiple-end' "$TMP/w3b.out" || fail "write multiple-end token"

echo "=== write: empty body append ==="
: > "$BODY_FILE"
printf 'only\n' > "$CONTENT"
rm -f "$EDIT_CAPTURE"
PATH="$STUB:$ORIG_PATH" "$WRITE" --issue 99 --content-file "$CONTENT" --repo owner/repo >"$TMP/w4.out" || fail "empty append"
grep -q 'MODE=appended' "$TMP/w4.out" || fail "empty append mode"
head -1 "$EDIT_CAPTURE" | grep -q '<!-- larch:plan:start -->' || fail "empty body should start with marker block"

LABEL_HELPER="$REPO_ROOT/scripts/clarify-label.sh"
[ -x "$LABEL_HELPER" ] || fail "clarify-label.sh not executable"
grep -Fq -- '--create-if-missing' "$LABEL_HELPER" || fail "clarify-label.sh missing --create-if-missing flag"

echo "All assertions passed."
