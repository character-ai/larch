#!/usr/bin/env bash
# Regression tests for scripts/timing-ledger.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_BASE=$(mktemp -d "${TMPDIR:-/tmp}/larch-timing-ledger-test.XXXXXX")
trap 'rm -rf "$TMP_BASE"' EXIT

LEDGER="$TMP_BASE/timing.tsv"

"$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$LEDGER" mark "Step 0"
"$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$LEDGER" workflow-path HARD
"$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$LEDGER" record-vendor-task \
    --vendor codex --task-kind codex-implement --start-s 10 --end-s 20 \
    --output "/private/work/output.txt" --exit-code 0 --status complete

[[ $(awk -F '\t' '{print NF}' "$LEDGER" | sort -u) == "13" ]]
grep -Fq $'v1\tmark\t' "$LEDGER"
grep -Fq $'v1\tworkflow\t' "$LEDGER"
grep -Fq $'\tcodex\tcodex-implement\t10\t20\t10\toutput.txt\t0\tcomplete' "$LEDGER"
if grep -Fq '/private/work/output.txt' "$LEDGER"; then
    echo "absolute output path leaked into timing ledger" >&2
    exit 1
fi

mode=$(stat -f '%Lp' "$LEDGER" 2>/dev/null || stat -c '%a' "$LEDGER")
[[ "$mode" == "600" ]]

WARN="$TMP_BASE/warn.txt"
"$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$LEDGER" record-vendor-task \
    --vendor cursor --task-kind cursor-custom-kind --start-s 30 --end-s 32 \
    --output "x"$'\t'"y.txt" 2>"$WARN"
grep -Fq 'unknown task-kind: cursor-custom-kind' "$WARN"
grep -Fq '<NUL>' "$LEDGER"

"$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$LEDGER" record-vendor-task \
    --vendor gemini --task-kind gemini-review --start-s 40 --end-s 35 \
    --output "z.txt" 2>"$WARN"
grep -Fq 'clamping duration_s to 0' "$WARN"
grep -Fq $'\tgemini\tgemini-review\t40\t35\t0\tz.txt\t0\tunknown' "$LEDGER"

BAD="$TMP_BASE/bad.txt"
"$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$LEDGER" record-vendor-task \
    --vendor codex --task-kind BadKind --start-s 1 --end-s 2 --output x 2>"$BAD"
grep -Fq 'malformed task-kind' "$BAD"

OUTSIDE="$TMP_BASE/outside.txt"
LARCH_TIMING_LEDGER="/not/allowed/timing.tsv" IMPLEMENT_TMPDIR="$TMP_BASE" \
    "$REPO_ROOT/scripts/timing-ledger.sh" mark "fall through" 2>"$OUTSIDE"
grep -Fq 'LARCH_TIMING_LEDGER not under any allowed root' "$OUTSIDE"
grep -Fq 'fall through' "$TMP_BASE/timing-ledger.tsv"

ENV_LEDGER="$TMP_BASE/env/timing.tsv"
mkdir -p "$TMP_BASE/env"
LARCH_TIMING_LEDGER="$ENV_LEDGER" IMPLEMENT_TMPDIR="$TMP_BASE" \
    "$REPO_ROOT/scripts/timing-ledger.sh" mark "env ok"
grep -Fq 'env ok' "$ENV_LEDGER"

SEQ_LEDGER="$TMP_BASE/parallel.tsv"
seq 1 20 | xargs -P 4 -I{} "$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$SEQ_LEDGER" mark "p{}"
[[ $(wc -l < "$SEQ_LEDGER" | tr -d ' ') == "20" ]]
[[ $(awk -F '\t' '{print NF}' "$SEQ_LEDGER" | sort -u) == "13" ]]

echo "PASS: test-timing-ledger.sh"
