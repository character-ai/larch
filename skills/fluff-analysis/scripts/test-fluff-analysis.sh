#!/usr/bin/env bash
# shellcheck disable=SC2129
# test-fluff-analysis.sh - offline regression harness for fluff-analysis.py.
#
# Builds a synthetic larch-logs fixture, runs the analyzer against it, and
# asserts the report shape, the --cutoff pre/post section, and the
# missing-log-root exit code.
#
# Usage:
#   bash skills/fluff-analysis/scripts/test-fluff-analysis.sh
#
# Exit codes:
#   0 - all assertions passed
#   1 - one or more assertions failed

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ANALYZER="$SCRIPT_DIR/fluff-analysis.py"

if [[ ! -r "$ANALYZER" ]]; then
    echo "ERROR: analyzer not readable at $ANALYZER" >&2
    exit 1
fi

PASS=0
FAIL=0

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        echo "  FAIL: $label (missing: $needle)" >&2
    fi
}

assert_eq() {
    local got="$1" want="$2" label="$3"
    if [[ "$got" == "$want" ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        echo "  FAIL: $label (got '$got' want '$want')" >&2
    fi
}

echo "== bootstrap path resolves repo python directory =="
(
    cd "$SCRIPT_DIR"
    python3 - <<'PY'
from pathlib import Path

assert (Path(__file__).resolve().parents[3] / "python" / "larch" / "review" / "self_review_tally.py").is_file()
PY
)
PASS=$((PASS + 1))
echo "  ok: script-dir bootstrap path reaches repo python helper"

FIX=$(mktemp -d "${TMPDIR:-/tmp}/fluff-fixture-XXXXXX")
trap 'rm -rf "$FIX"' EXIT

# ---- implement fixture: one accepted-important, one rejected-nit, one OOS ----
IMPL="$FIX/larch-logs/implement/RUN-IMPL-1"
mkdir -p "$IMPL"
cat > "$IMPL/manifest.json" <<'JSON'
{"started_at":"2026-05-20T10:00:00Z","larch_version":"48.9.9","skill":"implement"}
JSON
cat > "$IMPL/review-findings-full.jsonl" <<'JSONL'
{"id":"FINDING_2","phase":"code-review","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"1","category":"Inverted guard skips required validation","prose_body":"## Inverted guard skips required validation\n- **Severity**: important\n- **Concern**: logic error: the check is inverted and the feature is broken."}
{"id":"REJ_CR1_1","phase":"code-review","outcome":"rejected","reviewer_slots":["cursor-specialist-structure-output.txt"],"round_num":"1","category":"","body_severity":"nit","focus_area":"code-quality","prose_body":"## refactor: extract a helper for clarity\n- **Concern**: this would be cleaner as a refactor; more readable."}
{"id":"OOS_CR1_1","phase":"code-review","outcome":"out_of_scope","reviewer_slots":["cursor-specialist-edge-cases-output.txt"],"round_num":"1","category":"","body_severity":"latent","prose_body":"## perf: avoid a redundant read\n- **Concern**: a micro-optimization could cache this."}
JSONL

# ---- implement version fixture: post-version nits are not accepted ----
IMPL_POST="$FIX/larch-logs/implement/RUN-IMPL-2"
mkdir -p "$IMPL_POST"
cat > "$IMPL_POST/manifest.json" <<'JSON'
{"started_at":"2026-05-22T10:00:00Z","larch_version":"49.0.0","skill":"implement"}
JSON
cat > "$IMPL_POST/review-findings-full.jsonl" <<'JSONL'
{"id":"FINDING_3","phase":"code-review","outcome":"accepted","reviewer_slots":["codex-specialist-correctness-output.txt"],"round_num":"1","category":"Required write is missing","body_severity":"important","prose_body":"## Required write is missing"}
{"id":"REJ_CR2_1","phase":"code-review","outcome":"rejected","reviewer_slots":["codex-specialist-testing-output.txt"],"round_num":"1","category":"Optional future test","body_severity":"latent","prose_body":"## Optional future test"}
{"id":"OOS_CR2_1","phase":"code-review","outcome":"out_of_scope","reviewer_slots":["codex-specialist-style-output.txt"],"round_num":"1","category":"Naming nit","body_severity":"nit","prose_body":"## Naming nit"}
JSONL

IMPL_BAD_VERSION="$FIX/larch-logs/implement/RUN-IMPL-BAD"
mkdir -p "$IMPL_BAD_VERSION"
cat > "$IMPL_BAD_VERSION/manifest.json" <<'JSON'
{"started_at":"2026-05-23T10:00:00Z","larch_version":"not-a-version","skill":"implement"}
JSON
cat > "$IMPL_BAD_VERSION/review-findings-full.jsonl" <<'JSONL'
{"id":"FINDING_BAD","phase":"code-review","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"1","category":"Bad version run","body_severity":"important","prose_body":"## Bad version run"}
JSONL


# ---- implement false-negative TSV-primary fixture: TSV verdict wins over JSONL outcome/id ----
IMPL_FN="$FIX/larch-logs/implement/RUN-IMPL-FN"
mkdir -p "$IMPL_FN/round-1"
cat > "$IMPL_FN/manifest.json" <<'JSON'
{"started_at":"2026-05-28T10:00:00Z","larch_version":"49.0.0","skill":"implement"}
JSON
cat > "$IMPL_FN/round-1/review-findings-full.jsonl" <<'JSONL'
{"id":"REJ_CR1_4","phase":"code-review","outcome":"rejected","reviewer_slots":["cursor-validity"],"round_num":"1","category":"TSV neutral should win","body_severity":"important","prose_body":"## FINDING_4:\n- **Concern**: TSV links this mismatched JSONL id through the prose token."}
{"id":"REJ_CR1_5","phase":"code-review","outcome":"rejected","reviewer_slots":["codex-pragmatism"],"round_num":"1","category":"Blocking reject","body_severity":"blocking","prose_body":"## FINDING_5:\n- **Concern**: This is truly blocking."}
JSONL
printf 'finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tbody_severity\tscope\n' > "$IMPL_FN/round-1/findings-classification.tsv"
{
  printf 'FINDING_4\tcursor-validity\tneutral\tYES\ttrue\tmajor\tgood\tfalse\tcursor-validity\tNO\ttrue\tnit\tweak\tfalse\tcodex-plan\tNO\ttrue\tnit\tweak\tfalse\tcodex-prag\t\t\n'
} >> "$IMPL_FN/round-1/findings-classification.tsv"
printf 'FINDING_5\tcodex-pragmatism\trejected\tYES\ttrue\tmajor\tgood\tfalse\tcursor-validity\tNO\ttrue\tnit\tweak\tfalse\tcodex-plan\tNO\ttrue\tnit\tweak\tfalse\tcodex-prag\tblocking\t\n' >> "$IMPL_FN/round-1/findings-classification.tsv"
printf 'OOS_CR1_6\tcursor-validity\tneutral\tYES\ttrue\tmajor\tgood\tfalse\tcursor-validity\tNO\ttrue\tnit\tweak\tfalse\tcodex-plan\tNO\ttrue\tnit\tweak\tfalse\tcodex-prag\timportant\t\n' >> "$IMPL_FN/round-1/findings-classification.tsv"
printf 'FINDING_7\tcursor-validity\tneutral\tYES\ttrue\tmajor\tgood\tfalse\tcursor-validity\tNO\ttrue\tnit\tweak\tfalse\tcodex-plan\tNO\ttrue\tnit\tweak\tfalse\tcodex-prag\timportant\toos\n' >> "$IMPL_FN/round-1/findings-classification.tsv"
printf 'FINDING_8\tcursor-validity\tout_of_scope\tYES\ttrue\tmajor\tgood\tfalse\tcursor-validity\tNO\ttrue\tnit\tweak\tfalse\tcodex-plan\tNO\ttrue\tnit\tweak\tfalse\tcodex-prag\timportant\t\n' >> "$IMPL_FN/round-1/findings-classification.tsv"
printf 'FINDING_10\tcursor-validity\texonerated\tYES\ttrue\tmajor\tgood\tfalse\tcursor-validity\tNO\ttrue\tnit\tweak\tfalse\tcodex-plan\tNO\ttrue\tnit\tweak\tfalse\tcodex-prag\timportant\t\n' >> "$IMPL_FN/round-1/findings-classification.tsv"

# ---- implement self-review fixture: empty JSONL sentinel plus tally counts ----
IMPL_SELF="$FIX/larch-logs/implement/RUN-IMPL-SELF"
mkdir -p "$IMPL_SELF"
cat > "$IMPL_SELF/manifest.json" <<'JSON'
{"started_at":"2026-05-26T10:00:00Z","larch_version":"49.0.0","skill":"implement"}
JSON
: > "$IMPL_SELF/review-findings-full.jsonl"
cat > "$IMPL_SELF/code-review-tally.json" <<'JSON'
{"schema_version":2,"phase":"code-review","mode":"self-review","accepted_count":2,"rejected_count":1}
JSON

# ---- implement malformed JSONL fixture: must not fall back to self-review tally ----
IMPL_MALFORM="$FIX/larch-logs/implement/RUN-IMPL-MALFORM"
mkdir -p "$IMPL_MALFORM"
cat > "$IMPL_MALFORM/manifest.json" <<'JSON'
{"started_at":"2026-05-27T10:00:00Z","larch_version":"49.0.0","skill":"implement"}
JSON
printf '{not json\n' > "$IMPL_MALFORM/review-findings-full.jsonl"
cat > "$IMPL_MALFORM/code-review-tally.json" <<'JSON'
{"schema_version":2,"phase":"code-review","mode":"self-review","accepted_count":5,"rejected_count":3}
JSON

# ---- implement 21-column TSV fixture: voter severities stay aligned with vN_tool columns ----
IMPL_TSV21="$FIX/larch-logs/implement/RUN-IMPL-TSV21"
mkdir -p "$IMPL_TSV21/round-1"
cat > "$IMPL_TSV21/manifest.json" <<'JSON'
{"started_at":"2026-05-25T10:00:00Z","larch_version":"49.0.0","skill":"implement"}
JSON
cat > "$IMPL_TSV21/review-findings-full.jsonl" <<'JSONL'
{"id":"FINDING_21","phase":"code-review","outcome":"accepted","reviewer_slots":["cursor-validity"],"round_num":"1","category":"Twenty-one column probe","prose_body":"## Twenty-one column probe"}
JSONL
printf 'finding_id	reviewer_slots	voting_result	v1_vote	v1_correctness	v1_severity	v1_quality	v1_uncertain	v1_tool	v2_vote	v2_correctness	v2_severity	v2_quality	v2_uncertain	v2_tool	v3_vote	v3_correctness	v3_severity	v3_quality	v3_uncertain	v3_tool\n' > "$IMPL_TSV21/round-1/findings-classification.tsv"
printf 'FINDING_21	cursor-validity	accepted	YES	true	major	good	false	cursor-validity	NO	true	nit	weak	false	cursor-plan-fidelity	YES	true	minor	adequate	false	cursor-pragmatism\n' >> "$IMPL_TSV21/round-1/findings-classification.tsv"

# ---- design fixture: one accepted-major in-scope, one rejected-nit ----
DROUND="$FIX/larch-logs/design/RUN-DSGN-1/plan-review/round-1"
mkdir -p "$DROUND"
cat > "$FIX/larch-logs/design/RUN-DSGN-1/manifest.json" <<'JSON'
{"started_at":"2026-05-21T10:00:00Z","larch_version":"49.0.0"}
JSON
cat > "$FIX/larch-logs/design/RUN-DSGN-1/architectural-guideline-assessment.md" <<'MD'
Deviation approved for the final plan.
MD
cat > "$DROUND/findings.md" <<'MD'
### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Concern**: Plan omits a required file; the feature is incomplete without it.

### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Concern**: A rename would be cleaner here.
MD
printf 'finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tbody_severity\tscope\n' > "$DROUND/findings-classification.tsv"
{
  printf 'FINDING_1\tCursor-Arch\taccepted\tYES\ttrue\tmajor\tgood\tfalse\tClaude\tYES\ttrue\tmajor\tgood\tfalse\tCodex\tYES\ttrue\tmajor\tgood\tfalse\tCursor\timportant\t\n'
} >> "$DROUND/findings-classification.tsv"
printf 'FINDING_2\tCodex-Pragmatic\trejected\tNO\ttrue\tnit\tadequate\tfalse\tClaude\tNO\ttrue\tnit\tadequate\tfalse\tCodex\tNO\ttrue\tnit\tadequate\tfalse\tCursor\tnit\t\n' >> "$DROUND/findings-classification.tsv"
printf 'FINDING_3\tCodex-FN\tneutral\tYES\ttrue\tmajor\tgood\tfalse\tClaude\tNO\ttrue\tnit\tadequate\tfalse\tCodex\tNO\ttrue\tnit\tadequate\tfalse\tCursor\timportant\t\n' >> "$DROUND/findings-classification.tsv"
printf 'FINDING_4\tCodex-FN\trejected\tYES\ttrue\tmajor\tgood\tfalse\tClaude\tNO\ttrue\tnit\tadequate\tfalse\tCodex\tNO\ttrue\tnit\tadequate\tfalse\tCursor\tblocker\t\n' >> "$DROUND/findings-classification.tsv"
printf 'FINDING_5\tCodex-FN\tneutral\tYES\ttrue\tmajor\tgood\tfalse\tClaude\tNO\ttrue\tnit\tadequate\tfalse\tCodex\tNO\ttrue\tnit\tadequate\tfalse\tCursor\timportant\toos\n' >> "$DROUND/findings-classification.tsv"
printf 'FINDING_6\tCodex-FN\tout_of_scope\tYES\ttrue\tmajor\tgood\tfalse\tClaude\tNO\ttrue\tnit\tadequate\tfalse\tCodex\tNO\ttrue\tnit\tadequate\tfalse\tCursor\timportant\t\n' >> "$DROUND/findings-classification.tsv"


DROUND2="$FIX/larch-logs/design/RUN-DSGN-2/plan-review/round-1"
mkdir -p "$DROUND2"
cat > "$FIX/larch-logs/design/RUN-DSGN-2/manifest.json" <<'JSON'
{"started_at":"2026-05-22T10:00:00Z","larch_version":"49.0.0"}
JSON
printf 'finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tbody_severity\n' > "$DROUND2/findings-classification.tsv"
printf 'FINDING_9\tCodex-Concise\taccepted\tYES\ttrue\tminor\tgood\tfalse\tClaude\tYES\ttrue\tminor\tgood\tfalse\tCodex\tYES\ttrue\tminor\tgood\tfalse\tCursor\tlatent\n' >> "$DROUND2/findings-classification.tsv"

DEMPTY="$FIX/larch-logs/design/RUN-DSGN-EMPTY"
mkdir -p "$DEMPTY"
cat > "$DEMPTY/manifest.json" <<'JSON'
{"started_at":"2026-05-22T12:00:00Z","larch_version":"49.0.0"}
JSON
printf ' \n' > "$DEMPTY/architectural-guideline-assessment.md"

DASSESS="$FIX/larch-logs/design/RUN-DSGN-ASSESS"
mkdir -p "$DASSESS"
cat > "$DASSESS/manifest.json" <<'JSON'
{"started_at":"2026-05-23T10:00:00Z","larch_version":"49.0.0"}
JSON
python3 - "$DASSESS/architectural-guideline-assessment.md" "$SCRIPT_DIR/../../.." <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[2]) / "python"))
from larch.core.architectural_guidelines import CLEAN_PRESENTATION_NOTE

Path(sys.argv[1]).write_text(CLEAN_PRESENTATION_NOTE + "\n", encoding="utf-8")
PY

echo "== running analyzer over fixture =="
REPORT=$(python3 "$ANALYZER" --log-root "$FIX/larch-logs" --min-group 1)

assert_contains "$REPORT" "# Review Fluff Analysis" "report header"
assert_contains "$REPORT" "- Records: **18** total (implement code-review **11**, design in-scope **7**)" "self-review tally included in record counts"
assert_contains "$REPORT" "committed-self-review-tally=3" "self-review tally source included"
assert_contains "$REPORT" "## Baselines" "baselines section"
assert_contains "$REPORT" "## Guideline assessment coverage" "guideline assessment coverage section"
assert_contains "$REPORT" "| 4 | 2 | 1 | 1 |" "guideline assessment aggregate counts"
assert_contains "$REPORT" "| RUN-DSGN-1 | 2026-05-21T10:00:00Z | 49.0.0 | deviation |" "guideline deviation row listed"
assert_contains "$REPORT" "| RUN-DSGN-EMPTY | 2026-05-22T12:00:00Z | 49.0.0 | missing |" "empty assessment row excluded from artifact count"
assert_contains "$REPORT" "| RUN-DSGN-ASSESS | 2026-05-23T10:00:00Z | 49.0.0 | clean |" "assessment-only clean row listed"
assert_contains "$REPORT" "implement code-review" "implement baseline row"
assert_contains "$REPORT" "| implement code-review | 11 |" "implement baseline includes self-review tally records"
assert_contains "$REPORT" "design in-scope" "design baseline row"
assert_contains "$REPORT" "## Q1 — Low-acceptance semantic groups" "Q1 section"
assert_contains "$REPORT" "## Recommendations" "recommendations section"
# the rejected nit carries refactor/cleaner text -> a fluff group should surface
assert_contains "$REPORT" "theme:refactor/dry" "refactor group surfaced"
# severity table should separate important from nit
assert_contains "$REPORT" "reviewer-authored body severity" "implement severity table"
assert_contains "$REPORT" "## False-negative / under-acceptance metrics" "false-negative section appears by default"
assert_contains "$REPORT" "| implement false-negative | important | 1 | 2 | 50.0% | 1 |" "implement neutral-rate uses TSV verdict and token-aware JSONL enrichment"
assert_contains "$REPORT" "| design in-scope | important | 1 | 3 | 33.3% | 1 |" "design neutral-rate excludes scope and non-countable verdicts"
assert_contains "$REPORT" "| implement false-negative | 1 | 2 | 50.0% | 1 |" "important-reject-rate includes blocking alias"

echo "== assessment coverage renders without findings =="
EMPTY_FIX=$(mktemp -d "${TMPDIR:-/tmp}/fluff-empty-XXXXXX")
mkdir -p "$EMPTY_FIX/larch-logs/design/RUN-DSGN-ASSESS"
cat > "$EMPTY_FIX/larch-logs/design/RUN-DSGN-ASSESS/manifest.json" <<'JSON'
{"started_at":"2026-05-23T10:00:00Z","larch_version":"49.0.0"}
JSON
cp "$DASSESS/architectural-guideline-assessment.md" "$EMPTY_FIX/larch-logs/design/RUN-DSGN-ASSESS/architectural-guideline-assessment.md"
REPORT_EMPTY=$(python3 "$ANALYZER" --log-root "$EMPTY_FIX/larch-logs" --min-group 1)
rm -rf "$EMPTY_FIX"
assert_contains "$REPORT_EMPTY" "## Guideline assessment coverage" "coverage section appears for zero-finding corpus"
assert_contains "$REPORT_EMPTY" "## False-negative / under-acceptance metrics" "false-negative section appears for zero-finding corpus"
assert_contains "$REPORT_EMPTY" "| 1 | 1 | 1 | 0 |" "zero-finding coverage counts"
assert_contains "$REPORT_EMPTY" "> No review findings found under the log root. Nothing to analyze." "zero-finding footer retained"

echo "== direct run from script directory can import shared helper =="
REPORT_FROM_DIR=$(
    cd "$SCRIPT_DIR"
    python3 fluff-analysis.py --log-root "$FIX/larch-logs" --min-group 1
)
assert_contains "$REPORT_FROM_DIR" "# Review Fluff Analysis" "script-dir invocation succeeded"

echo "== --cutoff enables pre/post section =="
REPORT_CUT=$(python3 "$ANALYZER" --log-root "$FIX/larch-logs" --min-group 1 --cutoff 2026-05-21T00:00:00Z)
assert_contains "$REPORT_CUT" "## Pre/post cutoff" "pre/post section present with --cutoff"
assert_contains "$REPORT_CUT" "### Pre/post false-negative neutral-rate" "false-negative pre/post rows present with --cutoff"

echo "== --since-version enables version pre/post section =="
REPORT_VERSION=$(python3 "$ANALYZER" --log-root "$FIX/larch-logs" --min-group 1 --since-version 49.0.0)
assert_contains "$REPORT_VERSION" "## Pre/post comparison" "version pre/post header"
assert_contains "$REPORT_VERSION" "unknown-version skipped: 1" "malformed larch_version skipped"
assert_contains "$REPORT_VERSION" "| post | nit | 1 | 0.0" "post nit acceptance is zero"
assert_contains "$REPORT_VERSION" "post accepted-low-value: 0.0%" "post accepted-low-value line"
assert_contains "$REPORT_VERSION" "post tier-composition: important" "post tier composition line"
assert_contains "$REPORT_VERSION" "| pre | nit | 1 | 0.0" "explicit body_severity drives pre nit tier"
assert_contains "$REPORT_VERSION" "| post | implement false-negative | important | 1 | 2 | 50.0% | 1 |" "implement false-negative rows carry post period"

echo "== body_severity and focus_area survive prose cap =="
LONG_PROSE=$(python3 -c "print('z' * 2500)")
IMPL_CAP="$FIX/larch-logs/implement/RUN-IMPL-CAP"
mkdir -p "$IMPL_CAP"
cat > "$IMPL_CAP/manifest.json" <<'JSON'
{"started_at":"2026-05-24T10:00:00Z","larch_version":"49.0.0","skill":"implement"}
JSON
python3 - "$IMPL_CAP/review-findings-full.jsonl" "$LONG_PROSE" <<'PY'
import json, sys
path, prose = sys.argv[1], sys.argv[2]
row = {
    "id": "FINDING_CAP",
    "phase": "code-review",
    "outcome": "accepted",
    "reviewer_slots": ["cursor-specialist-testing-output.txt"],
    "round_num": "1",
    "category": "Cap probe",
    "body_severity": "nit",
    "focus_area": "testing",
    "prose_body": prose,
}
open(path, "w", encoding="utf-8").write(json.dumps(row) + "\n")
PY
python3 - "$ANALYZER" "$FIX/larch-logs" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("fluff_analysis", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
records = mod.extract(sys.argv[2], "", False, None, None, (49, 0, 0))
rec = next(r for r in records if r.get("finding_id") == "FINDING_CAP")
assert rec["severity"] == "nit", rec
assert rec.get("focus_area") == "testing", rec
assert len(rec.get("text", "")) <= 2000, len(rec.get("text", ""))
PY
PASS=$((PASS + 1))
echo "  ok: body_severity and focus_area extracted before prose cap"

echo "== concise design TSV severity is consumed without findings.md =="
python3 - "$ANALYZER" "$FIX/larch-logs" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("fluff_analysis", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
records = mod.extract(sys.argv[2], "", False, None, None, (49, 0, 0))
rec = next(r for r in records if r.get("finding_id") == "FINDING_9")
assert rec["severity"] == "latent", rec
assert rec["title"] == "FINDING_9", rec
assert "Codex-Concise" in rec["text"], rec
PY
PASS=$((PASS + 1))
echo "  ok: concise design severity fallback"


echo "== implement 21-column TSV severity columns are header-based =="
python3 - "$ANALYZER" "$FIX/larch-logs" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("fluff_analysis", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
records = mod.extract(sys.argv[2], "", False, None, None, None)
rec = next(r for r in records if r.get("finding_id") == "FINDING_21")
assert rec["v_severities"] == ["major", "nit", "minor"], rec
PY
PASS=$((PASS + 1))
echo "  ok: implement 21-column TSV severities parsed by header"

echo "== empty implement JSONL falls back to self-review tally =="
python3 - "$ANALYZER" "$FIX/larch-logs" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("fluff_analysis", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
records = mod.extract(sys.argv[2], "", False, None, None, None)
rows = [r for r in records if r.get("run_id") == "RUN-IMPL-SELF"]
assert [r["finding_id"] for r in rows] == [
    "SELF_REVIEW_ACCEPTED_1",
    "SELF_REVIEW_ACCEPTED_2",
    "SELF_REVIEW_REJECTED_1",
], rows
assert {r["source"] for r in rows} == {"committed-self-review-tally"}, rows
assert [r["outcome"] for r in rows] == ["accepted", "accepted", "rejected"], rows
PY
PASS=$((PASS + 1))
echo "  ok: self-review tally fallback extracted"

echo "== malformed implement JSONL does not fall back to self-review tally =="
python3 - "$ANALYZER" "$FIX/larch-logs" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("fluff_analysis", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
records = mod.extract(sys.argv[2], "", False, None, None, None)
rows = [r for r in records if r.get("run_id") == "RUN-IMPL-MALFORM"]
assert rows == [], rows
tally = [r for r in records if r.get("source") == "committed-self-review-tally" and r.get("run_id") == "RUN-IMPL-MALFORM"]
assert tally == [], tally
PY
PASS=$((PASS + 1))
echo "  ok: malformed JSONL skips self-review tally fallback"

echo "== missing log root exits 2 =="
set +e
python3 "$ANALYZER" --log-root "$FIX/does-not-exist" >/dev/null 2>&1
RC=$?
set -e
assert_eq "$RC" "2" "missing log-root exit code"

echo ""
echo "PASS=$PASS FAIL=$FAIL"
if [[ "$FAIL" -ne 0 ]]; then
    exit 1
fi
