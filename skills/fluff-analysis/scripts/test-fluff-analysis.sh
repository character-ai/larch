#!/usr/bin/env bash
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

FIX=$(mktemp -d "${TMPDIR:-/tmp}/fluff-fixture-XXXXXX")
trap 'rm -rf "$FIX"' EXIT

# ---- implement fixture: one accepted-important, one rejected-nit, one OOS ----
IMPL="$FIX/larch-logs/implement/RUN-IMPL-1"
mkdir -p "$IMPL"
cat > "$IMPL/manifest.json" <<'JSON'
{"started_at":"2026-05-20T10:00:00Z","skill":"implement"}
JSON
cat > "$IMPL/review-findings-full.jsonl" <<'JSONL'
{"id":"FINDING_2","phase":"code-review","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"1","category":"Inverted guard skips required validation","prose_body":"## Inverted guard skips required validation\n- **Severity**: important\n- **Concern**: logic error: the check is inverted and the feature is broken."}
{"id":"REJ_CR1_1","phase":"code-review","outcome":"rejected","reviewer_slots":["cursor-specialist-structure-output.txt"],"round_num":"1","category":"","prose_body":"## refactor: extract a helper for clarity\n- **Severity**: nit\n- **Concern**: this would be cleaner as a refactor; more readable."}
{"id":"OOS_CR1_1","phase":"code-review","outcome":"out_of_scope","reviewer_slots":["cursor-specialist-edge-cases-output.txt"],"round_num":"1","category":"","prose_body":"## perf: avoid a redundant read\n- **Severity**: latent\n- **Concern**: a micro-optimization could cache this."}
JSONL

# ---- design fixture: one accepted-major in-scope, one rejected-nit ----
DROUND="$FIX/larch-logs/design/RUN-DSGN-1/plan-review/round-1"
mkdir -p "$DROUND"
cat > "$FIX/larch-logs/design/RUN-DSGN-1/manifest.json" <<'JSON'
{"started_at":"2026-05-21T10:00:00Z"}
JSON
cat > "$DROUND/findings.md" <<'MD'
### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Concern**: Plan omits a required file; the feature is incomplete without it.

### FINDING_2:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: code-quality
- **Concern**: A rename would be cleaner here.
MD
printf 'finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\n' > "$DROUND/findings-classification.tsv"
printf 'FINDING_1\tCursor-Arch\taccepted\tYES\ttrue\tmajor\tgood\tfalse\tClaude\tYES\ttrue\tmajor\tgood\tfalse\tCodex\tYES\ttrue\tmajor\tgood\tfalse\tCursor\n' >> "$DROUND/findings-classification.tsv"
printf 'FINDING_2\tCodex-Edge\trejected\tNO\ttrue\tnit\tadequate\tfalse\tClaude\tNO\ttrue\tnit\tadequate\tfalse\tCodex\tNO\ttrue\tnit\tadequate\tfalse\tCursor\n' >> "$DROUND/findings-classification.tsv"

echo "== running analyzer over fixture =="
REPORT=$(python3 "$ANALYZER" --log-root "$FIX/larch-logs" --min-group 1)

assert_contains "$REPORT" "# Review Fluff Analysis" "report header"
assert_contains "$REPORT" "## Baselines" "baselines section"
assert_contains "$REPORT" "implement code-review" "implement baseline row"
assert_contains "$REPORT" "design in-scope" "design baseline row"
assert_contains "$REPORT" "## Q1 — Low-acceptance semantic groups" "Q1 section"
assert_contains "$REPORT" "## Recommendations" "recommendations section"
# the rejected nit carries refactor/cleaner text -> a fluff group should surface
assert_contains "$REPORT" "theme:refactor/dry" "refactor group surfaced"
# severity table should separate important from nit
assert_contains "$REPORT" "reviewer-authored body severity" "implement severity table"

echo "== --cutoff enables pre/post section =="
REPORT_CUT=$(python3 "$ANALYZER" --log-root "$FIX/larch-logs" --min-group 1 --cutoff 2026-05-21T00:00:00Z)
assert_contains "$REPORT_CUT" "## Pre/post cutoff" "pre/post section present with --cutoff"

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
