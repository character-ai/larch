#!/usr/bin/env bash
# test-design-step3b-tail.sh — offline adapter contract for the Step 4 tail.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
unset PYTHONPATH
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/design-step3b-tail.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

command grep -Fq 'bgjob adapt' "$SUBJECT" || fail 'wrapper must delegate through bgjob adapt'
command grep -Fq 'bgjob write-merge-result-env' "$SUBJECT" || fail 'wrapper must publish through the Rust merge-result writer'
command grep -Fq -- '--bgjob-child|--merge-result-env' "$SUBJECT" || fail 'wrapper must parse standard child controls'
if grep -Fq 'PYTHONPATH=' "$SUBJECT" || grep -Fq 'python3 -' "$SUBJECT"; then
  fail 'wrapper must not retain an inline Python runtime path'
fi
if ( command grep -Fq 'bgjob start' "$SUBJECT" ) || ( command grep -Fq 'design_step4_tail_bgjob_registry_state' "$SUBJECT" ); then
  fail 'wrapper must not retain direct start or local registry policy'
fi

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-design-step3b-tail.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
PLUGIN="$TMP/plugin"
mkdir -p "$PLUGIN/scripts" "$PLUGIN/skills/design/scripts"
cp "$SUBJECT" "$PLUGIN/skills/design/scripts/design-step3b-tail.sh"
chmod +x "$PLUGIN/skills/design/scripts/design-step3b-tail.sh"
cat >"$PLUGIN/scripts/larch.sh" <<'SH'
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
  "session require-plugin-root"|"session validate-design-tmpdir"|"timing mark"|"design dialectic-gatec"|"plan-review emit-rejected")
    exit 0
    ;;
  "plan-review preview")
    printf 'preview\n'
    exit 0
    ;;
  "design pause-save")
    design="$(option_value --design-tmpdir "$@")" || exit 2
    : >"$design/.pause-save-complete"
    exit 0
    ;;
  "bgjob write-merge-result-env")
    destination="$(option_value --path "$@")" || exit 2
    tmpdir="$(option_value --tmpdir "$@")" || exit 2
    case "$destination" in "$tmpdir"/*) ;; *) exit 2 ;; esac
    mkdir -p "${destination%/*}"
    : >"$destination"
    while [[ $# -gt 0 ]]; do
      if [[ "$1" == "--row" && $# -gt 1 ]]; then
        printf '%s\n' "$2" >>"$destination"
        shift 2
      else
        shift
      fi
    done
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
    for ((index = 0; index < ${#args[@]}; index++)); do
      if [[ "${args[$index]}" == "--" ]]; then
        command=("${args[@]:$((index + 1))}")
        break
      fi
    done
    [[ ${#command[@]} -gt 0 ]] || exit 2
    bgjob="$tmpdir/bgjob"
    result="$bgjob/$step.result.env"
    merge="$bgjob/$step.merge.env"
    mkdir -p "$bgjob"
    if [[ -f "$result" && ! -L "$result" ]]; then
      printf 'BGJOB_STATUS=DONE\n'
      cat "$result"
      exit 0
    fi
    : >"$merge"
    [[ "${TAIL_PAUSE_RACE:-}" == "1" ]] && : >"$tmpdir/.pause-requested"
    "${command[@]}" --bgjob-child --merge-result-env "$merge" >/dev/null 2>&1
    rc=$?
    {
      printf 'BGJOB_RC=%s\nSTEP=%s\n' "$rc" "$step"
      [[ -f "$merge" && ! -L "$merge" ]] && cat "$merge"
    } >"$result"
    printf 'BGJOB_STATUS=STARTED STEP=%s PGID=12345\n' "$step"
    exit 0
    ;;
esac
printf 'unexpected larch command: %s\n' "$*" >&2
exit 2
SH
chmod +x "$PLUGIN/scripts/larch.sh"

D="$TMP/design"
mkdir -p "$D/.completed" "$TMP/registry"
D="$(cd "$D" && pwd -P)"
: >"$D/.completed/finalize"
printf '{"skip_approve_requested":false}\n' >"$D/run-params.json"
printf 'digest\n' >"$D/dialectic-clarifier-digest.md"
cat >"$TMP/session-env.sh" <<ENV
export DESIGN_TMPDIR=$D
export CLAUDE_PLUGIN_ROOT=$PLUGIN
export ISSUE_NUMBER=42
ENV

out=$(env -u DESIGN_TMPDIR CLAUDE_PLUGIN_ROOT="$PLUGIN" LARCH_BGJOB_REGISTRY_ROOT="$TMP/registry" \
  "$PLUGIN/skills/design/scripts/design-step3b-tail.sh" \
  --session-env-path "$TMP/session-env.sh" --claude-pid $$)
case "$out" in
  BGJOB_STATUS=STARTED\ STEP=design-step4-tail\ PGID=*) ;;
  *) fail "fresh invocation must start through the adapter: $out" ;;
esac
result="$D/bgjob/design-step4-tail.result.env"
command grep -Fxq 'BGJOB_RC=0' "$result" || fail 'successful child result must have BGJOB_RC=0'
command grep -Fxq 'STEP4_STATUS=complete' "$result" || fail 'successful child must publish terminal status'
command grep -Fxq 'SKIP_APPROVE_REQUESTED_GATEC=false' "$result" || fail 'Gate C skip row missing'
command grep -Fxq 'REJECTED_FINDINGS_BEGIN=---LARCH-REJECTED-BEGIN---' "$result" || fail 'rejected-findings opening marker row missing'
command grep -Fxq 'REJECTED_FINDINGS_END=---LARCH-REJECTED-END---' "$result" || fail 'rejected-findings closing marker row missing'
command grep -Fxq "REJECTED_FINDINGS_BODY_PATH=$D/gatec-rejected-findings-framed.md" "$result" || fail 'rejected-findings body path row missing'
command grep -Fxq "GATEC_PREVIEW_PATH=$D/gatec-preview.md" "$result" || fail 'Gate C preview row missing'
command grep -Fxq "DIALECTIC_GATEC_DIGEST_PATH=$D/dialectic-clarifier-digest.md" "$result" || fail 'dialectic digest row missing'
pass 'fresh launcher-only session resolution and Gate C publication work'

out=$(env -u DESIGN_TMPDIR CLAUDE_PLUGIN_ROOT="$PLUGIN" LARCH_BGJOB_REGISTRY_ROOT="$TMP/registry" \
  "$PLUGIN/skills/design/scripts/design-step3b-tail.sh" \
  --session-env-path "$TMP/session-env.sh" --claude-pid $$)
case "$out" in BGJOB_STATUS=DONE*) ;; *) fail "completed result must reattach: $out" ;; esac
pass 'completed result reattaches without relaunch'

rm -f "$result" "$D/.pause-requested" "$D/.pause-save-complete"
out=$(env -u DESIGN_TMPDIR TAIL_PAUSE_RACE=1 CLAUDE_PLUGIN_ROOT="$PLUGIN" LARCH_BGJOB_REGISTRY_ROOT="$TMP/registry" \
  "$PLUGIN/skills/design/scripts/design-step3b-tail.sh" \
  --session-env-path "$TMP/session-env.sh" --claude-pid $$)
case "$out" in BGJOB_STATUS=STARTED*) ;; *) fail "pause-race invocation must start adapter: $out" ;; esac
command grep -Fxq 'BGJOB_RC=0' "$result" || fail 'handled pause race must exit zero'
command grep -Fxq 'STEP4_STATUS=pause-save' "$result" || fail 'handled pause race must publish its terminal route'
pass 'in-flight pause publishes a terminal adapter envelope'

printf 'PASS: test-design-step3b-tail.sh\n'
