#!/usr/bin/env bash
# Regression harness for scripts/reviewer-prune.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
HELPER="$ROOT/scripts/reviewer-prune.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-reviewer-prune.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
contains() { grep -Fq -- "$2" "$1" || fail "$3"; }
not_contains() { ! grep -Fq -- "$2" "$1" || fail "$3"; }
kv() { awk -F= -v k="$2" '$1==k { sub(/^[^=]*=/, ""); print; exit }' "$1"; }

manifest_code() {
    cat > "$1" <<JSON
{"slot":"dyn-foo","tool":"cursor","output":"$TMP/dyn-foo-output.txt","prompt_file":"$TMP/prompt.md"}
{"slot":"dyn-foo-codex","tool":"codex","output":"$TMP/dyn-foo-codex-output.txt","prompt_file":"$TMP/prompt.md"}
{"slot":"security","tool":"cursor","output":"$TMP/cursor-specialist-security-output.txt","agent":"$TMP/a.md"}
JSON
}

manifest_plan() {
    cat > "$1" <<JSON
{"slot":"cursor-plan-arch","tool":"cursor","output":"$TMP/cursor-plan-arch-output.txt","prompt_file":"$TMP/p.md"}
{"slot":"codex-plan-edge","tool":"codex","output":"$TMP/codex-primary-plan-edge-output.txt","prompt_file":"$TMP/p.md"}
JSON
    cat > "$2" <<'MAP'
cursor-plan-arch	Cursor-Arch
codex-plan-edge	Codex-Edge
MAP
}

m="$TMP/manifest.ndjson"
ledger="$TMP/ledger.tsv"
classification="$TMP/classification.tsv"
manifest_code "$m"
cat > "$classification" <<'TSV'
finding_id	reviewer_slots	voting_result
FINDING_1	dyn-foo-output.txt|dyn-foo-codex-output.txt	accepted
FINDING_2	dyn-foo-codex-output.txt	accepted
FINDING_3	dyn-foo-output.txt-phase2	accepted
FINDING_4	dyn-foo-output.txt (retry)	accepted
OOS_1	cursor-specialist-security-output.txt	accepted
FINDING_5	dyn-foo-output.txt-codex-output.txt	accepted
FINDING_6	dyn-foo-output.txt	rejected
TSV
"$HELPER" record --ledger "$ledger" --round 1 --manifest "$m" --classification "$classification"
contains "$ledger" $'1\tcursor\tdyn-foo\tdyn-foo-output.txt\t3' "code label exact/normalization count"
contains "$ledger" $'1\tcodex\tdyn-foo-codex\tdyn-foo-codex-output.txt\t2' "code codex count"
contains "$ledger" $'1\tcursor\tsecurity\tcursor-specialist-security-output.txt\t1' "accepted OOS count"
not_contains "$ledger" $'dyn-foo-output.txt-codex-output.txt\t1' "shared-prefix token must not create label row"

cat > "$classification" <<'TSV'
finding_id	reviewer_slots	voting_result
FINDING_1	dyn-foo-output.txt	accepted
TSV
"$HELPER" record --ledger "$ledger" --round 1 --manifest "$m" --classification "$classification"
contains "$ledger" $'1\tcursor\tdyn-foo\tdyn-foo-output.txt\t1' "round rerecord replaces count"
not_contains "$ledger" $'1\tcursor\tdyn-foo\tdyn-foo-output.txt\t3' "round rerecord removes old row"

: > "$TMP/empty.ndjson"
"$HELPER" record --ledger "$ledger" --round 1 --manifest "$TMP/empty.ndjson" --classification "$classification"
! awk -F '\t' '$1=="1" {found=1} END{exit found?0:1}' "$ledger" || fail "zero-row record should clear round"

plan_manifest="$TMP/plan.ndjson"
label_map="$TMP/labels.tsv"
manifest_plan "$plan_manifest" "$label_map"
cat > "$TMP/plan-classification.tsv" <<'TSV'
finding_id	finding_reviewers	voting_result
FINDING_1	Cursor-Arch Codex-Edge	accepted
FINDING_2	Cursor-Arch	accepted
OOS_1	Cursor-Arch	accepted
FINDING_3	Cursor-Arch,Codex-Edge	accepted
TSV
"$HELPER" record --ledger "$ledger" --round 2 --manifest "$plan_manifest" --classification "$TMP/plan-classification.tsv" --label-map "$label_map"
contains "$ledger" $'2\tcursor\tcursor-plan-arch\tCursor-Arch\t4' "plan whitespace/comma token matching"
contains "$ledger" $'2\tcodex\tcodex-plan-edge\tCodex-Edge\t2' "plan second token matching"

# Build two zero-strike rounds and assert round 3 pruning, clean slate, and round 5 re-probe.
manifest_code "$m"
cat > "$TMP/zero.tsv" <<'TSV'
finding_id	reviewer_slots	voting_result
TSV
"$HELPER" record --ledger "$ledger" --round 1 --manifest "$m" --classification "$TMP/zero.tsv"
"$HELPER" record --ledger "$ledger" --round 2 --manifest "$m" --classification "$TMP/zero.tsv"
out="$TMP/filter.ndjson"
envout="$TMP/filter.env"
for keep_round in 1 2 5 6; do
    "$HELPER" filter --ledger "$ledger" --round "$keep_round" --manifest "$m" --out "$out" > "$envout"
    [[ "$(kv "$envout" PRUNED_COUNT)" == 0 ]] || fail "round $keep_round should keep full manifest"
    [[ "$(wc -l < "$out" | awk '{print $1}')" == 3 ]] || fail "round $keep_round should preserve all rows"
done
"$HELPER" filter --ledger "$ledger" --round 3 --manifest "$m" --out "$out" > "$envout"
[[ "$(kv "$envout" PRUNE_ACTIVE)" == true ]] || fail "round3 prune active"
[[ "$(kv "$envout" PANEL_PRUNED_EMPTY)" == true ]] || fail "all-pruned marker"
[[ ! -s "$out" ]] || fail "all-pruned output should be empty"
contains "$envout" 'PRUNED_COMBOS=cursor:dyn-foo,codex:dyn-foo-codex,cursor:security' "pruned combo list"

one_round_ledger="$TMP/one-round-ledger.tsv"
"$HELPER" record --ledger "$one_round_ledger" --round 2 --manifest "$m" --classification "$TMP/zero.tsv"
"$HELPER" filter --ledger "$one_round_ledger" --round 3 --manifest "$m" --out "$out" > "$envout"
[[ "$(kv "$envout" PRUNED_COUNT)" == 0 ]] || fail "one prior launched round should keep clean slate"

LARCH_REVIEWER_PRUNE=off "$HELPER" filter --ledger "$ledger" --round 3 --manifest "$m" --out "$out" > "$envout"
[[ "$(kv "$envout" PRUNE_ACTIVE)" == false ]] || fail "off switch disables pruning"

LARCH_REVIEWER_PRUNE=on "$HELPER" filter --ledger "$ledger" --round 1 --manifest "$m" --out "$out" > "$envout"
contains "$envout" 'WARN=reviewer-prune: ignoring LARCH_REVIEWER_PRUNE value; set it exactly to off to disable' "non-off override warning"

printf 'not\ta\tledger\n' > "$ledger"
"$HELPER" filter --ledger "$ledger" --round 3 --manifest "$m" --out "$out" > "$envout"
[[ "$(kv "$envout" PRUNE_ACTIVE)" == false ]] || fail "corrupt ledger fail-open inactive"
contains "$envout" 'WARN=reviewer-prune: fail-open ledger read failed' "corrupt ledger warning"

printf 'ok\n'
