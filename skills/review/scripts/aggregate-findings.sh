#!/usr/bin/env bash
# aggregate-findings.sh — LLM pass to merge cross-reviewer findings before voting.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: aggregate-findings.sh --findings-file PATH --review-tmpdir DIR --codex-present true|false --cursor-present true|false --mode diff|description [--session-env-path PATH] [--diff-file PATH] [--plan-file PATH]"
}

FINDINGS_FILE=""
REVIEW_TMPDIR=""
CODEX_PRESENT=""
CURSOR_PRESENT=""
MODE=""
SESSION_ENV_PATH=""
DIFF_FILE=""
PLAN_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --findings-file) FINDINGS_FILE="${2:?}"; shift 2 ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?}"; shift 2 ;;
        --codex-present) CODEX_PRESENT="${2:?}"; shift 2 ;;
        --cursor-present) CURSOR_PRESENT="${2:?}"; shift 2 ;;
        --mode) MODE="${2:?}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?}"; shift 2 ;;
        --diff-file) DIFF_FILE="${2:?}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "aggregate-findings.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$FINDINGS_FILE" ]] || { larch_err "aggregate-findings.sh: --findings-file is required"; exit 2; }
[[ -n "$REVIEW_TMPDIR" ]] || { larch_err "aggregate-findings.sh: --review-tmpdir is required"; exit 2; }
REVIEW_TMPDIR_CANON="$(cd "$REVIEW_TMPDIR" && pwd -P)" || {
    larch_err "aggregate-findings.sh: cannot resolve --review-tmpdir: $REVIEW_TMPDIR"
    exit 2
}
[[ -f "$FINDINGS_FILE" && ! -L "$FINDINGS_FILE" ]] || {
    larch_err "aggregate-findings.sh: --findings-file must name an existing regular file (not a symlink): $FINDINGS_FILE"
    exit 2
}
_findings_canon="$(cd "$(dirname "$FINDINGS_FILE")" && pwd -P)/$(basename "$FINDINGS_FILE")"
case "$_findings_canon" in
    "$REVIEW_TMPDIR_CANON"/* | "$REVIEW_TMPDIR_CANON")
        ;;
    *)
        larch_err "aggregate-findings.sh: --findings-file must resolve under --review-tmpdir ($REVIEW_TMPDIR_CANON): $FINDINGS_FILE"
        exit 2
        ;;
esac
unset _findings_canon
[[ "$CODEX_PRESENT" == "true" || "$CODEX_PRESENT" == "false" ]] || { larch_err "aggregate-findings.sh: --codex-present must be true or false"; exit 2; }
[[ "$CURSOR_PRESENT" == "true" || "$CURSOR_PRESENT" == "false" ]] || { larch_err "aggregate-findings.sh: --cursor-present must be true or false"; exit 2; }
[[ "$MODE" == "diff" || "$MODE" == "description" ]] || { larch_err "aggregate-findings.sh: --mode must be diff or description"; exit 2; }

kv_get() {
    local file="$1" key="$2"
    awk -F= -v key="$key" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "$file" 2>/dev/null || true
}

execution_issues_log() {
    if [[ -n "${LARCH_EXECUTION_ISSUES_LOG:-}" ]]; then
        printf '%s\n' "$LARCH_EXECUTION_ISSUES_LOG"
    elif [[ -n "$SESSION_ENV_PATH" ]]; then
        printf '%s/execution-issues.md\n' "$(dirname "$SESSION_ENV_PATH")"
    elif [[ -n "${IMPLEMENT_TMPDIR:-}" ]]; then
        printf '%s/execution-issues.md\n' "$IMPLEMENT_TMPDIR"
    else
        printf '%s/execution-issues.md\n' "$REVIEW_TMPDIR"
    fi
}

append_warning() {
    local entry="$1"
    [[ -x "$PLUGIN_ROOT/scripts/append-execution-issue.sh" ]] || return 0
    "$PLUGIN_ROOT/scripts/append-execution-issue.sh" \
        --log "$(execution_issues_log)" \
        --category "External Reviewer Issues" \
        --entry "$entry" 2>/dev/null || true
}

count_finding_blocks() {
    local f="$1"
    [[ -f "$f" ]] || { printf '0'; return 0; }
    LC_ALL=C grep -c '^### FINDING_[0-9]' "$f" 2>/dev/null || true
}

INPUT_COUNT=""
MERGED_COUNT=""
AGGREGATED=false
REASON="ok"
FAILURE_LOG=""

emit_result() {
    emit_kv AGGREGATED "$AGGREGATED"
    emit_kv INPUT_COUNT "$INPUT_COUNT"
    emit_kv MERGED_COUNT "$MERGED_COUNT"
    emit_kv REASON "$REASON"
    if [[ -n "$FAILURE_LOG" ]]; then
        emit_kv FAILURE_LOG "$FAILURE_LOG"
    fi
}

if [[ "${LARCH_AGGREGATOR_DISABLED:-}" == "1" ]]; then
    INPUT_COUNT="0"
    MERGED_COUNT="0"
    REASON="disabled"
    emit_result
    exit 0
fi

strip_agent_frontmatter() {
    # Skip YAML fence: --- ... --- then print body.
    awk '
        BEGIN { c = 0 }
        /^---$/ {
            c++
            next
        }
        c >= 2 { print }
    ' "$1"
}

INPUT_COUNT="$(count_finding_blocks "$FINDINGS_FILE")"
MERGED_COUNT="$INPUT_COUNT"

if [[ "$INPUT_COUNT" -lt 2 ]]; then
    REASON="insufficient-input"
    emit_result
    exit 0
fi

AGGREGATOR_AGENT="$PLUGIN_ROOT/agents/orchestrator-aggregator.md"
[[ -f "$AGGREGATOR_AGENT" ]] || {
    REASON="validation-failed"
    FAILURE_LOG=""
    append_warning "- **findings aggregator**: missing agent template at agents/orchestrator-aggregator.md; leaving findings.md unchanged."
    emit_result
    exit 0
}

mkdir -p "$REVIEW_TMPDIR"
prompt_file="$REVIEW_TMPDIR/aggregator-prompt.md"
slots_file="$REVIEW_TMPDIR/aggregator-slots.ndjson"
out_file="$REVIEW_TMPDIR/aggregator-output.txt"

{
    strip_agent_frontmatter "$AGGREGATOR_AGENT"
    printf '\n\n## Raw reviewer findings (input)\n\n'
    cat "$FINDINGS_FILE"
} > "$prompt_file"

jq -nc \
    --arg out "$out_file" \
    --arg pf "$prompt_file" \
    '{slot:"aggregator",tool:"cursor",output:$out,prompt_file:$pf}' > "$slots_file"

DISPATCH_SH="${AGGREGATE_DISPATCH_SH:-$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh}"
dispatch_out="$REVIEW_TMPDIR/aggregator-dispatch.env"
set +e
"$DISPATCH_SH" \
    --slots-file "$slots_file" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" \
    --mode "$MODE" \
    ${DIFF_FILE:+--diff-file "$DIFF_FILE"} \
    ${PLAN_FILE:+--plan-file "$PLAN_FILE"} \
    > "$dispatch_out" 2>"$REVIEW_TMPDIR/aggregator-dispatch.stderr"
dispatch_rc=$?
set -e

if [[ "$dispatch_rc" -ne 0 ]]; then
    REASON="dispatch-failed"
    FAILURE_LOG="$REVIEW_TMPDIR/aggregator-dispatch.stderr"
    append_warning "- **findings aggregator**: dispatch-with-waterfall exited non-zero (rc=$dispatch_rc); leaving findings.md unchanged. See $FAILURE_LOG."
    emit_result
    exit 0
fi

DISPATCH_OK=$(kv_get "$dispatch_out" DISPATCH_OK)
if [[ "$DISPATCH_OK" != "true" ]]; then
    REASON="dispatch-failed"
    FAILURE_LOG="$REVIEW_TMPDIR/aggregator-dispatch.stderr"
    append_warning "- **findings aggregator**: DISPATCH_OK=$DISPATCH_OK; leaving findings.md unchanged."
    emit_result
    exit 0
fi

# ALL_OUTPUT_FILES is space-separated; single-slot aggregator uses the first path.
cand=$(kv_get "$dispatch_out" ALL_OUTPUT_FILES)
cand="${cand%% *}"
[[ -n "$cand" && -f "$cand" && -s "$cand" && ! -L "$cand" ]] || {
    REASON="dispatch-failed"
    append_warning "- **findings aggregator**: missing or empty aggregator output file; leaving findings.md unchanged."
    emit_result
    exit 0
}
_cand_canon="$(cd "$(dirname "$cand")" && pwd -P)/$(basename "$cand")"
case "$_cand_canon" in
    "$REVIEW_TMPDIR_CANON"/* | "$REVIEW_TMPDIR_CANON") ;;
    *)
        REASON="dispatch-failed"
        append_warning "- **findings aggregator**: aggregator output path resolves outside --review-tmpdir; leaving findings.md unchanged."
        emit_result
        exit 0
        ;;
esac
unset _cand_canon

validate_py="$REVIEW_TMPDIR/aggregate-validate.py"
cat > "$validate_py" <<'PY'
import re
import sys


def input_blocks(text):
    parts = re.split(r"(?m)^(?=### FINDING_[0-9]+:)", text)
    return [p for p in parts if re.match(r"^### FINDING_[0-9]+:", p, re.M)]


def output_blocks(text):
    parts = re.split(r"(?m)^(?=### FINDING_[0-9]+:)", text)
    return [p for p in parts if re.match(r"^### FINDING_[0-9]+:", p, re.M)]


def reviewer_line_slots(block):
    for line in block.splitlines():
        s = line.strip()
        m = re.match(r"^-\s*\*\*Reviewer\(s\)\*\*:\s*(.+)$", s)
        if not m:
            m = re.match(r"^-\s*\*\*Reviewers?\*\*:\s*(.+)$", s)
        if not m:
            m = re.match(r"^Reviewer\(s\):\s*(.+)$", s) or re.match(r"^Reviewers?:\s*(.+)$", s)
        if not m:
            continue
        raw = m.group(1).strip()
        slots = [p.strip() for p in raw.split(",") if p.strip()]
        return raw, slots
    return None, []


def heading_line(block):
    for line in block.splitlines():
        t = line.strip()
        if t:
            return t
    return ""


def oos_attributed_slots(text):
    """Reviewer labels that appear on any OOS-tagged input finding."""
    out = set()
    for block in input_blocks(text):
        head = heading_line(block)
        if "[OUT_OF_SCOPE]" not in head:
            continue
        _line, slots = reviewer_line_slots(block)
        for sl in slots:
            out.add(sl)
    return out


def finding_id_from_block(block):
    for line in block.splitlines():
        t = line.strip()
        m = re.match(r"^### (FINDING_[0-9]+):", t)
        if m:
            return m.group(1)
    return None


def main():
    input_path, output_path = sys.argv[1], sys.argv[2]
    intext = open(input_path, encoding="utf-8").read()
    outtext = open(output_path, encoding="utf-8").read()
    oos_slots = oos_attributed_slots(intext)
    input_slot_set = set()
    non_oos_input_slots = set()
    for block in input_blocks(intext):
        _line, slots = reviewer_line_slots(block)
        is_oos = "[OUT_OF_SCOPE]" in heading_line(block)
        for sl in slots:
            input_slot_set.add(sl)
            if not is_oos:
                non_oos_input_slots.add(sl)
    # Only flag reviewers who are EXCLUSIVELY OOS in the input. A reviewer that
    # contributed both OOS and in-scope input findings is legitimately attributed
    # to non-OOS merged output blocks (see issue #2491).
    oos_only_slots = oos_slots - non_oos_input_slots
    if not input_slot_set:
        print("no input reviewer labels", file=sys.stderr)
        return 1
    blocks = output_blocks(outtext)
    if not blocks:
        print("no output FINDING blocks", file=sys.stderr)
        return 1
    seen_merge_ids = set()
    for b in blocks:
        mid = finding_id_from_block(b)
        if not mid:
            print("output block missing ### FINDING_N: heading", file=sys.stderr)
            return 1
        if mid in seen_merge_ids:
            print("duplicate merged FINDING id: %r" % (mid,), file=sys.stderr)
            return 1
        seen_merge_ids.add(mid)
    all_out_slots = set()
    for b in blocks:
        head = heading_line(b)
        is_oos_out = "[OUT_OF_SCOPE]" in head
        _line, slots = reviewer_line_slots(b)
        if not slots:
            print("block missing reviewer attribution line", file=sys.stderr)
            return 1
        if not is_oos_out:
            for sl in slots:
                if sl in oos_only_slots:
                    print(
                        "merged output lacks [OUT_OF_SCOPE] while listing reviewer %r "
                        "that appears only on OOS-tagged input findings" % (sl,),
                        file=sys.stderr,
                    )
                    return 1
        for sl in slots:
            if sl not in input_slot_set:
                print("unknown reviewer slot in merge output: %r" % (sl,), file=sys.stderr)
                return 1
            all_out_slots.add(sl)
    missing = sorted(s for s in input_slot_set if s not in all_out_slots)
    if missing:
        print("input reviewers missing from merge output: %r" % (missing,), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

if ! python3 "$validate_py" "$FINDINGS_FILE" "$cand" 2>"$REVIEW_TMPDIR/aggregator-validate.stderr"; then
    REASON="validation-failed"
    FAILURE_LOG="$REVIEW_TMPDIR/aggregator-validate.stderr"
    append_warning "- **findings aggregator**: merged output failed validation; leaving findings.md unchanged. See $FAILURE_LOG."
    emit_result
    exit 0
fi

# Preserve trailing newline (match collect-findings / ballot conventions).
# Atomic replace: never truncate the live ballot until the staged copy validates.
merged_tmp="$(mktemp "$REVIEW_TMPDIR/findings.md.merged.XXXXXX")"
trap 'rm -f "${merged_tmp:-}"' EXIT
awk 1 "$cand" > "$merged_tmp"
[[ -s "$merged_tmp" ]] || {
    REASON="validation-failed"
    FAILURE_LOG="$REVIEW_TMPDIR/aggregator-empty-merge.stderr"
    printf '%s\n' "staged merge output empty after copy" >"$FAILURE_LOG"
    append_warning "- **findings aggregator**: staged merge output empty; leaving findings.md unchanged."
    emit_result
    exit 0
}
mv -f "$merged_tmp" "$FINDINGS_FILE"
trap - EXIT
MERGED_COUNT="$(count_finding_blocks "$FINDINGS_FILE")"
AGGREGATED=true
REASON="ok"
emit_result
exit 0
