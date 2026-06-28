#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
ANALYZER="$ROOT/skills/voter-calibration/scripts/voter-calibration.py"
FIX=$(mktemp -d)
trap 'rm -rf "$FIX"' EXIT

python3 - "$FIX/larch-logs" "$FIX/larch-logs-era" <<'PY'
import csv
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
era_root = Path(sys.argv[2])

def write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)

def write_manifest(run_dir, started_at, *, base):
    path = base / run_dir / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"started_at": started_at}) + "\n", encoding="utf-8")

def write_manifest_raw(run_dir, content, *, base):
    path = base / run_dir / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n", encoding="utf-8")

design22 = "finding_id finding_reviewers voting_result v1_vote v1_correctness v1_severity v1_quality v1_uncertain v1_tool v2_vote v2_correctness v2_severity v2_quality v2_uncertain v2_tool v3_vote v3_correctness v3_severity v3_quality v3_uncertain v3_tool body_severity".split()
write_manifest("design/run-a", "2026-06-25T12:00:00Z", base=root)
write(root / "design/run-a/plan-review/round-1/findings-classification.tsv", design22, [
    ["FINDING_1", "R", "accepted", "YES", "", "major", "", "", "Claude", "YES", "", "uncertain", "", "", "Codex", "NO", "", "nit", "", "", "Cursor", "major"],
    ["FINDING_2", "R", "neutral", "YES", "", "major", "", "", "Claude", "NO", "", "nit", "", "", "Codex", "", "", "", "", "", "Cursor", "minor"],
])

design21 = design22[:-1]
write_manifest("design/run-b", "2026-06-25T13:00:00Z", base=root)
write(root / "design/run-b/plan-review/round-1/findings-classification.tsv", design21, [
    ["FINDING_3", "R", "rejected", "NO", "", "nit", "", "", "Claude", "YES", "", "major", "", "", "Codex", "NO", "", "minor", "", "", "Cursor"],
])

write_manifest("design/run-corrupt", "2026-06-25T14:00:00Z", base=root)
write(root / "design/run-corrupt/plan-review/round-1/findings-classification.tsv", design22, [
    ["FINDING_BAD", "R", "bogus", "YES", "", "", "", "", "Claude", "YES", "", "", "", "", "Codex", "NO", "", "", "", "", "Cursor", "major"],
    ["FINDING_NEUTRAL", "R", "neutral", "YES", "", "", "", "", "Claude", "EXONERATE", "", "", "", "", "Codex", "YES", "", "", "", "", "Cursor", "minor"],
])

code21 = "finding_id reviewer_slots voting_result v1_vote v1_correctness v1_severity v1_quality v1_uncertain v1_tool v2_vote v2_correctness v2_severity v2_quality v2_uncertain v2_tool v3_vote v3_correctness v3_severity v3_quality v3_uncertain v3_tool".split()
write_manifest("implement/run-c", "2026-06-26T00:00:00Z", base=root)
write(root / "implement/run-c/round-1/findings-classification.tsv", code21, [
    ["FINDING_1", "R", "accepted", "YES", "", "blocker", "", "", "cursor-validity", "NO", "", "major", "", "", "cursor-plan-fidelity", "YES", "", "uncertain", "", "", "cursor-pragmatism"],
])

compact = "finding_id reviewer_slots voting_result v1_vote v1_correctness v1_severity v1_quality v1_uncertain v2_vote v2_correctness v2_severity v2_quality v2_uncertain v3_vote v3_correctness v3_severity v3_quality v3_uncertain".split()
rows = []
for idx in range(1, 5):
    v3_severity = "minor" if idx == 4 else "major"
    rows.append([f"FINDING_{idx}", "R", "accepted", "NO", "", "blocker", "", "", "YES", "", "major", "", "", "YES", "", v3_severity, "", ""])
rows.append(["FINDING_9", "R", "accepted", "YES", "", "major", "", "", "", "", "", "", "", "", "", "", "", ""])
write_manifest("review/run-d", "2026-06-26T01:00:00Z", base=root)
write(root / "review/run-d/review-findings-classification-round-1.tsv", compact, rows)

write_manifest("design/run-pre-era", "2026-06-25T12:00:00Z", base=era_root)
write(era_root / "design/run-pre-era/plan-review/round-1/findings-classification.tsv", design22, [
    ["FINDING_PRE", "R", "accepted", "YES", "", "major", "", "", "pre-era-voter", "NO", "", "minor", "", "", "pre-era-peer", "YES", "", "nit", "", "", "pre-era-third", "major"],
])

write_manifest("design/run-post-era", "2026-06-26T00:00:00Z", base=era_root)
write(era_root / "design/run-post-era/plan-review/round-1/findings-classification.tsv", design22, [
    ["FINDING_POST", "R", "accepted", "YES", "", "major", "", "", "post-era-voter", "NO", "", "minor", "", "", "post-era-peer", "YES", "", "nit", "", "", "post-era-third", "major"],
])

write(era_root / "design/run-missing-started-at/plan-review/round-1/findings-classification.tsv", design22, [
    ["FINDING_MISSING", "R", "accepted", "YES", "", "major", "", "", "missing-era-voter", "NO", "", "minor", "", "", "missing-era-peer", "YES", "", "nit", "", "", "missing-era-third", "major"],
])

write_manifest_raw("design/run-invalid-started-at-empty-manifest", "{}", base=era_root)
write(era_root / "design/run-invalid-started-at-empty-manifest/plan-review/round-1/findings-classification.tsv", design22, [
    ["FINDING_INVALID_EMPTY", "R", "accepted", "YES", "", "major", "", "", "invalid-empty-manifest-voter", "NO", "", "minor", "", "", "invalid-empty-manifest-peer", "YES", "", "nit", "", "", "invalid-empty-manifest-third", "major"],
])

write_manifest_raw("design/run-invalid-started-at-empty-string", '{"started_at": ""}', base=era_root)
write(era_root / "design/run-invalid-started-at-empty-string/plan-review/round-1/findings-classification.tsv", design22, [
    ["FINDING_INVALID_BLANK", "R", "accepted", "YES", "", "major", "", "", "invalid-empty-string-voter", "NO", "", "minor", "", "", "invalid-empty-string-peer", "YES", "", "nit", "", "", "invalid-empty-string-third", "major"],
])

write_manifest_raw("design/run-invalid-started-at-bad-date", '{"started_at": "not-a-date"}', base=era_root)
write(era_root / "design/run-invalid-started-at-bad-date/plan-review/round-1/findings-classification.tsv", design22, [
    ["FINDING_INVALID_DATE", "R", "accepted", "YES", "", "major", "", "", "invalid-bad-date-voter", "NO", "", "minor", "", "", "invalid-bad-date-peer", "YES", "", "nit", "", "", "invalid-bad-date-third", "major"],
])
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
grep -Fq '## Per-voter False-negative YES Rate' "$run_out"
grep -Fq '| design | Claude | 3 | 2 | 0 | 2 | 0.667 |' "$run_out"
grep -Fq '| design | Codex | 2 | 0 | 1 | 1 | 0.500 |' "$run_out"
grep -Fq '| design | Cursor | 1 | 1 | 0 | 1 | 1.000 |' "$run_out"
if grep -Fq '| design | Codex | 3 |' "$run_out"; then exit 1; fi
grep -Fq '| code-review | v2 | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |' "$run_out"
grep -Fq '| code-review | v3 | 4 | 0 | 3 | 1 | 0 | 0 | 0 | 0.750 | 1.000 | false |' "$run_out"
if grep -Fq 'pre-era-voter' "$run_out"; then exit 1; fi
if grep -Fq 'post-era-voter' "$run_out"; then exit 1; fi
if grep -Fq 'missing-era-voter' "$run_out"; then exit 1; fi

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

era_all="$FIX/era-all.md"
env -u CLAUDE_PLUGIN_ROOT python3 "$ANALYZER" --log-root "$FIX/larch-logs-era" --min-votes 1 --era all --era-since-date 2026-06-26 > "$era_all"
grep -Fq "Boundary source: \`explicit-date\`" "$era_all"
grep -Fq "Boundary timestamp: \`2026-06-26T00:00:00Z\`" "$era_all"
grep -Fq "Runs excluded for missing or invalid \`started_at\`: 4" "$era_all"
grep -Fq '## Pre-incentive era' "$era_all"
grep -Fq '## Post-incentive era' "$era_all"
agreement_count=$(grep -c '^## Agreement Table$' "$era_all" || true)
[[ "$agreement_count" -eq 2 ]]
era_severity_count=$(grep -c '^## Voter Severity Scoreboard$' "$era_all" || true)
[[ "$era_severity_count" -eq 2 ]]
pre_section=$(awk '/^## Pre-incentive era$/ {in_pre=1; next} /^## Post-incentive era$/ {in_pre=0} in_pre {print}' "$era_all")
printf '%s\n' "$pre_section" | grep -Fq 'pre-era-voter'
if printf '%s\n' "$pre_section" | grep -Fq 'post-era-voter'; then exit 1; fi
post_section=$(awk '/^## Post-incentive era$/ {in_post=1; next} /^## Notes$/ {in_post=0} in_post {print}' "$era_all")
printf '%s\n' "$post_section" | grep -Fq 'post-era-voter'
if printf '%s\n' "$post_section" | grep -Fq 'pre-era-voter'; then exit 1; fi
if grep -Fq 'missing-era-voter' "$era_all"; then exit 1; fi
if grep -Fq 'invalid-empty-manifest-voter' "$era_all"; then exit 1; fi
if grep -Fq 'invalid-empty-string-voter' "$era_all"; then exit 1; fi
if grep -Fq 'invalid-bad-date-voter' "$era_all"; then exit 1; fi

era_pre="$FIX/era-pre.md"
env -u CLAUDE_PLUGIN_ROOT python3 "$ANALYZER" --log-root "$FIX/larch-logs-era" --min-votes 1 --era pre --era-since-date 2026-06-26 > "$era_pre"
grep -Fq '## Pre-incentive era' "$era_pre"
if grep -Fq '## Post-incentive era' "$era_pre"; then exit 1; fi
grep -Fq 'pre-era-voter' "$era_pre"
if grep -Fq 'post-era-voter' "$era_pre"; then exit 1; fi
grep -Fq '## Agreement Table' "$era_pre"
grep -Fq '## Voter Severity Scoreboard' "$era_pre"

era_post="$FIX/era-post.md"
env -u CLAUDE_PLUGIN_ROOT python3 "$ANALYZER" --log-root "$FIX/larch-logs-era" --min-votes 1 --era post --era-since-date 2026-06-26 > "$era_post"
grep -Fq '## Post-incentive era' "$era_post"
if grep -Fq '## Pre-incentive era' "$era_post"; then exit 1; fi
grep -Fq 'post-era-voter' "$era_post"
if grep -Fq 'pre-era-voter' "$era_post"; then exit 1; fi
grep -Fq '## Agreement Table' "$era_post"
grep -Fq '## Voter Severity Scoreboard' "$era_post"

bad_date_status=0
env -u CLAUDE_PLUGIN_ROOT python3 "$ANALYZER" --log-root "$FIX/larch-logs" --era all --era-since-date 2026-13-01 > "$FIX/bad-date.out" 2> "$FIX/bad-date.err" || bad_date_status=$?
[[ "$bad_date_status" -eq 2 ]]
grep -Fq -- '--era-since-date must be a valid YYYY-MM-DD date' "$FIX/bad-date.err"

PYTHON=$(command -v python3)
REAL_GIT=$(command -v git)

nogh_bin="$FIX/no-gh-bin"
mkdir -p "$nogh_bin"
ln -s "$REAL_GIT" "$nogh_bin/git"
no_gh_file="$FIX/no-gh-report.md"
no_gh_stdout=$(PATH="$nogh_bin" CLAUDE_PLUGIN_ROOT='' "$PYTHON" "$ANALYZER" --log-root "$FIX/larch-logs" --era all --out "$no_gh_file")
[[ "$no_gh_stdout" == "REPORT_FILE=$no_gh_file" ]]
grep -Fq '## Era Boundary Unavailable' "$no_gh_file"
grep -Fq "Pass \`--era-since-date YYYY-MM-DD\`" "$no_gh_file"
if grep -Fq 'Traceback' "$no_gh_file"; then exit 1; fi

nogit_bin="$FIX/no-git-bin"
mkdir -p "$nogit_bin"
cat > "$nogit_bin/gh" <<'SH'
#!/bin/sh
echo invoked > "$LARCH_FAKE_GH_LOG"
exit 1
SH
chmod +x "$nogit_bin/gh"
nogit_log="$FIX/no-git-gh.log"
PATH="$nogit_bin" CLAUDE_PLUGIN_ROOT='' LARCH_FAKE_GH_LOG="$nogit_log" "$PYTHON" "$ANALYZER" --log-root "$FIX/larch-logs" --era all > "$FIX/no-git.out"
grep -Fq "Reason: \`repo_unresolved\`" "$FIX/no-git.out"
if grep -Fq 'Traceback' "$FIX/no-git.out"; then exit 1; fi
[[ ! -e "$nogit_log" ]]

fake_plugin="$FIX/fake-plugin"
mkdir -p "$fake_plugin"
ln -s "$ROOT/python" "$fake_plugin/python"
fake_bin="$FIX/fake-bin"
mkdir -p "$fake_bin"
cat > "$fake_bin/git" <<'SH'
#!/bin/sh
if [ "$1" = "-C" ] && [ "$3" = "config" ] && [ "$4" = "--get" ] && [ "$5" = "remote.origin.url" ]; then
  printf '%s\n' 'https://github.com/example/larch.git'
  exit 0
fi
exit 1
SH
chmod +x "$fake_bin/git"
fake_gh_log="$FIX/fake-gh.log"
cat > "$fake_bin/gh" <<SH
#!/bin/sh
printf '%s\n' "\$*" >> "$fake_gh_log"
if [ "\$1" = "repo" ]; then
  exit 9
fi
case " \$* " in
  *" --repo example/larch "* ) ;;
  * ) exit 8 ;;
esac
case " \$* " in
  *" --json number,state,stateReason,labels,body,closedAt,closedByPullRequestsReferences"* ) ;;
  * ) exit 7 ;;
esac
printf '%s\n' '{"number":5461,"state":"CLOSED","stateReason":"COMPLETED","labels":[],"body":"","closedAt":"2026-06-26T00:00:00Z","closedByPullRequestsReferences":[{"number":123}]}'
SH
chmod +x "$fake_bin/gh"
PATH="$fake_bin" CLAUDE_PLUGIN_ROOT="$fake_plugin" "$PYTHON" "$ANALYZER" --log-root "$FIX/larch-logs" --min-votes 1 --era all > "$FIX/fake-gh-success.out"
grep -Fq "Boundary source: \`gh-issue-closedAt\`" "$FIX/fake-gh-success.out"
grep -Fq "Boundary timestamp: \`2026-06-26T00:00:00Z\`" "$FIX/fake-gh-success.out"
grep -Fq "Resolved repo: \`example/larch\`" "$FIX/fake-gh-success.out"
grep -Fq -- '--json number,state,stateReason,labels,body,closedAt,closedByPullRequestsReferences' "$fake_gh_log"
[[ "$(wc -l < "$fake_gh_log" | tr -d ' ')" = "1" ]]
if grep -Fq 'repo view' "$fake_gh_log"; then exit 1; fi

missing_closed_bin="$FIX/missing-closed-bin"
mkdir -p "$missing_closed_bin"
cp "$fake_bin/git" "$missing_closed_bin/git"
cat > "$missing_closed_bin/gh" <<'SH'
#!/bin/sh
printf '%s\n' '{"number":5461,"state":"CLOSED","stateReason":"COMPLETED","labels":[],"body":"","closedByPullRequestsReferences":[{"number":123}]}'
SH
chmod +x "$missing_closed_bin/gh"
PATH="$missing_closed_bin" CLAUDE_PLUGIN_ROOT="$fake_plugin" "$PYTHON" "$ANALYZER" --log-root "$FIX/larch-logs" --era all > "$FIX/missing-closed-at.out"
grep -Fq "Reason: \`closedAt_unavailable\`" "$FIX/missing-closed-at.out"
grep -Fq "Pass \`--era-since-date YYYY-MM-DD\`" "$FIX/missing-closed-at.out"

unresolved_plugin="$FIX/unresolved-plugin"
mkdir -p "$unresolved_plugin"
ln -s "$ROOT/python" "$unresolved_plugin/python"
unresolved_bin="$FIX/unresolved-bin"
mkdir -p "$unresolved_bin"
ln -s "$REAL_GIT" "$unresolved_bin/git"
cat > "$unresolved_bin/gh" <<'SH'
#!/bin/sh
echo invoked > "$LARCH_FAKE_GH_LOG"
exit 1
SH
chmod +x "$unresolved_bin/gh"
unresolved_gh_log="$FIX/unresolved-gh.log"
PATH="$unresolved_bin" CLAUDE_PLUGIN_ROOT="$unresolved_plugin" LARCH_FAKE_GH_LOG="$unresolved_gh_log" "$PYTHON" "$ANALYZER" --log-root "$FIX/larch-logs" --era all > "$FIX/repo-unresolved.out"
grep -Fq "Reason: \`repo_unresolved\`" "$FIX/repo-unresolved.out"
[[ ! -e "$unresolved_gh_log" ]]


fn_root="$FIX/larch-logs-fn"
python3 - "$fn_root" <<'PY'
import csv
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])

def write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)

def manifest(path):
    path.mkdir(parents=True, exist_ok=True)
    (path / "manifest.json").write_text(json.dumps({"started_at": "2026-06-27T00:00:00Z"}) + "\n", encoding="utf-8")

manifest(root / "review/run-compact")
compact = "finding_id reviewer_slots voting_result v1_vote v1_correctness v1_severity v1_quality v1_uncertain v2_vote v2_correctness v2_severity v2_quality v2_uncertain v3_vote v3_correctness v3_severity v3_quality v3_uncertain".split()
write(root / "review/run-compact/review-findings-classification-round-1.tsv", compact, [
    ["FINDING_N", "R", "neutral", "YES", "", "major", "", "", "NO", "", "nit", "", "", "YES", "", "major", "", ""],
    ["FINDING_R", "R", "rejected", "YES", "", "major", "", "", "NO", "", "nit", "", "", "NO", "", "nit", "", ""],
])

manifest(root / "design/run-fallback")
design_min = "finding_id finding_reviewers voting_result v1_vote v2_vote v3_vote scope".split()
write(root / "design/run-fallback/plan-review/round-1/findings-classification.tsv", design_min, [
    ["FINDING_FB", "R", "neutral", "YES", "NO", "NO", ""],
])

manifest(root / "design/run-scope")
design23 = "finding_id finding_reviewers voting_result v1_vote v1_correctness v1_severity v1_quality v1_uncertain v1_tool v2_vote v2_correctness v2_severity v2_quality v2_uncertain v2_tool v3_vote v3_correctness v3_severity v3_quality v3_uncertain v3_tool body_severity scope".split()
write(root / "design/run-scope/plan-review/round-1/findings-classification.tsv", design23, [
    ["FINDING_SCOPE", "R", "neutral", "YES", "", "major", "", "", "scoped-out", "NO", "", "nit", "", "", "peer", "NO", "", "nit", "", "", "third", "major", "oos"],
])
PY
fn_out="$FIX/fn-report.md"
env -u CLAUDE_PLUGIN_ROOT python3 "$ANALYZER" --log-root "$fn_root" --min-votes 1 > "$fn_out"
grep -Fq '## Per-voter False-negative YES Rate' "$fn_out"
grep -Fq '| code-review | v1 | 2 | 1 | 1 | 2 | 1.000 |' "$fn_out"
grep -Fq '| code-review | v2 | 0 | 0 | 0 | 0 | n/a |' "$fn_out"
grep -Fq '| code-review | v3 | 1 | 1 | 0 | 1 | 1.000 |' "$fn_out"
grep -Fq '| design | Claude | 1 | 1 | 0 | 1 | 1.000 |' "$fn_out"
if grep -Fq 'scoped-out' "$fn_out"; then exit 1; fi

realized_oos_root="$FIX/larch-logs-realized-oos"
python3 - "$realized_oos_root" <<'PY'
import json
from pathlib import Path

root = Path(__import__("sys").argv[1])
run = root / "implement" / "run-oos"
(run / "round-1").mkdir(parents=True)
(run / "manifest.json").write_text(json.dumps({"started_at": "2026-06-27T00:00:00Z"}) + "\n", encoding="utf-8")
(run / "oos-issues.ndjson").write_text(
    json.dumps({
        "body": "- **Stable ID**: oos-accepted-review:OOS_1\n- **Filed URL**: https://github.com/example/larch/issues/5461",
    }) + "\n",
    encoding="utf-8",
)
PY
realized_no_gh_tmp="$FIX/realized-no-gh-tmp"
mkdir -p "$realized_no_gh_tmp"
realized_no_gh_out="$FIX/realized-no-gh.md"
realized_no_gh_status=0
TMPDIR="$realized_no_gh_tmp" PATH="$nogh_bin" CLAUDE_PLUGIN_ROOT='' "$PYTHON" "$ANALYZER" --log-root "$realized_oos_root" --realized-outcomes --repo example/larch > "$realized_no_gh_out" || realized_no_gh_status=$?
[[ "$realized_no_gh_status" -eq 0 ]]
grep -Fq '## Realized-outcome voter calibration' "$realized_no_gh_out"
grep -Fq "Skipped: \`gh_unavailable\`" "$realized_no_gh_out"
if grep -Fq 'Traceback' "$realized_no_gh_out"; then exit 1; fi
if find "$realized_no_gh_tmp" -name 'voter-calibration-issues-*.json' | grep -q .; then exit 1; fi

bulk_load_bin="$FIX/bulk-load-bin"
mkdir -p "$bulk_load_bin"
ln -s "$REAL_GIT" "$bulk_load_bin/git"
cat > "$bulk_load_bin/gh" <<'SH'
#!/bin/sh
case " $* " in
  *" issue list "* )
    printf '%s\n' '["bad", "bad", {"number": 1, "title": "ok", "body": ""}]'
    exit 0
    ;;
  *" issue view "* )
    exit 1
    ;;
esac
exit 1
SH
chmod +x "$bulk_load_bin/gh"
bulk_load_tmp="$FIX/bulk-load-tmp"
mkdir -p "$bulk_load_tmp"
bulk_load_out="$FIX/realized-bulk-load-failed.md"
bulk_load_status=0
TMPDIR="$bulk_load_tmp" PATH="$bulk_load_bin" CLAUDE_PLUGIN_ROOT="$fake_plugin" "$PYTHON" "$ANALYZER" --log-root "$realized_oos_root" --realized-outcomes --repo example/larch > "$bulk_load_out" || bulk_load_status=$?
[[ "$bulk_load_status" -eq 0 ]]
grep -Fq 'bulk_load_failed' "$bulk_load_out"
if grep -Fq 'Traceback' "$bulk_load_out"; then exit 1; fi
if find "$bulk_load_tmp" -name 'voter-calibration-issues-*.json' | grep -q .; then exit 1; fi

realized_era_no_gh_out="$FIX/realized-era-no-gh.md"
realized_era_no_gh_status=0
PATH="$nogh_bin" CLAUDE_PLUGIN_ROOT='' "$PYTHON" "$ANALYZER" --log-root "$FIX/larch-logs" --era all --realized-outcomes --repo example/larch > "$realized_era_no_gh_out" || realized_era_no_gh_status=$?
[[ "$realized_era_no_gh_status" -eq 0 ]]
grep -Fq '## Era Boundary Unavailable' "$realized_era_no_gh_out"
grep -Fq "Pass \`--era-since-date YYYY-MM-DD\`" "$realized_era_no_gh_out"
if grep -Fq 'Traceback' "$realized_era_no_gh_out"; then exit 1; fi

details_json="$FIX/filed-details.json"
printf '%s\n' '{"123":{"number":123,"title":"Offline issue","body":"","state":"CLOSED","labels":[]}}' > "$details_json"
env -u CLAUDE_PLUGIN_ROOT python3 "$ANALYZER" --log-root "$fn_root" --realized-outcomes --repo example/larch --filed-issue-details-json "$details_json" > "$FIX/realized-offline.md"
grep -Fq '## Ground-truth Voter Calibration' "$FIX/realized-offline.md"

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
