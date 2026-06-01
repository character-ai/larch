#!/usr/bin/env bash
# Offline unit harness for scripts/step-telemetry-mark.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
HELPER="$REPO_ROOT/scripts/step-telemetry-mark.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[[ -x "$HELPER" ]] || fail "step-telemetry-mark.sh must be executable (git mode 0755)"

TMP_BASE="$(mktemp -d "${TMPDIR:-/tmp}/test-step-telemetry-mark.XXXXXX")"
trap 'rm -rf "$TMP_BASE"' EXIT

sha256_hex() {
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "$1" | LC_ALL=C shasum -a 256 | awk '{print $1}'
  else
    printf '%s' "$1" | sha256sum | awk '{print $1}'
  fi
}

# Happy path: both ledger rows for the supplied label.
IMPL_TMP="$TMP_BASE/impl-happy"
mkdir -p "$IMPL_TMP"
TIMING_LEDGER="$IMPL_TMP/timing-ledger.tsv"
cat > "$IMPL_TMP/session-env.sh" <<EOF
LARCH_TOKEN_SESSION_ID=harness-session-id
LARCH_CLAUDE_SOURCE_FILE=/dev/null
LARCH_TIMING_LEDGER=$TIMING_LEDGER
EOF

LABEL="Step probe — harness"
"$HELPER" --implement-tmpdir "$IMPL_TMP" --label "$LABEL" || fail "happy path should exit 0"

slug=$(sha256_hex "harness-session-id")
TOKEN_LEDGER="$IMPL_TMP/larch-tokens-${slug}.jsonl"
[[ -f "$TOKEN_LEDGER" ]] || fail "token ledger not created: $TOKEN_LEDGER"
[[ -f "$TIMING_LEDGER" ]] || fail "timing ledger not created: $TIMING_LEDGER"

if jq -e --arg step "$LABEL" 'select(.type=="mark" and .step==$step)' "$TOKEN_LEDGER" >/dev/null; then
  :
else
  fail "token ledger missing mark for label"
fi

grep -Fq "$LABEL" "$TIMING_LEDGER" || fail "timing ledger missing mark row for label"

# Bad --implement-tmpdir: never fatal.
BAD_TMP="$TMP_BASE/no-such-dir"
"$HELPER" --implement-tmpdir "$BAD_TMP" --label "bad tmpdir" || fail "bad tmpdir should exit 0"

# Omitted --implement-tmpdir: never fatal under set -u in the helper.
"$HELPER" --label "omitted tmpdir" || fail "omitted --implement-tmpdir should exit 0"

# Missing --label: never fatal.
"$HELPER" --implement-tmpdir "$IMPL_TMP" || fail "missing --label should exit 0"

echo "PASS: test-step-telemetry-mark.sh"
