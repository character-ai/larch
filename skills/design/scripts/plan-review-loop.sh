#!/usr/bin/env bash
# plan-review-loop.sh — Single-pass /design plan-review driver (scout → panel → collect → ballot → aggregate → voters → tally).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# Optional harness overrides (see test-plan-review-loop.sh).
PLAN_REVIEW_SCOUT_SH="${LARCH_PLAN_REVIEW_SCOUT_SH:-$PLUGIN_ROOT/skills/design/scripts/scout-plan-archetypes-wrapper.sh}"
PLAN_REVIEW_DISPATCH_PANEL_SH="${LARCH_PLAN_REVIEW_DISPATCH_PANEL_SH:-$PLUGIN_ROOT/skills/design/scripts/dispatch-plan-review-panel.sh}"
PLAN_REVIEW_COLLECT_SH="${LARCH_PLAN_REVIEW_COLLECT_SH:-$PLUGIN_ROOT/scripts/collect-agent-results.sh}"
PLAN_REVIEW_DISPATCH_VOTERS_SH="${LARCH_PLAN_REVIEW_DISPATCH_VOTERS_SH:-$PLUGIN_ROOT/scripts/dispatch-plan-voters.sh}"
PLAN_REVIEW_TALLY_SH="${LARCH_PLAN_REVIEW_TALLY_SH:-$PLUGIN_ROOT/skills/design/scripts/tally-plan-review.sh}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-vote-tally.sh
source "$PLUGIN_ROOT/scripts/lib-vote-tally.sh"
_dedup_failed=0

usage() {
    larch_err "Usage: plan-review-loop.sh --design-tmpdir DIR --plan-file PATH [--feature-file PATH] [--round-num N] --codex-present true|false --cursor-present true|false [--timeout SEC] [--help]"
}

DESIGN_TMPDIR=""
PLAN_FILE=""
FEATURE_FILE=""
ROUND_NUM="1"
CODEX_PRESENT=""
CURSOR_PRESENT=""
COLLECT_TIMEOUT="1860"
PANEL_TIMEOUT="1860"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?}"; shift 2 ;;
        --round-num) ROUND_NUM="${2:?}"; shift 2 ;;
        --codex-present) CODEX_PRESENT="${2:?}"; shift 2 ;;
        --cursor-present) CURSOR_PRESENT="${2:?}"; shift 2 ;;
        --timeout) PANEL_TIMEOUT="${2:?}"; COLLECT_TIMEOUT="${2:?}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "plan-review-loop.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$DESIGN_TMPDIR" ]] || { usage; exit 2; }
[[ -n "$PLAN_FILE" && -f "$PLAN_FILE" ]] || { larch_err "plan-review-loop.sh: --plan-file must name a readable file"; exit 2; }
[[ "$CODEX_PRESENT" == "true" || "$CODEX_PRESENT" == "false" ]] || { larch_err "plan-review-loop.sh: --codex-present must be true or false"; exit 2; }
[[ "$CURSOR_PRESENT" == "true" || "$CURSOR_PRESENT" == "false" ]] || { larch_err "plan-review-loop.sh: --cursor-present must be true or false"; exit 2; }
case "$ROUND_NUM" in ''|*[!0-9]*) larch_err "plan-review-loop.sh: --round-num must be a positive integer"; exit 2 ;; esac
ROUND_NUM=$((10#$ROUND_NUM))
(( ROUND_NUM > 0 )) || { larch_err "plan-review-loop.sh: --round-num must be a positive integer"; exit 2; }
case "$COLLECT_TIMEOUT" in ''|*[!0-9]*) larch_err "plan-review-loop.sh: --timeout must be a positive integer"; exit 2 ;; esac

DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
mkdir -p "$DESIGN_TMPDIR"

if [[ -z "$FEATURE_FILE" ]]; then
    FEATURE_FILE="${IMPLEMENT_TMPDIR:-$DESIGN_TMPDIR}/feature-description.txt"
fi
[[ -f "$FEATURE_FILE" ]] || { larch_err "plan-review-loop.sh: feature file not found: $FEATURE_FILE"; exit 2; }

_brainstorm_file="$DESIGN_TMPDIR/brainstorm.md"
if [[ -f "$_brainstorm_file" && -s "$_brainstorm_file" ]]; then
    _merged_feature="$DESIGN_TMPDIR/plan-review-feature-context.txt"
    {
        printf '%s\n' "## Feature / issue context (base)"
        cat "$FEATURE_FILE"
        printf '\n\n%s\n' "## Brainstorm synthesis (additive; optional)"
        cat "$_brainstorm_file"
    } >"$_merged_feature"
    FEATURE_FILE="$_merged_feature"
fi

emit_loop_kvs() {
    local loop_status="$1" accepted_count="$2" degraded_panel="$3" aggregator_status="$4" tally_status="$5" voting_tally_file="$6" voter1_parse="$7"
    emit_kv LOOP_STATUS "$loop_status"
    emit_kv ACCEPTED_COUNT "$accepted_count"
    emit_kv DEGRADED_PANEL "$degraded_panel"
    emit_kv ROUNDS_COMPLETED "$ROUND_NUM"
    emit_kv AGGREGATOR_STATUS "$aggregator_status"
    emit_kv TALLY_PLAN_REVIEW_STATUS "$tally_status"
    emit_kv VOTING_TALLY_FILE "$voting_tally_file"
    emit_kv VOTER_1_PARSE_RATE_STATUS "$voter1_parse"
}

reset_findings_classification() {
    local classification_out="$DESIGN_TMPDIR/plan-review/round-$ROUND_NUM/findings-classification.tsv"
    mkdir -p "$(dirname "$classification_out")"
    findings_classification_header > "$classification_out"
}

write_empty_review_artifacts() {
    local tally_note="$1"
    local classification_out="$DESIGN_TMPDIR/plan-review/round-$ROUND_NUM/findings-classification.tsv"
    : > "$DESIGN_TMPDIR/accepted-plan-findings.md"
    : > "$DESIGN_TMPDIR/rejected-findings.md"
    : > "$DESIGN_TMPDIR/oos.md"
    : > "$DESIGN_TMPDIR/oos-accepted-design.md"
    mkdir -p "$(dirname "$classification_out")"
    findings_classification_header > "$classification_out"
    {
        printf '# Plan Review Voting Tally\n\n'
        printf '%s\n' "$tally_note"
    } > "$DESIGN_TMPDIR/voting-tally.md"
}

plan_slot_human_label() {
    python3 - "$1" <<'PY'
import sys
s = sys.argv[1]
pairs = [
    ("dyn-cursor-plan-", "Cursor-dyn-"),
    ("dyn-codex-plan-", "Codex-dyn-"),
    ("cursor-plan-", "Cursor-"),
    ("codex-plan-", "Codex-"),
]
for pfx, name in pairs:
    if s.startswith(pfx):
        rest = s[len(pfx) :]
        if name.endswith("dyn-"):
            print(name + rest)
        else:
            print(name + rest.replace("_", " ").title().replace(" ", ""))
        raise SystemExit(0)
print(s)
PY
}

plan_review_slot_for_reviewer() {
    python3 - "$1" "$2" <<'PY'
import json, os, sys


def norm(p: str) -> str:
    try:
        return os.path.realpath(p)
    except OSError:
        return os.path.normpath(p)


def main() -> None:
    mp, rf = sys.argv[1], sys.argv[2]
    try:
        rfn = norm(rf)
    except OSError:
        rfn = rf
    try:
        with open(mp, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                out = (o.get("output") or "").strip()
                slot = (o.get("slot") or "").strip()
                if not out or not slot:
                    continue
                try:
                    if rfn == norm(out) or rf == out or os.path.normpath(rf) == os.path.normpath(out):
                        print(slot)
                        return
                except OSError:
                    if rf == out:
                        print(slot)
                        return
    except OSError:
        pass
    print("unknown-slot")


if __name__ == "__main__":
    main()
PY
}

# --- Step 2: scout (fail-open) ---
"$PLAN_REVIEW_SCOUT_SH" \
    --plan-file "$PLAN_FILE" \
    --description-file "$FEATURE_FILE" \
    --output "$DESIGN_TMPDIR/scout-plan-manifest.json" \
    --max-archetypes 6 \
    --session-env-path "$DESIGN_TMPDIR/source-env.sh" || true

# --- Step 3: panel dispatch ---
_panel_raw=$("$PLAN_REVIEW_DISPATCH_PANEL_SH" \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" \
    --plan-file "$PLAN_FILE" \
    --feature-file "$FEATURE_FILE" \
    --timeout "$PANEL_TIMEOUT")

PANEL_DISPATCH_OK="true"
PANEL_PATHS_FILE=""
ALL_OUTPUT_FILES_PATH=""
STATIC_DISPATCH_OK="true"
FALLBACK_COUNT="0"
DEGRADED_ROUND="false"
DYNAMIC_SLOT_COUNT="0"
while IFS= read -r _line || [[ -n "$_line" ]]; do
    _key="${_line%%=*}"
    _value="${_line#*=}"
    case "$_key" in
        DISPATCH_OK) PANEL_DISPATCH_OK="$_value" ;;
        PANEL_PATHS_FILE) PANEL_PATHS_FILE="$_value" ;;
        ALL_OUTPUT_FILES_PATH) ALL_OUTPUT_FILES_PATH="$_value" ;;
        STATIC_DISPATCH_OK) STATIC_DISPATCH_OK="$_value" ;;
        FALLBACK_COUNT) FALLBACK_COUNT="$_value" ;;
        DEGRADED_ROUND) DEGRADED_ROUND="$_value" ;;
        DYNAMIC_SLOT_COUNT) DYNAMIC_SLOT_COUNT="$_value" ;;
        WARN) emit_kv WARN "$_value" ;;
    esac
done <<< "$_panel_raw"

printf '%s\n' "$_panel_raw"

[[ -n "$PANEL_PATHS_FILE" ]] || PANEL_PATHS_FILE="$ALL_OUTPUT_FILES_PATH"
_paths_readable=0
if [[ -n "$PANEL_PATHS_FILE" && -f "$PANEL_PATHS_FILE" && -s "$PANEL_PATHS_FILE" ]]; then
    _paths_readable=1
fi

if [[ "$_paths_readable" -eq 0 ]]; then
    write_empty_review_artifacts "**Plan-review panel dispatch failed; voting was not run.**"
    : > "$DESIGN_TMPDIR/ballot.txt"
    emit_loop_kvs panel-failed 0 1 skipped panel-failed "" SKIPPED
    exit 1
fi

# --- Step 5: collect ---
_collect_out=$("$PLAN_REVIEW_COLLECT_SH" \
    --timeout "$COLLECT_TIMEOUT" \
    --substantive-validation \
    --validation-mode \
    --structured-reviewer-validation \
    --paths-file "$PANEL_PATHS_FILE")

_manifest="$DESIGN_TMPDIR/plan-review-slots.ndjson"
_slot_lines=()
while IFS= read -r _srow || [[ -n "$_srow" ]]; do
    [[ -n "$_srow" ]] || continue
    _slot=$(printf '%s' "$_srow" | jq -r '.slot // empty')
    [[ -n "$_slot" ]] && _slot_lines+=("$_slot")
done < "$_manifest"

_dirty_out=$("$PLUGIN_ROOT/scripts/check-mid-run-dirty-tree.sh" --mode checkpoint || true)
if grep -qE '^STATUS=(dirty|unknown)$' <<< "$_dirty_out"; then
    printf '%s\n' "$_dirty_out" > "$DESIGN_TMPDIR/dirty-tree-detected.env" || true
    emit_kv WARN "plan-review-collection: dirty tree detected"
fi

_parse_py="$DESIGN_TMPDIR/.plan-review-loop-parse-collect.py"
cat > "$_parse_py" <<'PY'
import sys

def main():
    text = sys.stdin.read()
    blocks = []
    for para in text.split("\n\n"):
        lines = [ln.strip() for ln in para.splitlines() if ln.strip()]
        if not lines:
            continue
        d = {}
        for ln in lines:
            if "=" not in ln:
                continue
            k, v = ln.split("=", 1)
            d[k] = v
        if "REVIEWER_FILE" in d or "STATUS" in d:
            blocks.append(d)
    for b in blocks:
        sys.stdout.write(
            "%s\x1f%s\x1f%s\x1f%s\x1f%s\n"
            % (
                b.get("REVIEWER_FILE", ""),
                b.get("TOOL", ""),
                b.get("STATUS", ""),
                b.get("EXIT_CODE", "0"),
                b.get("FAILURE_REASON", ""),
            )
        )


if __name__ == "__main__":
    main()
PY

_findings_tmp="$DESIGN_TMPDIR/findings.md.tmp"
: > "$_findings_tmp"
while IFS= read -r _rec || [[ -n "$_rec" ]]; do
    [[ -z "$_rec" ]] && continue
    IFS=$'\x1f' read -r _rf _tool _st _xc _fr <<< "$_rec" || true
    _slot_name=$(plan_review_slot_for_reviewer "$_manifest" "$_rf")
    _human=$(plan_slot_human_label "$_slot_name")
    if [[ "$_st" != "OK" ]]; then
        _fail_slug=$(python3 -c 'import re,sys; s=sys.argv[1].strip(); s=re.sub(r"[^A-Za-z0-9._+-]+","_",s); print((s or "slot")[:200])' "$_slot_name")
        _fail_log="$DESIGN_TMPDIR/${_fail_slug}-collector.failure.log"
        _srec="REVIEWER_FILE=${_rf}|TOOL=${_tool}|STATUS=${_st}|EXIT_CODE=${_xc}|FAILURE_REASON=${_fr}"
        "$PLUGIN_ROOT/scripts/compose-collector-failure-log.sh" \
            --reviewer-file "$_rf" \
            --structured-record "$_srec" \
            --output "$_fail_log" || true
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 3" \
            --tool "collect-agent-results.sh ${_tool} ${_st}" \
            --exit-code "${_xc:-1}" \
            --category "External Reviewer Issues" \
            --output-file "$_fail_log" \
            --redact >/dev/null 2>&1 || true
    else
        _tsv="${_rf}.tsv"
        _frag=$(mktemp "$DESIGN_TMPDIR/.plan-find-frag.XXXXXX")
        python3 - "$_rf" "$_human" "$_tsv" <<'PY' > "$_frag" 2>/dev/null || true
import csv, sys

reviewer_path, slot, tsv_path = sys.argv[1:4]
fi = 1
oi = 1


def emit_finding(n, slot, sev, focus, loc, what, scen, fix):
    print("### FINDING_%d:" % n)
    print("- **Reviewer(s)**: %s" % slot)
    print("- **Severity**: %s" % (sev or "important"))
    print("- **Focus area**: %s" % focus)
    print("- **Location**: %s" % loc)
    print("- **Concern**: %s. Scenario: %s" % (what, scen))
    print("- **Proposed resolution**: %s" % fix)
    print()


def emit_oos(n, slot, sev, focus, loc, what, scen, fix):
    print("### OOS_%d:" % n)
    print("- **Description**: %s. Scenario: %s" % (what, scen))
    print("- **Reviewer**: %s" % slot)
    print("- **Severity**: %s" % (sev or "important"))
    print("- **Focus area**: %s" % focus)
    print("- **Location**: %s" % loc)
    print("- **Phase**: design")
    print()


def main():
    rows = []
    try:
        with open(tsv_path, "r", encoding="utf-8", errors="replace") as fh:
            rdr = csv.DictReader(fh, delimiter="\t")
            for row in rdr:
                rows.append(row)
    except OSError:
        rows = []
    if not rows:
        return
    fi = 1
    oi = 1
    for row in rows:
        scope = (row.get("scope") or "").strip().lower()
        sev = (row.get("severity") or "").strip()
        focus = (row.get("focus_area") or "").strip()
        loc = (row.get("location") or "").strip()
        what = (row.get("what") or "").strip()
        scen = (row.get("scenario_or_breakage") or "").strip()
        fix = (row.get("suggested_fix") or "").strip()
        if scope in ("out_of_scope", "out-of-scope", "oos"):
            emit_oos(oi, slot, sev, focus, loc, what, scen, fix)
            oi += 1
        else:
            emit_finding(fi, slot, sev, focus, loc, what, scen, fix)
            fi += 1


if __name__ == "__main__":
    main()
PY
        if [[ -s "$_frag" ]] && grep -qE '^### (FINDING|OOS)_[0-9]+:' "$_frag" 2>/dev/null; then
            cat "$_frag" >> "$_findings_tmp"
        elif [[ ! -s "$_frag" ]]; then
            if [[ "$_st" == "OK" ]]; then
                emit_kv WARN "plan-review-tsv: empty or missing structured reviewer rows for ${_rf}"
            fi
        else
            emit_kv WARN "plan-review-tsv-parse: ${_rf}"
        fi
        rm -f "$_frag"
    fi
done < <(printf '%s' "$_collect_out" | python3 "$_parse_py")
rm -f "$_parse_py"

_dedup_py="$DESIGN_TMPDIR/.plan-review-loop-dedup.py"
cat > "$_dedup_py" <<'PY'
import re, sys

# Jaccard token overlap on `what` field text inside FINDING / OOS blocks; merge >0.6.
# In-scope wins over OOS when same `what` text.


def tokens(s):
    return set(re.findall(r"[A-Za-z0-9_]+", s.lower()))


def jaccard(a, b):
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def split_all_blocks(text):
    parts = re.split(r"(?m)^(?=### (?:FINDING|OOS)_[0-9]+:)", text)
    fins, oos = [], []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = re.match(r"^### (FINDING|OOS)_[0-9]+:", p)
        if not m:
            continue
        (fins if m.group(1) == "FINDING" else oos).append(p)
    return fins, oos


def what_text(block):
    for label in ("Concern", "Description"):
        m = re.search(
            r"- \*\*%s\*\*:\s*(.+?)(?:\.\s*Scenario:|\s*Scenario:|(?=\n- \*\*)|\Z)"
            % label,
            block,
            re.S,
        )
        if m:
            t = m.group(1).strip()
            if t:
                return t
    return block


def merge_reviewers(a, b):
    ma = re.search(r"(\*\*Reviewer\(s\)\*\*: )([^\n]+)", a)
    mb2 = re.search(r"(\*\*Reviewer\(s\)\*\*: )([^\n]+)", b) or re.search(
        r"(\*\*Reviewer\*\*: )([^\n]+)", b
    )
    if ma and mb2:
        return re.sub(
            r"(\*\*Reviewer\(s\)\*\*: )([^\n]+)",
            lambda m: m.group(1) + m.group(2) + ", " + mb2.group(2),
            a,
            count=1,
        )
    return a


def dedup(blocks, thresh=0.6):
    kept = []
    for blk in blocks:
        wt = what_text(blk)
        t = tokens(wt)
        merged = False
        for i, kb in enumerate(kept):
            if jaccard(t, tokens(what_text(kb))) > thresh:
                kept[i] = merge_reviewers(kb, blk)
                merged = True
                break
        if not merged:
            kept.append(blk)
    return kept


def main():
    raw = sys.stdin.read()
    fins, oos = split_all_blocks(raw)
    fins2 = dedup(fins)
    owt = {what_text(b) for b in fins2}
    oos2 = []
    for b in dedup(oos):
        if what_text(b) in owt:
            continue
        oos2.append(b)
    out = []
    for i, b in enumerate(fins2, 1):
        out.append(re.sub(r"^### FINDING_[0-9]+:", "### FINDING_%d:" % i, b, count=1, flags=re.M))
    for i, b in enumerate(oos2, 1):
        out.append(re.sub(r"^### OOS_[0-9]+:", "### OOS_%d:" % i, b, count=1, flags=re.M))
    sys.stdout.write("\n\n".join(out))
    if out:
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
PY

if python3 "$_dedup_py" < "$_findings_tmp" > "$DESIGN_TMPDIR/findings.md"; then
    :
else
    _dedup_failed=1
    cp "$_findings_tmp" "$DESIGN_TMPDIR/findings.md"
    emit_kv WARN "plan-review-dedup: python deduper failed; raw findings retained without dedup"
fi
rm -f "$_dedup_py"

if ! grep -qE '^### (FINDING|OOS)_[0-9]+:' "$DESIGN_TMPDIR/findings.md" 2>/dev/null; then
    write_empty_review_artifacts "No findings were raised — voting was not needed."
    : > "$DESIGN_TMPDIR/ballot.txt"
    emit_loop_kvs complete 0 0 skipped-empty-input skipped-empty-findings "$DESIGN_TMPDIR/voting-tally.md" SKIPPED
    exit 0
fi

python3 - "$DESIGN_TMPDIR/findings.md" "$DESIGN_TMPDIR/findings-in-scope.md" "$DESIGN_TMPDIR/findings-oos.md" <<'PY'
import re, sys

src, out_in, out_oos = sys.argv[1:4]
text = open(src, "r", encoding="utf-8", errors="replace").read()
fin = []
oos = []
for m in re.finditer(r"(?ms)^### FINDING_[0-9]+:.*?(?=^### |\Z)", text):
    fin.append(m.group(0).strip())
for m in re.finditer(r"(?ms)^### OOS_[0-9]+:.*?(?=^### |\Z)", text):
    oos.append(m.group(0).strip())
open(out_in, "w", encoding="utf-8").write("\n\n".join(fin) + ("\n\n" if fin else ""))
open(out_oos, "w", encoding="utf-8").write("\n\n".join(oos) + ("\n\n" if oos else ""))
PY

AGGREGATOR_STATUS="ok"
_agg_in="$DESIGN_TMPDIR/findings-in-scope.md"
_agg_out="$_agg_in"
if [[ "${LARCH_AGGREGATOR_DISABLED:-0}" == "1" ]]; then
    AGGREGATOR_STATUS="disabled"
else
    _agg_full=$("$PLUGIN_ROOT/skills/review/scripts/aggregate-findings.sh" \
        --findings-file "$_agg_in" \
        --review-tmpdir "$DESIGN_TMPDIR" \
        --codex-present "$CODEX_PRESENT" \
        --cursor-present "$CURSOR_PRESENT" \
        --mode description \
        --plan-file "$PLAN_FILE" \
        --session-env-path "$DESIGN_TMPDIR/source-env.sh" \
        --input-mode plan)
    AGGREGATED="false"
    REASON="ok"
    while IFS= read -r _ln; do
        [[ -z "$_ln" ]] && continue
        _k="${_ln%%=*}"
        _v="${_ln#*=}"
        case "$_k" in
            AGGREGATED) AGGREGATED="$_v" ;;
            REASON) REASON="$_v" ;;
        esac
    done <<< "$_agg_full"
    if [[ "$AGGREGATED" == "true" ]]; then
        AGGREGATOR_STATUS="${REASON:-ok}"
    else
        AGGREGATOR_STATUS="$REASON"
    fi
fi

cat "$_agg_out" "$DESIGN_TMPDIR/findings-oos.md" > "$DESIGN_TMPDIR/ballot.txt"

_voter_raw=$("$PLAN_REVIEW_DISPATCH_VOTERS_SH" \
    --ballot-file "$DESIGN_TMPDIR/ballot.txt" \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --codex-available "$CODEX_PRESENT" \
    --cursor-available "$CURSOR_PRESENT" \
    --session-env-path "$DESIGN_TMPDIR/source-env.sh")

VOTER_DISPATCH_OK="true"
VOTER_1_PARSE_RATE_STATUS=""
VOTER_1_PATH=""
VOTER_2_PATH=""
VOTER_3_PATH=""
VOTER_1_STATUS="failed"
VOTER_2_STATUS="failed"
VOTER_3_STATUS="failed"
while IFS= read -r _vln || [[ -n "$_vln" ]]; do
    _vk="${_vln%%=*}"
    _vv="${_vln#*=}"
    case "$_vk" in
        DISPATCH_OK) VOTER_DISPATCH_OK="$_vv" ;;
        VOTER_1_PATH) VOTER_1_PATH="$_vv" ;;
        VOTER_2_PATH) VOTER_2_PATH="$_vv" ;;
        VOTER_3_PATH) VOTER_3_PATH="$_vv" ;;
        VOTER_1_STATUS) VOTER_1_STATUS="$_vv" ;;
        VOTER_2_STATUS) VOTER_2_STATUS="$_vv" ;;
        VOTER_3_STATUS) VOTER_3_STATUS="$_vv" ;;
        VOTER_1_PARSE_RATE_STATUS) VOTER_1_PARSE_RATE_STATUS="$_vv" ;;
        WARN) emit_kv WARN "$_vv" ;;
    esac
done <<< "$_voter_raw"

printf '%s\n' "$_voter_raw"

_dirty2=$("$PLUGIN_ROOT/scripts/check-mid-run-dirty-tree.sh" --mode checkpoint || true)
if grep -qE '^STATUS=(dirty|unknown)$' <<< "$_dirty2"; then
    printf '%s\n' "$_dirty2" > "$DESIGN_TMPDIR/dirty-tree-detected.env" || true
    emit_kv WARN "plan-review-voters: dirty tree detected"
fi

_vt_args=()
if [[ "$VOTER_1_STATUS" != "failed" && -n "$VOTER_1_PATH" ]]; then
    _vt_args+=( "Claude:$VOTER_1_PATH" )
fi
if [[ "$VOTER_2_STATUS" != "failed" && -n "$VOTER_2_PATH" ]]; then
    _vt_args+=( "Codex:$VOTER_2_PATH" )
fi
if [[ "$VOTER_3_STATUS" != "failed" && -n "$VOTER_3_PATH" ]]; then
    _vt_args+=( "Cursor:$VOTER_3_PATH" )
fi

_classification_out="$DESIGN_TMPDIR/plan-review/round-$ROUND_NUM/findings-classification.tsv"
mkdir -p "$(dirname "$_classification_out")"

_tally_cmd=(
    "$PLAN_REVIEW_TALLY_SH"
    --ballot-file "$DESIGN_TMPDIR/ballot.txt"
    --design-tmpdir "$DESIGN_TMPDIR"
    --findings-classification-out "$_classification_out"
)
TALLY_PLAN_REVIEW_STATUS=""
VOTING_TALLY_FILE=""
set +e
if ((${#_vt_args[@]} > 0)); then
    _tally_voter_args=()
    for _vt in "${_vt_args[@]}"; do
        _tally_voter_args+=(--voter "$_vt")
    done
    _tally_raw=$("${_tally_cmd[@]}" "${_tally_voter_args[@]}")
else
    _tally_raw=$("${_tally_cmd[@]}")
fi
_tally_rc=$?
set -e
while IFS= read -r _tln || [[ -n "$_tln" ]]; do
    _tk="${_tln%%=*}"
    _tv="${_tln#*=}"
    case "$_tk" in
        TALLY_PLAN_REVIEW_STATUS) TALLY_PLAN_REVIEW_STATUS="$_tv" ;;
        VOTING_TALLY_FILE) VOTING_TALLY_FILE="$_tv" ;;
        WARN) emit_kv WARN "$_tv" ;;
    esac
done <<< "$_tally_raw"

if [[ "$_tally_rc" -ne 0 ]]; then
    emit_kv WARN "plan-review-tally: tally-plan-review.sh exited with rc=$_tally_rc"
    TALLY_PLAN_REVIEW_STATUS="tally-error"
    reset_findings_classification
    [[ -z "$VOTING_TALLY_FILE" ]] && VOTING_TALLY_FILE="$DESIGN_TMPDIR/voting-tally.md"
    if [[ ! -s "$VOTING_TALLY_FILE" ]]; then
        {
            printf '# Plan Review Voting Tally\n\n'
            printf '**⚠ Tally aborted (rc=%s); no votes tallied.**\n' "$_tally_rc"
        } > "$VOTING_TALLY_FILE"
    fi
fi

printf '%s\n' "$_tally_raw"

ACCEPTED_COUNT=$(grep -cE '^### FINDING_[0-9]+:' "$DESIGN_TMPDIR/accepted-plan-findings.md" 2>/dev/null || printf '0')

slot_count="${#_slot_lines[@]}"
floor_half=$((slot_count / 2))
case "$FALLBACK_COUNT" in ''|*[!0-9]*) FALLBACK_COUNT=0 ;; esac
DEGRADED_PANEL=0
[[ "${STATIC_DISPATCH_OK:-true}" == "false" ]] && DEGRADED_PANEL=1
[[ "${PANEL_DISPATCH_OK:-true}" == "false" ]] && DEGRADED_PANEL=1
[[ "${VOTER_DISPATCH_OK:-true}" == "false" ]] && DEGRADED_PANEL=1
[[ "${DEGRADED_ROUND:-false}" == "true" ]] && DEGRADED_PANEL=1
[[ "$_dedup_failed" -eq 1 ]] && DEGRADED_PANEL=1
: "${DYNAMIC_SLOT_COUNT:-0}"
if (( 10#$FALLBACK_COUNT > floor_half )); then
    DEGRADED_PANEL=1
fi
_nonfailed_voters=0
for _vp in "${_vt_args[@]+"${_vt_args[@]}"}"; do
    _vp_path="${_vp#*:}"
    [[ -s "$_vp_path" ]] && _nonfailed_voters=$((_nonfailed_voters + 1))
done
if (( _nonfailed_voters < 2 )); then
    DEGRADED_PANEL=1
fi

LOOP_STATUS="complete"
[[ "$TALLY_PLAN_REVIEW_STATUS" == "main-agent-vote-required" ]] && LOOP_STATUS="main-agent-vote-required"

[[ -z "$VOTER_1_PARSE_RATE_STATUS" ]] && VOTER_1_PARSE_RATE_STATUS="SKIPPED"
[[ -z "$VOTING_TALLY_FILE" ]] && VOTING_TALLY_FILE="$DESIGN_TMPDIR/voting-tally.md"

emit_loop_kvs "$LOOP_STATUS" "$ACCEPTED_COUNT" "$DEGRADED_PANEL" "$AGGREGATOR_STATUS" "$TALLY_PLAN_REVIEW_STATUS" "$VOTING_TALLY_FILE" "$VOTER_1_PARSE_RATE_STATUS"

if [[ "$LOOP_STATUS" == "main-agent-vote-required" ]]; then
    exit 0
fi
exit 0
