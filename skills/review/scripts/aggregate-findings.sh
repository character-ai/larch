#!/usr/bin/env bash
# aggregate-findings.sh — LLM pass to merge cross-reviewer findings before voting.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: aggregate-findings.sh --findings-file PATH --review-tmpdir DIR --codex-present true|false --cursor-present true|false --mode diff|description [--session-env-path PATH] [--diff-file PATH] [--plan-file PATH] [--input-mode plan|code]"
}

FINDINGS_FILE=""
REVIEW_TMPDIR=""
CODEX_PRESENT=""
CURSOR_PRESENT=""
MODE=""
SESSION_ENV_PATH=""
DIFF_FILE=""
PLAN_FILE=""
INPUT_MODE="code"

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
        --input-mode) INPUT_MODE="${2:?}"; shift 2 ;;
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
# shellcheck source=skills/review/scripts/aggregate-findings-phrases.inc.bash
source "$PLUGIN_ROOT/skills/review/scripts/aggregate-findings-phrases.inc.bash"
[[ "$CODEX_PRESENT" == "true" || "$CODEX_PRESENT" == "false" ]] || { larch_err "aggregate-findings.sh: --codex-present must be true or false"; exit 2; }
[[ "$CURSOR_PRESENT" == "true" || "$CURSOR_PRESENT" == "false" ]] || { larch_err "aggregate-findings.sh: --cursor-present must be true or false"; exit 2; }
[[ "$MODE" == "diff" || "$MODE" == "description" ]] || { larch_err "aggregate-findings.sh: --mode must be diff or description"; exit 2; }
[[ "$INPUT_MODE" == "plan" || "$INPUT_MODE" == "code" ]] || { larch_err "aggregate-findings.sh: --input-mode must be plan or code"; exit 2; }
export LARCH_AGGREGATE_INPUT_MODE="$INPUT_MODE"

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

{
    strip_agent_frontmatter "$AGGREGATOR_AGENT"
    printf '\n\n## Raw reviewer findings (input)\n\n'
    cat "$FINDINGS_FILE"
} > "$prompt_file"

validate_py="$REVIEW_TMPDIR/aggregate-validate.py"
cat > "$validate_py" <<'PY'
import os
import re
import sys

INPUT_MODE = os.environ.get("LARCH_AGGREGATE_INPUT_MODE", "code")


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
            out.add(normalize_slot(sl))
    return out


def finding_id_from_block(block):
    for line in block.splitlines():
        t = line.strip()
        m = re.match(r"^### (FINDING_[0-9]+):", t)
        if m:
            return m.group(1)
    return None


def normalize_slot(sl):
    # Symmetric contract: input and output slot tokens strip one trailing
    # parenthetical suffix so labels that differ only by "(...)" collapse.
    return re.sub(r"\s*\([^)]*\)\s*$", "", sl).strip()


EMPTY_MERGE_ATTESTATION = "LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED"

_STRICT_FINDING_HEADING = re.compile(r"^### FINDING_[0-9]+:")
_SEVERITY_LINE = re.compile(
    r"(?m)^-\s*\*\*Severity\*\*:\s*(important|latent|nit)\s*$", re.IGNORECASE
)


def block_has_severity(block):
    """Merged output blocks must carry a severity line for downstream voting (Piece 2)."""
    return bool(_SEVERITY_LINE.search(block))


# Two forms of preamble contradiction:
#   1. Heading-format: "### FINDING_24:" or "### FINDING_N:" in narrative prose.
#   2. Numbered prose: "(FINDING_24–28)" or similar bare numeric FINDING_N references.
# "### FINDING_ids" (non-numeric suffix) and generic "FINDING_" without a number do NOT trip
# this signal — they may appear in legitimate empty-merge commentary.
_PREAMBLE_FINDING_SIGNAL = re.compile(r"###\s*FINDING_[0-9N]|\bFINDING_[0-9]{1,4}\b")


def has_preamble_finding_signal(text):
    """True when narrative references structured FINDING headings or numbered IDs without valid blocks."""
    return bool(_PREAMBLE_FINDING_SIGNAL.search(text))


def line_has_impure_empty_merge_attestation(line):
    """True when trimmed line begins with the attestation token but is not exactly it."""
    st = line.strip()
    return st.startswith(EMPTY_MERGE_ATTESTATION) and st != EMPTY_MERGE_ATTESTATION


def drop_impure_empty_merge_attestation_lines(text):
    """Remove near-attestation lines that would survive exact-line strip (suffix/format drift)."""
    if not text:
        return text
    ends_nl = text.endswith("\n")
    kept = [
        line
        for line in text.splitlines()
        if not line_has_impure_empty_merge_attestation(line)
    ]
    out = "\n".join(kept)
    if ends_nl:
        out += "\n"
    return out


def line_opens_valid_finding_block(line):
    """True when this line starts a validator-recognized ### FINDING_N: block."""
    ls = line.lstrip("\t ")
    return bool(_STRICT_FINDING_HEADING.match(ls))


# Drifted pseudo-heading: ### optional spaces FINDING_<digit>… but not the strict
# "### FINDING_<digits>:" block opener (e.g. ###FINDING_1: typo, or ### FINDING_1 x).
# Require a digit after FINDING_ so prose like "### FINDING_ids …" does not trigger
# the preamble drift guard (issue: FINDING_ids line with zero real blocks).
_PSEUDO_FINDING_HEADING = re.compile(r"^###\s*FINDING_[0-9]")


def has_nonconforming_finding_heading_markers(text):
    """
    True when a line looks like a FINDING heading but is not ### FINDING_<digits>:
    (detects narrative that contains drifted pseudo-headings that no longer parse
    as structured blocks).
    """
    for line in text.splitlines():
        ls = line.lstrip("\t ")
        if not ls.startswith("###"):
            continue
        if _PSEUDO_FINDING_HEADING.match(ls) and not line_opens_valid_finding_block(line):
            return True
    return False


# End of "Suggested revisions" sub-list: only known top-level finding fields,
# not arbitrary "- **Capital..." lines that may appear inside folded revision text.
_REVISION_SUBLIST_END_HEADING = re.compile(
    r"^-\s*\*\*(?:Reviewer(?:\(s\))?|Reviewers?|Concern|Justification|Suggested revisions?)\*\*:",
    re.IGNORECASE,
)


def input_blocks_by_slot(text):
    """Map each normalized slot to a list of raw block texts that cite it."""
    slot_map = {}
    for block in input_blocks(text):
        _line, slots = reviewer_line_slots(block)
        for sl in slots:
            slot_map.setdefault(normalize_slot(sl), []).append(block)
    return slot_map


def suggested_revisions_bullets(block, bid="?"):
    """Parse 'Suggested revisions' sub-list; return (bullets, parse_warnings)."""
    lines = block.splitlines()
    in_revisions = False
    bullets = []
    parse_warnings = []
    pending_from = None  # (slot_label, list of text fragments)
    for line in lines:
        s = line.strip()
        if re.match(r"^-\s*\*\*Suggested revisions", s, re.IGNORECASE):
            in_revisions = True
            continue
        if not in_revisions:
            continue
        m_from = re.match(r"^-\s+From\s+(.+?):\s+(.+)$", s, re.IGNORECASE)
        if m_from:
            if pending_from:
                bullets.append(
                    (pending_from[0], " ".join(pending_from[1]).strip())
                )
            pending_from = (m_from.group(1).strip(), [m_from.group(2).strip()])
            continue
        if _REVISION_SUBLIST_END_HEADING.match(s):
            if pending_from:
                # Verbatim fix text can contain lines that look like finding
                # fields (e.g. "- **Concern**:"); keep folding until the next
                # "- From ..." bullet or real sub-list end (no active bullet).
                pending_from[1].append(s)
                continue
            parse_warnings.append(
                "field-like line in Suggested revisions before first 'From:' bullet "
                "in %s (%r)" % (bid, s[:120])
            )
            break
        if pending_from:
            pending_from[1].append(s)
            continue
        if s:
            parse_warnings.append(
                "unexpected line in Suggested revisions sub-list before first "
                "'From:' bullet in %s (%r)" % (bid, s[:120])
            )
    if pending_from:
        bullets.append((pending_from[0], " ".join(pending_from[1]).strip()))
    return bullets, parse_warnings


def singular_suggested_revision(block):
    """Legacy singular '- **Suggested revision**:' line body, if any."""
    for line in block.splitlines():
        s = line.strip()
        m = re.match(r"^-\s*\*\*Suggested revision\*\*:\s*(.+)$", s, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def normalize_for_match(text):
    """Lowercase and collapse whitespace/punctuation for substring matching."""
    return re.sub(r"[^\w\s]", " ", text.lower())


def output_reviewer_slots_norm(block):
    _line, slots = reviewer_line_slots(block)
    return {normalize_slot(sl) for sl in slots}


def scope_input_blocks_for_merge(norm_slot, output_slots_norm, slot_map):
    """Input blocks citing norm_slot that share a reviewer with merged output."""
    candidates = slot_map.get(norm_slot, [])
    if not output_slots_norm:
        return list(candidates)
    scoped = []
    for in_block in candidates:
        _il, islots = reviewer_line_slots(in_block)
        in_norms = {normalize_slot(x) for x in islots}
        if in_norms & output_slots_norm:
            scoped.append(in_block)
    return scoped


def revision_traceable_in_blocks(revision_text, in_blocks):
    """True when normalized revision matches within a single scoped input block."""
    if not in_blocks:
        return False
    rev_norm = normalize_for_match(revision_text).strip()
    if not rev_norm:
        return False
    use_prefix = os.environ.get("LARCH_AGGREGATE_REVISION_TRACE_PREFIX_FALLBACK") == "1"
    words = rev_norm.split()
    window = min(6, len(words)) if len(words) >= 2 else 0
    needle = " ".join(words[:window]) if window else ""
    for block in in_blocks:
        corp_norm = normalize_for_match(block)
        if rev_norm in corp_norm:
            return True
        if use_prefix and needle and needle in corp_norm:
            return True
    return False


def check_revision_traceability(input_text, output_blocks_list):
    """Warn when merged revision text can't be traced to scoped input for that merge."""
    slot_map = input_blocks_by_slot(input_text)
    warnings = []
    for block in output_blocks_list:
        head = heading_line(block)
        is_oos = "[OUT_OF_SCOPE]" in head
        if is_oos:
            continue
        output_slots_norm = output_reviewer_slots_norm(block)
        bid = finding_id_from_block(block) or "?"
        bullets, parse_warnings = suggested_revisions_bullets(block, bid)
        warnings.extend(parse_warnings)
        singular = singular_suggested_revision(block)
        if singular and bullets:
            warnings.append(
                "both legacy singular Suggested revision and multi-reviewer revision "
                "bullets present in %s" % (bid,)
            )
        if not bullets and not singular:
            continue
        trace_items = []
        if bullets:
            trace_items.extend(bullets)
        if singular:
            trace_items.append(
                ("(legacy singular Suggested revision)", singular)
                if bullets
                else ("(merged reviewers)", singular)
            )
        for slot_label, revision_text in trace_items:
            norm_slot = (
                None
                if slot_label
                in ("(merged reviewers)", "(legacy singular Suggested revision)")
                else normalize_slot(slot_label)
            )
            if norm_slot is not None and norm_slot not in slot_map:
                warnings.append(
                    "unknown From slot label %r in %s (not present on any input finding)"
                    % (slot_label, bid)
                )
                continue
            if norm_slot is None:
                scoped = []
                for in_block in input_blocks(input_text):
                    _il, islots = reviewer_line_slots(in_block)
                    in_norms = {normalize_slot(x) for x in islots}
                    if in_norms & output_slots_norm:
                        scoped.append(in_block)
            else:
                scoped = scope_input_blocks_for_merge(
                    norm_slot, output_slots_norm, slot_map
                )
            found = revision_traceable_in_blocks(revision_text, scoped)
            if not found:
                warnings.append(
                    "fix text for slot %r in %s not traceable to scoped input "
                    "(first 80 chars: %r)" % (slot_label, bid, revision_text[:80])
                )
    return warnings


def main():
    input_path, output_path = sys.argv[1], sys.argv[2]
    intext = open(input_path, encoding="utf-8").read()
    outtext = open(output_path, encoding="utf-8").read()
    outtext = drop_impure_empty_merge_attestation_lines(outtext)
    for line in outtext.splitlines():
        if line_has_impure_empty_merge_attestation(line):
            print(
                "empty-merge attestation line must be exactly %r when present (found impure line)"
                % (EMPTY_MERGE_ATTESTATION,),
                file=sys.stderr,
            )
            return 1
    oos_slots = oos_attributed_slots(intext)
    input_slot_set = set()
    non_oos_input_slots = set()
    for block in input_blocks(intext):
        _line, slots = reviewer_line_slots(block)
        is_oos = "[OUT_OF_SCOPE]" in heading_line(block)
        for sl in slots:
            input_slot_set.add(normalize_slot(sl))
            if not is_oos:
                non_oos_input_slots.add(normalize_slot(sl))
    # Only flag reviewers who are EXCLUSIVELY OOS in the input. A reviewer that
    # contributed both OOS and in-scope input findings is legitimately attributed
    # to non-OOS merged output blocks (see issue #2491).
    oos_only_slots = oos_slots - non_oos_input_slots
    if not input_slot_set:
        print("no input reviewer labels", file=sys.stderr)
        return 1
    blocks = output_blocks(outtext)
    has_attest_line = any(
        line.strip() == EMPTY_MERGE_ATTESTATION for line in outtext.splitlines()
    )
    if blocks and has_attest_line:
        print(
            "empty-merge attestation %r must not appear when merged FINDING blocks exist"
            % (EMPTY_MERGE_ATTESTATION,),
            file=sys.stderr,
        )
        return 1
    if not blocks:
        # input_slot_set non-empty (checked above) ⇒ structured input findings exist.
        if (
            has_preamble_finding_signal(outtext)
            and not has_nonconforming_finding_heading_markers(outtext)
        ):
            print(
                "AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring",
                file=sys.stderr,
            )
            return 1
        if not has_attest_line:
            print(
                "zero merged FINDING blocks while input had findings; "
                "output must include a line whose trimmed text equals %r "
                "(machine-readable attestation; leading/trailing whitespace ignored)"
                % (EMPTY_MERGE_ATTESTATION,),
                file=sys.stderr,
            )
            return 1
        input_finding_count = len(input_blocks(intext))
        print(
            "AGGREGATOR_VALIDATION_FAILED=empty_merge_from_nonempty_input",
            file=sys.stderr,
        )
        print(
            "input had %d FINDING blocks; merged output has zero "
            "(attestation present is not sufficient when inputs were nonempty)"
            % (input_finding_count,),
            file=sys.stderr,
        )
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
        if INPUT_MODE == "code" and not block_has_severity(b):
            print(
                "output block missing - **Severity**: important|latent|nit line",
                file=sys.stderr,
            )
            return 1
        if not is_oos_out:
            for sl in slots:
                if normalize_slot(sl) in oos_only_slots:
                    print(
                        "merged output lacks [OUT_OF_SCOPE] while listing reviewer %r "
                        "that appears only on OOS-tagged input findings" % (sl,),
                        file=sys.stderr,
                    )
                    return 1
        for sl in slots:
            normalized = normalize_slot(sl)
            if normalized not in input_slot_set:
                print("unknown reviewer slot in merge output: %r" % (sl,), file=sys.stderr)
                return 1
            all_out_slots.add(normalized)
    missing = sorted(s for s in input_slot_set if s not in all_out_slots)
    if missing:
        print("input reviewers missing from merge output: %r" % (missing,), file=sys.stderr)
        return 1
    # Advisory: warn when 'Suggested revisions' bullets can't be traced back to input.
    rev_warnings = check_revision_traceability(intext, blocks)
    for w in rev_warnings:
        print("warning: " + w, file=sys.stderr)
    if os.environ.get("LARCH_AGGREGATE_REVISION_TRACE_STRICT") == "1" and rev_warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

DISPATCH_SH="${AGGREGATE_DISPATCH_SH:-$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh}"
dispatch_out="$REVIEW_TMPDIR/aggregator-dispatch.env"

_agg_pipeline_for_candidate() {
    local cand="$1"
    local merged_tmp
    MERGE_PIPELINE_RC=2

    if ! python3 "$validate_py" "$FINDINGS_FILE" "$cand" 2>"$REVIEW_TMPDIR/aggregator-validate.stderr"; then
        if grep -Eq '^AGGREGATOR_VALIDATION_FAILED=(preamble_finding_substring|empty_merge_from_nonempty_input)$' "$REVIEW_TMPDIR/aggregator-validate.stderr" 2>/dev/null; then
            MERGE_PIPELINE_RC=1
            return 0
        fi
        MERGE_PIPELINE_RC=2
        return 0
    fi

    merged_tmp="$(mktemp "$REVIEW_TMPDIR/findings.md.merged.XXXXXX")"
    if ! python3 - "$cand" <<'PY' >"$merged_tmp" 2>"$REVIEW_TMPDIR/aggregator-strip.stderr"
import sys

EMPTY_MERGE_ATTESTATION = "LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED"
path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    for line in f:
        stripped = line.strip()
        if stripped == EMPTY_MERGE_ATTESTATION:
            continue
        if stripped.startswith(EMPTY_MERGE_ATTESTATION):
            continue
        sys.stdout.write(line)
PY
    then
        rm -f "$merged_tmp"
        MERGE_PIPELINE_RC=2
        return 0
    fi
    if [[ "$(count_finding_blocks "$cand")" -eq 0 ]]; then
        [[ -s "$merged_tmp" ]] || printf '\n' >"$merged_tmp"
    fi
    if [[ ! -s "$merged_tmp" ]]; then
        rm -f "$merged_tmp"
        printf '%s\n' "staged merge output empty after successful strip (zero FINDING blocks in vendor output; expected narrative or whitespace)" >"$REVIEW_TMPDIR/aggregator-empty-merge.stderr"
        MERGE_PIPELINE_RC=2
        return 0
    fi
    mv -f "$merged_tmp" "$FINDINGS_FILE"
    MERGE_PIPELINE_RC=0
}

jq -nc \
    --arg out "$REVIEW_TMPDIR/aggregator-output.txt" \
    --arg pf "$prompt_file" \
    '{slot:"aggregator",tool:"codex",output:$out,prompt_file:$pf}' > "$slots_file"

dispatch_args=(
    --slots-file "$slots_file"
    --codex-present "$CODEX_PRESENT"
    --cursor-present "$CURSOR_PRESENT"
    --mode "$MODE"
)
[[ -n "$DIFF_FILE" ]] && dispatch_args+=(--diff-file "$DIFF_FILE")
[[ -n "$PLAN_FILE" ]] && dispatch_args+=(--plan-file "$PLAN_FILE")
dispatch_args+=(--require-result-pattern '^(### FINDING_[0-9]+:|[[:space:]]*LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED[[:space:]]*$)')

set +e
"$DISPATCH_SH" "${dispatch_args[@]}" > "$dispatch_out" 2>"$REVIEW_TMPDIR/aggregator-dispatch.stderr"
dispatch_rc=$?
set -e

if [[ "$dispatch_rc" -ne 0 ]]; then
    REASON="dispatch-failed"
    FAILURE_LOG="$REVIEW_TMPDIR/aggregator-dispatch.stderr"
    append_warning "- **findings aggregator**: dispatch-with-waterfall exited non-zero (rc=$dispatch_rc); leaving findings.md unchanged. $(failure_see_phrase "$FAILURE_LOG")"
    emit_result
    exit 0
fi

DISPATCH_OK=$(kv_get "$dispatch_out" DISPATCH_OK)
if [[ "$DISPATCH_OK" != "true" ]]; then
    REASON="dispatch-failed"
    FAILURE_LOG="$REVIEW_TMPDIR/aggregator-dispatch.stderr"
    append_warning "- **findings aggregator**: DISPATCH_OK=$DISPATCH_OK; leaving findings.md unchanged. $(failure_see_phrase "$FAILURE_LOG")"
    emit_result
    exit 0
fi

cand=""
all_output_files_path=$(kv_get "$dispatch_out" ALL_OUTPUT_FILES_PATH)
if [[ -n "$all_output_files_path" && -f "$all_output_files_path" && -r "$all_output_files_path" ]]; then
    read -r cand < "$all_output_files_path" || true
fi
if [[ -z "$cand" ]]; then
    cand=$(kv_get "$dispatch_out" ALL_OUTPUT_FILES)
    cand="${cand%% *}"
fi
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

_agg_pipeline_for_candidate "$cand"
case "${MERGE_PIPELINE_RC:-2}" in
    0)
        MERGED_COUNT="$(count_finding_blocks "$FINDINGS_FILE")"
        AGGREGATED=true
        REASON="ok"
        emit_result
        exit 0
        ;;
    1)
        AGGREGATED=false
        REASON="validation-exhausted"
        FAILURE_LOG="$REVIEW_TMPDIR/aggregator-validate.stderr"
        if grep -Fxq 'AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring' "$FAILURE_LOG" 2>/dev/null; then
            append_warning "- **findings aggregator**: validation exhausted (narrow-trigger preamble contradiction after pattern-gated dispatch); leaving findings.md unchanged. $(failure_see_phrase "$FAILURE_LOG")"
        else
            append_warning "- **findings aggregator**: validation exhausted (narrow-trigger empty merge after pattern-gated dispatch); leaving findings.md unchanged. $(failure_see_phrase "$FAILURE_LOG")"
        fi
        emit_result
        exit 0
        ;;
    2)
        REASON="validation-failed"
        FAILURE_LOG="$REVIEW_TMPDIR/aggregator-validate.stderr"
        if [[ ! -f "$FAILURE_LOG" || ! -s "$FAILURE_LOG" ]]; then
            if [[ -f "$REVIEW_TMPDIR/aggregator-strip.stderr" && -s "$REVIEW_TMPDIR/aggregator-strip.stderr" ]]; then
                FAILURE_LOG="$REVIEW_TMPDIR/aggregator-strip.stderr"
            elif [[ -f "$REVIEW_TMPDIR/aggregator-empty-merge.stderr" ]]; then
                FAILURE_LOG="$REVIEW_TMPDIR/aggregator-empty-merge.stderr"
            fi
        fi
        append_warning "- **findings aggregator**: merged output failed validation; leaving findings.md unchanged. $(failure_see_phrase "$FAILURE_LOG")"
        emit_result
        exit 0
        ;;
    *)
        REASON="validation-failed"
        append_warning "- **findings aggregator**: merge pipeline returned unexpected status (${MERGE_PIPELINE_RC:-unset}); leaving findings.md unchanged."
        emit_result
        exit 0
        ;;
esac
