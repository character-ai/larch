#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
ANALYZER="$ROOT/skills/voter-calibration/scripts/voter-calibration.py"
FIX=$(mktemp -d)
trap 'rm -rf "$FIX"' EXIT

python3 - "$FIX/larch-logs" <<'PY'
import csv
import sys
from pathlib import Path

root = Path(sys.argv[1])

def write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)

design22 = "finding_id finding_reviewers voting_result v1_vote v1_correctness v1_severity v1_quality v1_uncertain v1_tool v2_vote v2_correctness v2_severity v2_quality v2_uncertain v2_tool v3_vote v3_correctness v3_severity v3_quality v3_uncertain v3_tool body_severity".split()
write(root / "design/run-a/plan-review/round-1/findings-classification.tsv", design22, [
    ["FINDING_1", "R", "accepted", "YES", "", "major", "", "", "Claude", "YES", "", "uncertain", "", "", "Codex", "NO", "", "nit", "", "", "Cursor", "major"],
    ["FINDING_2", "R", "neutral", "YES", "", "major", "", "", "Claude", "NO", "", "nit", "", "", "Codex", "", "", "", "", "", "Cursor", "minor"],
])

design21 = design22[:-1]
write(root / "design/run-b/plan-review/round-1/findings-classification.tsv", design21, [
    ["FINDING_3", "R", "rejected", "NO", "", "nit", "", "", "Claude", "YES", "", "major", "", "", "Codex", "NO", "", "minor", "", "", "Cursor"],
])

write(root / "design/run-corrupt/plan-review/round-1/findings-classification.tsv", design22, [
    ["FINDING_BAD", "R", "bogus", "YES", "", "", "", "", "Claude", "YES", "", "", "", "", "Codex", "NO", "", "", "", "", "Cursor", "major"],
    ["FINDING_NEUTRAL", "R", "neutral", "YES", "", "", "", "", "Claude", "NO", "", "", "", "", "Codex", "YES", "", "", "", "", "Cursor", "minor"],
])

code21 = "finding_id reviewer_slots voting_result v1_vote v1_correctness v1_severity v1_quality v1_uncertain v1_tool v2_vote v2_correctness v2_severity v2_quality v2_uncertain v2_tool v3_vote v3_correctness v3_severity v3_quality v3_uncertain v3_tool".split()
write(root / "implement/run-c/round-1/findings-classification.tsv", code21, [
    ["FINDING_1", "R", "accepted", "YES", "", "blocker", "", "", "cursor-validity", "NO", "", "major", "", "", "cursor-plan-fidelity", "YES", "", "uncertain", "", "", "cursor-pragmatism"],
])

compact = "finding_id reviewer_slots voting_result v1_vote v1_correctness v1_severity v1_quality v1_uncertain v2_vote v2_correctness v2_severity v2_quality v2_uncertain v3_vote v3_correctness v3_severity v3_quality v3_uncertain".split()
rows = []
for idx in range(1, 5):
    v3_severity = "minor" if idx == 4 else "major"
    rows.append([f"FINDING_{idx}", "R", "accepted", "NO", "", "blocker", "", "", "YES", "", "major", "", "", "YES", "", v3_severity, "", ""])
rows.append(["FINDING_9", "R", "accepted", "YES", "", "major", "", "", "", "", "", "", "", "", "", "", "", ""])
write(root / "review/run-d/review-findings-classification-round-1.tsv", compact, rows)
PY

run_out="$FIX/report.md"
env -u CLAUDE_PLUGIN_ROOT python3 "$ANALYZER" --log-root "$FIX/larch-logs" --min-votes 3 --outlier-threshold 0.50 > "$run_out"
grep -Fq '# Voter Calibration Report' "$run_out"
grep -Fq '| design | Claude |' "$run_out"
grep -Fq '| design | Cursor |' "$run_out"
grep -Fq '| code-review | cursor-validity |' "$run_out"
grep -Fq '| code-review | v1 | 4 | 0 | 4 | 0 | 0.000 | true |' "$run_out"
grep -Fq 'Single-voter and zero-voter panels are excluded' "$run_out"
grep -Fq 'Malformed data rows dropped: 1' "$run_out"
grep -Fq 'Ineligible panels excluded: 3' "$run_out"
severity_count=$(grep -c '## Voter Severity Scoreboard' "$run_out" || true)
[[ "$severity_count" -ge 2 ]]
awk '/^## Agreement Table$/,/^## Global Voter Agreement$/ {print}' "$run_out" | grep -Fq '## Voter Severity Scoreboard'
awk '
  /^## Global Voter Agreement$/ {in_global=1; next}
  in_global && /^## Voter Severity Scoreboard$/ {found=1}
  in_global && found && /^## Chronic Outliers / {exit}
  END {exit !found}
' "$run_out"
grep -Fq 'Uncertain' "$run_out"
grep -Fq 'Calibration Score' "$run_out"
grep -Fq '| code-review | v2 | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |' "$run_out"
grep -Fq '| code-review | v3 | 4 | 0 | 3 | 1 | 0 | 0 | 0 | 0.750 | 1.000 | false |' "$run_out"

threshold_out="$FIX/report-threshold.md"
env -u CLAUDE_PLUGIN_ROOT python3 "$ANALYZER" --log-root "$FIX/larch-logs" --min-votes 3 --outlier-threshold 0.50 --high-severity-threshold 0.50 > "$threshold_out"
grep -Fq '| code-review | v3 | 4 | 0 | 3 | 1 | 0 | 0 | 0 | 0.750 | 0.500 | true |' "$threshold_out"

run_b_only="$FIX/run-b-only"
mkdir -p "$run_b_only/design/run-b/plan-review/round-1"
cp "$FIX/larch-logs/design/run-b/plan-review/round-1/findings-classification.tsv" "$run_b_only/design/run-b/plan-review/round-1/"
run_b_out="$FIX/report-run-b.md"
env -u CLAUDE_PLUGIN_ROOT python3 "$ANALYZER" --log-root "$run_b_only" --min-votes 2 --outlier-threshold 0.50 > "$run_b_out"
grep -Fq '| design | Codex | 1 | 0 | 1 | 0 | 0.000 | false |' "$run_b_out"
grep -Fq '| design | Cursor | 1 | 1 | 0 | 0 | 1.000 | false |' "$run_b_out"

out_file="$FIX/out/report.md"
stdout=$(env -u CLAUDE_PLUGIN_ROOT python3 "$ANALYZER" --log-root "$FIX/larch-logs" --out "$out_file")
[[ "$stdout" == "REPORT_FILE=$out_file" ]]
grep -Fq '# Voter Calibration Report' "$out_file"
grep -Fq 'Calibration Score' "$out_file"

missing_status=0
env -u CLAUDE_PLUGIN_ROOT python3 "$ANALYZER" --log-root "$FIX/missing" > "$FIX/missing.out" 2> "$FIX/missing.err" || missing_status=$?
[[ "$missing_status" -eq 2 ]]
grep -Fq 'resolved log root is missing' "$FIX/missing.err"

worktree="$FIX/worktree"
mkdir -p "$worktree"
cp -R "$FIX/larch-logs" "$worktree/larch-logs"
git -C "$worktree" init -q
(
  cd "$worktree"
  env -u CLAUDE_PLUGIN_ROOT python3 "$ANALYZER" --min-votes 3 > "$FIX/default-root.md"
)
grep -Fq '| code-review | v1 | 4 | 0 | 4 | 0 | 0.000 | true |' "$FIX/default-root.md"
