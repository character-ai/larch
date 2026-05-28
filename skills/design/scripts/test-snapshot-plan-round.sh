#!/usr/bin/env bash
# Offline harness for snapshot-plan-round.sh
set -euo pipefail
export LARCH_QUIET_DISABLE=1

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/snapshot-plan-round.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

bash -n "$SUBJECT" || fail 'bash -n failed'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/tspr.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP"
printf 'plan v1\n' >"$TMP/plan.txt"

"$SUBJECT" write-original --design-tmpdir "$TMP" >/dev/null 2>&1 || fail 'write-original failed'
[[ -f "$TMP/plan.txt-original" ]] || fail 'missing plan.txt-original'
out2=$("$SUBJECT" write-original --design-tmpdir "$TMP" 2>&1) || fail 'write-original second failed'
printf '%s\n' "$out2" | grep -Fq 'already exists' || fail 'second write-original must preserve'

"$SUBJECT" write-after --design-tmpdir "$TMP" --round 1 >/dev/null
[[ -f "$TMP/plan-after-round-1.txt" ]] || fail 'missing plan-after-round-1'

cursor=$("$SUBJECT" read-cursor --design-tmpdir "$TMP")
printf '%s\n' "$cursor" | grep -Fq 'ROUND_CURSOR=1' || fail 'default cursor not 1'

printf '2\n' >"$TMP/plan-review-round-cursor.txt"
cursor2=$("$SUBJECT" read-cursor --design-tmpdir "$TMP")
printf '%s\n' "$cursor2" | grep -Fq 'ROUND_CURSOR=2' || fail 'cursor read failed'

printf '2 trailing\n' >"$TMP/plan-review-round-cursor.txt"
warn=$("$SUBJECT" read-cursor --design-tmpdir "$TMP" 2>&1)
printf '%s\n' "$warn" | grep -Fq 'defaulting to 1' || fail 'malformed cursor must warn'
printf '%s\n' "$warn" | grep -Fq 'ROUND_CURSOR=1' || fail 'malformed cursor must default 1'

"$SUBJECT" write-cursor --design-tmpdir "$TMP" --value 3 >/dev/null
[[ "$(cat "$TMP/plan-review-round-cursor.txt")" == "3" ]] || fail 'write-cursor failed'

pass 'snapshot-plan-round harness'
