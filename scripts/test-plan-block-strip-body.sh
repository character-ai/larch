#!/usr/bin/env bash
# test-plan-block-strip-body.sh — offline harness for plan-block-strip-body.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
STRIP="$REPO_ROOT/scripts/plan-block-strip-body.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-plan-block-strip-body.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() { echo "FAIL: $1" >&2; exit 1; }

cat >"$TMP/body.md" <<'BODY'
Intro

<!-- larch:plan:start -->
inside
<!-- larch:plan:end -->

Tail
BODY
"$STRIP" --file "$TMP/body.md" --output "$TMP/out.md"
cmp -s "$TMP/out.md" - <<'EXPECTED' || fail "well-formed strip removed wrong content"
Intro


Tail
EXPECTED

printf 'plain\nbody\n' >"$TMP/body.md"
"$STRIP" --file "$TMP/body.md" >"$TMP/out.md"
cmp -s "$TMP/out.md" "$TMP/body.md" || fail "zero-marker pass-through changed body"

check_malformed() {
    local name="$1" token="$2"
    set +e
    "$STRIP" --file "$TMP/${name}.md" --output "$TMP/${name}.out" >"$TMP/${name}.stdout"
    local rc=$?
    set -e
    [ "$rc" -eq 1 ] || fail "$name exit $rc"
    grep -Fq "MALFORMED=$token" "$TMP/${name}.stdout" || fail "$name token"
    [ ! -s "$TMP/${name}.out" ] || fail "$name should truncate output"
}

cat >"$TMP/multi-start.md" <<'BODY'
<!-- larch:plan:start -->
a
<!-- larch:plan:end -->
<!-- larch:plan:start -->
b
<!-- larch:plan:end -->
BODY
check_malformed multi-start multiple-start

cat >"$TMP/multi-end.md" <<'BODY'
<!-- larch:plan:start -->
a
<!-- larch:plan:end -->
<!-- larch:plan:end -->
BODY
check_malformed multi-end multiple-end

cat >"$TMP/start-without-end.md" <<'BODY'
<!-- larch:plan:start -->
a
BODY
check_malformed start-without-end start-without-end

cat >"$TMP/end-without-start.md" <<'BODY'
<!-- larch:plan:end -->
BODY
check_malformed end-without-start end-without-start

cat >"$TMP/end-before-start.md" <<'BODY'
<!-- larch:plan:end -->
a
<!-- larch:plan:start -->
BODY
check_malformed end-before-start end-before-start

echo "PASS: test-plan-block-strip-body.sh"
