#!/usr/bin/env bash
# Offline harness for dispatch-plan-assessors.sh
set -euo pipefail
export LARCH_QUIET_DISABLE=1
unset LARCH_QUIET_LOG_FILE || true

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/dispatch-plan-assessors.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/tdpa.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
STUB="$TMP/bin"
mkdir -p "$STUB"
PLUGIN_STUB="$TMP/plugin"
mkdir -p "$PLUGIN_STUB/scripts" "$PLUGIN_STUB/skills/shared/scripts" "$PLUGIN_STUB/skills/design/scripts"

cp "$ROOT/skills/shared/scripts/render-assessor-prompt.sh" "$PLUGIN_STUB/skills/shared/scripts/"
cp "$ROOT/scripts/lib-quiet.sh" "$PLUGIN_STUB/scripts/"
chmod +x "$PLUGIN_STUB/skills/shared/scripts/render-assessor-prompt.sh"

cat >"$PLUGIN_STUB/scripts/launch-claude-review.sh" <<'STUB'
#!/usr/bin/env bash
OUTPUT="" PROMPT_FILE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) OUTPUT="${2:?}"; shift 2 ;;
    --prompt-file) PROMPT_FILE="${2:?}"; shift 2 ;;
    --mode|--role|--timeout|--timing-task-kind) shift 2 ;;
    *) shift ;;
  esac
done
printf 'ASSESSMENT: WORSE\nREASONING: claude ok\nQUALIFICATIONS: claude qual\n' >"$OUTPUT"
printf '0\n' >"${OUTPUT}.done"
STUB
chmod +x "$PLUGIN_STUB/scripts/launch-claude-review.sh"

cat >"$PLUGIN_STUB/scripts/dispatch-with-waterfall.sh" <<'STUB'
#!/usr/bin/env bash
SLOTS_FILE="" REQUIRE_PATTERN="" CODEX_PRESENT="" CURSOR_PRESENT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slots-file) SLOTS_FILE="${2:?}"; shift 2 ;;
    --require-result-pattern) REQUIRE_PATTERN="${2:?}"; shift 2 ;;
    --codex-present) CODEX_PRESENT="${2:?}"; shift 2 ;;
    --cursor-present) CURSOR_PRESENT="${2:?}"; shift 2 ;;
    --mode|--timeout|--feature-file|--no-fallback)
      [[ -n "${PLAN_ASSESSOR_WF_ARGS_LOG:-}" ]] && printf '%s\n' "$1" >>"${PLAN_ASSESSOR_WF_ARGS_LOG}"
      shift 2
      ;;
    *) shift ;;
  esac
done
[[ -n "$REQUIRE_PATTERN" ]] || { echo "missing pattern" >&2; exit 2; }
[[ "$REQUIRE_PATTERN" == '^[[:space:]]*\**[Aa][Ss][Ss][Ee][Ss][Ss][Mm][Ee][Nn][Tt][[:space:]]*[:=]' ]] || { echo "unexpected pattern: $REQUIRE_PATTERN" >&2; exit 3; }
out1="" out2=""
while IFS= read -r row; do
  [[ -n "$row" ]] || continue
  tool=$(printf '%s' "$row" | sed -n 's/.*"tool":"\([^"]*\)".*/\1/p')
  output=$(printf '%s' "$row" | sed -n 's/.*"output":"\([^"]*\)".*/\1/p')
  prompt_file=$(printf '%s' "$row" | sed -n 's/.*"prompt_file":"\([^"]*\)".*/\1/p')
  [[ "$row" == '{"slot":"plan-assessor","tool":"'"$tool"'","output":"'"$output"'","prompt_file":"'"$prompt_file"'"}' ]] || {
    echo "unexpected manifest row: $row" >&2
    exit 4
  }
  if [[ "$tool" == codex ]]; then
    if [[ "$CODEX_PRESENT" == false ]]; then
      printf 'ASSESSMENT: BETTER\nREASONING: codex fallback\nQUALIFICATIONS: x qual\n' >"$output"
      tool_out1=claude
    else
      printf 'ASSESSMENT: BETTER\nREASONING: codex ok\nQUALIFICATIONS: x qual\n' >"$output"
      tool_out1=codex
    fi
    out1="$output"
  fi
  if [[ "$tool" == cursor ]]; then
    if [[ "${CURSOR_STUB_MODE:-ok}" == narrate ]]; then
      trace="${PLAN_ASSESSOR_TRACE_FILE:?}"
      printf '%s\n' 'phase1:cursor:narrative-only' >>"$trace"
      printf 'Still narrating instead of emitting an ASSESSMENT line.\n' >"$output"
      out2="$output"
      tool_out2=cursor
    elif [[ "$CURSOR_PRESENT" == false ]]; then
      printf 'ASSESSMENT: TIE\nREASONING: cursor fallback\nQUALIFICATIONS: c qual\n' >"$output"
      tool_out2=claude
    else
      printf 'ASSESSMENT: TIE\nREASONING: cursor ok\nQUALIFICATIONS: c qual\n' >"$output"
      tool_out2=cursor
    fi
    out2="$output"
  fi
done <"$SLOTS_FILE"
printf 'DISPATCH_OK=true\nALL_OUTPUT_FILES=%s %s\nALL_OUTPUT_TOOLS=%s %s\n' "$out1" "$out2" "${tool_out1:-codex}" "${tool_out2:-cursor}"
STUB
chmod +x "$PLUGIN_STUB/scripts/dispatch-with-waterfall.sh"

printf 'feature\n' >"$TMP/feature.txt"
printf 'o\n' >"$TMP/o.txt"
printf 'p\n' >"$TMP/p.txt"
printf 'c\n' >"$TMP/c.txt"

export CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB"
export LARCH_LAUNCH_CLAUDE_REVIEW_SH="$PLUGIN_STUB/scripts/launch-claude-review.sh"
export LARCH_DISPATCH_WITH_WATERFALL_SH="$PLUGIN_STUB/scripts/dispatch-with-waterfall.sh"
export DESIGN_TMPDIR="$TMP"
export PLAN_ASSESSOR_TRACE_FILE="$TMP/waterfall.trace"
export PLAN_ASSESSOR_WF_ARGS_LOG="$TMP/wf-args.log"
: >"$PLAN_ASSESSOR_WF_ARGS_LOG"
unset IMPLEMENT_TMPDIR || true

out=$(LARCH_QUIET_DISABLE='' "$SUBJECT" \
  --design-tmpdir "$TMP" \
  --round-num 2 \
  --plan-original "$TMP/o.txt" \
  --plan-prev "$TMP/p.txt" \
  --plan-current "$TMP/c.txt" \
  --feature-file "$TMP/feature.txt" \
  --codex-present true \
  --cursor-present true)

printf '%s\n' "$out" | grep -Fq 'DISPATCH_OK=true' || fail 'DISPATCH_OK not true'
printf '%s\n' "$out" | grep -Fq 'CLAUDE_ASSESSOR_PATH=' || fail 'missing claude path kv'
printf '%s\n' "$out" | grep -Fq 'DEGRADED_PANEL_WARNING=false' || fail 'happy path should not be degraded'
grep -Fq 'plan-assessor' "$TMP/plan-assessor-slots.ndjson" || fail 'missing manifest'
[[ "$(grep -c . "$TMP/plan-assessor-slots.ndjson" || true)" == "2" ]] || fail 'both-present assessor manifest should have two rows'
grep -Fq -- '--no-fallback' "$PLAN_ASSESSOR_WF_ARGS_LOG" || fail 'assessor waterfall must pass --no-fallback'

mkdir -p "$TMP/codex-only" "$TMP/cursor-only" "$TMP/both-absent"
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" \
  --design-tmpdir "$TMP/codex-only" \
  --round-num 2 \
  --plan-original "$TMP/o.txt" \
  --plan-prev "$TMP/p.txt" \
  --plan-current "$TMP/c.txt" \
  --feature-file "$TMP/feature.txt" \
  --codex-present true \
  --cursor-present false)
[[ "$(grep -c . "$TMP/codex-only/plan-assessor-slots.ndjson" || true)" == "1" ]] || fail 'codex-only assessor manifest should have one row'
grep -Fq '"tool":"codex"' "$TMP/codex-only/plan-assessor-slots.ndjson" || fail 'codex-only manifest must be codex row'

out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" \
  --design-tmpdir "$TMP/cursor-only" \
  --round-num 2 \
  --plan-original "$TMP/o.txt" \
  --plan-prev "$TMP/p.txt" \
  --plan-current "$TMP/c.txt" \
  --feature-file "$TMP/feature.txt" \
  --codex-present false \
  --cursor-present true)
[[ "$(grep -c . "$TMP/cursor-only/plan-assessor-slots.ndjson" || true)" == "1" ]] || fail 'cursor-only assessor manifest should have one row'
grep -Fq '"tool":"cursor"' "$TMP/cursor-only/plan-assessor-slots.ndjson" || fail 'cursor-only manifest must be cursor row'

out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" \
  --design-tmpdir "$TMP/both-absent" \
  --round-num 2 \
  --plan-original "$TMP/o.txt" \
  --plan-prev "$TMP/p.txt" \
  --plan-current "$TMP/c.txt" \
  --feature-file "$TMP/feature.txt" \
  --codex-present false \
  --cursor-present false)
[[ ! -s "$TMP/both-absent/plan-assessor-slots.ndjson" ]] || fail 'both-absent assessor manifest must be empty'
printf '%s\n' "$out" | grep -Fq 'DISPATCH_OK=true' || fail 'both-absent assessor dispatch should remain DISPATCH_OK=true'
printf '%s\n' "$out" | grep -Fq 'CLAUDE_ASSESSOR_STATUS=launched' || fail 'both-absent must launch Claude assessor floor'
_claude_assessor_path=$(printf '%s\n' "$out" | awk -F= '$1=="CLAUDE_ASSESSOR_PATH"{print substr($0,index($0,"=")+1);exit}')
[[ -n "$_claude_assessor_path" && -s "$_claude_assessor_path" ]] \
    || fail 'both-absent must produce non-empty Claude assessor output'

out=$(CURSOR_STUB_MODE=narrate LARCH_QUIET_DISABLE=1 "$SUBJECT" \
  --design-tmpdir "$TMP" \
  --round-num 2 \
  --plan-original "$TMP/o.txt" \
  --plan-prev "$TMP/p.txt" \
  --plan-current "$TMP/c.txt" \
  --feature-file "$TMP/feature.txt" \
  --codex-present true \
  --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'DISPATCH_OK=true' || fail 'drop-on-failure assessor dispatch should remain DISPATCH_OK=true'
printf '%s\n' "$out" | grep -Fq 'DEGRADED_PANEL_WARNING=true' || fail 'narration-only cursor output should mark degraded panel'
grep -Fqx 'phase1:cursor:narrative-only' "$TMP/waterfall.trace" || fail 'narration-only cursor case must record cursor phase-1 attempt'
grep -Fq 'phase2:codex' "$TMP/waterfall.trace" && fail 'narration-only cursor case must not record phase-2 codex retry'
grep -Fq 'phase3:claude' "$TMP/waterfall.trace" && fail 'narration-only cursor case must not record phase-3 claude retry'
jq -s -e 'all(.[]; has("fallback_group") | not)' "$TMP/plan-assessor-slots.ndjson" >/dev/null \
    || fail 'assessor manifest must not include fallback_group'

cat >"$PLUGIN_STUB/scripts/launch-claude-review.sh" <<'STUB'
#!/usr/bin/env bash
OUTPUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) OUTPUT="${2:?}"; shift 2 ;;
    --prompt-file|--mode|--role|--timeout|--timing-task-kind) shift 2 ;;
    *) shift ;;
  esac
done
: >"$OUTPUT"
exit 9
STUB
chmod +x "$PLUGIN_STUB/scripts/launch-claude-review.sh"
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" \
  --design-tmpdir "$TMP" \
  --round-num 2 \
  --plan-original "$TMP/o.txt" \
  --plan-prev "$TMP/p.txt" \
  --plan-current "$TMP/c.txt" \
  --feature-file "$TMP/feature.txt" \
  --codex-present true \
  --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'CLAUDE_ASSESSOR_STATUS=failed' || fail 'launcher failure should be surfaced as failed claude assessor'
printf '%s\n' "$out" | grep -Fq 'DEGRADED_PANEL_WARNING=true' || fail 'launcher failure should mark degraded panel'

out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" \
  --design-tmpdir "$TMP" \
  --round-num 2 \
  --plan-original "$TMP/o.txt" \
  --plan-prev "$TMP/p.txt" \
  --plan-current "$TMP/c.txt" \
  --feature-file "$TMP/feature.txt" \
  --codex-present false \
  --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'CODEX_ASSESSOR_STATUS=failed' || fail 'codex-unavailable path should mark codex assessor failed'

out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" \
  --design-tmpdir "$TMP" \
  --round-num 2 \
  --plan-original "$TMP/o.txt" \
  --plan-prev "$TMP/p.txt" \
  --plan-current "$TMP/c.txt" \
  --feature-file "$TMP/feature.txt" \
  --codex-present true \
  --cursor-present false)
printf '%s\n' "$out" | grep -Fq 'CURSOR_ASSESSOR_STATUS=failed' || fail 'cursor-unavailable path should mark cursor assessor failed'

cat >"$PLUGIN_STUB/scripts/launch-claude-review.sh" <<'STUB'
#!/usr/bin/env bash
OUTPUT="" PROMPT_FILE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) OUTPUT="${2:?}"; shift 2 ;;
    --prompt-file) PROMPT_FILE="${2:?}"; shift 2 ;;
    --mode|--role|--timeout|--timing-task-kind) shift 2 ;;
    *) shift ;;
  esac
done
printf 'ASSESSMENT: WORSE\nREASONING: claude ok\nQUALIFICATIONS: claude qual\n' >"$OUTPUT"
printf '0\n' >"${OUTPUT}.done"
STUB
chmod +x "$PLUGIN_STUB/scripts/launch-claude-review.sh"
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" \
  --design-tmpdir "$TMP" \
  --round-num 2 \
  --plan-original "$TMP/o.txt" \
  --plan-prev "$TMP/p.txt" \
  --plan-current "$TMP/c.txt" \
  --feature-file "$TMP/feature.txt" \
  --codex-present false \
  --cursor-present false)
printf '%s\n' "$out" | grep -Fq 'DISPATCH_OK=true' || fail 'both-external-absent path should still satisfy dispatch contract'
printf '%s\n' "$out" | grep -Fq 'CODEX_ASSESSOR_STATUS=failed' || fail 'both-external-absent path should mark codex assessor failed'
printf '%s\n' "$out" | grep -Fq 'CURSOR_ASSESSOR_STATUS=failed' || fail 'both-external-absent path should mark cursor assessor failed'

if LARCH_QUIET_DISABLE=1 "$SUBJECT" \
  --design-tmpdir "$TMP" \
  --round-num 02x \
  --plan-original "$TMP/o.txt" \
  --plan-prev "$TMP/p.txt" \
  --plan-current "$TMP/c.txt" \
  --feature-file "$TMP/feature.txt" \
  --codex-present true \
  --cursor-present true >/tmp/larch-dispatch-assessor-invalid.out 2>&1; then
  fail 'invalid round number should fail closed'
fi

pass 'dispatch-plan-assessors harness'
