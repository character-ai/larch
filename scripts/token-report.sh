#!/usr/bin/env bash
# token-report.sh — Render /implement token reports from Claude transcripts + ledger.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

unavailable() {
    printf 'Token report unavailable: %s\n' "$1" >&2
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

    # When LARCH_DEBUG_TOKEN_REPORT matches the explicit truthy allowlist
    # below, redirect jq stderr to a temp file and surface a fixed
    # diagnostic suffix (`(jq stderr captured; debug)`) on stdout via
    # RENDER_FAIL_REASON, while emitting the actual file path on the
    # script's own stderr (`token-report.sh: jq stderr captured at <path>`).
    # The published surface (stdout, which flows verbatim into tracking
    # issue anchors and PR bodies) never carries the absolute
    # TMPDIR/username-bearing path. The redirect is a plain
    # `2>"$jq_stderr_dest"`, not a `tee` — jq diagnostics go only to the
    # temp file. Default behavior (silent stderr to /dev/null) is
    # preserved for any unset / negative / unrecognized value (`no`,
    # `off`, `disabled`, `0`, etc.) so the report stays non-blocking; the
    # env var is purely an opt-in development diagnostic. mktemp failure
    # degrades silently to /dev/null so the debug knob never breaks
    # production.
    local jq_stderr_dest="/dev/null"
    local jq_stderr_path=""
    # Allowlist of explicit truthy values — narrower than a blanket
    # "anything non-empty / non-zero" gate so common negatives (`no`, `off`,
    # `disabled`, etc.) do not silently enable the debug capture path. The
    # set matches the doc's enumerated examples (1, true, yes, on) plus their
    # case variants.
    case "${LARCH_DEBUG_TOKEN_REPORT:-}" in
        1|true|TRUE|True|yes|YES|Yes|on|ON|On)
            # mktemp template puts the X's at the end (no `.log` suffix) so
            # BSD mktemp on macOS expands them — BSD mktemp leaves trailing X's
            # alone when a literal suffix follows them, producing a static
            # filename that concurrent runs would clobber. Explicit chmod 0600
            # is defense-in-depth even though most mktemp implementations
            # already create with that mode (closes #1466 review FINDING_8 —
            # predictable shared-tmp filename + jq stderr can include input
            # snippets).
            if jq_stderr_path=$(mktemp "${TMPDIR:-/tmp}/larch-token-report-jq-stderr-XXXXXX" 2>/dev/null); then
                chmod 0600 "$jq_stderr_path" 2>/dev/null || true
                jq_stderr_dest="$jq_stderr_path"
            else
                jq_stderr_path=""
            fi
            ;;
    esac

    jq -r -s --slurpfile ledger "$ledger" --arg mode "$mode" '
      def epoch:
        if . == null then null
        else (tostring | gsub("\\.[0-9]+Z$"; "Z") | fromdateiso8601? // null)
        end;
      def n($x): ($x // 0 | tonumber? // 0);
      def fmt($x): ($x | tostring);
      def md_cell($s):
        ($s // "" | tostring
          | gsub("\r\n"; " ")
          | gsub("\n"; " ")
          | gsub("\r"; " ")
          | gsub("\\|"; "\\|"));
      def claude_total($r):
        n($r.message.usage.input_tokens)
        + n($r.message.usage.cache_read_input_tokens)
        + n($r.message.usage.cache_creation_input_tokens)
        + n($r.message.usage.output_tokens);
      # Returns the step name whose window [mark.ts, next_mark.ts) contains $ts,
      # or null when $ts falls outside all windows (e.g. before the first mark).
      def enclosing_step_label($marks; $ts):
        first(
          range($marks | length) as $i |
          select(
            $marks[$i].ts != null and $marks[$i].ts <= $ts and
            ($i + 1 >= ($marks | length) or $marks[$i + 1].ts == null or $marks[$i + 1].ts > $ts)
          ) |
          $marks[$i].step
        ) // null;
      def usage_row($r; $marks):
        ($r.timestamp | epoch) as $ts |
        {
          ts: $ts,
          skill: (if $r.attributionSkill != null then $r.attributionSkill
                  else
                    (enclosing_step_label($marks; $ts)) as $step_name |
                    if $step_name != null then "inferred:" + $step_name
                    else "unattributed"
                    end
                  end),
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
          total: (if ($r | has("total"))
                  then n($r.total)
                  else (n($r.input) + n($r.output) + n($r.cache_read) + n($r.cache_create))
                  end)
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

      # --- Shared helpers ---

      # Vendor-name to display heading. Explicit map so headings render
      # capitalized. Unknown vendors fall through to "### " + raw name to keep
      # coverage lossless when ledger contains arbitrary vendor strings; the
      # raw fallback routes through md_cell so a vendor string containing |
      # or newlines cannot break the heading or inject a fake row separator.
      def vendor_label($vname):
        if   $vname == "codex"  then "Codex"
        elif $vname == "cursor" then "Cursor"
        elif $vname == "gemini" then "Gemini"
        else md_cell($vname)
        end;

      # Claude-table 6-column header — used only by claude_table. The two
      # cache columns are surfaced because cache_read (typically 5-20x
      # uncached input on long orchestrators) and cache_create are real
      # billable input volume; hiding them understates Anthropic spend.
      def vendor_header($input_label; $cache_read_label; $cache_create_label; $output_label):
        "| Step | Skill | " + $input_label + " | " + $cache_read_label + " | " + $cache_create_label + " | " + $output_label + " |\n"
        + "| --- | --- | ---: | ---: | ---: | ---: |";

      # Claude-table 6-column row — used only by claude_table.
      def vrow($step; $name; $in; $cr; $cc; $out):
        "| " + md_cell($step) + " | " + md_cell($name) + " | "
        + ($in|tostring) + " | " + ($cr|tostring) + " | " + ($cc|tostring) + " | " + ($out|tostring) + " |";

      # Vendor-table 5-column header — used only by vendor_table.
      def vendor_header5:
        "| Step | Skill | Input | Output | Total |\n"
        + "| --- | --- | ---: | ---: | ---: |";

      # Vendor-table 5-column row — used only by vendor_table.
      def vrow5($step; $name; $in; $out; $tot):
        "| " + md_cell($step) + " | " + md_cell($name) + " | "
        + ($in|tostring) + " | " + ($out|tostring) + " | " + ($tot|tostring) + " |";

      # Single-array slice helper: the one-array analog of step_slice.
      def slice1($rows; $start; $end):
        $rows | map(select(.ts != null and .ts >= $start and ($end == null or .ts < $end)));

      # --- Claude table ---

      # Always emitted because Claude is the primary surface.
      def claude_table($marks; $claude):
        ["### Claude", "", vendor_header("Claude Input"; "Claude Cache Read"; "Claude Cache Create"; "Claude Output")]
        + ([range(0; $marks|length) as $i
            | ($marks[$i]) as $m
            | (($marks[$i+1].ts) // null) as $end
            | (slice1($claude; $m.ts; $end)) as $sl
            | (totals($sl)) as $st
            | vrow($m.step; "**step total**"; $st.input; $st.cache_read; $st.cache_create; $st.output),
              ($sl
                | group_by(.skill)
                | map({skill: .[0].skill, totals: totals(.)})
                | .[]
                | vrow(""; .skill; .totals.input; .totals.cache_read; .totals.cache_create; .totals.output))
           ])
        + [
            ($marks[0].ts) as $first
            | (slice1($claude; $first; null)) as $in_run
            | (totals($in_run)) as $gt
            | vrow("**Grand total**"; ""; $gt.input; $gt.cache_read; $gt.cache_create; $gt.output)
          ]
        | join("\n");

      # --- Per-vendor table ---

      # Filters $vendor to the requested name and in-run window. Both the
      # emit/omit decision and totals read from that same filtered set.
      def vendor_table($vname; $marks; $vendor):
        ($marks[0].ts) as $first
        | ($vendor | map(select(.vendor == $vname and .ts != null and .ts >= $first))) as $vrows
        | if ($vrows | length) == 0 then null
          else
            ["### " + vendor_label($vname), "", vendor_header5]
            + ([range(0; $marks|length) as $i
                | ($marks[$i]) as $m
                | (($marks[$i+1].ts) // null) as $end
                | (slice1($vrows; $m.ts; $end)) as $sl
                | (sumfield($sl; "input")) as $vi
                | (sumfield($sl; "output")) as $vo
                | (sumfield($sl; "total")) as $vt
                | vrow5($m.step; "**step total**"; $vi; $vo; $vt)
               ])
            + [
                (sumfield($vrows; "input")) as $gi
                | (sumfield($vrows; "output")) as $go
                | (sumfield($vrows; "total")) as $gt
                | vrow5("**Grand total**"; ""; $gi; $go; $gt)
              ]
            | join("\n")
          end;

      # Coverage-lossless vendor enumeration: take distinct vendor names in
      # the in-run window, then emit codex first, cursor second, and any other
      # vendors alphabetically.
      def vendor_names($marks; $vendor):
        ($marks[0].ts) as $first
        | ($vendor | map(select(.ts != null and .ts >= $first)) | map(.vendor) | unique) as $present
        | (["codex", "cursor"] | map(select(. as $v | $present | index($v) != null)))
        + ($present - ["codex", "cursor"] | sort);

      def markdown($marks; $claude; $vendor):
        ([claude_table($marks; $claude)]
         + (vendor_names($marks; $vendor) | map(vendor_table(.; $marks; $vendor)))
         | map(select(. != null))
         | join("\n\n"));

      ($ledger // []) as $l
      | ($l | map(select(.type == "mark") | {step, ts: (.ts | epoch)}) | map(select(.ts != null))) as $marks
      | ($l | map(select(.type == "vendor") | vendor_row(.)) | map(select(.ts != null))) as $vendor
      | (map(select(.type == "assistant" and .message.usage? and .timestamp?) | usage_row(.; $marks)) | map(select(.ts != null))) as $claude
      | if ($marks | length) == 0 then error("no step marks in ledger")
        elif $mode == "terse" then terse_line($claude; $vendor; $marks[-1])
        else markdown($marks; $claude; $vendor)
        end
    ' "${TRANSCRIPT_FILES[@]}" 2>"$jq_stderr_dest" || {
        if [[ -n "$jq_stderr_path" && -s "$jq_stderr_path" ]]; then
            # `unavailable` now routes to stderr; the tracking-issue anchor
            # and PR body are populated via stdout-only calls (--append-*).
            # The absolute jq stderr path — which carries TMPDIR + username —
            # must not appear in RENDER_FAIL_REASON. Emit a fixed phrase via
            # unavailable (stderr) and surface the actual path on stderr only
            # (closes #1511 finding B).
            RENDER_FAIL_REASON="failed to parse token sources (jq stderr captured; debug)"
            printf 'token-report.sh: jq stderr captured at %s\n' "$jq_stderr_path" >&2
        else
            RENDER_FAIL_REASON="failed to parse token sources"
            # Empty stderr file on a debug-mode failure carries no signal —
            # remove it so $TMPDIR is not littered with empties.
            if [[ -n "$jq_stderr_path" ]]; then
                rm -f "$jq_stderr_path"
            fi
        fi
        return 1
    }
    # Success path: the debug-mode stderr file is almost always empty
    # (jq wrote nothing to stderr); remove it so successful runs do not
    # litter $TMPDIR.
    if [[ -n "$jq_stderr_path" ]]; then
        rm -f "$jq_stderr_path"
    fi
}

replace_token_block() {
    local target="$1"
    local block_file="$2"
    local tmp has_begin=0 has_end=0
    mkdir -p "$(dirname "$target")"
    tmp="$target.tmp"
    if [[ -f "$target" ]]; then
        # Presence probes use the SAME whole-line anchored regex as the
        # awk rewrite below — keeping them in sync prevents a data-loss
        # path where substring grep selects the matched-pair / lone-marker
        # branch but awk never matches a structural sentinel and either
        # drops legitimate trailing content (lone-end + trailing prose
        # mention) or silently no-ops the replacement (prose-only mentions
        # of both markers). #1511 round-1 review consensus FINDING (data
        # loss path).
        grep -Eq '^[[:space:]]*<!-- token-report-begin -->[[:space:]]*$' "$target" && has_begin=1
        grep -Eq '^[[:space:]]*<!-- token-report-end -->[[:space:]]*$' "$target" && has_end=1
    fi
    if (( has_begin == 1 && has_end == 1 )); then
        # Both markers present — replace the bracketed region in place.
        # Marker regexes are anchored to whole-line (allowing leading /
        # trailing whitespace) so a legitimate prose / table-cell line that
        # merely *mentions* the marker substring is not treated as a
        # structural sentinel. token-report.sh always emits the markers on
        # their own line, so this is the author-side contract; parity with
        # assemble-anchor.sh marker-pair walks (closes #1511 finding A).
        awk -v repl="$block_file" '
          BEGIN {
            while ((getline line < repl) > 0) replacement = replacement line "\n"
            close(repl)
          }
          /^[[:space:]]*<!-- token-report-begin -->[[:space:]]*$/ {
            printf "%s", replacement
            skip=1
            next
          }
          /^[[:space:]]*<!-- token-report-end -->[[:space:]]*$/ && skip { skip=0; next }
          !skip { print }
        ' "$target" > "$tmp"
    elif (( has_begin == 1 || has_end == 1 )); then
        # Mismatched markers (lone begin or lone end) indicate a damaged or
        # half-written prior write. Normalize: drop content from the first
        # surviving marker through end-of-file (lone-begin) or the file head
        # through the surviving marker (lone-end), then append a fresh block.
        # Emit a stderr warning so the corruption is observable.
        # Marker regex is whole-line anchored for the same reason as the
        # matched-pair branch above.
        if (( has_begin == 1 )); then
            printf 'token-report.sh: warning: %s has lone <!-- token-report-begin --> marker; truncating from marker and rewriting block\n' "$target" >&2
            awk '/^[[:space:]]*<!-- token-report-begin -->[[:space:]]*$/ {found=1; next} !found {print}' "$target" > "$tmp"
        else
            printf 'token-report.sh: warning: %s has lone <!-- token-report-end --> marker; dropping head through marker and rewriting block\n' "$target" >&2
            awk '/^[[:space:]]*<!-- token-report-end -->[[:space:]]*$/ {found=1; next} found {print}' "$target" > "$tmp"
        fi
        # Ensure trailing newline before appending the fresh block.
        if [[ -s "$tmp" ]] && [[ "$(tail -c 1 "$tmp" | wc -c)" -gt 0 ]]; then
            # tail -c 1 returns 1 byte if file does not end in newline, 0 if it does.
            # If last byte is not newline, append one.
            last=$(tail -c 1 "$tmp")
            if [[ "$last" != $'\n' ]]; then
                printf '\n' >> "$tmp"
            fi
        fi
        cat "$block_file" >> "$tmp"
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
TOKEN_REPORT_TARGET=""

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
        --append-token-report) TOKEN_REPORT_TARGET="${2:?--append-token-report requires a value}"; MODE="append"; shift 2 ;;
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
    replace_token_block "$TOKEN_REPORT_TARGET" "$block"
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
