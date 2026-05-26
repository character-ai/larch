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
mkdir -p "$A/impl-parent/round-1"
write_ballot "$A/impl-parent/round-1/ballot.md"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\nOOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n' > "$A/impl-parent/round-1/v1.txt"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=adequate UNCERTAIN=false\nOOS_1: NO CORRECTNESS=partially-true SEVERITY=minor QUALITY=weak UNCERTAIN=false\n' > "$A/impl-parent/round-1/v2.txt"
out="$A/impl-parent/round-1/out.env"
IMPLEMENT_TMPDIR="$A/impl-parent" "$TALLY" --ballot-file "$A/impl-parent/round-1/ballot.md" --review-tmpdir "$A/impl-parent/round-1" --session-env-path "$A/impl-parent/session-env.sh" --voter-files "$A/impl-parent/round-1/v1.txt" "$A/impl-parent/round-1/v2.txt" > "$out"
class_file=$(kv FINDINGS_CLASSIFICATION_TSV_FILE "$out")
[[ "$class_file" == "$A/impl-parent/round-1/findings-classification.tsv" ]] || fail "nested classification path drifted: $class_file"
read -r header < "$class_file"
[[ "$header" == "$HEADER" ]] || fail "classification header drifted"
grep -Fq $'FINDING_1\tcursor-a-output.txt|codex-b-output.txt\taccepted\tYES\ttrue\tmajor\tgood\tfalse\tYES\ttrue\tmajor\tadequate\tfalse\t\t\t\t\t' "$class_file" \
    || fail "nested compact 2-voter row missing"
grep -Fq $'OOS_1\tcursor-oos-output.txt\tneutral' "$class_file" || fail "OOS_N classification row missing"
log_root="$A/logs"
"$LARCH_LOG" write-round --log-root "$log_root" --skill implement --run-id run-a --round 1 --source-dir "$A/impl-parent/round-1" >/dev/null
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

echo "# Fixture B2: standalone --session-env plus ambient IMPLEMENT_TMPDIR still uses round-scoped TSV"
B2="$TMP/b2"
mkdir -p "$B2" "$TMP/ambient-impl"
write_ballot "$B2/ballot.md"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\nOOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n' > "$B2/v1.txt"
out="$B2/out.env"
IMPLEMENT_TMPDIR="$TMP/ambient-impl" "$TALLY" --ballot-file "$B2/ballot.md" --review-tmpdir "$B2" --session-env-path "$B2/session-env.sh" --round-num 2 --voter-files "$B2/v1.txt" > "$out"
class_file=$(kv FINDINGS_CLASSIFICATION_TSV_FILE "$out")
[[ "$class_file" == "$B2/findings-classification-round-2.tsv" ]] || fail "standalone session-env path should remain round-scoped: $class_file"

echo "# Fixture B3: round-N tmpdir shape alone uses nested findings-classification.tsv"
B3="$TMP/impl-shape/round-3"
mkdir -p "$B3"
write_ballot "$B3/ballot.md"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\nOOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n' > "$B3/v1.txt"
out="$B3/out.env"
IMPLEMENT_TMPDIR="" "$TALLY" --ballot-file "$B3/ballot.md" --review-tmpdir "$B3" --round-num 3 --voter-files "$B3/v1.txt" > "$out"
class_file=$(kv FINDINGS_CLASSIFICATION_TSV_FILE "$out")
[[ "$class_file" == "$B3/findings-classification.tsv" ]] || fail "round-N tmpdir should use nested classification filename: $class_file"

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

echo "# Fixture F: parser and vote_for_id parity, including missing-ID fallback shape"
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
[[ "$("$PARSER" "$F/votes.txt" FINDING_2 | awk -F= '$1=="PARSED_VOTE"{print $2}')" == "" ]] \
    || fail "missing ballot ID should stay empty before tally normalization"

echo "# Fixture F2: missing ballot line records JUDGE_ERROR in TSV without changing tally semantics"
F2="$TMP/f2"
mkdir -p "$F2"
write_ballot "$F2/ballot.md"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\nOOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n' > "$F2/v1.txt"
printf 'OOS_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n' > "$F2/v2.txt"
out="$F2/out.env"
IMPLEMENT_TMPDIR="" "$TALLY" --ballot-file "$F2/ballot.md" --review-tmpdir "$F2" --round-num 1 --voter-files "$F2/v1.txt" "$F2/v2.txt" > "$out"
class_file=$(kv FINDINGS_CLASSIFICATION_TSV_FILE "$out")
python3 - "$class_file" <<'PY'
import csv, sys
with open(sys.argv[1], newline="") as fh:
    rows = {row["finding_id"]: row for row in csv.DictReader(fh, delimiter="\t")}
r = rows["FINDING_1"]
assert r["voting_result"] == "rejected", r
assert r["v2_vote"] == "JUDGE_ERROR", r
assert r["v2_correctness"] == "", r
assert r["v2_severity"] == "", r
assert r["v2_quality"] == "", r
assert r["v2_uncertain"] == "true", r
PY

echo "# Fixture F3: reviewer attribution is formula-neutralized in TSV"
F3="$TMP/f3"
mkdir -p "$F3"
cat > "$F3/ballot.md" <<'EOF'
### FINDING_1: Spreadsheet payload
- **Reviewer**: =SUM(1,1)
- **Concern**: Real issue.
- **Suggested revision**: Fix it.
EOF
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n' > "$F3/v1.txt"
out="$F3/out.env"
IMPLEMENT_TMPDIR="" "$TALLY" --ballot-file "$F3/ballot.md" --review-tmpdir "$F3" --round-num 1 --voter-files "$F3/v1.txt" > "$out"
class_file=$(kv FINDINGS_CLASSIFICATION_TSV_FILE "$out")
python3 - "$class_file" <<'PY'
import csv, sys
with open(sys.argv[1], newline="") as fh:
    rows = {row["finding_id"]: row for row in csv.DictReader(fh, delimiter="\t")}
assert rows["FINDING_1"]["reviewer_slots"] == "'=SUM(1|1)", rows["FINDING_1"]
PY

echo "# Fixture G: malicious rating tokens are sanitized to enum-only TSV cells"
G="$TMP/g"
mkdir -p "$G"
write_ballot "$G/ballot.md"
cat > "$G/v1.txt" <<'EOF'
FINDING_1: YES CORRECTNESS=true|owned SEVERITY=critical QUALITY=great UNCERTAIN=maybe
OOS_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false
EOF
cat > "$G/v2.txt" <<'EOF'
FINDING_1: NO CORRECTNESS=partially-true SEVERITY=minor QUALITY=weak UNCERTAIN=false
OOS_1: EXONERATE CORRECTNESS=partially-true SEVERITY=minor QUALITY=weak UNCERTAIN=false
EOF
out="$G/out.env"
IMPLEMENT_TMPDIR="" "$TALLY" --ballot-file "$G/ballot.md" --review-tmpdir "$G" --round-num 1 --voter-files "$G/v1.txt" "$G/v2.txt" > "$out"
class_file=$(kv FINDINGS_CLASSIFICATION_TSV_FILE "$out")
python3 - "$class_file" <<'PY'
import csv, sys
allowed = {
    "voting_result": {"accepted", "rejected", "exonerated", "neutral"},
    "vote": {"", "YES", "NO", "EXONERATE", "JUDGE_ERROR"},
    "correctness": {"", "true", "partially-true", "false-positive", "uncertain"},
    "severity": {"", "blocker", "major", "minor", "nit", "uncertain"},
    "quality": {"", "excellent", "good", "adequate", "weak", "no-fix", "uncertain"},
    "uncertain": {"", "true", "false"},
}
with open(sys.argv[1], newline="") as fh:
    for row in csv.DictReader(fh, delimiter="\t"):
        assert row["voting_result"] in allowed["voting_result"], row
        for idx in (1, 2, 3):
            assert row[f"v{idx}_vote"] in allowed["vote"], row
            assert row[f"v{idx}_correctness"] in allowed["correctness"], row
            assert row[f"v{idx}_severity"] in allowed["severity"], row
            assert row[f"v{idx}_quality"] in allowed["quality"], row
            assert row[f"v{idx}_uncertain"] in allowed["uncertain"], row
PY

echo "# Fixture H: quiet mode still emits a non-empty classification TSV contract"
H="$TMP/h"
mkdir -p "$H"
write_ballot "$H/ballot.md"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\nOOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n' > "$H/v1.txt"
out="$H/out.env"
env -u LARCH_QUIET_DISABLE IMPLEMENT_TMPDIR="" "$TALLY" --ballot-file "$H/ballot.md" --review-tmpdir "$H" --round-num 1 --voter-files "$H/v1.txt" > "$out"
class_file=$(kv FINDINGS_CLASSIFICATION_TSV_FILE "$out")
[[ -n "$class_file" && -s "$class_file" ]] || fail "quiet-mode tally should emit a non-empty classification TSV"

echo "PASS: test-findings-classification.sh"
