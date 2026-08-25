#!/usr/bin/env bash
# test-design-step5c.sh — offline harness for design-step5c bgjob launcher.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/design-step5c.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-design-step5c.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

FAKE_PLUGIN="$TMP/plugin"
mkdir -p "$FAKE_PLUGIN/scripts" "$FAKE_PLUGIN/skills/design/scripts"
cp "$SUBJECT" "$FAKE_PLUGIN/skills/design/scripts/design-step5c.sh"
chmod +x "$FAKE_PLUGIN/skills/design/scripts/design-step5c.sh"
cat >"$FAKE_PLUGIN/scripts/larch.sh" <<'SH'
#!/usr/bin/env bash
set -uo pipefail

option_value() {
  local needle="$1"
  shift
  while [[ $# -gt 1 ]]; do
    if [[ "$1" == "$needle" ]]; then
      printf '%s\n' "$2"
      return 0
    fi
    shift
  done
  return 1
}

case "${1:-} ${2:-}" in
  "session require-plugin-root"|"session validate-design-tmpdir")
    exit 0
    ;;
  "bgjob adapt")
    if [[ " $* " == *" --resolve-session-env "* ]]; then
      source_path="$(option_value --session-env-path "$@")" || exit 2
      cat "$source_path"
      exit 0
    fi
    step="$(option_value --step "$@")" || exit 2
    tmpdir="$(option_value --tmpdir "$@")" || exit 2
    args=("$@")
    command=()
    replace=false
    for ((index = 0; index < ${#args[@]}; index++)); do
      [[ "${args[$index]}" == "--replace-completed-result" ]] && replace=true
      if [[ "${args[$index]}" == "--" ]]; then
        command=("${args[@]:$((index + 1))}")
        break
      fi
    done
    [[ ${#command[@]} -gt 0 ]] || exit 2
    result_dir="$tmpdir/bgjob"
    result="$result_dir/$step.result.env"
    merge="$result_dir/$step.merge.env"
    mkdir -p "$result_dir"
    if [[ -f "$result" && ! -L "$result" && "$replace" == false ]]; then
      printf 'BGJOB_STATUS=DONE\n'
      cat "$result"
      exit 0
    fi
    [[ "$replace" == true ]] && rm -f "$result"
    : >"$merge"
    "${command[@]}" --bgjob-child --merge-result-env "$merge" >/dev/null 2>&1
    rc=$?
    {
      printf 'BGJOB_RC=%s\nBGJOB_ELAPSED_S=0\nSTEP=%s\n' "$rc" "$step"
      if [[ -f "$merge" && ! -L "$merge" ]]; then
        while IFS= read -r row; do
          case "$row" in BGJOB_RC=*|BGJOB_ELAPSED_S=*|STEP=*) ;; *=*) printf '%s\n' "$row" ;; esac
        done <"$merge"
      fi
    } >"$result"
    printf 'BGJOB_STATUS=STARTED STEP=%s PGID=12345\n' "$step"
    exit 0
    ;;
  "bgjob wait")
    step="$(option_value --step "$@")" || exit 2
    tmpdir="$(option_value --tmpdir "$@")" || exit 2
    result="$tmpdir/bgjob/$step.result.env"
    if [[ -f "$result" && ! -L "$result" ]]; then
      printf 'BGJOB_STATUS=DONE\n'
      cat "$result"
    else
      printf 'BGJOB_STATUS=DEAD\n'
    fi
    exit 0
    ;;
  "design step5c")
    [[ -n "${DESIGN_STEP5C_STUB_LOG:-}" ]] && printf '%s\n' "$@" >"$DESIGN_STEP5C_STUB_LOG"
    refusal="${DESIGN_STEP5C_STUB_REFUSAL:-}"
    if [[ -n "$refusal" ]]; then
      plan_write_ok=false
      publish_ok=false
      publish_rc=4
      cleanup_eligible=false
    else
      plan_write_ok=true
      publish_ok=true
      publish_rc=0
      cleanup_eligible=true
    fi
    status_file="${DESIGN_TMPDIR:?}/.design-step5c-status.env"
    {
      printf 'PLAN_WRITE_OK=%s\n' "$plan_write_ok"
      printf 'PUBLISH_OK=%s\n' "$publish_ok"
      printf 'PUBLISH_RC=%s\n' "$publish_rc"
      printf 'VALIDATE_STATUS=ok\nFINAL_SUMMARY_PATH=/tmp/final-summary.md\n'
      printf 'CLEANUP_ELIGIBLE=%s\n' "$cleanup_eligible"
      printf 'PUBLISH_REFUSE_REASON=%s\n' "$refusal"
    } >"$status_file"
    merge="$(option_value --merge-result-env "$@" || true)"
    [[ -n "$merge" ]] && cp "$status_file" "$merge"
    exit "${DESIGN_STEP5C_STUB_RC:-0}"
    ;;
esac
printf 'unexpected larch command: %s\n' "$*" >&2
exit 2
SH
chmod +x "$FAKE_PLUGIN/scripts/larch.sh"

D="$TMP/design"
mkdir -p "$D/.completed" "$TMP/registry"
: >"$D/.completed/step-5b"
cat >"$TMP/source-env.sh" <<ENV
export DESIGN_TMPDIR=$D
export CLAUDE_PLUGIN_ROOT=$FAKE_PLUGIN
ENV

LOG="$TMP/argv.txt"
out=$(CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" DESIGN_TMPDIR="$D" DESIGN_STEP5C_STUB_LOG="$LOG" LARCH_BGJOB_REGISTRY_ROOT="$TMP/registry" \
  "$FAKE_PLUGIN/skills/design/scripts/design-step5c.sh" \
  --session-env-path "$TMP/source-env.sh" --claude-pid $$ --skip-validate -- --public value)
case "$out" in
  BGJOB_STATUS=STARTED\ STEP=design-step5c\ PGID=*) ;;
  *) fail "wrapper stdout must be exactly bgjob STARTED line, got: $out" ;;
esac
[[ "$(sed -n '1p' "$LOG")" == design ]] || fail 'wrapper argv must start with design'
[[ "$(sed -n '2p' "$LOG")" == step5c ]] || fail 'wrapper argv must select step5c'
[[ "$(sed -n '3p' "$LOG")" == --session-env-path ]] || fail 'wrapper argv must pass the session env flag'
[[ "$(sed -n '4p' "$LOG")" == "$TMP/source-env.sh" ]] || fail 'wrapper argv must pass the session env path'
[[ "$(sed -n '5p' "$LOG")" == --claude-pid ]] || fail 'wrapper argv must pass the Claude PID flag'
[[ "$(sed -n '6p' "$LOG")" == "$$" ]] || fail 'wrapper argv must pass the Claude PID'
grep -Fxq -- '--skip-validate' "$LOG" || fail 'wrapper argv must retain --skip-validate'
tail -n 5 "$LOG" | sed -n '1p' | grep -Fxq -- '--public' || fail 'wrapper argv must retain public option'
tail -n 5 "$LOG" | sed -n '2p' | grep -Fxq 'value' || fail 'wrapper argv must retain public value'
tail -n 5 "$LOG" | sed -n '3p' | grep -Fxq -- '--bgjob-child' || fail 'wrapper argv must append bgjob child flag'
tail -n 5 "$LOG" | sed -n '4p' | grep -Fxq -- '--merge-result-env' || fail 'wrapper argv must append merge result flag'
pass 'wrapper launches bgjob adapt and child delegates to scripts/larch.sh design step5c'

grep -Fxq 'PLAN_WRITE_OK=true' "$D/bgjob/design-step5c.result.env" || fail 'bgjob result env must merge Step 5c status rows'
grep -Fxq 'BGJOB_RC=0' "$D/bgjob/design-step5c.result.env" || fail 'bgjob result env must include BGJOB_RC'
pass 'wrapper writes bgjob result env'

cat >"$D/bgjob/design-step5c.result.env" <<'ENV'
BGJOB_RC=7
STEP=design-step5c
STALE_RESULT=true
ENV
stale_result=$(cat "$D/bgjob/design-step5c.result.env")
out=$(CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" DESIGN_TMPDIR="$D" LARCH_BGJOB_REGISTRY_ROOT="$TMP/registry" \
  "$FAKE_PLUGIN/skills/design/scripts/design-step5c.sh" --session-env-path "$TMP/source-env.sh" --claude-pid $$)
case "$out" in
  BGJOB_STATUS=DONE*) ;;
  *) fail "ordinary duplicate must reattach the completed result, got: $out" ;;
esac
new_result=$(cat "$D/bgjob/design-step5c.result.env")
[ "$new_result" = "$stale_result" ] || fail 'ordinary duplicate must preserve the terminal result env'
pass 'ordinary duplicate reattaches without relaunch'

out=$(CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" DESIGN_TMPDIR="$D" LARCH_BGJOB_REGISTRY_ROOT="$TMP/registry" \
  "$FAKE_PLUGIN/skills/design/scripts/design-step5c.sh" --fresh-attempt \
  --session-env-path "$TMP/source-env.sh" --claude-pid $$)
case "$out" in
  BGJOB_STATUS=STARTED\ STEP=design-step5c\ PGID=*) ;;
  *) fail "explicit retry must start a fresh bgjob, got: $out" ;;
esac
grep -Fxq 'BGJOB_RC=0' "$D/bgjob/design-step5c.result.env" || fail 'fresh retry result env must contain the new bgjob result'
pass 'explicit retry replaces the completed result'

for refusal in validator-defects oversize-no-override missing-invariant-assessment; do
  cat >"$D/bgjob/design-step5c.result.env" <<'ENV'
BGJOB_RC=7
STEP=design-step5c
STALE_RESULT=true
ENV
  out=$(CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" DESIGN_TMPDIR="$D" DESIGN_STEP5C_STUB_REFUSAL="$refusal" LARCH_BGJOB_REGISTRY_ROOT="$TMP/registry" \
    "$FAKE_PLUGIN/skills/design/scripts/design-step5c.sh" --fresh-attempt \
    --session-env-path "$TMP/source-env.sh" --claude-pid $$)
  case "$out" in
    BGJOB_STATUS=STARTED\ STEP=design-step5c\ PGID=*) ;;
    *) fail "fresh refusal retry must start a replacement bgjob, got: $out" ;;
  esac
  grep -Fxq 'BGJOB_RC=0' "$D/bgjob/design-step5c.result.env" || fail "fresh $refusal retry must publish a merged result"
  grep -Fxq "PUBLISH_REFUSE_REASON=$refusal" "$D/bgjob/design-step5c.result.env" || fail "fresh $refusal retry must replace stale rows with refusal rows"
  if grep -Fxq 'STALE_RESULT=true' "$D/bgjob/design-step5c.result.env"; then
    fail "fresh $refusal retry must not retain stale result rows"
  fi
done
pass 'fresh refusal retries replace completed results with merged rows'

printf 'PASS: test-design-step5c.sh\n'
