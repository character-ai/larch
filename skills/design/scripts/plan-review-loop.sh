#!/usr/bin/env bash
# plan-review-loop.sh — Multi-round /design plan-review driver (legacy single-pass when --round-cap omitted).
# --round-num is a stateless integer supplied by the caller; this script does
# not read or write review-round-count.txt.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$REPO_ROOT}"
if [[ ! -f "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh" ]]; then
    PLUGIN_ROOT="$REPO_ROOT"
fi
# Optional harness overrides (see test-plan-review-loop.sh).
PLAN_REVIEW_SCOUT_SH="${LARCH_PLAN_REVIEW_SCOUT_SH:-$PLUGIN_ROOT/skills/design/scripts/scout-plan-archetypes-wrapper.sh}"
PLAN_REVIEW_DISPATCH_PANEL_SH="${LARCH_PLAN_REVIEW_DISPATCH_PANEL_SH:-$PLUGIN_ROOT/skills/design/scripts/dispatch-plan-review-panel.sh}"
PLAN_REVIEW_COLLECT_SH="${LARCH_PLAN_REVIEW_COLLECT_SH:-$PLUGIN_ROOT/scripts/collect-agent-results.sh}"
PLAN_REVIEW_DISPATCH_VOTERS_SH="${LARCH_PLAN_REVIEW_DISPATCH_VOTERS_SH:-$PLUGIN_ROOT/scripts/dispatch-plan-voters.sh}"
PLAN_REVIEW_TALLY_SH="${LARCH_PLAN_REVIEW_TALLY_SH:-$PLUGIN_ROOT/skills/design/scripts/tally-plan-review.sh}"
PLAN_REVIEW_REVISE_SH="${LARCH_PLAN_REVIEW_REVISE_SH:-$PLUGIN_ROOT/skills/design/scripts/revise-plan-with-waterfall.sh}"
DESIGN_DRIVER_SH="$PLUGIN_ROOT/skills/design/scripts/design-driver.sh"
CHECK_PLAN_SIZE_SH="$PLUGIN_ROOT/skills/design/scripts/check-plan-size.sh"
INVOKE_PLAN_VALIDATOR_SH="$PLUGIN_ROOT/skills/design/scripts/invoke-plan-validator.sh"
DEDUP_PLAN_LINES_PY="${LARCH_DEDUP_PLAN_LINES_PY:-$PLUGIN_ROOT/skills/design/scripts/dedup-plan-lines.py}"
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
# shellcheck source=skills/design/scripts/lib-plan-optional-trailers.sh
source "$SCRIPT_DIR/lib-plan-optional-trailers.sh"

usage() {
    larch_err "Usage: plan-review-loop.sh --design-tmpdir DIR --plan-file PATH [--feature-file PATH] [--round-num N] [--round-cap N] [--convergence-threshold N] --codex-present true|false --cursor-present true|false [--timeout SEC] [--help]"
}

DESIGN_TMPDIR=""
PLAN_FILE=""
FEATURE_FILE=""
ROUND_NUM="1"
ROUND_CAP="${LARCH_DESIGN_ROUND_CAP:-5}"
CONVERGENCE_THRESHOLD="${LARCH_DESIGN_CONVERGENCE_THRESHOLD:-3}"
ROUND_CAP_ARG_SEEN=0
CODEX_PRESENT=""
CURSOR_PRESENT=""
COLLECT_TIMEOUT="1860"
PANEL_TIMEOUT="1860"
_dedup_failed=0
_paths_readable=0
loop_status_override=""
collect_ok_count=0
collect_failure_count=0
revise_status=""
revise_winning_tier=""
LOOP_REASON=""
IMPORTANT_ACCEPTED_COUNT=0
CONVERGENCE_STREAK=0
COLLECT_OK_COUNT=0
COLLECT_FAILURE_COUNT=0
PLAN_HASH_BEFORE_REVISE=""
PLAN_HASH_AFTER_REVISE=""
TALLY_PLAN_REVIEW_STATUS=""
VOTING_TALLY_FILE=""
AGGREGATOR_STATUS=""
ACCEPTED_COUNT=0
DEGRADED_PANEL=0
VOTER_1_PARSE_RATE_STATUS=""
LOOP_STATUS="complete"
_last_collect_out=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?}"; shift 2 ;;
        --round-num) ROUND_NUM="${2:?}"; shift 2 ;;
        --round-cap) ROUND_CAP="${2:?}"; ROUND_CAP_ARG_SEEN=1; shift 2 ;;
        --convergence-threshold) CONVERGENCE_THRESHOLD="${2:?}"; shift 2 ;;
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
if (( ROUND_CAP_ARG_SEEN )); then
    case "$ROUND_CAP" in ''|*[!0-9]*) larch_err "plan-review-loop.sh: --round-cap must be a positive integer"; exit 2 ;; esac
    ROUND_CAP=$((10#$ROUND_CAP))
    (( ROUND_CAP > 0 )) || { larch_err "plan-review-loop.sh: --round-cap must be a positive integer"; exit 2; }
    if (( ROUND_NUM > ROUND_CAP )); then
        larch_err "plan-review-loop.sh: --round-num must not exceed --round-cap"
        exit 2
    fi
    case "$CONVERGENCE_THRESHOLD" in ''|*[!0-9]*) larch_err "plan-review-loop.sh: --convergence-threshold must be a non-negative integer"; exit 2 ;; esac
    CONVERGENCE_THRESHOLD=$((10#$CONVERGENCE_THRESHOLD))
fi

larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit $?

DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
mkdir -p "$DESIGN_TMPDIR"
export DESIGN_TMPDIR

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
    local loop_status="$1" accepted_count="$2" degraded_panel="$3" aggregator_status="$4" tally_status="$5" voting_tally_file="$6" voter1_parse="$7" rounds_completed="${8:-$ROUND_NUM}"
    emit_kv LOOP_STATUS "$loop_status"
    emit_kv ACCEPTED_COUNT "$accepted_count"
    emit_kv IMPORTANT_ACCEPTED_COUNT "${IMPORTANT_ACCEPTED_COUNT:-0}"
    emit_kv DEGRADED_PANEL "$degraded_panel"
    emit_kv ROUNDS_COMPLETED "$rounds_completed"
    emit_kv AGGREGATOR_STATUS "$aggregator_status"
    emit_kv TALLY_PLAN_REVIEW_STATUS "$tally_status"
    emit_kv VOTING_TALLY_FILE "$voting_tally_file"
    emit_kv VOTER_1_PARSE_RATE_STATUS "$voter1_parse"
    emit_kv CONVERGENCE_STREAK "${CONVERGENCE_STREAK:-0}"
    emit_kv REASON "${LOOP_REASON:-}"
    emit_kv REVISE_STATUS "${revise_status:-}"
    emit_kv COLLECT_OK_COUNT "${COLLECT_OK_COUNT:-0}"
    emit_kv COLLECT_FAILURE_COUNT "${COLLECT_FAILURE_COUNT:-0}"
}

write_step3_result_env() {
    local out="$DESIGN_TMPDIR/.step3-plan-review-result.env"
    local tmp="${out}.tmp"
    {
        printf 'LOOP_STATUS=%s\n' "${LOOP_STATUS:-}"
        printf 'ACCEPTED_COUNT=%s\n' "${ACCEPTED_COUNT:-0}"
        printf 'IMPORTANT_ACCEPTED_COUNT=%s\n' "${IMPORTANT_ACCEPTED_COUNT:-0}"
        printf 'DEGRADED_PANEL=%s\n' "${DEGRADED_PANEL:-0}"
        printf 'ROUNDS_COMPLETED=%s\n' "${1:-$ROUND_NUM}"
        printf 'REASON=%s\n' "${LOOP_REASON:-}"
        printf 'REVISE_STATUS=%s\n' "${revise_status:-}"
        printf 'CONVERGENCE_STREAK=%s\n' "${CONVERGENCE_STREAK:-0}"
        printf 'AGGREGATOR_STATUS=%s\n' "${AGGREGATOR_STATUS:-}"
        printf 'TALLY_PLAN_REVIEW_STATUS=%s\n' "${TALLY_PLAN_REVIEW_STATUS:-}"
        printf 'VOTING_TALLY_FILE=%s\n' "${VOTING_TALLY_FILE:-}"
        printf 'VOTER_1_PARSE_RATE_STATUS=%s\n' "${VOTER_1_PARSE_RATE_STATUS:-}"
        printf 'COLLECT_OK_COUNT=%s\n' "${COLLECT_OK_COUNT:-0}"
        printf 'COLLECT_FAILURE_COUNT=%s\n' "${COLLECT_FAILURE_COUNT:-0}"
    } >"$tmp"
    mv -f "$tmp" "$out"
}

write_empty_review_artifacts() {
    local tally_note="$1" round_num="${2:-$ROUND_NUM}"
    : > "$DESIGN_TMPDIR/accepted-plan-findings.md"
    : > "$DESIGN_TMPDIR/rejected-findings.md"
    : > "$DESIGN_TMPDIR/oos.md"
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

_read_manual_gate_b() {
    local params="$1"
    [[ -f "$params" ]] || { printf 'false'; return 0; }
    python3 - "$params" <<'PY' 2>/dev/null || awk '
        BEGIN { found=0 }
        /"manual_gate_b"[[:space:]]*:[[:space:]]*true/ { found=1 }
        END { print found ? "true" : "false" }
    ' "$params"
import json, sys

try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    raise SystemExit(1)

print("true" if data.get("manual_gate_b") is True else "false")
PY
}

_count_collector_evidence() {
    collect_ok_count=0
    collect_failure_count=0
    local rec st
    while IFS= read -r rec || [[ -n "$rec" ]]; do
        [[ -z "$rec" ]] && continue
        IFS=$'\x1f' read -r _rf _tool st _xc _fr <<< "$rec" || true
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
                "%s\x1f%s\x1f%s\x1f%s\x1f%s\n"
                % (
                    d.get("REVIEWER_FILE", ""),
                    d.get("TOOL", ""),
                    d.get("STATUS", ""),
                    d.get("EXIT_CODE", "0"),
                    d.get("FAILURE_REASON", ""),
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

_snapshot_terminal_exit_preserving_status() {
    local round_num="$1" rc="$2" summary_revise="$3"
    if ! _snapshot_round_dir "$round_num"; then
        emit_kv WARN "plan-review-snapshot: round-${round_num} snapshot failed after terminal status ${LOOP_STATUS:-unknown}"
        LOOP_REASON="${LOOP_REASON:+${LOOP_REASON},}snapshot-failed"
    fi
    _write_round_summary "$round_num" "$LOOP_STATUS" "${LOOP_REASON:-}" "$summary_revise"
    _terminal_exit "$rc" "$round_num"
}

_write_round_summary() {
    local round_num="$1" loop_status="${2:-}" reason="${3:-}" revise_st="${4:-}"
    local dest="$DESIGN_TMPDIR/plan-review/round-${round_num}/round-summary.env"
    mkdir -p "$(dirname "$dest")"
    local tmp="${dest}.tmp"
    {
        printf 'ROUND_NUM=%s\n' "$round_num"
        printf 'LOOP_STATUS=%s\n' "$loop_status"
        printf 'REASON=%s\n' "$reason"
        printf 'CONVERGENCE_STREAK=%s\n' "${CONVERGENCE_STREAK:-0}"
        printf 'ACCEPTED_COUNT=%s\n' "${ACCEPTED_COUNT:-0}"
        printf 'IMPORTANT_ACCEPTED_COUNT=%s\n' "${IMPORTANT_ACCEPTED_COUNT:-0}"
        printf 'DEGRADED_PANEL=%s\n' "${DEGRADED_PANEL:-0}"
        printf 'TALLY_PLAN_REVIEW_STATUS=%s\n' "${TALLY_PLAN_REVIEW_STATUS:-}"
        printf 'AGGREGATOR_STATUS=%s\n' "${AGGREGATOR_STATUS:-}"
        printf 'REVISE_STATUS=%s\n' "$revise_st"
        printf 'REVISE_WINNING_TIER=%s\n' "${revise_winning_tier:-}"
        printf 'PLAN_HASH_BEFORE_REVISE=%s\n' "${PLAN_HASH_BEFORE_REVISE:-}"
        printf 'PLAN_HASH_AFTER_REVISE=%s\n' "${PLAN_HASH_AFTER_REVISE:-}"
        printf 'COLLECT_OK_COUNT=%s\n' "${COLLECT_OK_COUNT:-0}"
        printf 'COLLECT_FAILURE_COUNT=%s\n' "${COLLECT_FAILURE_COUNT:-0}"
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

_run_revise_with_status_parse() {
    local round_num="$1"
    revise_status="failed-no-patch"
    revise_winning_tier=""
    local revise_out rc
    set +e
    revise_out=$("$PLAN_REVIEW_REVISE_SH" \
        --design-tmpdir "$DESIGN_TMPDIR" \
        --plan-file "$PLAN_FILE" \
        --findings-file "$DESIGN_TMPDIR/accepted-plan-findings.md" \
        --feature-file "$FEATURE_FILE" \
        --round-num "$round_num" \
        --codex-present "$CODEX_PRESENT" \
        --cursor-present "$CURSOR_PRESENT" \
        --timeout "$COLLECT_TIMEOUT")
    rc=$?
    set -e
    local k v
    while IFS= read -r _ln || [[ -n "$_ln" ]]; do
        [[ -z "$_ln" ]] && continue
        k="${_ln%%=*}"
        v="${_ln#*=}"
        case "$k" in
            REVISE_STATUS) revise_status="$v" ;;
            REVISE_WINNING_TIER) revise_winning_tier="$v" ;;
        esac
    done <<<"$revise_out"
    if (( rc != 0 )); then
        revise_status="failed-apply"
        return 1
    fi
    [[ "$revise_status" == "ok" || "$revise_status" == "ok-fallback" ]] && return 0
    return 1
}

_run_post_apply_pipeline() {
    local round_num="$1"
    local plan_backup="${2:-}"
    export DESIGN_TMPDIR
    export CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}"
    local plan_path="$DESIGN_TMPDIR/plan.txt"
    local optional_keys_file dedup_rc
    optional_keys_file=$(mktemp "$DESIGN_TMPDIR/.plan-optional-trailer-keys.XXXXXX")
    snapshot_optional_trailer_keys "$plan_path" "$optional_keys_file"
    local optional_had_trailers=0
    [[ -s "$optional_keys_file" ]] && optional_had_trailers=1
    dedup_rc=0
    dedup_plan_preserve_optional_trailers "$plan_path" "$optional_keys_file" "$DESIGN_TMPDIR" "$DEDUP_PLAN_LINES_PY" || dedup_rc=$?
    case "$dedup_rc" in
        1)
            rm -f "$optional_keys_file" "$(_optional_trailer_values_file "$optional_keys_file")"
            if (( optional_had_trailers == 0 )) && [[ -n "$plan_backup" ]]; then
                cp -f "$plan_backup" "$plan_path"
            fi
            rm -f "$plan_backup"
            LOOP_STATUS=optional-trailer-dedup-loss
            LOOP_REASON=optional-trailer-dedup-loss
            return 1
            ;;
        2)
            rm -f "$optional_keys_file" "$(_optional_trailer_values_file "$optional_keys_file")"
            [[ -n "$plan_backup" ]] && cp -f "$plan_backup" "$plan_path"
            rm -f "$plan_backup"
            LOOP_STATUS=emit-plan-failed
            LOOP_REASON=dedup-python-failed
            return 1
            ;;
    esac
    rm -f "$optional_keys_file" "$(_optional_trailer_values_file "$optional_keys_file")"
    local emit_out emit_rc
    set +e
    emit_out=$(printf 'ACTION=EMIT_PLAN\n' | "$DESIGN_DRIVER_SH" --design-tmpdir "$DESIGN_TMPDIR")
    emit_rc=$?
    set -e
    if (( emit_rc != 0 )); then
        [[ -n "$plan_backup" ]] && cp -f "$plan_backup" "$plan_path"
        rm -f "$plan_backup"
        LOOP_STATUS=emit-plan-failed
        LOOP_REASON=emit-plan-driver-failed
        return 1
    fi
    local emit_st
    emit_st=$(printf '%s\n' "$emit_out" | awk -F= '$1 == "EMIT_PLAN_STATUS" { print $2; found=1 } END { if (!found) print "" }')
    if [[ "$emit_st" == "missing-diff-lines" ]]; then
        [[ -n "$plan_backup" ]] && cp -f "$plan_backup" "$plan_path"
        rm -f "$plan_backup"
        LOOP_STATUS=emit-plan-failed
        LOOP_REASON=emit-plan-failed
        return 1
    fi
    local val_out val_rc val_st
    set +e
    val_out=$("$INVOKE_PLAN_VALIDATOR_SH" "$plan_path")
    val_rc=$?
    set -e
    val_st=$(printf '%s\n' "$val_out" | awk -F= '$1 == "VALIDATE_STATUS" { split($2, parts, /[[:space:]]+/); print parts[1]; found=1; exit } END { if (!found) print "" }')
    if (( val_rc != 0 )) || [[ "$val_st" == "defects-found" ]]; then
        LOOP_STATUS="plan-validator-defects"
        if [[ "$val_st" == "defects-found" ]]; then
            LOOP_REASON=validator-defects
        else
            LOOP_REASON=validator-driver-failed
        fi
        rm -f "$plan_backup"
        return 1
    fi
    local size_out hard soft diff_added diff_deleted diff_lines
    size_out=$("$CHECK_PLAN_SIZE_SH" --design-tmpdir "$DESIGN_TMPDIR" --plan-file "$plan_path")
    hard=$(printf '%s\n' "$size_out" | awk -F= '$1 == "HARD_TRIGGER_FIRED" { print $2; found=1 } END { if (!found) print "false" }')
    soft=$(printf '%s\n' "$size_out" | awk -F= '$1 == "SOFT_ADVISORY" { print $2; found=1 } END { if (!found) print "false" }')
    if [[ "$soft" == "true" ]]; then
        diff_added=$(printf '%s\n' "$size_out" | awk -F= '$1 == "DIFF_ADDED" { print $2; found=1 } END { if (!found) print "" }')
        diff_deleted=$(printf '%s\n' "$size_out" | awk -F= '$1 == "DIFF_DELETED" { print $2; found=1 } END { if (!found) print "" }')
        diff_lines=$(printf '%s\n' "$size_out" | awk -F= '$1 == "DIFF_LINES" { print $2; found=1 } END { if (!found) print "" }')
        if [[ "$hard" == "true" ]]; then
            printf '⏩ plan-review: plan-size — mechanical-churn advisory: diff gate downgraded (DIFF_ADDED=%s DIFF_DELETED=%s DIFF_LINES=%s); plan-body gate still requires the Split / Override / Cancel prompt\n' \
                "${diff_added:-}" "${diff_deleted:-}" "${diff_lines:-}"
        else
            printf '⏩ plan-review: plan-size — mechanical-churn advisory: diff gate downgraded (DIFF_ADDED=%s DIFF_DELETED=%s DIFF_LINES=%s); proceeding\n' \
                "${diff_added:-}" "${diff_deleted:-}" "${diff_lines:-}"
        fi
    fi
    if [[ "$hard" == "true" ]]; then
        LOOP_STATUS="plan-size-trigger"
        LOOP_REASON="plan-size-hard"
        rm -f "$plan_backup"
        return 1
    fi
    rm -f "$plan_backup"
    return 0
}

_terminal_exit() {
    local rc="$1" rounds_completed="$2"
    write_step3_result_env "$rounds_completed"
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

_run_plan_review_round() {
    local round_num="$1"
    _dedup_failed=0
    loop_status_override=""

# --- Step 2: scout (fail-open) ---
"$PLAN_REVIEW_SCOUT_SH" \
    --plan-file "$PLAN_FILE" \
    --description-file "$FEATURE_FILE" \
    --output "$DESIGN_TMPDIR/scout-plan-manifest.json" \
    --max-archetypes 6 \
    --session-env-path "$DESIGN_TMPDIR/source-env.sh" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" || true

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
COMBINED_FALLBACK_COUNT=""
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
        COMBINED_FALLBACK_COUNT) COMBINED_FALLBACK_COUNT="$_value" ;;
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
_collect_out=$(LARCH_QUIET_DISABLE=1 "$PLAN_REVIEW_COLLECT_SH" \
    --timeout "$COLLECT_TIMEOUT" \
    --substantive-validation \
    --validation-mode \
    --structured-reviewer-validation \
    --paths-file "$PANEL_PATHS_FILE" 2> >(tee -a "$_collect_err" >&${_collect_stderr_fd}))
_last_collect_out="$_collect_out"

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

_dirty_out=$("$PLUGIN_ROOT/scripts/check-mid-run-dirty-tree.sh" --mode checkpoint || true)
if grep -qE '^STATUS=(dirty|unknown)$' <<< "$_dirty_out"; then
    printf '%s\n' "$_dirty_out" > "$DESIGN_TMPDIR/dirty-tree-detected.env" || true
    emit_kv WARN "plan-review-collection: dirty tree detected"
fi

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
done < <(_parse_collect_records "$_collect_out")

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
        TALLY_PLAN_REVIEW_STATUS) TALLY_PLAN_REVIEW_STATUS="$_tv" ;;
        VOTING_TALLY_FILE) VOTING_TALLY_FILE="$_tv" ;;
        WARN) emit_kv WARN "$_tv" ;;
    esac
done <<< "$_tally_raw"

if [[ "$_tally_rc" -ne 0 ]]; then
    emit_kv WARN "plan-review-tally: tally-plan-review.sh exited with rc=$_tally_rc"
    TALLY_PLAN_REVIEW_STATUS="tally-error"
    [[ -z "$VOTING_TALLY_FILE" ]] && VOTING_TALLY_FILE="$DESIGN_TMPDIR/voting-tally.md"
    emit_findings_classification_header > "$_findings_classification_out"
    if [[ ! -s "$VOTING_TALLY_FILE" ]]; then
        {
            printf '# Plan Review Voting Tally\n\n'
            printf '**⚠ Tally aborted (rc=%s); no votes tallied.**\n' "$_tally_rc"
        } > "$VOTING_TALLY_FILE"
    fi
fi

printf '%s\n' "$_tally_raw"

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

# --- Legacy single-pass (no --round-cap on argv) ---
if (( ROUND_CAP_ARG_SEEN == 0 )); then
    set +e
    _run_plan_review_round "$ROUND_NUM"
    _round_rc=$?
    set -e
    if (( _round_rc != 0 )); then
        LOOP_STATUS=panel-failed
        IMPORTANT_ACCEPTED_COUNT=0
        _terminal_exit 1 "$ROUND_NUM"
    fi
    IMPORTANT_ACCEPTED_COUNT=$(_count_important_findings "$DESIGN_TMPDIR/accepted-plan-findings.md")
    _count_collector_evidence
    if [[ "$TALLY_PLAN_REVIEW_STATUS" == "main-agent-vote-required" ]]; then
        LOOP_STATUS=main-agent-vote-required
    else
        LOOP_STATUS=complete
    fi
    _terminal_exit 0 "$ROUND_NUM"
fi

# --- Multi-round mode ---
round_num=$ROUND_NUM
convergence_streak=0
CONVERGENCE_STREAK=0
manual_mode=false
if [[ -f "$DESIGN_TMPDIR/run-params.json" ]]; then
    _mg=$(_read_manual_gate_b "$DESIGN_TMPDIR/run-params.json")
    [[ "$_mg" == "true" ]] && manual_mode=true
fi

while (( round_num <= ROUND_CAP )); do
    _clear_session_root_review_artifacts
    _last_collect_out=""
    _prior_cum_oos="$DESIGN_TMPDIR/.oos-accepted-design.prev.md"
    if [[ -f "$DESIGN_TMPDIR/oos-accepted-design.md" ]]; then
        cp -f "$DESIGN_TMPDIR/oos-accepted-design.md" "$_prior_cum_oos"
    else
        rm -f "$_prior_cum_oos"
    fi
    set +e
    _run_plan_review_round "$round_num"
    _round_rc=$?
    set -e

    if [[ "$loop_status_override" == "main-agent-vote-required" ]]; then
        LOOP_STATUS=main-agent-vote-required
        LOOP_REASON=""
        IMPORTANT_ACCEPTED_COUNT=$(_count_important_findings "$DESIGN_TMPDIR/accepted-plan-findings.md")
        _count_collector_evidence
        _accumulate_round_oos "$round_num" "$_prior_cum_oos"
        _snapshot_terminal_exit_preserving_status "$round_num" 0 skipped
    fi

    if (( _round_rc != 0 )); then
        _restore_prior_round_oos "$_prior_cum_oos"
        LOOP_STATUS=panel-failed
        LOOP_REASON=panel-failed
        revise_status=skipped
        IMPORTANT_ACCEPTED_COUNT=0
        _count_collector_evidence
        if ! _snapshot_round_dir "$round_num"; then
            LOOP_REASON=snapshot-failed
            _write_round_summary "$round_num" panel-failed snapshot-failed skipped
            _terminal_exit 1 "$round_num"
        fi
        _write_round_summary "$round_num" panel-failed panel-failed skipped
        _terminal_exit 1 "$round_num"
    fi

    if [[ "$TALLY_PLAN_REVIEW_STATUS" == "tally-error" ]]; then
        _restore_prior_round_oos "$_prior_cum_oos"
        LOOP_STATUS=tally-error
        LOOP_REASON=tally-error
        revise_status=skipped
        IMPORTANT_ACCEPTED_COUNT=0
        _count_collector_evidence
        _snapshot_terminal_exit_preserving_status "$round_num" 0 skipped
    fi

    _accumulate_round_oos "$round_num" "$_prior_cum_oos"
    _count_collector_evidence
    ACCEPTED_COUNT=0
    if [[ -f "$DESIGN_TMPDIR/accepted-plan-findings.md" ]]; then
        ACCEPTED_COUNT=$(grep -cE '^### FINDING_[0-9]+:' "$DESIGN_TMPDIR/accepted-plan-findings.md" 2>/dev/null || true)
    fi
    IMPORTANT_ACCEPTED_COUNT=$(_count_important_findings "$DESIGN_TMPDIR/accepted-plan-findings.md")
    PLAN_HASH_BEFORE_REVISE=$(git hash-object --no-filters "$PLAN_FILE" 2>/dev/null || printf '')

    if [[ "$ACCEPTED_COUNT" -eq 0 ]]; then
        if [[ "$collect_ok_count" -eq 0 ]]; then
            LOOP_STATUS=degraded-empty-collector
            LOOP_REASON=degraded-empty-collector
            DEGRADED_PANEL=1
            revise_status=skipped
            _snapshot_terminal_exit_preserving_status "$round_num" 0 skipped
        fi
        if [[ "$DEGRADED_PANEL" -eq 1 ]]; then
            LOOP_STATUS=zero-findings-degraded-panel
            LOOP_REASON=zero-findings-degraded-panel
        else
            LOOP_STATUS=converged
            LOOP_REASON=zero-findings
        fi
        revise_status=skipped
        _snapshot_terminal_exit_preserving_status "$round_num" 0 skipped
    fi

    if [[ "$manual_mode" == true ]]; then
        LOOP_STATUS=complete
        LOOP_REASON=manual-gate-b
        revise_status=skipped
        _snapshot_terminal_exit_preserving_status "$round_num" 0 skipped
    fi

    _pre_revise_plan_backup=$(mktemp "$DESIGN_TMPDIR/.plan-before-revise.XXXXXX")
    cp -f "$PLAN_FILE" "$_pre_revise_plan_backup"
    if ! _run_revise_with_status_parse "$round_num"; then
        rm -f "$_pre_revise_plan_backup"
        DEGRADED_PANEL=1
        PLAN_HASH_AFTER_REVISE=$(git hash-object --no-filters "$PLAN_FILE" 2>/dev/null || printf '')
        LOOP_STATUS=revision-failed
        LOOP_REASON=revision-failed
        _snapshot_terminal_exit_preserving_status "$round_num" 0 "${revise_status:-failed-no-patch}"
    fi
    PLAN_HASH_AFTER_REVISE=$(git hash-object --no-filters "$PLAN_FILE" 2>/dev/null || printf '')
    revise_status="${revise_status:-ok}"

    if ! _run_post_apply_pipeline "$round_num" "$_pre_revise_plan_backup"; then
        _snapshot_terminal_exit_preserving_status "$round_num" 0 "${revise_status:-ok}"
    fi

    _next_terminal_status=""
    _next_terminal_reason=""
    _next_convergence_streak="$convergence_streak"
    if ! _snapshot_round_dir "$round_num"; then
        if [[ "$DEGRADED_PANEL" -eq 1 ]]; then
            _next_convergence_streak=0
        elif [[ "$ACCEPTED_COUNT" -le "$CONVERGENCE_THRESHOLD" && "$IMPORTANT_ACCEPTED_COUNT" -eq 0 ]]; then
            _next_convergence_streak=$((convergence_streak + 1))
            if (( _next_convergence_streak >= 2 )); then
                _next_terminal_status=converged
                _next_terminal_reason=streak
            fi
        else
            _next_convergence_streak=0
        fi
        if [[ -z "$_next_terminal_status" && $round_num -eq $ROUND_CAP ]]; then
            _next_terminal_status=cap-hit
            _next_terminal_reason=cap-hit
        fi
        if [[ -n "$_next_terminal_status" ]]; then
            LOOP_STATUS="$_next_terminal_status"
            LOOP_REASON="${_next_terminal_reason},snapshot-failed"
            CONVERGENCE_STREAK="$_next_convergence_streak"
            _write_round_summary "$round_num" "$LOOP_STATUS" "$LOOP_REASON" "${revise_status:-ok}"
            _terminal_exit 0 "$round_num"
        fi
        LOOP_STATUS=panel-failed
        LOOP_REASON=snapshot-failed
        _write_round_summary "$round_num" panel-failed snapshot-failed "${revise_status:-ok}"
        _terminal_exit 1 "$round_num"
    fi

    if [[ "$DEGRADED_PANEL" -eq 1 ]]; then
        convergence_streak=0
        CONVERGENCE_STREAK=0
    elif [[ "$ACCEPTED_COUNT" -le "$CONVERGENCE_THRESHOLD" && "$IMPORTANT_ACCEPTED_COUNT" -eq 0 ]]; then
        convergence_streak=$((convergence_streak + 1))
        CONVERGENCE_STREAK=$convergence_streak
        if (( convergence_streak >= 2 )); then
            LOOP_STATUS=converged
            LOOP_REASON=streak
            _write_round_summary "$round_num" converged streak "${revise_status:-ok}"
            _terminal_exit 0 "$round_num"
        fi
    else
        convergence_streak=0
        CONVERGENCE_STREAK=0
    fi

    if (( round_num == ROUND_CAP )); then
        LOOP_STATUS=cap-hit
        LOOP_REASON=cap-hit
        _write_round_summary "$round_num" cap-hit cap-hit "${revise_status:-ok}"
        _terminal_exit 0 "$round_num"
    fi

    _write_round_summary "$round_num" "" "" "${revise_status:-ok}"
    round_num=$((round_num + 1))
done

_terminal_exit 0 "$ROUND_CAP"
