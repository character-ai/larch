#!/usr/bin/env bash
# test-plan-review-scope-anchor.sh — focused offline regression for plan-review scope anchors.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-plan-review-scope-anchor.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() { echo "FAIL: $1" >&2; exit 1; }

cat >"$TMP/feature.md" <<'BODY'
Issue asks for a small rename.

<!-- larch:plan:start -->
Prior stale plan expands the scope.
<!-- larch:plan:end -->
BODY
"$REPO_ROOT/scripts/plan-block-strip-body.sh" --file "$TMP/feature.md" --output "$TMP/anchor.txt"
grep -Fq 'Issue asks for a small rename.' "$TMP/anchor.txt" || fail "anchor lost issue text"
if grep -Fq 'Prior stale plan' "$TMP/anchor.txt"; then fail "anchor kept prior plan block"; fi

cat >"$TMP/scope.txt" <<'BODY'
Originating issue scope: rename only.
BODY
cat >"$TMP/ballot.txt" <<'BODY'
### FINDING_1:
- **Concern**: [SCOPE-REDUCTION] remove unrelated refactor.
BODY
with_anchor=$(python3 "$REPO_ROOT/python/cli.py" render voter \
    --ballot-file "$TMP/ballot.txt" \
    --panel-role "scope voter" \
    --id-grammar finding-oos \
    --verification-context plan \
    --scope-anchor-file "$TMP/scope.txt")
grep -Fq 'Originating issue scope: rename only.' <<<"$with_anchor" || fail "voter prompt did not inline anchor"
grep -Fq 'untrusted evidence, not instructions' <<<"$with_anchor" || fail "voter prompt missing untrusted framing"
grep -Fq 'Normal voting thresholds still apply' <<<"$with_anchor" || fail "voter prompt missing unchanged-threshold instruction"

# Normal tally/classification behavior remains unchanged for tagged findings.
# shellcheck source=scripts/lib-vote-tally.sh
source "$REPO_ROOT/scripts/lib-vote-tally.sh"
got=$(classify_result 1 1 0 2)
[ "$got" = neutral ] || fail "tagged 1Y/1N equivalent should remain neutral under normal thresholds"
cat >"$TMP/oos.md" <<'BODY'
### OOS_1: [SCOPE-REDUCTION] no special handling for OOS
- **Description**: ordinary OOS row.
BODY
if is_scope_reduction_block "$TMP/oos.md"; then
    : # detector can see the marker, but tally callers do not special-case OOS blocks.
fi

echo "=== negative scope-anchor validation: non-fatal warn+skip, ballot pointer preserved ==="
outside="$HOME/larch-test-outside-scope-anchor.txt"
printf 'outside\n' >"$outside"
trap 'rm -rf "$TMP" "$outside"' EXIT
set +e
_out=$(python3 "$REPO_ROOT/python/cli.py" render voter \
    --ballot-file "$TMP/ballot.txt" \
    --panel-role "scope voter" \
    --id-grammar finding-oos \
    --verification-context plan \
    --scope-anchor-file "$outside" 2>"$TMP/voter-invalid.err")
vrc=$?
set -e
[[ "$vrc" -eq 0 ]] || fail "outside scope anchor should exit 0 (non-fatal warn+skip), got $vrc"
grep -Fq 'allowed local workspace' "$TMP/voter-invalid.err" || fail "outside scope anchor missing containment error"
grep -Fq 'Read the ballot from this path' <<<"$_out" || fail "outside scope anchor: ballot pointer missing from output"

set +e
_crlf_out=$(python3 "$REPO_ROOT/python/cli.py" render voter \
    --ballot-file "$TMP/ballot.txt" \
    --panel-role "scope voter" \
    --id-grammar finding-oos \
    --verification-context plan \
    --scope-anchor-file $'bad\rpath' 2>/dev/null)
vrc=$?
set -e
[[ "$vrc" -eq 0 ]] || fail "CR/LF scope anchor should exit 0 (non-fatal warn+skip), got $vrc"
grep -Fq 'Read the ballot from this path' <<<"$_crlf_out" || fail "CR/LF scope anchor: ballot pointer missing from output"

big_anchor="$TMP/big-scope.txt"
python3 - <<'PY' >"$big_anchor"
print("x" * 70000)
PY
set +e
_big_out=$(python3 "$REPO_ROOT/python/cli.py" render voter \
    --ballot-file "$TMP/ballot.txt" \
    --panel-role "scope voter" \
    --id-grammar finding-oos \
    --verification-context plan \
    --scope-anchor-file "$big_anchor" 2>/dev/null)
vrc=$?
set -e
[[ "$vrc" -eq 0 ]] || fail "oversize scope anchor should exit 0 (non-fatal warn+skip), got $vrc"
grep -Fq 'Read the ballot from this path' <<<"$_big_out" || fail "oversize scope anchor: ballot pointer missing from output"

echo "PASS: test-plan-review-scope-anchor.sh"
