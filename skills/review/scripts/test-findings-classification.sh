#!/usr/bin/env bash
# Regression harness for code-review findings-classification.tsv.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CLAUDE_PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
export CLAUDE_PLUGIN_ROOT
TALLY="$SCRIPT_DIR/tally-code-votes.sh"
LOG_PHASE="$SCRIPT_DIR/log-phase.sh"
LARCH_LOG="$CLAUDE_PLUGIN_ROOT/scripts/larch-log.sh"
PARSER="$CLAUDE_PLUGIN_ROOT/scripts/parse-judge-vote-and-rating.sh"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/review-findings-classification.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

kv() {
    awk -F= -v k="$1" '$1 == k { print substr($0, length(k) + 2); exit }' "$2"
}

write_ballot() {
    local file="$1"
    cat > "$file" <<'EOF'
### FINDING_1: In-scope concern
- **Reviewer(s)**: cursor-a-output.txt, codex-b-output.txt
- **Concern**: Real issue.
- **Suggested revision**: Fix it.

### OOS_1: Future concern
- **Reviewer**: cursor-oos-output.txt
- **Concern**: Future issue.
- **Suggested revision**: File it.
EOF
}

HEADER=$'finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain'

echo "# Fixture A: nested /implement path, 2 effective voters, OOS_N rows, write-round publish"
A="$TMP/a"
mkdir -p "$A"
write_ballot "$A/ballot.md"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\nOOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n' > "$A/v1.txt"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=adequate UNCERTAIN=false\nOOS_1: NO CORRECTNESS=partially-true SEVERITY=minor QUALITY=weak UNCERTAIN=false\n' > "$A/v2.txt"
out="$A/out.env"
IMPLEMENT_TMPDIR="$A/impl-parent" "$TALLY" --ballot-file "$A/ballot.md" --review-tmpdir "$A" --session-env-path "$A/session-env.sh" --voter-files "$A/v1.txt" "$A/v2.txt" > "$out"
class_file=$(kv FINDINGS_CLASSIFICATION_TSV_FILE "$out")
[[ "$class_file" == "$A/findings-classification.tsv" ]] || fail "nested classification path drifted: $class_file"
read -r header < "$class_file"
[[ "$header" == "$HEADER" ]] || fail "classification header drifted"
grep -Fq $'FINDING_1\tcursor-a-output.txt|codex-b-output.txt\taccepted\tYES\ttrue\tmajor\tgood\tfalse\tYES\ttrue\tmajor\tadequate\tfalse\t\t\t\t\t' "$class_file" \
    || fail "nested compact 2-voter row missing"
grep -Fq $'OOS_1\tcursor-oos-output.txt\tneutral' "$class_file" || fail "OOS_N classification row missing"
log_root="$A/logs"
"$LARCH_LOG" write-round --log-root "$log_root" --skill implement --run-id run-a --round 1 --source-dir "$A" >/dev/null
[[ -f "$log_root/implement/run-a/round-1/findings-classification.tsv" ]] || fail "write-round did not publish findings-classification.tsv"

echo "# Fixture B: standalone lenient missing rating handling does not change vote result"
B="$TMP/b"
mkdir -p "$B"
write_ballot "$B/ballot.md"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\nOOS_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n' > "$B/v1.txt"
printf 'FINDING_1: YES SEVERITY=major QUALITY=adequate UNCERTAIN=false\nOOS_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n' > "$B/v2.txt"
printf 'FINDING_1: NO CORRECTNESS=partially-true SEVERITY=minor QUALITY=weak UNCERTAIN=false\nOOS_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n' > "$B/v3.txt"
out="$B/out.env"
IMPLEMENT_TMPDIR="" "$TALLY" --ballot-file "$B/ballot.md" --review-tmpdir "$B" --round-num 1 --voter-files "$B/v1.txt" "$B/v2.txt" "$B/v3.txt" > "$out"
class_file=$(kv FINDINGS_CLASSIFICATION_TSV_FILE "$out")
[[ "$class_file" == "$B/findings-classification-round-1.tsv" ]] || fail "standalone round path drifted"
python3 - "$class_file" <<'PY'
import csv, sys
with open(sys.argv[1], newline="") as fh:
    rows = {row["finding_id"]: row for row in csv.DictReader(fh, delimiter="\t")}
r = rows["FINDING_1"]
assert r["voting_result"] == "accepted", r
assert r["v2_vote"] == "YES", r
assert r["v2_correctness"] == "", r
assert r["v2_uncertain"] == "true", r
PY

echo "# Fixture C: 0-judge path emits rows with empty voter columns"
C="$TMP/c"
mkdir -p "$C"
write_ballot "$C/ballot.md"
out="$C/out.env"
IMPLEMENT_TMPDIR="" "$TALLY" --ballot-file "$C/ballot.md" --review-tmpdir "$C" > "$out"
[[ "$(kv TALLY_STATUS "$out")" == "main-agent-vote-required" ]] || fail "0-judge status drifted"
class_file=$(kv FINDINGS_CLASSIFICATION_TSV_FILE "$out")
python3 - "$class_file" <<'PY'
import csv, sys
with open(sys.argv[1], newline="") as fh:
    rows = list(csv.DictReader(fh, delimiter="\t"))
assert len(rows) == 2, rows
for row in rows:
    assert row["voting_result"] == "rejected", row
    for k, v in row.items():
        if len(k) > 2 and k[0] == "v" and k[1].isdigit() and k[2] == "_":
            assert v == "", (k, row)
PY

echo "# Fixture D: empty ballot emits header-only TSV and KV"
D="$TMP/d"
mkdir -p "$D"
: > "$D/ballot.md"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n' > "$D/v1.txt"
out="$D/out.env"
IMPLEMENT_TMPDIR="" "$TALLY" --ballot-file "$D/ballot.md" --review-tmpdir "$D" --voter-files "$D/v1.txt" > "$out"
class_file=$(kv FINDINGS_CLASSIFICATION_TSV_FILE "$out")
[[ -f "$class_file" ]] || fail "empty ballot classification file missing"
[[ "$(wc -l < "$class_file" | tr -d ' ')" == "1" ]] || fail "empty ballot TSV should be header-only"

echo "# Fixture E: standalone multi-round files and review log batches"
E="$TMP/e"
mkdir -p "$E"
write_ballot "$E/ballot.md"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\nOOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n' > "$E/v1.txt"
for round in 1 2; do
    out="$E/out-$round.env"
    IMPLEMENT_TMPDIR="" "$TALLY" --ballot-file "$E/ballot.md" --review-tmpdir "$E" --round-num "$round" --voter-files "$E/v1.txt" > "$out"
    class_file=$(kv FINDINGS_CLASSIFICATION_TSV_FILE "$out")
    [[ -f "$E/findings-classification-round-${round}.tsv" ]] || fail "round $round classification TSV missing"
    "$LOG_PHASE" --log-root "$E/logs" --run-id run-e --batch "review-findings-classification-round-$round" --action write --payload-file "$class_file" >/dev/null
    [[ -f "$E/logs/review/run-e/review-findings-classification-round-${round}.tsv" ]] || fail "round $round review log TSV missing"
done

echo "# Fixture F: parser and vote_for_id parity"
F="$TMP/f"
mkdir -p "$F"
cat > "$F/votes.txt" <<'EOF'
FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false
OOS_1: EXONERATE CORRECTNESS=partially-true SEVERITY=minor QUALITY=weak UNCERTAIN=false
EOF
# shellcheck source=scripts/lib-vote-tally.sh
source "$CLAUDE_PLUGIN_ROOT/scripts/lib-vote-tally.sh"
for id in FINDING_1 OOS_1; do
    parsed=$("$PARSER" "$F/votes.txt" "$id")
    parser_vote=$(printf '%s\n' "$parsed" | awk -F= '$1=="PARSED_VOTE"{print $2}')
    lib_vote=$(vote_for_id "$id" "$F/votes.txt")
    [[ "$parser_vote" == "$lib_vote" ]] || fail "parser/vote_for_id parity failed for $id"
done

echo "PASS: test-findings-classification.sh"
