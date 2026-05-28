#!/usr/bin/env bash
# Offline harness for dispatch-plan-assessors.sh
set -euo pipefail
export LARCH_QUIET_DISABLE=1

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
SLOTS_FILE="" REQUIRE_PATTERN=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slots-file) SLOTS_FILE="${2:?}"; shift 2 ;;
    --require-result-pattern) REQUIRE_PATTERN="${2:?}"; shift 2 ;;
    --codex-present|--cursor-present|--mode|--timeout|--feature-file) shift 2 ;;
    *) shift ;;
  esac
done
[[ -n "$REQUIRE_PATTERN" ]] || { echo "missing pattern" >&2; exit 2; }
out1="" out2=""
while IFS= read -r row; do
  [[ -n "$row" ]] || continue
  tool=$(printf '%s' "$row" | sed -n 's/.*"tool":"\([^"]*\)".*/\1/p')
  output=$(printf '%s' "$row" | sed -n 's/.*"output":"\([^"]*\)".*/\1/p')
  if [[ "$tool" == codex ]]; then out1="$output"; fi
  if [[ "$tool" == cursor ]]; then
    if [[ "${CURSOR_STUB_MODE:-ok}" == narrate ]]; then
      printf 'I will now assess the plan.\n' >"$output"
    else
      printf 'ASSESSMENT: TIE\nREASONING: cursor ok\nQUALIFICATIONS: c qual\n' >"$output"
    fi
    out2="$output"
  fi
done <"$SLOTS_FILE"
printf 'DISPATCH_OK=true\nALL_OUTPUT_FILES=%s %s\nALL_OUTPUT_TOOLS=codex cursor\n' "$out1" "$out2"
STUB
chmod +x "$PLUGIN_STUB/scripts/dispatch-with-waterfall.sh"

printf 'feature\n' >"$TMP/feature.txt"
printf 'o\n' >"$TMP/o.txt"
printf 'p\n' >"$TMP/p.txt"
printf 'c\n' >"$TMP/c.txt"

export CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB"
export LARCH_LAUNCH_CLAUDE_REVIEW_SH="$PLUGIN_STUB/scripts/launch-claude-review.sh"
export LARCH_DISPATCH_WITH_WATERFALL_SH="$PLUGIN_STUB/scripts/dispatch-with-waterfall.sh"

out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" \
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
grep -Fq 'plan-assessor' "$TMP/plan-assessor-slots.ndjson" || fail 'missing manifest'

pass 'dispatch-plan-assessors harness'
