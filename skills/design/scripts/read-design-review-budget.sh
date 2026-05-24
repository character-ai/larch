#!/usr/bin/env bash
# Emit review_budget (quick|full) from design run-params.json.
# Used by invoke-plan-validator-if-not-quick.sh and documented in SKILL.md.
# Fallback order: python3 JSON → jq → grep literals → sketch_budget heuristic.
set -euo pipefail

f="${1:?usage: read-design-review-budget.sh RUN_PARAMS_JSON}"

if [[ ! -r "$f" ]]; then
    printf '%s\n' full
    exit 0
fi

if command -v python3 >/dev/null 2>&1; then
    _out=$(
        python3 -c 'import json,sys
path=sys.argv[1]
with open(path) as fp:
    d=json.load(fp)
rb=d.get("review_budget")
if rb in ("quick","full"):
    print(rb)
else:
    try:
        sb=int(d.get("sketch_budget"))
    except (TypeError, ValueError):
        sb=None
    print("quick" if sb == 0 else "full")' "$f" 2>/dev/null
    ) && [[ "$_out" == "quick" || "$_out" == "full" ]] && printf '%s\n' "$_out" && exit 0
fi

if command -v jq >/dev/null 2>&1; then
    _out=$(jq -r 'if .review_budget=="quick" or .review_budget=="full" then .review_budget elif .sketch_budget==0 then "quick" else "full" end' "$f" 2>/dev/null) || _out=""
    [[ "$_out" == "quick" || "$_out" == "full" ]] && printf '%s\n' "$_out" && exit 0
fi

if grep -qE '"review_budget"[[:space:]]*:[[:space:]]*"quick"' "$f" 2>/dev/null; then
    printf '%s\n' quick
    exit 0
fi
if grep -qE '"review_budget"[[:space:]]*:[[:space:]]*"full"' "$f" 2>/dev/null; then
    printf '%s\n' full
    exit 0
fi

if grep -qE '"sketch_budget"[[:space:]]*:[[:space:]]*0([^0-9]|$)' "$f" 2>/dev/null; then
    printf '%s\n' quick
    exit 0
fi

printf '%s\n' full
