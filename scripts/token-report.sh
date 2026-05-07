#!/usr/bin/env bash
# token-report.sh — Render /implement token reports from Claude transcripts + ledger.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

unavailable() {
    printf 'Token report unavailable: %s\n' "$1"
    exit 0
}

tmp_root() {
    local root="${TMPDIR:-/tmp}"
    (cd "$root" 2>/dev/null && pwd -P) || return 1
}

validate_tmp_path() {
    local raw="$1"
    local root parent parent_dir base resolved
    root=$(tmp_root) || return 1
    case "$raw" in
        ""|*/../*|../*|*/..|..) return 1 ;;
    esac
    if [[ "$raw" = /* ]]; then
        parent="$raw"
    else
        parent="$root/$raw"
    fi
    parent_dir=$(dirname "$parent")
    base=$(basename "$parent")
    mkdir -p "$parent_dir" 2>/dev/null || return 1
    resolved=$(cd "$parent_dir" 2>/dev/null && pwd -P) || return 1
    [[ "$resolved" == "$root" || "$resolved" == "$root"/* ]] || return 1
    printf '%s/%s' "$resolved" "$base"
}

ledger_from_dump() {
    "$SCRIPT_DIR/token-ledger.sh" dump 2>/dev/null | sed -n '1p'
}

resolve_sources() {
    local transcript_override="$1"
    local session_dir_override="$2"
    TRANSCRIPT_FILES=()

    if [[ -n "$transcript_override" ]]; then
        [[ -f "$transcript_override" ]] || unavailable "transcript not found"
        TRANSCRIPT_FILES+=("$transcript_override")
        if [[ -n "$session_dir_override" && -d "$session_dir_override/subagents" ]]; then
            while IFS= read -r f; do
                TRANSCRIPT_FILES+=("$f")
            done < <(find "$session_dir_override/subagents" -type f -name '*.jsonl' | sort)
        fi
        return 0
    fi

    local source_out transcript session_dir
    if ! source_out=$("$SCRIPT_DIR/token-claude-source.sh" 2>/dev/null); then
        local reason
        reason=$(printf '%s\n' "$source_out" | awk '/^REASON=/ { sub(/^REASON=/, ""); print; exit }')
        unavailable "${reason:-Claude transcript source unavailable}"
    fi
    transcript=$(printf '%s\n' "$source_out" | awk '/^TRANSCRIPT_PATH=/ { sub(/^TRANSCRIPT_PATH=/, ""); print; exit }')
    session_dir=$(printf '%s\n' "$source_out" | awk '/^SESSION_DIR=/ { sub(/^SESSION_DIR=/, ""); print; exit }')
    [[ -n "$transcript" && -f "$transcript" ]] || unavailable "transcript not found"
    TRANSCRIPT_FILES+=("$transcript")
    if [[ -n "$session_dir" && -d "$session_dir/subagents" ]]; then
        while IFS= read -r f; do
            TRANSCRIPT_FILES+=("$f")
        done < <(find "$session_dir/subagents" -type f -name '*.jsonl' | sort)
    fi
}

RENDER_FAIL_REASON=""

# render_jq writes the rendered report to stdout on success and returns 0.
# On failure, sets RENDER_FAIL_REASON to a short message and returns non-zero
# WITHOUT calling `unavailable` — this is critical because `render_jq` is
# sometimes invoked from inside a redirect to a temp file (see Step 2 below);
# calling `exit 0` from `unavailable` here would only exit a subshell when
# called from `$(...)`, and would prematurely exit the parent script when
# called from a `>file` redirect, in either case losing the chance for the
# caller to clean up its temp files. Top-level dispatch maps RENDER_FAIL_REASON
# back to `unavailable` in the parent shell.
render_jq() {
    local mode="$1"
    local ledger="$2"
    if ! command -v jq >/dev/null 2>&1; then
        RENDER_FAIL_REASON="jq not found"
        return 1
    fi
    if [[ ! -f "$ledger" ]]; then
        RENDER_FAIL_REASON="ledger not found"
        return 1
    fi
    if [[ "${#TRANSCRIPT_FILES[@]}" -eq 0 ]]; then
        RENDER_FAIL_REASON="transcript not found"
        return 1
    fi

    jq -r -s --slurpfile ledger "$ledger" --arg mode "$mode" '
      def epoch:
        if . == null then null
        else (tostring | gsub("\\.[0-9]+Z$"; "Z") | fromdateiso8601? // null)
        end;
      def n($x): ($x // 0 | tonumber? // 0);
      def fmt($x): ($x | tostring);
      def claude_total($r):
        n($r.message.usage.input_tokens)
        + n($r.message.usage.cache_read_input_tokens)
        + n($r.message.usage.cache_creation_input_tokens)
        + n($r.message.usage.output_tokens);
      def usage_row($r):
        {
          ts: ($r.timestamp | epoch),
          skill: ($r.attributionSkill // "unattributed"),
          input: n($r.message.usage.input_tokens),
          cache_read: n($r.message.usage.cache_read_input_tokens),
          cache_create: n($r.message.usage.cache_creation_input_tokens),
          output: n($r.message.usage.output_tokens),
          total: claude_total($r)
        };
      def vendor_row($r):
        {
          ts: ($r.ts | epoch),
          vendor: ($r.vendor // "unknown"),
          input: n($r.input),
          output: n($r.output),
          cache_read: n($r.cache_read),
          cache_create: n($r.cache_create),
          total: n($r.total)
        };
      def sumfield($rows; $field): reduce $rows[] as $r (0; . + ($r[$field] // 0));
      def totals($rows): {
        input: sumfield($rows; "input"),
        cache_read: sumfield($rows; "cache_read"),
        cache_create: sumfield($rows; "cache_create"),
        output: sumfield($rows; "output"),
        total: sumfield($rows; "total")
      };
      def vendor_breakdown($rows):
        ($rows | group_by(.vendor) | map({vendor: .[0].vendor, total: sumfield(.; "total")}));
      def step_slice($claude; $vendor; $start; $end):
        {
          claude: ($claude | map(select(.ts != null and .ts >= $start and ($end == null or .ts < $end)))),
          vendor: ($vendor | map(select(.ts != null and .ts >= $start and ($end == null or .ts < $end))))
        };
      def terse_line($claude; $vendor; $mark):
        (step_slice($claude; $vendor; $mark.ts; null)) as $s
        | (totals($s.claude)) as $ct
        | (sumfield($s.vendor; "total")) as $vt
        | (vendor_breakdown($s.vendor)) as $vb
        | ($mark.step + ": claude=" + fmt($ct.total) + " tokens (input=" + fmt($ct.input)
          + " cache_read=" + fmt($ct.cache_read) + " cache_create=" + fmt($ct.cache_create)
          + " output=" + fmt($ct.output) + "); vendor=" + fmt($vt)
          + (if $vt > 0 then " (" + ($vb | map(.vendor + "=" + (.total|tostring)) | join(", ")) + ")" else "" end));
      def md_header:
        "| Step | Skill | Claude input | Cache read | Cache create | Output | Claude total | Vendor total |\n"
        + "|---|---:|---:|---:|---:|---:|---:|---:|";
      def md_row($step; $skill; $ci; $cr; $cc; $out; $ct; $vt):
        "| " + $step + " | " + $skill + " | " + ($ci|tostring) + " | " + ($cr|tostring)
        + " | " + ($cc|tostring) + " | " + ($out|tostring) + " | " + ($ct|tostring)
        + " | " + ($vt|tostring) + " |";
      def md_na_row($step; $skill; $vt):
        "| " + $step + " | " + $skill + " | N/A | N/A | N/A | N/A | N/A | " + ($vt|tostring) + " |";
      def markdown($marks; $claude; $vendor):
        [md_header] + (
          [range(0; $marks|length) as $i
            | ($marks[$i]) as $m
            | (($marks[$i+1].ts) // null) as $end
            | (step_slice($claude; $vendor; $m.ts; $end)) as $s
            | (totals($s.claude)) as $ct
            | (sumfield($s.vendor; "total")) as $vt
            | md_row($m.step; "**step total**"; $ct.input; $ct.cache_read; $ct.cache_create; $ct.output; $ct.total; $vt),
              ($s.claude
                | group_by(.skill)
                | map({skill: .[0].skill, totals: totals(.)})
                | .[]
                | md_row("" ; ("&nbsp;&nbsp;" + .skill); .totals.input; .totals.cache_read; .totals.cache_create; .totals.output; .totals.total; 0)),
              ($s.vendor
                | group_by(.vendor)
                | map({vendor: .[0].vendor, total: sumfield(.; "total")})
                | .[]
                | md_na_row("" ; ("&nbsp;&nbsp;vendor:" + .vendor); .total))
          ]
        ) + [
          # Filter grand totals to only rows at or after the first mark so the
          # table reconciles: each step row uses step_slice with mark.ts as the
          # lower bound, so rows BEFORE the first mark are excluded from every
          # per-step row and would otherwise appear only in the grand total —
          # producing a sum-of-step-rows ≠ grand-total mismatch. Filtering here
          # keeps the grand row consistent with the per-step partition.
          ($marks[0].ts) as $first
          | ($claude | map(select(.ts != null and .ts >= $first))) as $claude_in_run
          | ($vendor | map(select(.ts != null and .ts >= $first))) as $vendor_in_run
          | (totals($claude_in_run)) as $gt
          | md_row("**Grand total**"; ""; $gt.input; $gt.cache_read; $gt.cache_create; $gt.output; $gt.total; (sumfield($vendor_in_run; "total")))
        ] | join("\n");

      ($ledger // []) as $l
      | ($l | map(select(.type == "mark") | {step, ts: (.ts | epoch)}) | map(select(.ts != null))) as $marks
      | ($l | map(select(.type == "vendor") | vendor_row(.)) | map(select(.ts != null))) as $vendor
      | (map(select(.type == "assistant" and .message.usage? and .timestamp?) | usage_row(.)) | map(select(.ts != null))) as $claude
      | if ($marks | length) == 0 then error("no step marks in ledger")
        elif $mode == "terse" then terse_line($claude; $vendor; $marks[-1])
        else markdown($marks; $claude; $vendor)
        end
    ' "${TRANSCRIPT_FILES[@]}" 2>/dev/null || {
        RENDER_FAIL_REASON="failed to parse token sources"
        return 1
    }
}

replace_token_block() {
    local target="$1"
    local block_file="$2"
    local tmp
    mkdir -p "$(dirname "$target")"
    tmp="$target.tmp"
    if [[ -f "$target" ]] && grep -Fq '<!-- token-report-begin -->' "$target" && grep -Fq '<!-- token-report-end -->' "$target"; then
        awk -v repl="$block_file" '
          BEGIN {
            while ((getline line < repl) > 0) replacement = replacement line "\n"
            close(repl)
          }
          /<!-- token-report-begin -->/ {
            printf "%s", replacement
            skip=1
            next
          }
          /<!-- token-report-end -->/ && skip { skip=0; next }
          !skip { print }
        ' "$target" > "$tmp"
    else
        if [[ -f "$target" ]]; then
            cat "$target" > "$tmp"
            printf '\n' >> "$tmp"
        else
            : > "$tmp"
        fi
        cat "$block_file" >> "$tmp"
    fi
    mv "$tmp" "$target"
}

MODE=""
OUTPUT=""
LEDGER_OVERRIDE=""
TRANSCRIPT_OVERRIDE=""
SESSION_DIR_OVERRIDE=""
RUN_STATS_TARGET=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --since-last-mark) MODE="terse"; shift ;;
        --terse) shift ;;
        --full) MODE="full"; shift ;;
        --markdown) shift ;;
        --output) OUTPUT="${2:?--output requires a value}"; shift 2 ;;
        --ledger) LEDGER_OVERRIDE="${2:?--ledger requires a value}"; shift 2 ;;
        --transcript) TRANSCRIPT_OVERRIDE="${2:?--transcript requires a value}"; shift 2 ;;
        --session-dir) SESSION_DIR_OVERRIDE="${2:?--session-dir requires a value}"; shift 2 ;;
        --append-run-statistics) RUN_STATS_TARGET="${2:?--append-run-statistics requires a value}"; MODE="append"; shift 2 ;;
        *) unavailable "unknown flag: $1" ;;
    esac
done

[[ -n "$MODE" ]] || unavailable "missing report mode"

if [[ -n "$LEDGER_OVERRIDE" ]]; then
    LEDGER=$(validate_tmp_path "$LEDGER_OVERRIDE") || unavailable "invalid ledger path"
else
    LEDGER=$(ledger_from_dump)
fi
[[ -n "$LEDGER" ]] || unavailable "ledger path unavailable"

resolve_sources "$TRANSCRIPT_OVERRIDE" "$SESSION_DIR_OVERRIDE"

if [[ "$MODE" == "append" ]]; then
    rendered_file=$(mktemp "${TMPDIR:-/tmp}/token-report-rendered.XXXXXX")
    if ! render_jq full "$LEDGER" > "$rendered_file"; then
        rm -f "$rendered_file"
        unavailable "${RENDER_FAIL_REASON:-failed to render token report}"
    fi
    block=$(mktemp "${TMPDIR:-/tmp}/token-report-block.XXXXXX")
    {
        printf '<!-- token-report-begin -->\n'
        printf '## Token Report\n\n'
        cat "$rendered_file"
        printf '\n<!-- token-report-end -->\n'
    } > "$block"
    replace_token_block "$RUN_STATS_TARGET" "$block"
    rm -f "$block" "$rendered_file"
elif [[ "$MODE" == "full" && -n "$OUTPUT" ]]; then
    tmp="$OUTPUT.tmp"
    if ! render_jq full "$LEDGER" > "$tmp"; then
        rm -f "$tmp"
        unavailable "${RENDER_FAIL_REASON:-failed to render token report}"
    fi
    mv "$tmp" "$OUTPUT"
else
    if ! render_jq "$MODE" "$LEDGER"; then
        unavailable "${RENDER_FAIL_REASON:-failed to render token report}"
    fi
fi
