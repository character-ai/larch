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
printf 'snapshot v1\n' >"$TMP/plan-after-round-1.txt"
printf 'plan v2\n' >"$TMP/plan.txt"
out3=$("$SUBJECT" write-after --design-tmpdir "$TMP" --round 1 2>&1) || fail 'write-after second failed'
printf '%s\n' "$out3" | grep -Fq 'already exists' || fail 'second write-after must preserve'
[[ "$(cat "$TMP/plan-after-round-1.txt")" == "snapshot v1" ]] || fail 'write-after idempotence must preserve existing snapshot'

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
"$SUBJECT" write-cursor --design-tmpdir "$TMP" --value 0004 >/dev/null
[[ "$(cat "$TMP/plan-review-round-cursor.txt")" == "4" ]] || fail 'write-cursor must normalize leading zeros'

rm -f "$TMP/plan.txt"
if "$SUBJECT" write-after --design-tmpdir "$TMP" --round 2 >/tmp/larch-snapshot-fail.out 2>&1; then
  fail 'write-after without plan.txt must fail closed'
fi
[[ ! -e "$TMP/plan-after-round-2.txt" ]] || fail 'failed write-after must not create destination snapshot'

if "$SUBJECT" write-after --design-tmpdir "$TMP" >/tmp/larch-snapshot-argv.out 2>&1; then
  fail 'write-after without round should fail closed'
fi
if "$SUBJECT" write-cursor --design-tmpdir "$TMP" --value 0 >/tmp/larch-snapshot-argv2.out 2>&1; then
  fail 'write-cursor zero should fail closed'
fi

STUBBIN="$TMP/stub-bin"
mkdir -p "$STUBBIN"
cat >"$STUBBIN/mv" <<'EOF'
#!/usr/bin/env bash
exit 91
EOF
chmod +x "$STUBBIN/mv"
printf 'plan v3\n' >"$TMP/plan.txt"
rm -f "$TMP/plan-after-round-3.txt"
before_tmp_count=$(find "$TMP" -maxdepth 1 -name '.snapshot-after.*' | wc -l | tr -d ' ')
if PATH="$STUBBIN:$PATH" "$SUBJECT" write-after --design-tmpdir "$TMP" --round 3 >/tmp/larch-snapshot-mvfail.out 2>&1; then
  fail 'write-after rename failure should fail closed'
fi
after_tmp_count=$(find "$TMP" -maxdepth 1 -name '.snapshot-after.*' | wc -l | tr -d ' ')
[[ ! -e "$TMP/plan-after-round-3.txt" ]] || fail 'rename failure must not leave destination snapshot'
[[ "$before_tmp_count" == "$after_tmp_count" ]] || fail 'rename failure must clean temporary snapshot file'

# revert-round (#3628): WORSE-majority Revert restores pre-round plan + rolls back cursor/counter.
REV=$(mktemp -d "${TMPDIR:-/tmp}/tspr-rev.XXXXXX")

# Round-2 revert restores from plan-after-round-1.txt.
printf 'orig\n' >"$REV/plan.txt-original"
printf 'after round1\n' >"$REV/plan-after-round-1.txt"
printf 'after round2\n' >"$REV/plan-after-round-2.txt"
printf 'round2 applied\n' >"$REV/plan.txt"
printf '2\n' >"$REV/plan-review-round-cursor.txt"
printf '2\n' >"$REV/review-round-count.txt"
mkdir -p "$REV/plan-review/round-1" "$REV/plan-review/round-2"
printf 'round1 accepted\n' >"$REV/plan-review/round-1/accepted-plan-findings.md"
printf 'round2 accepted\n' >"$REV/accepted-plan-findings.md"
printf 'round2 tally\n' >"$REV/voting-tally.md"
printf 'round2 rejected\n' >"$REV/rejected-findings.md"
printf 'round2 oos\n' >"$REV/oos.md"
printf 'round2 assessor\n' >"$REV/assessor-verdict-round-2.txt"
printf 'stale postplan\n' >"$REV/.design-postplan-emit-result.env"
printf 'diff_added\n' >"$REV/.gate-b-optional-trailer-keys"
printf 'diff_added=99\n' >"$REV/.gate-b-optional-trailer-keys.values"
printf 'stale validator\n' >"$REV/validate-plan-commands.log"
printf '999\n' >"$REV/diff-lines.txt"
mkdir -p "$REV/.completed"
: >"$REV/.completed/finalize"
: >"$REV/.completed/step-3b"
: >"$REV/.plan-command-autofix-design_Step_3.5_Gate_B.attempted"
rev2=$("$SUBJECT" revert-round --design-tmpdir "$REV" --round 2 2>&1) || fail 'revert-round N=2 failed'
printf '%s\n' "$rev2" | grep -Fq 'REVERT_STATUS=ok' || fail 'revert-round N=2 missing REVERT_STATUS=ok'
[[ "$(cat "$REV/plan.txt")" == "after round1" ]] || fail 'revert-round N=2 must restore plan-after-round-1'
[[ ! -e "$REV/plan-after-round-2.txt" ]] || fail 'revert-round N=2 must drop round-2 snapshot'
[[ "$(cat "$REV/plan-review-round-cursor.txt")" == "2" ]] || fail 'revert-round N=2 cursor must be 2'
[[ "$(cat "$REV/review-round-count.txt")" == "1" ]] || fail 'revert-round N=2 count must be 1'
[[ "$(cat "$REV/accepted-plan-findings.md")" == "round1 accepted" ]] || fail 'revert-round N=2 must restore prior accepted findings'
[[ ! -e "$REV/voting-tally.md" ]] || fail 'revert-round N=2 must remove stale tally when prior has none'
[[ ! -e "$REV/plan-review/round-2" ]] || fail 'revert-round N=2 must remove stale round-2 artifacts'
[[ ! -e "$REV/assessor-verdict-round-2.txt" ]] || fail 'revert-round N=2 must remove stale assessor verdict'
[[ ! -e "$REV/.design-postplan-emit-result.env" ]] || fail 'revert-round N=2 must clear stale postplan result'
[[ ! -e "$REV/.gate-b-optional-trailer-keys" ]] || fail 'revert-round N=2 must clear trailer snapshot'
[[ ! -e "$REV/validate-plan-commands.log" ]] || fail 'revert-round N=2 must clear stale validator log'
[[ ! -e "$REV/.completed/finalize" && ! -e "$REV/.completed/step-3b" ]] || fail 'revert-round N=2 must clear downstream completion sentinels'
[[ ! -e "$REV/.plan-command-autofix-design_Step_3.5_Gate_B.attempted" ]] || fail 'revert-round N=2 must clear auto-fix cycle sentinels'
[[ ! -e "$REV/diff-lines.txt" ]] || fail 'revert-round N=2 must clear stale diff-lines when restored plan has no trailer'

# Round-1 revert restores from plan.txt-original; counter rolls to 0.
printf 'orig\n' >"$REV/plan.txt-original"
printf 'after round1\n' >"$REV/plan-after-round-1.txt"
printf 'round1 applied\n' >"$REV/plan.txt"
printf '1\n' >"$REV/plan-review-round-cursor.txt"
printf '1\n' >"$REV/review-round-count.txt"
printf 'round1 accepted\n' >"$REV/accepted-plan-findings.md"
printf 'round1 tally\n' >"$REV/voting-tally.md"
rev1=$("$SUBJECT" revert-round --design-tmpdir "$REV" --round 1 2>&1) || fail 'revert-round N=1 failed'
printf '%s\n' "$rev1" | grep -Fq 'RESTORED_FROM=plan.txt-original' || fail 'revert-round N=1 must restore from original'
[[ "$(cat "$REV/plan.txt")" == "orig" ]] || fail 'revert-round N=1 must restore plan.txt-original'
[[ ! -e "$REV/plan-after-round-1.txt" ]] || fail 'revert-round N=1 must drop round-1 snapshot'
[[ "$(cat "$REV/plan-review-round-cursor.txt")" == "1" ]] || fail 'revert-round N=1 cursor must be 1'
[[ "$(cat "$REV/review-round-count.txt")" == "0" ]] || fail 'revert-round N=1 count must be 0'
[[ ! -e "$REV/accepted-plan-findings.md" ]] || fail 'revert-round N=1 must remove accepted findings'
[[ ! -e "$REV/voting-tally.md" ]] || fail 'revert-round N=1 must remove voting tally'

# Missing restore source → exit 2, plan.txt untouched (orchestrator keeps applied plan).
printf 'round5 applied\n' >"$REV/plan.txt"
if "$SUBJECT" revert-round --design-tmpdir "$REV" --round 5 >/tmp/larch-snapshot-rev-src.out 2>&1; then
  fail 'revert-round with missing source snapshot must fail closed'
fi
[[ "$(cat "$REV/plan.txt")" == "round5 applied" ]] || fail 'revert-round failure must not mutate plan.txt'

# Symlink restore sources are unsafe and must be rejected before copy-back.
ln -sf /etc/hosts "$REV/plan-after-round-4.txt"
if "$SUBJECT" revert-round --design-tmpdir "$REV" --round 5 >/tmp/larch-snapshot-rev-symlink.out 2>&1; then
  fail 'revert-round with symlink source snapshot must fail closed'
fi
[[ "$(cat "$REV/plan.txt")" == "round5 applied" ]] || fail 'symlink revert failure must not mutate plan.txt'

# Missing --round → exit 2.
if "$SUBJECT" revert-round --design-tmpdir "$REV" >/tmp/larch-snapshot-rev-argv.out 2>&1; then
  fail 'revert-round without --round must fail closed'
fi
rm -rf "$REV"

pass 'snapshot-plan-round harness'
