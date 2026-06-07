#!/usr/bin/env bash
# plan-review-loop.sh — Single-pass /design plan-review driver.
# --round-num is a stateless integer supplied by the caller; this script does
# not read or write review-round-count.txt.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$REPO_ROOT}"
if [[ ! -f "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh" ]] || [[ ! -f "$PLUGIN_ROOT/scripts/lib-scope-anchor-handoff.sh" ]]; then
    PLUGIN_ROOT="$REPO_ROOT"
fi
# Optional harness overrides (see test-plan-review-loop.sh).
PLAN_REVIEW_SCOUT_SH="${LARCH_PLAN_REVIEW_SCOUT_SH:-$PLUGIN_ROOT/skills/design/scripts/scout-plan-archetypes-wrapper.sh}"
PLAN_REVIEW_DISPATCH_PANEL_SH="${LARCH_PLAN_REVIEW_DISPATCH_PANEL_SH:-$PLUGIN_ROOT/skills/design/scripts/dispatch-plan-review-panel.sh}"
PLAN_REVIEW_COLLECT_SH="${LARCH_PLAN_REVIEW_COLLECT_SH:-$PLUGIN_ROOT/scripts/collect-agent-results.sh}"
PLAN_REVIEW_DISPATCH_VOTERS_SH="${LARCH_PLAN_REVIEW_DISPATCH_VOTERS_SH:-$PLUGIN_ROOT/scripts/dispatch-plan-voters.sh}"
PLAN_REVIEW_TALLY_SH="${LARCH_PLAN_REVIEW_TALLY_SH:-$PLUGIN_ROOT/skills/design/scripts/tally-plan-review.sh}"
SCOPE_MARKER_HELPER="$PLUGIN_ROOT/scripts/check-scope-reduction-marker.sh"
if [[ ! -x "$SCOPE_MARKER_HELPER" ]]; then
    SCOPE_MARKER_HELPER="$REPO_ROOT/scripts/check-scope-reduction-marker.sh"
fi
PLAN_BLOCK_STRIP_BODY_SH="$PLUGIN_ROOT/scripts/plan-block-strip-body.sh"
if [[ ! -x "$PLAN_BLOCK_STRIP_BODY_SH" ]]; then
    PLAN_BLOCK_STRIP_BODY_SH="$REPO_ROOT/scripts/plan-block-strip-body.sh"
fi
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh"
# shellcheck source=skills/design/scripts/lib-findings-classification.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-findings-classification.sh"
# shellcheck source=scripts/lib-design-round-artifacts.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../../../scripts/lib-design-round-artifacts.sh"
# shellcheck source=skills/design/scripts/lib-phase-driver.sh
source "$SCRIPT_DIR/lib-phase-driver.sh"
# shellcheck source=scripts/lib-scope-anchor-handoff.sh
source "$PLUGIN_ROOT/scripts/lib-scope-anchor-handoff.sh"

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
_dedup_failed=0
_paths_readable=0
loop_status_override=""
collect_ok_count=0
collect_failure_count=0
revise_status="skipped"
LOOP_REASON=""
IMPORTANT_ACCEPTED_COUNT=0
NIT_ACCEPTED_COUNT=0
NON_NIT_ACCEPTED_COUNT=0
COLLECT_OK_COUNT=0
COLLECT_FAILURE_COUNT=0
TALLY_PLAN_REVIEW_STATUS=""
VOTING_TALLY_FILE=""
TALLY_PLAN_REVIEW_FATAL=false
AGGREGATOR_STATUS=""
ACCEPTED_COUNT=0
DEGRADED_PANEL=0
VOTER_1_PARSE_RATE_STATUS=""
SCOPE_ANCHOR_FILE=""
LOOP_STATUS="complete"
_last_collect_out=""

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

larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit $?

DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
mkdir -p "$DESIGN_TMPDIR"
export DESIGN_TMPDIR

if [[ -z "$FEATURE_FILE" ]]; then
    FEATURE_FILE="$DESIGN_TMPDIR/feature-description.txt"
fi
[[ -f "$FEATURE_FILE" ]] || { larch_err "plan-review-loop.sh: feature file not found: $FEATURE_FILE"; exit 2; }
ORIGINAL_FEATURE_FILE="$FEATURE_FILE"
SCOPE_ANCHOR_FILE="$DESIGN_TMPDIR/plan-review-scope-anchor.txt"
_LOOP_SCOPE_ANCHOR_IN=""
_PARSED_SCOPE_ANCHOR_FILE=""

_materialize_scope_anchor() {
    local stripped_tmp anchor_tmp strip_kv strip_err malformed strip_rc
    stripped_tmp=$(mktemp "$DESIGN_TMPDIR/.plan-review-scope-anchor.XXXXXX")
    anchor_tmp=$(mktemp "$DESIGN_TMPDIR/.plan-review-scope-anchor-body.XXXXXX")
    strip_kv=$(mktemp "$DESIGN_TMPDIR/.plan-strip-kv.XXXXXX")
    strip_err=$(mktemp "$DESIGN_TMPDIR/.plan-strip-stderr.XXXXXX")
    trap 'rm -f "$stripped_tmp" "$anchor_tmp" "$strip_kv"' RETURN
    malformed=""
    set +e
    LARCH_QUIET_DISABLE=1 "$PLAN_BLOCK_STRIP_BODY_SH" --file "$ORIGINAL_FEATURE_FILE" --output "$stripped_tmp" >"$strip_kv" 2>"$strip_err"
    strip_rc=$?
    set -e
    if [[ "$strip_rc" -ne 0 ]]; then
        malformed=$(awk -F= '$1=="MALFORMED"{print $2; exit}' "$strip_kv")
        if [[ -n "$malformed" ]]; then
            larch_err "plan-review-loop.sh: failed to strip embedded larch:plan block while materializing scope anchor (MALFORMED=$malformed)"
        else
            larch_err "plan-review-loop.sh: failed to strip embedded larch:plan block while materializing scope anchor"
        fi
        if [[ -s "$strip_err" ]]; then
            sed 's/^/plan-block-strip-body.sh: /' "$strip_err" >&2 || true
        fi
        rm -f "$strip_err"
        return 2
    fi
    rm -f "$strip_kv" "$strip_err"
    {
        cat "$stripped_tmp"
        if [[ -f "$DESIGN_TMPDIR/.outline-approved" && -s "$DESIGN_TMPDIR/design-outline.md" ]]; then
            printf '\n\n## Approved direction (outline)\n\n'
            cat "$DESIGN_TMPDIR/design-outline.md"
        fi
    } >"$anchor_tmp"
    if ! grep -q '[^[:space:]]' "$anchor_tmp"; then
        larch_err "plan-review-loop.sh: scope anchor is empty after stripping embedded larch:plan block"
        return 2
    fi
    "$PLUGIN_ROOT/scripts/redact-secrets.sh" <"$anchor_tmp" >"$SCOPE_ANCHOR_FILE"
    if ! grep -q '[^[:space:]]' "$SCOPE_ANCHOR_FILE"; then
        larch_err "plan-review-loop.sh: scope anchor is empty after redaction"
        return 2
    fi
    case "$SCOPE_ANCHOR_FILE" in
        *$'\r'*|*$'\n'*) larch_err "plan-review-loop.sh: scope anchor path contains CR/LF"; return 2 ;;
    esac
    local anchor_size
    anchor_size=$(wc -c <"$SCOPE_ANCHOR_FILE" 2>/dev/null | awk '{print $1}' || printf '65537')
    case "$anchor_size" in ''|*[!0-9]*) anchor_size=65537 ;; esac
    if (( anchor_size > 65536 )); then
        larch_err "plan-review-loop.sh: scope anchor exceeds 64KiB"
        return 2
    fi
}
_materialize_scope_anchor || exit $?
_LOOP_SCOPE_ANCHOR_IN="$SCOPE_ANCHOR_FILE"

_brainstorm_file="$DESIGN_TMPDIR/brainstorm.md"
if [[ -f "$_brainstorm_file" && -s "$_brainstorm_file" ]]; then
    _merged_feature="$DESIGN_TMPDIR/plan-review-feature-context.txt"
    _feature_context_base="$DESIGN_TMPDIR/.plan-review-feature-context-base.txt"
    if ! LARCH_QUIET_DISABLE=1 "$PLAN_BLOCK_STRIP_BODY_SH" --file "$ORIGINAL_FEATURE_FILE" --output "$_feature_context_base" >/dev/null; then
        rm -f "$_feature_context_base"
        larch_err "plan-review-loop.sh: failed to strip embedded larch:plan block while materializing brainstorm feature context"
        exit 2
    fi
    {
        printf '%s\n' "## Feature / issue context (base)"
        cat "$_feature_context_base"
        printf '\n\n%s\n' "## Brainstorm synthesis (additive; optional, non-binding)"
        cat "$_brainstorm_file"
    } >"$_merged_feature"
    rm -f "$_feature_context_base"
fi

emit_loop_kvs() {
    local loop_status="$1" accepted_count="$2" degraded_panel="$3" aggregator_status="$4" tally_status="$5" voting_tally_file="$6" voter1_parse="$7" rounds_completed="${8:-$ROUND_NUM}"
    local scope_anchor_file saved_loop saved_tally
    saved_loop="${LOOP_STATUS:-}"
    saved_tally="${TALLY_PLAN_REVIEW_STATUS:-}"
    LOOP_STATUS="$loop_status"
    TALLY_PLAN_REVIEW_STATUS="$tally_status"
    scope_anchor_file="$(_scope_anchor_handoff_value)"
    LOOP_STATUS="$saved_loop"
    TALLY_PLAN_REVIEW_STATUS="$saved_tally"
    emit_kv LOOP_STATUS "$loop_status"
    emit_kv ACCEPTED_COUNT "$accepted_count"
    emit_kv IMPORTANT_ACCEPTED_COUNT "${IMPORTANT_ACCEPTED_COUNT:-0}"
    emit_kv DEGRADED_PANEL "$degraded_panel"
    emit_kv ROUNDS_COMPLETED "$rounds_completed"
    emit_kv AGGREGATOR_STATUS "$aggregator_status"
    emit_kv TALLY_PLAN_REVIEW_STATUS "$tally_status"
    emit_kv VOTING_TALLY_FILE "$voting_tally_file"
    emit_kv VOTER_1_PARSE_RATE_STATUS "$voter1_parse"
    [[ -z "$scope_anchor_file" ]] || emit_kv SCOPE_ANCHOR_FILE "$scope_anchor_file"
    emit_kv NIT_ACCEPTED_COUNT "${NIT_ACCEPTED_COUNT:-0}"
    emit_kv NON_NIT_ACCEPTED_COUNT "${NON_NIT_ACCEPTED_COUNT:-0}"
    emit_kv REASON "${LOOP_REASON:-}"
    emit_kv REVISE_STATUS "${revise_status:-}"
    emit_kv COLLECT_OK_COUNT "${COLLECT_OK_COUNT:-0}"
    emit_kv COLLECT_FAILURE_COUNT "${COLLECT_FAILURE_COUNT:-0}"
}

_scope_anchor_handoff_value() {
    local design_canon
    design_canon="$(cd "$DESIGN_TMPDIR" && pwd -P)" || return 0
    larch_scope_anchor_design_handoff_value "$design_canon" "${_PARSED_SCOPE_ANCHOR_FILE:-}" "${_LOOP_SCOPE_ANCHOR_IN:-}"
}

write_step3_result_env() {
    local out="$DESIGN_TMPDIR/.step3-plan-review-result.env"
    local scope_anchor_file
    scope_anchor_file="$(_scope_anchor_handoff_value)"
    local kvs=(
        "LOOP_STATUS=${LOOP_STATUS:-}" \
        "ACCEPTED_COUNT=${ACCEPTED_COUNT:-0}" \
        "IMPORTANT_ACCEPTED_COUNT=${IMPORTANT_ACCEPTED_COUNT:-0}" \
        "DEGRADED_PANEL=${DEGRADED_PANEL:-0}" \
        "ROUNDS_COMPLETED=${1:-$ROUND_NUM}" \
        "REASON=${LOOP_REASON:-}" \
        "REVISE_STATUS=${revise_status:-}" \
        "NIT_ACCEPTED_COUNT=${NIT_ACCEPTED_COUNT:-0}" \
        "NON_NIT_ACCEPTED_COUNT=${NON_NIT_ACCEPTED_COUNT:-0}" \
        "AGGREGATOR_STATUS=${AGGREGATOR_STATUS:-}" \
        "TALLY_PLAN_REVIEW_STATUS=${TALLY_PLAN_REVIEW_STATUS:-}" \
        "VOTING_TALLY_FILE=${VOTING_TALLY_FILE:-}" \
        "VOTER_1_PARSE_RATE_STATUS=${VOTER_1_PARSE_RATE_STATUS:-}" \
        "COLLECT_OK_COUNT=${COLLECT_OK_COUNT:-0}" \
        "COLLECT_FAILURE_COUNT=${COLLECT_FAILURE_COUNT:-0}"
    )
    [[ -z "$scope_anchor_file" ]] || kvs+=("SCOPE_ANCHOR_FILE=$scope_anchor_file")
    if ! phase_driver_write_result_env "$out" "${kvs[@]}"; then
        larch_err "plan-review-loop.sh: refusing to write invalid or symlinked Step 3 result env"
        return 1
    fi
}

write_empty_review_artifacts() {
    local tally_note="$1" round_num="${2:-$ROUND_NUM}"
    : > "$DESIGN_TMPDIR/accepted-plan-findings.md"
    : > "$DESIGN_TMPDIR/rejected-findings.md"
    : > "$DESIGN_TMPDIR/oos.md"
    : > "$DESIGN_TMPDIR/oos-accepted-design.md"
    {
        printf '# Plan Review Voting Tally\n\n'
        printf '%s\n' "$tally_note"
    } > "$DESIGN_TMPDIR/voting-tally.md"
    _fc_out="$DESIGN_TMPDIR/plan-review/round-${round_num}/findings-classification.tsv"
    mkdir -p "$(dirname "$_fc_out")"
    emit_findings_classification_header > "$_fc_out"
}

_count_important_findings() {
    local path="$1"
    [[ -f "$path" ]] || { printf '0'; return 0; }
    awk '
        /^### FINDING_[0-9]+:/ {
            if (in_block && important) c++
            in_block=1
            important=0
            next
        }
        in_block && /^- \*\*Severity\*\*: important/ { important=1 }
        in_block && /^### / { if (important) c++; in_block=0; important=0; next }
        END { if (in_block && important) c++; print c+0 }
    ' "$path"
}

_count_nit_findings() {
    local path="$1"
    [[ -f "$path" ]] || { printf '0'; return 0; }
    awk '
        /^### FINDING_[0-9]+:/ {
            if (in_block && nit) c++
            in_block=1
            nit=0
            next
        }
        in_block && /^- \*\*Severity\*\*: nit/ { nit=1 }
        in_block && /^### / { if (nit) c++; in_block=0; nit=0; next }
        END { if (in_block && nit) c++; print c+0 }
    ' "$path"
}

_update_nit_accepted_counts() {
    local accepted_path="$1"
    NIT_ACCEPTED_COUNT=$(_count_nit_findings "$accepted_path")
    NIT_ACCEPTED_COUNT=$((10#${NIT_ACCEPTED_COUNT:-0}))
    if (( NIT_ACCEPTED_COUNT > ACCEPTED_COUNT )); then
        NIT_ACCEPTED_COUNT=$ACCEPTED_COUNT
    fi
    NON_NIT_ACCEPTED_COUNT=$((ACCEPTED_COUNT - NIT_ACCEPTED_COUNT))
}

_count_collector_evidence() {
    collect_ok_count=0
    collect_failure_count=0
    local rec st
    while IFS= read -r rec || [[ -n "$rec" ]]; do
        [[ -z "$rec" ]] && continue
        IFS=$'\x1f' read -r _rf _tool st _xc _fr _sidecar <<< "$rec" || true
        case "$st" in
            OK) collect_ok_count=$((collect_ok_count + 1)) ;;
            *) collect_failure_count=$((collect_failure_count + 1)) ;;
        esac
    done < <(_parse_collect_records "$_last_collect_out")
    COLLECT_OK_COUNT=$collect_ok_count
    COLLECT_FAILURE_COUNT=$collect_failure_count
}

_parse_collect_records() {
    local _parse_py="$DESIGN_TMPDIR/.plan-review-loop-parse-collect-inline.py"
    cat > "$_parse_py" <<'PY'
import sys

def main():
    text = sys.stdin.read()
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
            sys.stdout.write(
                "%s\x1f%s\x1f%s\x1f%s\x1f%s\x1f%s\n"
                % (
                    d.get("REVIEWER_FILE", ""),
                    d.get("TOOL", ""),
                    d.get("STATUS", ""),
                    d.get("EXIT_CODE", "0"),
                    d.get("FAILURE_REASON", ""),
                    d.get("STRUCTURED_SIDECAR", ""),
                )
            )

if __name__ == "__main__":
    main()
PY
    printf '%s' "${1:-}" | python3 "$_parse_py"
    rm -f "$_parse_py"
}

_clear_session_root_review_artifacts() {
    local f
    for f in findings.md findings-in-scope.md findings-oos.md accepted-plan-findings.md \
        rejected-findings.md oos.md oos-this-round.md ballot.txt voting-tally.md; do
        : >"$DESIGN_TMPDIR/$f"
    done
}

_snapshot_round_dir() {
    local round_num="$1"
    local dest="$DESIGN_TMPDIR/plan-review/round-${round_num}"
    local tmp="${dest}.snapshot-tmp"
    rm -rf "$tmp"
    mkdir -p "$tmp"
    local name src failed=0
    for src in "$DESIGN_TMPDIR"/*; do
        [[ -f "$src" ]] || continue
        name=$(basename "$src")
        design_round_artifact_included "$name" || continue
        if [[ -L "$src" ]]; then
            emit_kv WARN "plan-review-snapshot: refusing symlink source $name"
            failed=1
            continue
        fi
        cp -f "$src" "$tmp/$name"
    done
    if (( failed != 0 )); then
        rm -rf "$tmp"
        return 1
    fi
    if [[ -d "$dest" ]]; then
        for src in "$dest"/*; do
            [[ -f "$src" ]] || continue
            name=$(basename "$src")
            design_round_artifact_included "$name" || continue
            [[ -e "$tmp/$name" ]] && continue
            if [[ -L "$src" ]]; then
                emit_kv WARN "plan-review-snapshot: refusing symlink round artifact $name"
                failed=1
                continue
            fi
            cp -f "$src" "$tmp/$name"
        done
    fi
    if (( failed != 0 )); then
        rm -rf "$tmp"
        return 1
    fi
    if [[ -d "$dest/revise" ]]; then
        local rname rsrc
        mkdir -p "$tmp/revise"
        for rsrc in "$dest/revise"/*; do
            [[ -f "$rsrc" ]] || continue
            rname=$(basename "$rsrc")
            design_round_revise_artifact_included "$rname" || continue
            if [[ -L "$rsrc" ]]; then
                emit_kv WARN "plan-review-snapshot: refusing symlink revise artifact $rname"
                failed=1
                continue
            fi
            cp -f "$rsrc" "$tmp/revise/$rname"
        done
    fi
    if (( failed != 0 )); then
        rm -rf "$tmp"
        return 1
    fi
    mkdir -p "$dest"
    local existing
    for existing in "$dest"/*; do
        [[ -e "$existing" ]] || continue
        [[ "$(basename "$existing")" == "revise" ]] && continue
        rm -rf "$existing"
    done
    for src in "$tmp"/*; do
        [[ -e "$src" ]] || continue
        name=$(basename "$src")
        if [[ "$name" == "revise" ]]; then
            mkdir -p "$dest/revise"
            local revise_existing
            for revise_existing in "$dest/revise"/*; do
                [[ -e "$revise_existing" ]] || continue
                rm -f "$revise_existing"
            done
            cp -f "$src"/* "$dest/revise/" 2>/dev/null || true
            continue
        fi
        cp -f "$src" "$dest/$name"
    done
    rm -rf "$tmp"
}


_plan_round_now_s() {
    date +%s
}

_plan_round_start_path() {
    local round_num="$1"
    printf '%s/plan-review/round-%s/round-start-s' "$DESIGN_TMPDIR" "$round_num"
}

_persist_plan_round_start() {
    local round_num="$1" start_s="$2" path
    path=$(_plan_round_start_path "$round_num")
    mkdir -p "$(dirname "$path")"
    if [[ ! -e "$path" ]]; then
        printf '%s\n' "$start_s" > "$path" 2>/dev/null || true
    fi
}

_emit_plan_round_timing_row() {
    local round_num="$1" start_s="$2" end_s="$3"
    local guard_var="PLAN_ROUND_${round_num}_TIMING_EMITTED"
    if [[ "${!guard_var:-}" == "true" ]]; then
        return 0
    fi
    [[ "$start_s" =~ ^[0-9]+$ ]] || return 0
    [[ "$end_s" =~ ^[0-9]+$ ]] || return 0
    if "$SCRIPT_DIR/record-plan-review-round-timing.sh" \
        --design-tmpdir "$DESIGN_TMPDIR" \
        --round "$round_num" \
        --start-s "$start_s" \
        --end-s "$end_s"; then
        printf -v "$guard_var" '%s' true
    fi
}

_snapshot_terminal_exit_preserving_status() {
    local round_num="$1" rc="$2" summary_revise="$3"
    if [[ "${LOOP_STATUS:-}" == "main-agent-vote-required" ]]; then
        _persist_plan_round_start "$round_num" "${_round_start:-}"
    else
        _emit_plan_round_timing_row "$round_num" "${_round_start:-}" "$(_plan_round_now_s)"
    fi
    if ! _snapshot_round_dir "$round_num"; then
        emit_kv WARN "plan-review-snapshot: round-${round_num} snapshot failed after terminal status ${LOOP_STATUS:-unknown}"
        LOOP_REASON="${LOOP_REASON:+${LOOP_REASON},}snapshot-failed"
    fi
    _write_round_summary "$round_num" "$LOOP_STATUS" "${LOOP_REASON:-}" "$summary_revise"
    _terminal_exit "$rc" "$round_num"
}

_write_round_summary() {
    local round_num="$1" loop_status="${2:-}" reason="${3:-}" revise_st="${4:-}"
    local summary_scope_anchor=""
    local dest="$DESIGN_TMPDIR/plan-review/round-${round_num}/round-summary.env"
    mkdir -p "$(dirname "$dest")"
    local tmp="${dest}.tmp"
    {
        printf 'ROUND_NUM=%s\n' "$round_num"
        printf 'LOOP_STATUS=%s\n' "$loop_status"
        printf 'REASON=%s\n' "$reason"
        printf 'NIT_ACCEPTED_COUNT=%s\n' "${NIT_ACCEPTED_COUNT:-0}"
        printf 'NON_NIT_ACCEPTED_COUNT=%s\n' "${NON_NIT_ACCEPTED_COUNT:-0}"
        printf 'ACCEPTED_COUNT=%s\n' "${ACCEPTED_COUNT:-0}"
        printf 'IMPORTANT_ACCEPTED_COUNT=%s\n' "${IMPORTANT_ACCEPTED_COUNT:-0}"
        printf 'DEGRADED_PANEL=%s\n' "${DEGRADED_PANEL:-0}"
        printf 'TALLY_PLAN_REVIEW_STATUS=%s\n' "${TALLY_PLAN_REVIEW_STATUS:-}"
        printf 'AGGREGATOR_STATUS=%s\n' "${AGGREGATOR_STATUS:-}"
        printf 'REVISE_STATUS=%s\n' "$revise_st"
        printf 'COLLECT_OK_COUNT=%s\n' "${COLLECT_OK_COUNT:-0}"
        printf 'COLLECT_FAILURE_COUNT=%s\n' "${COLLECT_FAILURE_COUNT:-0}"
        if [[ -n "$loop_status" ]]; then
            summary_scope_anchor="$(_scope_anchor_handoff_value)"
            [[ -z "$summary_scope_anchor" ]] || printf 'SCOPE_ANCHOR_FILE=%s\n' "$summary_scope_anchor"
        fi
    } >"$tmp"
    mv -f "$tmp" "$dest"
}

_restore_prior_round_oos() {
    local prior_cum="$1"
    if [[ -f "$prior_cum" ]]; then
        cp -f "$prior_cum" "$DESIGN_TMPDIR/oos-accepted-design.md"
    else
        rm -f "$DESIGN_TMPDIR/oos-accepted-design.md"
    fi
}

_accumulate_round_oos() {
    local round_num="$1" prior_cum="$2"
    local round_accepted="$DESIGN_TMPDIR/oos-accepted-design.md"
    local round_snapshot="$DESIGN_TMPDIR/plan-review/round-${round_num}/oos-accepted-design.md"
    [[ -f "$round_accepted" ]] && cp -f "$round_accepted" "$round_snapshot"
    if [[ ! -f "$round_accepted" || ! -s "$round_accepted" ]]; then
        _restore_prior_round_oos "$prior_cum"
        return 0
    fi
    python3 - "$prior_cum" "$round_accepted" <<'PY'
import re, sys

prior_path, current_path = sys.argv[1:3]
text = open(current_path, encoding="utf-8", errors="replace").read()
blocks = [m.group(0).strip() for m in re.finditer(r"(?ms)^### OOS_[0-9]+:.*?(?=^### |\Z)", text)]
if not blocks:
    raise SystemExit(0)

def desc_key(block):
    m = re.search(r"\*\*Description\*\*:\s*(.+?)(?:\n|$)", block, re.S)
    text = m.group(1) if m else block
    return " ".join(text.strip().lower().split())

try:
    existing = open(prior_path, encoding="utf-8", errors="replace").read()
except OSError:
    existing = ""
existing_keys = []
for m in re.finditer(r"(?ms)^### OOS_[0-9]+:.*?(?=^### |\Z)", existing):
    existing_keys.append(desc_key(m.group(0)))

out_parts = [existing.rstrip()] if existing.strip() else []
for blk in blocks:
    dk = desc_key(blk)
    if dk in existing_keys:
        continue
    existing_keys.append(dk)
    out_parts.append(blk)

body = "\n\n".join(p for p in out_parts if p.strip())
if body:
    body += "\n\n"
open(current_path, "w", encoding="utf-8").write(body)
PY
}

_restore_prior_round_accepted_all() {
    local prior_all="$1"
    if [[ -f "$prior_all" ]]; then
        cp -f "$prior_all" "$DESIGN_TMPDIR/accepted-plan-findings-all.md"
    else
        rm -f "$DESIGN_TMPDIR/accepted-plan-findings-all.md"
    fi
}

_accumulate_round_accepted_all() {
    local prior_all="$1"
    local round_accepted="$DESIGN_TMPDIR/accepted-plan-findings.md"
    local cumulative="$DESIGN_TMPDIR/accepted-plan-findings-all.md"
    if [[ ! -f "$round_accepted" || ! -s "$round_accepted" ]]; then
        _restore_prior_round_accepted_all "$prior_all"
        return 0
    fi
    {
        if [[ -f "$prior_all" && -s "$prior_all" ]]; then
            sed -e '${/^[[:space:]]*$/d;}' "$prior_all"
            printf '\n\n'
        fi
        sed -e '${/^[[:space:]]*$/d;}' "$round_accepted"
        printf '\n\n'
    } >"$cumulative"
}

_clear_current_accepted_findings() {
    rm -f "$DESIGN_TMPDIR/accepted-plan-findings.md"
    : >"$DESIGN_TMPDIR/accepted-plan-findings.md"
}

_terminal_exit() {
    local rc="$1" rounds_completed="$2"
    if ! write_step3_result_env "$rounds_completed"; then
        emit_kv WARN "plan-review-loop: failed to write .step3-plan-review-result.env"
        exit 2
    fi
    emit_loop_kvs "$LOOP_STATUS" "$ACCEPTED_COUNT" "$DEGRADED_PANEL" "$AGGREGATOR_STATUS" \
        "$TALLY_PLAN_REVIEW_STATUS" "$VOTING_TALLY_FILE" "$VOTER_1_PARSE_RATE_STATUS" "$rounds_completed"
    exit "$rc"
}

plan_review_voter_tool_label() {
    case "$1" in
        claude|Claude) printf 'Claude' ;;
        codex|Codex) printf 'Codex' ;;
        cursor|Cursor) printf 'Cursor' ;;
        mainagent|MainAgent) printf 'MainAgent' ;;
        *) printf '%s' "$1" ;;
    esac
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

_log_dropped_slots() {
    # #3392: append a per-slot diagnostic to execution-issues.md for each reviewer
    # slot the panel dropped under --no-fallback. The drops sidecar (TSV rows of
    # slot<TAB>tool<TAB>reason<TAB>snippet) is produced by dispatch-with-waterfall.sh
    # and forwarded through dispatch-plan-review-panel.sh as DROPPED_SLOTS_FILE.
    # Without this, a format-gate-miss (a healthy reviewer that merely leads with a
    # conversational preamble) is invisible beyond one terse aggregate WARN, which
    # is indistinguishable from a tool outage.
    local drops_file="$1"
    [[ -n "$drops_file" && -f "$drops_file" && -s "$drops_file" ]] || return 0
    local _slot _tool _reason _detail _tmp
    while IFS=$'\t' read -r _slot _tool _reason _detail || [[ -n "$_slot" ]]; do
        [[ -n "$_slot" ]] || continue
        _tmp=$(mktemp "$DESIGN_TMPDIR/.plan-review-drop.XXXXXX")
        {
            printf 'Reviewer slot %s (%s) was dropped under --no-fallback: %s.\n' \
                "$_slot" "${_tool:-unknown}" "${_reason:-unknown}"
            if [[ -n "$_detail" ]]; then
                printf 'First ~200 chars of the offending output:\n%s\n' "$_detail"
            fi
        } >"$_tmp"
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 3" \
            --tool "${_tool:-unknown} plan-review slot ${_slot}" \
            --exit-code 0 \
            --status-label "dropped: ${_reason:-unknown}" \
            --category "External Reviewer Issues" \
            --output-file "$_tmp" \
            --redact >/dev/null 2>&1 || true
        rm -f "$_tmp"
    done < "$drops_file"
}

_run_plan_review_round() {
    local round_num="$1"
    _dedup_failed=0
    loop_status_override=""

# --- Step 2: scout (fail-open) ---
"$PLAN_REVIEW_SCOUT_SH" \
    --plan-file "$PLAN_FILE" \
    --description-file "$SCOPE_ANCHOR_FILE" \
    --output "$DESIGN_TMPDIR/scout-plan-manifest.json" \
    --max-archetypes 3 \
    --session-env-path "$DESIGN_TMPDIR/source-env.sh" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" || true

# --- Step 3: panel dispatch ---
_panel_raw=$("$PLAN_REVIEW_DISPATCH_PANEL_SH" \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" \
    --plan-file "$PLAN_FILE" \
    --feature-file "$SCOPE_ANCHOR_FILE" \
    --timeout "$PANEL_TIMEOUT")

PANEL_DISPATCH_OK="true"
PANEL_PATHS_FILE=""
ALL_OUTPUT_FILES_PATH=""
STATIC_DISPATCH_OK="true"
FALLBACK_COUNT="0"
COMBINED_FALLBACK_COUNT=""
DEGRADED_ROUND="false"
DYNAMIC_SLOT_COUNT="0"
ALL_SLOTS_DROPPED="false"
DROPPED_SLOTS_FILE=""
while IFS= read -r _line || [[ -n "$_line" ]]; do
    _key="${_line%%=*}"
    _value="${_line#*=}"
    case "$_key" in
        DISPATCH_OK) PANEL_DISPATCH_OK="$_value" ;;
        PANEL_PATHS_FILE) PANEL_PATHS_FILE="$_value" ;;
        ALL_OUTPUT_FILES_PATH) ALL_OUTPUT_FILES_PATH="$_value" ;;
        STATIC_DISPATCH_OK) STATIC_DISPATCH_OK="$_value" ;;
        FALLBACK_COUNT) FALLBACK_COUNT="$_value" ;;
        COMBINED_FALLBACK_COUNT) COMBINED_FALLBACK_COUNT="$_value" ;;
        DEGRADED_ROUND) DEGRADED_ROUND="$_value" ;;
        DYNAMIC_SLOT_COUNT) DYNAMIC_SLOT_COUNT="$_value" ;;
        ALL_SLOTS_DROPPED) ALL_SLOTS_DROPPED="$_value" ;;
        DROPPED_SLOTS_FILE) DROPPED_SLOTS_FILE="$_value" ;;
        WARN) emit_kv WARN "$_value" ;;
    esac
done <<< "$_panel_raw"

printf '%s\n' "$_panel_raw"

# #3392: record per-slot drop reasons (format-gate-miss / collector-failure /
# tool-absent / empty / result-*) before the paths-readability branch, so partial
# drops (some slots kept) and total drops are both surfaced in execution-issues.md.
_dropped_slot_count=0
if [[ -n "$DROPPED_SLOTS_FILE" && -f "$DROPPED_SLOTS_FILE" ]]; then
    _log_dropped_slots "$DROPPED_SLOTS_FILE"
    _dropped_slot_count=$(grep -c . "$DROPPED_SLOTS_FILE" 2>/dev/null || true)
    case "$_dropped_slot_count" in ''|*[!0-9]*) _dropped_slot_count=0 ;; esac
fi

[[ -n "$PANEL_PATHS_FILE" ]] || PANEL_PATHS_FILE="$ALL_OUTPUT_FILES_PATH"
_paths_readable=0
if [[ -n "$PANEL_PATHS_FILE" && -f "$PANEL_PATHS_FILE" && -s "$PANEL_PATHS_FILE" ]]; then
    _paths_readable=1
fi

if [[ "$_paths_readable" -eq 0 && "$PANEL_DISPATCH_OK" != "true" \
    && "$ALL_SLOTS_DROPPED" != "true" && "$DEGRADED_ROUND" != "true" ]]; then
    write_empty_review_artifacts "**Plan-review panel dispatch failed; voting was not run.**" "$round_num"
    : > "$DESIGN_TMPDIR/ballot.txt"
    TALLY_PLAN_REVIEW_STATUS=panel-failed
    AGGREGATOR_STATUS=skipped
    ACCEPTED_COUNT=0
    DEGRADED_PANEL=1
    VOTING_TALLY_FILE="$DESIGN_TMPDIR/voting-tally.md"
    VOTER_1_PARSE_RATE_STATUS=SKIPPED
    LOOP_STATUS=panel-failed
    return 1
fi

# --- Step 5: collect ---
_collect_err="$DESIGN_TMPDIR/plan-review-collector.stderr"
_collect_stderr_fd=2
if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
    _collect_stderr_fd=4
fi
: >"$_collect_err"
_collect_err_tmp=$(mktemp "${DESIGN_TMPDIR}/plan-review-collector.stderr.XXXXXX")
set +e
_collect_rc=0
_collect_out=""
if [[ "$_paths_readable" -eq 1 ]]; then
    _collect_out=$(LARCH_QUIET_DISABLE=1 "$PLAN_REVIEW_COLLECT_SH" \
        --timeout "$COLLECT_TIMEOUT" \
        --substantive-validation \
        --validation-mode \
        --structured-reviewer-validation \
        --paths-file "$PANEL_PATHS_FILE" 2>"$_collect_err_tmp")
    _collect_rc=$?
elif (( _dropped_slot_count > 0 )); then
    emit_kv WARN "plan-review-panel: dispatch produced no reviewer paths (--no-fallback dropped ${_dropped_slot_count} slot(s); per-slot reasons recorded in execution-issues.md → External Reviewer Issues)"
else
    emit_kv WARN "plan-review-panel: dispatch produced no reviewer paths (--no-fallback drops)"
fi
_last_collect_out="$_collect_out"
if [[ "$_collect_rc" -ne 0 ]]; then
    _collect_parseable=0
    while IFS= read -r _crec || [[ -n "$_crec" ]]; do
        [[ -n "$_crec" ]] && _collect_parseable=1 && break
    done < <(_parse_collect_records "$_collect_out")
    if [[ "$_collect_parseable" -eq 0 ]]; then
        write_empty_review_artifacts "**Plan-review collector failed with no parseable output; voting was not run.**" "$round_num"
        : > "$DESIGN_TMPDIR/ballot.txt"
        TALLY_PLAN_REVIEW_STATUS=panel-failed
        AGGREGATOR_STATUS=skipped
        ACCEPTED_COUNT=0
        DEGRADED_PANEL=1
        VOTER_1_PARSE_RATE_STATUS=SKIPPED
        LOOP_STATUS=panel-failed
        set +e
        rm -f "$_collect_err_tmp"
        return 1
    fi
fi
set -e
if [[ -s "$_collect_err_tmp" ]]; then
    cat "$_collect_err_tmp" >>"$_collect_err" || true
    cat "$_collect_err_tmp" >&${_collect_stderr_fd} || true
fi
rm -f "$_collect_err_tmp"

_manifest="$DESIGN_TMPDIR/plan-review-slots.ndjson"
_slot_lines=()
while IFS= read -r _srow || [[ -n "$_srow" ]]; do
    [[ -n "$_srow" ]] || continue
    _slot=$(printf '%s' "$_srow" | jq -r '.slot // empty')
    [[ -n "$_slot" ]] && _slot_lines+=("$_slot")
done < "$_manifest"

slot_count="${#_slot_lines[@]}"
floor_half=$((slot_count / 2))
case "$FALLBACK_COUNT" in ''|*[!0-9]*) FALLBACK_COUNT=0 ;; esac
case "$COMBINED_FALLBACK_COUNT" in ''|*[!0-9]*) COMBINED_FALLBACK_COUNT="$FALLBACK_COUNT" ;; esac
_dispatch_degraded_panel=0
[[ "${STATIC_DISPATCH_OK:-true}" == "false" ]] && _dispatch_degraded_panel=1
[[ "${PANEL_DISPATCH_OK:-true}" == "false" ]] && _dispatch_degraded_panel=1
[[ "${DEGRADED_ROUND:-false}" == "true" ]] && _dispatch_degraded_panel=1
if (( 10#$COMBINED_FALLBACK_COUNT > floor_half )); then
    _dispatch_degraded_panel=1
fi
if [[ "$_paths_readable" -eq 1 ]]; then
    _path_ok_count=0
    while IFS= read -r _pp || [[ -n "$_pp" ]]; do
        [[ -n "$_pp" ]] && _path_ok_count=$((_path_ok_count + 1))
    done < "$PANEL_PATHS_FILE"
    if (( slot_count > 0 && _path_ok_count < slot_count )); then
        _dispatch_degraded_panel=1
    fi
fi

_dirty_out=$("$PLUGIN_ROOT/scripts/check-mid-run-dirty-tree.sh" --mode checkpoint || true)
if grep -qE '^STATUS=(dirty|unknown)$' <<< "$_dirty_out"; then
    printf '%s\n' "$_dirty_out" > "$DESIGN_TMPDIR/dirty-tree-detected.env" || true
    emit_kv WARN "plan-review-collection: dirty tree detected"
fi

_findings_tmp="$DESIGN_TMPDIR/findings.md.tmp"
: > "$_findings_tmp"
while IFS= read -r _rec || [[ -n "$_rec" ]]; do
    [[ -z "$_rec" ]] && continue
    IFS=$'\x1f' read -r _rf _tool _st _xc _fr _sidecar <<< "$_rec" || true
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
        _structured_path=""
        if [[ -n "$_sidecar" && -f "$_sidecar" ]]; then
            _structured_path="$_sidecar"
        elif [[ -f "${_rf}.tsv" ]]; then
            _structured_path="${_rf}.tsv"
        elif [[ -f "${_rf}.jsonl" ]]; then
            _structured_path="${_rf}.jsonl"
        else
            _structured_path="${_rf}.tsv"
        fi
        _frag=$(mktemp "$DESIGN_TMPDIR/.plan-find-frag.XXXXXX")
        python3 - "$_rf" "$_human" "$_structured_path" <<'PY' > "$_frag" 2>/dev/null || true
import csv, json, sys

reviewer_path, slot, structured_path = sys.argv[1:4]
fi = 1
oi = 1


def emit_finding(n, slot, sev, focus, loc, what, scen, fix):
    print("### FINDING_%d:" % n)
    print("- **Reviewer(s)**: %s" % slot)
    print("- **Severity**: %s" % (sev or "nit"))
    print("- **Focus area**: %s" % focus)
    print("- **Location**: %s" % loc)
    print("- **Concern**: %s. Scenario: %s" % (what, scen))
    print("- **Proposed resolution**: %s" % fix)
    print()


def emit_oos(n, slot, sev, focus, loc, what, scen, fix):
    print("### OOS_%d:" % n)
    print("- **Description**: %s. Scenario: %s" % (what, scen))
    print("- **Reviewer**: %s" % slot)
    print("- **Severity**: %s" % (sev or "nit"))
    print("- **Focus area**: %s" % focus)
    print("- **Location**: %s" % loc)
    print("- **Phase**: design")
    print()


def load_rows(path):
    rows = []
    if path.endswith(".jsonl"):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(obj, dict):
                        continue
                    rows.append(
                        {
                            "scope": obj.get("scope", ""),
                            "severity": obj.get("severity", ""),
                            "focus_area": obj.get("focus_area", ""),
                            "location": obj.get("location", ""),
                            "what": obj.get("what", ""),
                            "scenario_or_breakage": obj.get("scenario_or_breakage", ""),
                            "suggested_fix": obj.get("suggested_fix", ""),
                        }
                    )
        except OSError:
            rows = []
        return rows
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            rdr = csv.DictReader(fh, delimiter="\t")
            for row in rdr:
                rows.append(row)
    except OSError:
        rows = []
    return rows


def main():
    rows = load_rows(structured_path)
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
                if ! grep -qE '^[[:space:]]*\{"no_issues_found' "$_rf" 2>/dev/null; then
                    emit_kv WARN "plan-review-tsv: empty or missing structured reviewer rows for ${_rf}"
                fi
            fi
        else
            emit_kv WARN "plan-review-tsv-parse: ${_rf}"
        fi
        rm -f "$_frag"
    fi
done < <(_parse_collect_records "$_collect_out")

python3 - "$_findings_tmp" "$DESIGN_TMPDIR/findings-in-scope.pre-dedup.md" "$DESIGN_TMPDIR/findings-oos.pre-dedup.md" <<'PY'
import re, sys
src, out_in, out_oos = sys.argv[1:4]
text = open(src, encoding="utf-8", errors="replace").read()
fin = [m.group(0).strip() for m in re.finditer(r"(?ms)^### FINDING_[0-9]+:.*?(?=^### |\Z)", text)]
oos = [m.group(0).strip() for m in re.finditer(r"(?ms)^### OOS_[0-9]+:.*?(?=^### |\Z)", text)]
open(out_in, "w", encoding="utf-8").write("\n\n".join(fin) + ("\n\n" if fin else ""))
open(out_oos, "w", encoding="utf-8").write("\n\n".join(oos) + ("\n\n" if oos else ""))
PY

_dedup_py="$DESIGN_TMPDIR/.plan-review-loop-dedup.py"
cat > "$_dedup_py" <<'PY'
import os
import re
import subprocess
import sys
import tempfile

helper = os.environ.get("SCOPE_MARKER_HELPER")


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


def is_tagged(block):
    if not helper:
        return False
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as fh:
        fh.write(block)
        name = fh.name
    try:
        proc = subprocess.run([helper, "--file", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if proc.returncode == 0:
            return True
        if proc.returncode == 1:
            return False
        print("ERROR: scope marker helper failed (rc=%d); refusing to dedup scope-reduction findings" % proc.returncode, file=sys.stderr)
        raise SystemExit(2)
    finally:
        try:
            os.unlink(name)
        except OSError:
            pass


def problem_text(block):
    candidate_lines = []
    for line in re.sub(r"```.*?```", "", block, flags=re.S).splitlines():
        stripped = line.strip()
        for pattern in (
            r"^###\s+(?:FINDING|OOS)_[0-9]+:\s*(.*)$",
            r"^-?\s*(?:\*\*)?Concern(?:\*\*)?:\s*(.*)$",
            r"^\s*what:\s*(.*)$",
        ):
            m = re.match(pattern, stripped, re.I)
            if m and m.group(1).strip():
                candidate_lines.append(m.group(1).strip())
    if is_tagged(block):
        for label in ("Concern", "Description"):
            m = re.search(r"- \*\*%s\*\*:\s*(.+?)(?:\.\s*Scenario:|\s*Scenario:|(?=\n- \*\*)|\Z)" % label, block, re.S)
            if m and m.group(1).strip():
                return m.group(1).strip()
        if candidate_lines:
            return candidate_lines[0]
    for label in ("Concern", "Description"):
        m = re.search(r"- \*\*%s\*\*:\s*(.+?)(?:\.\s*Scenario:|\s*Scenario:|(?=\n- \*\*)|\Z)" % label, block, re.S)
        if m and m.group(1).strip():
            return m.group(1).strip()
    if candidate_lines:
        return candidate_lines[0]
    head = block.splitlines()[0] if block.splitlines() else block
    return re.sub(r"^###\s+(?:FINDING|OOS)_[0-9]+:\s*", "", head).strip() or block


def comparison_text(block):
    text = problem_text(block)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)
    text = re.sub(r"^\s*\[(?:important|nit|latent)\]\s*", "", text, flags=re.I)
    text = re.sub(r"^\s*\[SCOPE-REDUCTION\]\s*", "", text, flags=re.I)
    return text


def tokens(s):
    return set(re.findall(r"[A-Za-z0-9_]+", s.lower()))


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def reviewer_line(block):
    m = re.search(r"(\*\*Reviewer\(s\)\*\*: )([^\n]+)", block)
    if m:
        return m
    return re.search(r"(\*\*Reviewers?\*\*: )([^\n]+)", block)


def merge_reviewers(a, b):
    ma = reviewer_line(a)
    mb = reviewer_line(b)
    if not ma or not mb:
        return a
    existing = [x.strip() for x in ma.group(2).split(",") if x.strip()]
    for item in [x.strip() for x in mb.group(2).split(",") if x.strip()]:
        if item not in existing:
            existing.append(item)
    return a[:ma.start(2)] + ", ".join(existing) + a[ma.end(2):]


def choose_tagged_body(a, b):
    return b if len(tokens(comparison_text(b))) > len(tokens(comparison_text(a))) else a


def dedup(blocks, thresh=0.6):
    kept = []
    kept_tagged = []
    for blk in blocks:
        t = tokens(comparison_text(blk))
        tagged = is_tagged(blk)
        merged = False
        for i, kb in enumerate(kept):
            if jaccard(t, tokens(comparison_text(kb))) > thresh:
                if tagged and kept_tagged[i]:
                    kept[i] = merge_reviewers(choose_tagged_body(kb, blk), kb if choose_tagged_body(kb, blk) is blk else blk)
                    kept_tagged[i] = True
                elif tagged and not kept_tagged[i]:
                    kept[i] = merge_reviewers(blk, kb)
                    kept_tagged[i] = True
                else:
                    kept[i] = merge_reviewers(kb, blk)
                    kept_tagged[i] = kept_tagged[i] or tagged
                merged = True
                break
        if not merged:
            kept.append(blk)
            kept_tagged.append(tagged)
    return kept


def renumber(fins, oos):
    out = []
    for i, b in enumerate(fins, 1):
        out.append(re.sub(r"^### FINDING_[0-9]+:", "### FINDING_%d:" % i, b, count=1, flags=re.M))
    for i, b in enumerate(oos, 1):
        out.append(re.sub(r"^### OOS_[0-9]+:", "### OOS_%d:" % i, b, count=1, flags=re.M))
    return out


def main():
    raw = sys.stdin.read()
    fins, oos = split_all_blocks(raw)
    fins2 = dedup(fins)
    fin_keys = {" ".join(sorted(tokens(comparison_text(b)))) for b in fins2}
    oos2 = []
    for b in dedup(oos):
        if " ".join(sorted(tokens(comparison_text(b)))) in fin_keys:
            continue
        oos2.append(b)
    out = renumber(fins2, oos2)
    sys.stdout.write("\n\n".join(out))
    if out:
        sys.stdout.write("\n")

if __name__ == "__main__":
    main()
PY
if SCOPE_MARKER_HELPER="$SCOPE_MARKER_HELPER" python3 "$_dedup_py" < "$_findings_tmp" > "$DESIGN_TMPDIR/findings.md"; then
    :
else
    _dedup_failed=1
    cp "$_findings_tmp" "$DESIGN_TMPDIR/findings.md"
    emit_kv WARN "plan-review-dedup: python deduper failed; raw findings retained without dedup"
fi
rm -f "$_dedup_py"

if ! grep -qE '^### (FINDING|OOS)_[0-9]+:' "$DESIGN_TMPDIR/findings.md" 2>/dev/null; then
    write_empty_review_artifacts "No findings were raised — voting was not needed." "$round_num"
    : > "$DESIGN_TMPDIR/ballot.txt"
    _short_circuit_degraded="$_dispatch_degraded_panel"
    [[ "$_dedup_failed" -eq 1 ]] && _short_circuit_degraded=1
    TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings
    AGGREGATOR_STATUS=skipped-empty-input
    ACCEPTED_COUNT=0
    DEGRADED_PANEL="$_short_circuit_degraded"
    VOTING_TALLY_FILE="$DESIGN_TMPDIR/voting-tally.md"
    VOTER_1_PARSE_RATE_STATUS=SKIPPED
    LOOP_STATUS=complete
    return 0
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

set +e
python3 - "$SCOPE_MARKER_HELPER" "$DESIGN_TMPDIR/findings-in-scope.pre-dedup.md" "$DESIGN_TMPDIR/findings-in-scope.md" <<'PY'
import os, re, subprocess, sys, tempfile
helper, pre, post = sys.argv[1:4]
def blocks(path):
    text=open(path, encoding='utf-8', errors='replace').read() if os.path.exists(path) else ''
    return [m.group(0).strip() for m in re.finditer(r'(?ms)^### FINDING_[0-9]+:.*?(?=^### |\Z)', text)]
def tagged(block):
    f=tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False); f.write(block); f.close()
    try:
        rc=subprocess.run([helper, '--file', f.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        if rc == 0:
            return True
        if rc == 1:
            return False
        print("scope marker helper failed during dedup parity (rc=%d)" % rc, file=sys.stderr)
        raise SystemExit(2)
    finally: os.unlink(f.name)
def prob(block):
    txt=problem_text(block)
    txt=re.sub(r'```.*?```','',txt,flags=re.S); txt=re.sub(r'`[^`\n]*`','',txt)
    while re.match(r'^\s*\[[A-Za-z0-9_-]+\]\s*', txt) and not re.match(r'^\s*\[SCOPE-REDUCTION\]', txt, re.I):
        txt=re.sub(r'^\s*\[[A-Za-z0-9_-]+\]\s*','',txt)
    txt=re.sub(r'^\s*\[SCOPE-REDUCTION\]\s*','',txt,flags=re.I)
    return set(re.findall(r'[A-Za-z0-9_]+', txt.lower()))
def reviewers(block):
    m=re.search(r'- \*\*Reviewer\(s\)\*\*:\s*([^\n]+)', block)
    if not m:
        m=re.search(r'- \*\*Reviewers?\*\*:\s*([^\n]+)', block)
    if not m:
        return set()
    return {x.strip().lower() for x in m.group(1).split(',') if x.strip()}
post_tag=[b for b in blocks(post) if tagged(b)]
pre_tag=[b for b in blocks(pre) if tagged(b)]
if len(post_tag) < len(pre_tag):
    sys.exit(1)
used=set()
for src in pre_tag:
    st=prob(src); sr=reviewers(src)
    ok=False
    for i,dst in enumerate(post_tag):
        if i in used:
            continue
        if not tagged(dst):
            continue
        dt=prob(dst); dr=reviewers(dst)
        if sr and dr and not (sr & dr):
            continue
        if st and dt and len(st & dt)/len(st | dt) >= 0.5:
            used.add(i)
            ok=True
            break
    if not ok:
        sys.exit(1)
sys.exit(0)
PY
_parity_rc=$?
set -e
if [[ "$_parity_rc" -ne 0 ]]; then
    cp -f "$DESIGN_TMPDIR/findings-in-scope.pre-dedup.md" "$DESIGN_TMPDIR/findings-in-scope.md"
    if [[ "$_parity_rc" -eq 2 ]]; then
        emit_kv WARN "plan-review-dedup: scope marker helper failed during parity check; using pre-dedup in-scope findings"
    else
        emit_kv WARN "plan-review-dedup: scope-reduction marker parity failed; using pre-dedup in-scope findings"
    fi
fi

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
        --input-mode plan \
        --scope-anchor-file "$SCOPE_ANCHOR_FILE" \
        --allow-findings-outside-tmpdir true)
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

_ballot_renumber_failed=0
set +e
python3 - "$_agg_out" "$DESIGN_TMPDIR/findings-oos.md" "$DESIGN_TMPDIR/ballot.txt" <<'PY'
import re, sys
inp, oos_path, out_path = sys.argv[1:4]
text = open(inp, encoding='utf-8', errors='replace').read() if inp else ''
oos_text = open(oos_path, encoding='utf-8', errors='replace').read()
fins=[m.group(0).strip() for m in re.finditer(r'(?ms)^### FINDING_[0-9]+:.*?(?=^### |\Z)', text)]
oos=[m.group(0).strip() for m in re.finditer(r'(?ms)^### OOS_[0-9]+:.*?(?=^### |\Z)', oos_text)]
out=[]
for i,b in enumerate(fins,1): out.append(re.sub(r'^### FINDING_[0-9]+:', f'### FINDING_{i}:', b, count=1, flags=re.M))
for i,b in enumerate(oos,1): out.append(re.sub(r'^### OOS_[0-9]+:', f'### OOS_{i}:', b, count=1, flags=re.M))
heads=[]
for b in out:
    m=re.match(r'^### ((?:FINDING|OOS)_[0-9]+):', b)
    if m: heads.append(m.group(1))
if len(heads) != len(set(heads)):
    raise SystemExit('duplicate headings after renumber')
open(out_path,'w',encoding='utf-8').write('\n\n'.join(out)+("\n" if out else ""))
PY
_ballot_rc=$?
set -e
if [[ "$_ballot_rc" -ne 0 ]]; then
    emit_kv WARN "plan-review-ballot: renumber failed (rc=$_ballot_rc); falling back to pre-dedup in-scope findings"
    cp -f "$DESIGN_TMPDIR/findings-in-scope.pre-dedup.md" "$_agg_out"
    _ballot_oos_fallback="$DESIGN_TMPDIR/findings-oos.pre-dedup.md"
    [[ -f "$_ballot_oos_fallback" ]] || _ballot_oos_fallback="$DESIGN_TMPDIR/findings-oos.md"
    set +e
    python3 - "$_agg_out" "$_ballot_oos_fallback" "$DESIGN_TMPDIR/ballot.txt" <<'PY'
import re, sys
inp, oos_path, out_path = sys.argv[1:4]
text = open(inp, encoding='utf-8', errors='replace').read() if inp else ''
oos_text = open(oos_path, encoding='utf-8', errors='replace').read()
fins=[m.group(0).strip() for m in re.finditer(r'(?ms)^### FINDING_[0-9]+:.*?(?=^### |\Z)', text)]
oos=[m.group(0).strip() for m in re.finditer(r'(?ms)^### OOS_[0-9]+:.*?(?=^### |\Z)', oos_text)]
out=[]
for i,b in enumerate(fins,1): out.append(re.sub(r'^### FINDING_[0-9]+:', f'### FINDING_{i}:', b, count=1, flags=re.M))
for i,b in enumerate(oos,1): out.append(re.sub(r'^### OOS_[0-9]+:', f'### OOS_{i}:', b, count=1, flags=re.M))
heads=[]
for b in out:
    m=re.match(r'^### ((?:FINDING|OOS)_[0-9]+):', b)
    if m: heads.append(m.group(1))
if len(heads) != len(set(heads)):
    raise SystemExit('duplicate headings after renumber')
open(out_path,'w',encoding='utf-8').write('\n\n'.join(out)+("\n" if out else ""))
PY
    _ballot_rc=$?
    set -e
    if [[ "$_ballot_rc" -ne 0 ]]; then
        larch_err "plan-review-ballot: renumber failed on pre-dedup fallback (rc=$_ballot_rc)"
        LOOP_STATUS=panel-failed
        LOOP_REASON=panel-failed
        return 1
    fi
fi

_voter_raw=$("$PLAN_REVIEW_DISPATCH_VOTERS_SH" \
    --ballot-file "$DESIGN_TMPDIR/ballot.txt" \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --codex-available "$CODEX_PRESENT" \
    --cursor-available "$CURSOR_PRESENT" \
    --scope-anchor-file "$SCOPE_ANCHOR_FILE" \
    --session-env-path "$DESIGN_TMPDIR/source-env.sh")

VOTER_DISPATCH_OK="true"
VOTER_1_PARSE_RATE_STATUS=""
VOTER_1_PATH=""
VOTER_2_PATH=""
VOTER_3_PATH=""
VOTER_1_TOOL=""
VOTER_2_TOOL=""
VOTER_3_TOOL=""
VOTER_1_STATUS=""
VOTER_2_STATUS=""
VOTER_3_STATUS=""
while IFS= read -r _vln || [[ -n "$_vln" ]]; do
    _vk="${_vln%%=*}"
    _vv="${_vln#*=}"
    case "$_vk" in
        DISPATCH_OK) VOTER_DISPATCH_OK="$_vv" ;;
        VOTER_1_PARSE_RATE_STATUS) VOTER_1_PARSE_RATE_STATUS="$_vv" ;;
        VOTER_1_PATH) VOTER_1_PATH="$_vv" ;;
        VOTER_2_PATH) VOTER_2_PATH="$_vv" ;;
        VOTER_3_PATH) VOTER_3_PATH="$_vv" ;;
        VOTER_1_TOOL) VOTER_1_TOOL="$_vv" ;;
        VOTER_2_TOOL) VOTER_2_TOOL="$_vv" ;;
        VOTER_3_TOOL) VOTER_3_TOOL="$_vv" ;;
        VOTER_1_STATUS) VOTER_1_STATUS="$_vv" ;;
        VOTER_2_STATUS) VOTER_2_STATUS="$_vv" ;;
        VOTER_3_STATUS) VOTER_3_STATUS="$_vv" ;;
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
append_plan_review_voter_arg() {
    local _slot="$1" _vp="$2" _vt="$3" _vs="$4" _tool_label
    [[ -n "$_vp" ]] || return 0
    [[ "$_vs" != "failed" ]] || return 0
    _tool_label=$(plan_review_voter_tool_label "$_vt")
    _vt_args+=(--voter "$_slot:$_tool_label:$_vp")
}
append_plan_review_voter_arg 1 "$VOTER_1_PATH" "$VOTER_1_TOOL" "$VOTER_1_STATUS"
append_plan_review_voter_arg 2 "$VOTER_2_PATH" "$VOTER_2_TOOL" "$VOTER_2_STATUS"
append_plan_review_voter_arg 3 "$VOTER_3_PATH" "$VOTER_3_TOOL" "$VOTER_3_STATUS"

_findings_classification_out="$DESIGN_TMPDIR/plan-review/round-${round_num}/findings-classification.tsv"
mkdir -p "$(dirname "$_findings_classification_out")"

_tally_cmd=(
    "$PLAN_REVIEW_TALLY_SH"
    --ballot-file "$DESIGN_TMPDIR/ballot.txt"
    --design-tmpdir "$DESIGN_TMPDIR"
    --findings-classification-out "$_findings_classification_out"
)
TALLY_PLAN_REVIEW_STATUS=""
VOTING_TALLY_FILE=""
TALLY_PLAN_REVIEW_FATAL=false
_PARSED_SCOPE_ANCHOR_FILE=""
set +e
if ((${#_vt_args[@]} > 0)); then
    _tally_raw=$("${_tally_cmd[@]}" "${_vt_args[@]}")
else
    _tally_raw=$("${_tally_cmd[@]}")
fi
_tally_rc=$?
set -e
while IFS= read -r _tln || [[ -n "$_tln" ]]; do
    _tk="${_tln%%=*}"
    _tv="${_tln#*=}"
    case "$_tk" in
        TALLY_PLAN_REVIEW_STATUS) TALLY_PLAN_REVIEW_STATUS="$_tv"; [[ "$_tv" == "tally-error" ]] && TALLY_PLAN_REVIEW_FATAL=true ;;
        VOTING_TALLY_FILE) VOTING_TALLY_FILE="$_tv" ;;
        SCOPE_ANCHOR_FILE) _PARSED_SCOPE_ANCHOR_FILE="$_tv" ;;
        WARN) emit_kv WARN "$_tv" ;;
    esac
done <<< "$_tally_raw"

if [[ "$_tally_rc" -ne 0 ]]; then
    emit_kv WARN "plan-review-tally: tally-plan-review.sh exited with rc=$_tally_rc"
    TALLY_PLAN_REVIEW_STATUS="tally-error"
    TALLY_PLAN_REVIEW_FATAL=true
    [[ -z "$VOTING_TALLY_FILE" ]] && VOTING_TALLY_FILE="$DESIGN_TMPDIR/voting-tally.md"
    emit_findings_classification_header > "$_findings_classification_out"
    if [[ ! -s "$VOTING_TALLY_FILE" ]]; then
        {
            printf '# Plan Review Voting Tally\n\n'
            printf '**⚠ Tally aborted (rc=%s); no votes tallied.**\n' "$_tally_rc"
        } > "$VOTING_TALLY_FILE"
    fi
fi

printf '%s\n' "$_tally_raw" | sed -E \
    '/^SCOPE_ANCHOR_FILE=/d;/^TALLY_PLAN_REVIEW_STATUS=/d;/^VOTING_TALLY_FILE=/d'

ACCEPTED_COUNT=0
if [[ -f "$DESIGN_TMPDIR/accepted-plan-findings.md" ]]; then
    ACCEPTED_COUNT=$(grep -cE '^### FINDING_[0-9]+:' "$DESIGN_TMPDIR/accepted-plan-findings.md" 2>/dev/null || true)
fi

DEGRADED_PANEL="$_dispatch_degraded_panel"
[[ "${VOTER_DISPATCH_OK:-true}" == "false" ]] && DEGRADED_PANEL=1
[[ "$_dedup_failed" -eq 1 ]] && DEGRADED_PANEL=1
: "${DYNAMIC_SLOT_COUNT:-0}"
_nonfailed_voters=0
[[ "$VOTER_1_STATUS" != "failed" && -s "$VOTER_1_PATH" ]] && _nonfailed_voters=$((_nonfailed_voters + 1))
[[ "$VOTER_2_STATUS" != "failed" && -s "$VOTER_2_PATH" ]] && _nonfailed_voters=$((_nonfailed_voters + 1))
[[ "$VOTER_3_STATUS" != "failed" && -s "$VOTER_3_PATH" ]] && _nonfailed_voters=$((_nonfailed_voters + 1))
if (( _nonfailed_voters < 2 )); then
    DEGRADED_PANEL=1
fi

LOOP_STATUS="complete"
[[ "$TALLY_PLAN_REVIEW_STATUS" == "main-agent-vote-required" ]] && LOOP_STATUS="main-agent-vote-required" && loop_status_override="main-agent-vote-required"

[[ -z "$VOTER_1_PARSE_RATE_STATUS" ]] && VOTER_1_PARSE_RATE_STATUS="SKIPPED"
[[ -z "$VOTING_TALLY_FILE" ]] && VOTING_TALLY_FILE="$DESIGN_TMPDIR/voting-tally.md"
return 0
}

# --- Single-pass mode ---
_clear_session_root_review_artifacts
_last_collect_out=""
_prior_cum_oos="$DESIGN_TMPDIR/.oos-accepted-design.prev.md"
if [[ -f "$DESIGN_TMPDIR/oos-accepted-design.md" ]]; then
    cp -f "$DESIGN_TMPDIR/oos-accepted-design.md" "$_prior_cum_oos"
else
    rm -f "$_prior_cum_oos"
fi
_prior_accepted_all="$DESIGN_TMPDIR/.accepted-plan-findings-all.prev.md"
if [[ -f "$DESIGN_TMPDIR/accepted-plan-findings-all.md" ]]; then
    cp -f "$DESIGN_TMPDIR/accepted-plan-findings-all.md" "$_prior_accepted_all"
else
    rm -f "$_prior_accepted_all"
fi
mkdir -p "$DESIGN_TMPDIR/plan-review/round-${ROUND_NUM}"
if [[ -f "$_prior_cum_oos" ]]; then
    cp -f "$_prior_cum_oos" "$DESIGN_TMPDIR/plan-review/round-${ROUND_NUM}/oos-accepted-design.before.md"
else
    rm -f "$DESIGN_TMPDIR/plan-review/round-${ROUND_NUM}/oos-accepted-design.before.md"
fi

_round_start=$(_plan_round_now_s)
set +e
_run_plan_review_round "$ROUND_NUM"
_round_rc=$?
set -e

_count_collector_evidence

if (( _round_rc != 0 )) || [[ "${LOOP_STATUS:-}" == "panel-failed" ]]; then
    _restore_prior_round_oos "$_prior_cum_oos"
    _restore_prior_round_accepted_all "$_prior_accepted_all"
    LOOP_STATUS=panel-failed
    LOOP_REASON=panel-failed
    revise_status=skipped
    IMPORTANT_ACCEPTED_COUNT=0
    NIT_ACCEPTED_COUNT=0
    NON_NIT_ACCEPTED_COUNT=0
    _snapshot_terminal_exit_preserving_status "$ROUND_NUM" 1 skipped
fi

if [[ "${loop_status_override:-}" == "main-agent-vote-required" || "${TALLY_PLAN_REVIEW_STATUS:-}" == "main-agent-vote-required" ]]; then
    LOOP_STATUS=main-agent-vote-required
    LOOP_REASON=""
    revise_status=skipped
    IMPORTANT_ACCEPTED_COUNT=$(_count_important_findings "$DESIGN_TMPDIR/accepted-plan-findings.md")
    ACCEPTED_COUNT=0
    if [[ -f "$DESIGN_TMPDIR/accepted-plan-findings.md" ]]; then
        ACCEPTED_COUNT=$(grep -cE '^### FINDING_[0-9]+:' "$DESIGN_TMPDIR/accepted-plan-findings.md" 2>/dev/null || true)
    fi
    _update_nit_accepted_counts "$DESIGN_TMPDIR/accepted-plan-findings.md"
    _accumulate_round_oos "$ROUND_NUM" "$_prior_cum_oos"
    _restore_prior_round_accepted_all "$_prior_accepted_all"
    _snapshot_terminal_exit_preserving_status "$ROUND_NUM" 0 skipped
fi

if [[ "${TALLY_PLAN_REVIEW_STATUS:-}" == "tally-error" && "${TALLY_PLAN_REVIEW_FATAL:-false}" == "true" ]]; then
    _restore_prior_round_oos "$_prior_cum_oos"
    _restore_prior_round_accepted_all "$_prior_accepted_all"
    _clear_current_accepted_findings
    LOOP_STATUS=tally-error
    LOOP_REASON=tally-error
    revise_status=skipped
    ACCEPTED_COUNT=0
    IMPORTANT_ACCEPTED_COUNT=0
    NIT_ACCEPTED_COUNT=0
    NON_NIT_ACCEPTED_COUNT=0
    _snapshot_terminal_exit_preserving_status "$ROUND_NUM" 0 skipped
fi

_accumulate_round_oos "$ROUND_NUM" "$_prior_cum_oos"
_accumulate_round_accepted_all "$_prior_accepted_all"
ACCEPTED_COUNT=0
if [[ -f "$DESIGN_TMPDIR/accepted-plan-findings.md" ]]; then
    ACCEPTED_COUNT=$(grep -cE '^### FINDING_[0-9]+:' "$DESIGN_TMPDIR/accepted-plan-findings.md" 2>/dev/null || true)
fi
IMPORTANT_ACCEPTED_COUNT=$(_count_important_findings "$DESIGN_TMPDIR/accepted-plan-findings.md")
_update_nit_accepted_counts "$DESIGN_TMPDIR/accepted-plan-findings.md"
revise_status=skipped

if [[ "$ACCEPTED_COUNT" -eq 0 \
    && "$collect_ok_count" -eq 0 \
    && "$DEGRADED_PANEL" -eq 1 \
    && "${TALLY_PLAN_REVIEW_STATUS:-}" == "skipped-empty-findings" \
    && "${ALL_SLOTS_DROPPED:-false}" != "true" ]]; then
    LOOP_STATUS=zero-findings-degraded-panel
    LOOP_REASON=zero-findings-degraded-panel
elif [[ "$ACCEPTED_COUNT" -eq 0 && "$collect_ok_count" -eq 0 ]]; then
    LOOP_STATUS=degraded-empty-collector
    LOOP_REASON=degraded-empty-collector
    DEGRADED_PANEL=1
elif [[ "$ACCEPTED_COUNT" -eq 0 && "$DEGRADED_PANEL" -eq 1 ]]; then
    LOOP_STATUS=zero-findings-degraded-panel
    LOOP_REASON=zero-findings-degraded-panel
else
    LOOP_STATUS=complete
    LOOP_REASON=""
fi

_snapshot_terminal_exit_preserving_status "$ROUND_NUM" 0 skipped
