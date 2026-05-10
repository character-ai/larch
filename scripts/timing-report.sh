#!/usr/bin/env bash
# timing-report.sh — Render timing reports from timing-ledger.sh TSV data.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Path-validation primitives are shared with timing-ledger.sh so the two
# scripts agree on the allowed-roots set (closes review FINDING_1 +
# FINDING_4). Previously timing-report.sh accepted only ${TMPDIR:-/tmp},
# while timing-ledger.sh writes ledgers under any of TMPDIR /
# IMPLEMENT_TMPDIR / DESIGN_TMPDIR / REVIEW_TMPDIR /
# dirname(SESSION_ENV_PATH); a path valid for writes is now also valid
# for reads.
# shellcheck source=scripts/lib-timing-paths.sh
source "$SCRIPT_DIR/lib-timing-paths.sh"

unavailable() {
    printf 'Timing report unavailable: %s\n' "$1" >&2
    exit 0
}

# Accept a `--ledger PATH` override under the same containment roots
# `timing-ledger.sh` accepts (TMPDIR + the four optional env-derived
# roots), not just TMPDIR. Print the canonicalized path on success;
# return 1 on failure so the caller can `unavailable "invalid ledger
# path"`.
validate_ledger_override() {
    local raw="$1"
    local -a roots=()
    local root candidate
    while IFS= read -r root; do
        [[ -n "$root" ]] && roots+=("$root")
    done < <(timing_allowed_roots)
    candidate=$(validate_under_roots "$raw" "${roots[@]+"${roots[@]}"}") || return 1
    printf '%s' "$candidate"
}

ledger_from_dump() {
    "$SCRIPT_DIR/timing-ledger.sh" dump 2>/dev/null | sed -n '1p'
}

replace_timing_block() {
    local target="$1"
    local block_file="$2"
    local tmp
    mkdir -p "$(dirname "$target")"
    tmp="$target.tmp"
    if [[ -f "$target" ]] && grep -Fq '<!-- timing-report-begin -->' "$target" && grep -Fq '<!-- timing-report-end -->' "$target"; then
        awk -v repl="$block_file" '
          BEGIN {
            while ((getline line < repl) > 0) replacement = replacement line "\n"
            close(repl)
          }
          /<!-- timing-report-begin -->/ {
            printf "%s", replacement
            skip=1
            next
          }
          /<!-- timing-report-end -->/ && skip { skip=0; next }
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

render_report() {
    local mode="$1"
    local ledger="$2"
    local now="${LARCH_TEST_TIMING_NOW:-$(date +%s)}"
    local skill="${LARCH_TIMING_SKILL:-implement}"
    [[ -f "$ledger" ]] || unavailable "ledger not found"
    awk -F '\t' -v mode="$mode" -v now="$now" -v terse_skill="$skill" '
      function hms(sec, h, m, s) {
        if (sec < 0) sec = 0
        h = int(sec / 3600)
        m = int((sec % 3600) / 60)
        s = sec % 60
        return sprintf("%02d:%02d:%02d", h, m, s)
      }
      function minutes(sec) {
        return sprintf("%.1f min", sec / 60.0)
      }
      function md(s) {
        gsub(/\|/, "\\|", s)
        gsub(/\r/, " ", s)
        gsub(/\n/, " ", s)
        return s
      }
      function vendor_index(v) {
        return v == "codex" ? 1 : (v == "cursor" ? 2 : (v == "gemini" ? 3 : 4))
      }
      function row_ok() {
        if ($1 != "v1") return 0
        if (NF != 13) {
          printf "timing-report.sh: WARNING: skipping malformed row with %d columns\n", NF > "/dev/stderr"
          return 0
        }
        return 1
      }
      row_ok() && $2 == "mark" {
        mark_count++
        mark_ts[mark_count] = $3 + 0
        mark_skill[mark_count] = $4
        mark_step[mark_count] = $5
        skill_count[$4]++
        idx = $4 SUBSEP skill_count[$4]
        skill_mark_ts[idx] = $3 + 0
        skill_mark_step[idx] = $5
        if ($4 == terse_skill) {
          last_terse_ts = $3 + 0
          last_terse_step = $5
        }
        next
      }
      row_ok() && $2 == "vendor" {
        vendor_count++
        vendor_ts[vendor_count] = $3 + 0
        vendor_end[vendor_count] = $9 + 0
        vendor_name[vendor_count] = $6
        vendor_kind[vendor_count] = $7
        vendor_duration[vendor_count] = $10 + 0
        vendor_exit[vendor_count] = $12 + 0
        vendor_status[vendor_count] = $13
        next
      }
      row_ok() && $2 == "workflow" {
        workflow = $13
        workflow_ts = $3 + 0
        next
      }
      END {
        if (mode == "terse") {
          if (last_terse_ts == "") {
            print "Timing report unavailable: no step marks in ledger"
            exit 0
          }
          codex = cursor = gemini = total = 0
          for (i = 1; i <= vendor_count; i++) {
            # Compare vendor_end (col $9) with the latest mark timestamp;
            # using the row write-time ($3) inflated counts when a task
            # finished before the mark but its trap fired after. (FINDING_5.)
            if (vendor_end[i] >= last_terse_ts) {
              total++
              if (vendor_name[i] == "codex") codex++
              else if (vendor_name[i] == "cursor") cursor++
              else if (vendor_name[i] == "gemini") gemini++
            }
          }
          printf "%s: elapsed=%s vendor-tasks=%d (codex=%d, cursor=%d, gemini=%d)\n", last_terse_step, hms(now - last_terse_ts), total, codex, cursor, gemini
          exit 0
        }
        if (mark_count == 0) {
          print "Timing report unavailable: no step marks in ledger"
          exit 0
        }
        if (workflow == "") workflow = "unknown"
        print "**Workflow path**: " workflow
        print ""
        print "## Per-Step Durations"
        print ""
        print "| Skill | Step | Duration |"
        print "| --- | --- | ---: |"
        if (skill_count["implement"] > 0) {
          first_impl_ts = skill_mark_ts["implement" SUBSEP 1]
          last_impl_ts = skill_mark_ts["implement" SUBSEP skill_count["implement"]]
          total_duration = last_impl_ts - first_impl_ts
          for (i = 1; i <= skill_count["implement"]; i++) {
            s = skill_mark_ts["implement" SUBSEP i]
            e = (i < skill_count["implement"]) ? skill_mark_ts["implement" SUBSEP (i + 1)] : last_event_ts()
            print "| implement | " md(skill_mark_step["implement" SUBSEP i]) " | " hms(e - s) " |"
            emit_child_rows("design", s, e)
            emit_child_rows("review", s, e)
          }
        } else {
          first_mark_ts = mark_ts[1]
          last_mark_ts = mark_ts[mark_count]
          total_duration = last_mark_ts - first_mark_ts
          for (i = 1; i <= mark_count; i++) {
            e = (i < mark_count) ? mark_ts[i + 1] : last_event_ts()
            print "| " md(mark_skill[i]) " | " md(mark_step[i]) " | " hms(e - mark_ts[i]) " |"
          }
        }
        print "| **Total** | | " hms(total_duration) " |"
        print ""
        print "## Vendor Task Averages"
        print ""
        print "| Vendor | Task kind | Samples | Average | Range |"
        print "| --- | --- | ---: | ---: | --- |"
        for (i = 1; i <= vendor_count; i++) {
          key = vendor_name[i] SUBSEP vendor_kind[i]
          if (vendor_status[i] == "complete" && vendor_exit[i] == 0) {
            sample_count[key]++
            sample_sum[key] += vendor_duration[i]
            if (!(key in sample_min) || vendor_duration[i] < sample_min[key]) sample_min[key] = vendor_duration[i]
            if (!(key in sample_max) || vendor_duration[i] > sample_max[key]) sample_max[key] = vendor_duration[i]
            if (!(key in key_seen)) {
              key_seen[key] = 1
              key_order[++key_order_count] = key
            }
          } else {
            fail_key = vendor_kind[i]
            fail_count[fail_key]++
            if (!(fail_key in fail_seen)) {
              fail_seen[fail_key] = 1
              fail_order[++fail_order_count] = fail_key
            }
          }
        }
        sort_keys()
        for (oi = 1; oi <= key_order_count; oi++) {
          key = key_order[oi]
          split(key, parts, SUBSEP)
          n = sample_count[key]
          avg = sample_sum[key] / n
          if (n == 1) {
            range = "(1 sample)"
          } else {
            range = minutes(sample_min[key]) "-" minutes(sample_max[key])
          }
          print "| " md(parts[1]) " | " md(parts[2]) " | " n " | " minutes(avg) " | " range " |"
        }
        if (fail_order_count > 0) {
          msg = ""
          for (i = 1; i <= fail_order_count; i++) {
            if (i > 1) msg = msg "; "
            msg = msg fail_count[fail_order[i]] " " fail_order[i]
          }
          print ""
          print "(Failures: " msg " not included in averages.)"
        }
      }
      function last_event_ts(    t, i) {
        t = now
        if (workflow_ts > t) t = workflow_ts
        for (i = 1; i <= vendor_count; i++) if (vendor_ts[i] > t) t = vendor_ts[i]
        return t
      }
      function skill_interval_end(skill, idx,    key) {
        key = skill SUBSEP (idx + 1)
        if (idx < skill_count[skill]) return skill_mark_ts[key]
        return last_event_ts()
      }
      function emit_child_rows(skill, start, end,    i, s, e, step) {
        for (i = 1; i <= skill_count[skill]; i++) {
          s = skill_mark_ts[skill SUBSEP i]
          if (s >= start && s < end) {
            e = skill_interval_end(skill, i)
            if (e > end) e = end
            step = skill_mark_step[skill SUBSEP i]
            print "|   ↳ " md(skill) " | " md(step) " | " hms(e - s) " |"
          }
        }
      }
      function sort_keys(    i, j, tmp, a, b, av, bv) {
        for (i = 1; i <= key_order_count; i++) {
          for (j = i + 1; j <= key_order_count; j++) {
            a = key_order[i]; b = key_order[j]
            split(a, av, SUBSEP); split(b, bv, SUBSEP)
            if (vendor_index(av[1]) > vendor_index(bv[1]) || (vendor_index(av[1]) == vendor_index(bv[1]) && av[2] > bv[2])) {
              tmp = key_order[i]; key_order[i] = key_order[j]; key_order[j] = tmp
            }
          }
        }
      }
    ' "$ledger"
}

MODE=""
OUTPUT=""
LEDGER_OVERRIDE=""
TIMING_TARGET=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --since-last-mark) MODE="terse"; shift ;;
        --terse) shift ;;
        --full) MODE="full"; shift ;;
        --markdown) shift ;;
        --output) OUTPUT="${2:?--output requires a value}"; shift 2 ;;
        --ledger) LEDGER_OVERRIDE="${2:?--ledger requires a value}"; shift 2 ;;
        --append-timing-section) TIMING_TARGET="${2:?--append-timing-section requires a value}"; MODE="append"; shift 2 ;;
        *) unavailable "unknown flag: $1" ;;
    esac
done

[[ -n "$MODE" ]] || unavailable "missing report mode"

if [[ -n "$LEDGER_OVERRIDE" ]]; then
    LEDGER=$(validate_ledger_override "$LEDGER_OVERRIDE") || unavailable "invalid ledger path"
else
    LEDGER=$(ledger_from_dump)
fi
[[ -n "$LEDGER" ]] || unavailable "ledger path unavailable"

if [[ "$MODE" == "append" ]]; then
    rendered_file=$(mktemp "${TMPDIR:-/tmp}/timing-report-rendered.XXXXXX")
    render_report full "$LEDGER" > "$rendered_file"
    block=$(mktemp "${TMPDIR:-/tmp}/timing-report-block.XXXXXX")
    {
        printf '<!-- timing-report-begin -->\n'
        printf '## Timing Report\n\n'
        cat "$rendered_file"
        printf '\n<!-- timing-report-end -->\n'
    } > "$block"
    replace_timing_block "$TIMING_TARGET" "$block"
    rm -f "$block" "$rendered_file"
elif [[ "$MODE" == "full" && -n "$OUTPUT" ]]; then
    tmp="$OUTPUT.tmp"
    render_report full "$LEDGER" > "$tmp"
    mv "$tmp" "$OUTPUT"
else
    render_report "$MODE" "$LEDGER"
fi
