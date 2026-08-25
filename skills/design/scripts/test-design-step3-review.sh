#!/usr/bin/env bash
# test-design-step3-review.sh — Step 3 bgjob reporting contract checks.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
unset PYTHONPATH
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
RUST_OWNER="$ROOT/crates/larch-cli/src/plan_review_commands.rs"
export LARCH_BINARY="${LARCH_BINARY:-$ROOT/target/debug/larch}"
WRAPPER="$ROOT/skills/design/scripts/design-step3-review.sh"
SKILL_MD="$ROOT/skills/design/SKILL.md"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

command grep -Fq 'bgjob write-merge-result-env' "$WRAPPER" || fail 'wrapper must publish through the Rust merge-result writer'
if grep -Fq 'PYTHONPATH=' "$WRAPPER" || grep -Fq 'python3 -' "$WRAPPER"; then
  fail 'wrapper must not retain an inline Python runtime path'
fi

make_fake_step3_plugin() {
  local dir="$1"
  mkdir -p "$dir/scripts"
  cat >"$dir/scripts/larch.sh" <<'LARCH'
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
  "session require-plugin-root"|"session validate-design-tmpdir") exit 0 ;;
  "bgjob write-merge-result-env") exec "${LARCH_BINARY:?}" "$@" ;;
  "scope-anchor validate") exec "${LARCH_BINARY:?}" "$@" ;;
  "plan-review normalize-status"|"plan-review prelaunch-failure") exec "${LARCH_BINARY:?}" "$@" ;;
  "design pause-save")
    : >"${DESIGN_TMPDIR:?}/.pause-published"
    exit 0
    ;;
  "plan-review run")
    design="$(option_value --design-tmpdir "$@")" || exit 2
    [[ "${FAKE_STEP3_EMPTY:-}" == "1" ]] && exit 0
    {
      printf 'NEXT_ACTION=step3b\n'
      printf 'STEP3_REVIEW_LOOP_STATUS=complete\n'
      printf 'LOOP_STATUS=complete\n'
      printf 'ROUNDS_COMPLETED=1\n'
      printf 'FINAL_ROUND_NUM=1\n'
      printf 'ACCEPTED_COUNT=0\n'
    } >"$design/.step3-review-result.env"
    printf 'STEP3_REVIEW_LOOP_STATUS=complete\n'
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
    clear_path=""
    for ((index = 0; index < ${#args[@]}; index++)); do
      [[ "${args[$index]}" == "--replace-completed-result" ]] && replace=true
      if [[ "${args[$index]}" == "--clear-on-fresh" && $((index + 1)) -lt ${#args[@]} ]]; then
        clear_path="${args[$((index + 1))]}"
      fi
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
    [[ -n "$clear_path" ]] && rm -f "$clear_path"
    if [[ "${FAKE_STEP3_MERGE_DIRECTORY:-}" == "1" ]]; then
      mkdir "$merge"
    else
      : >"$merge"
    fi
    "${command[@]}" --bgjob-child --merge-result-env "$merge" >/dev/null 2>&1
    rc=$?
    [[ "${FAKE_STEP3_EMPTY:-}" == "1" && "$rc" == 0 ]] && rc=1
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
      printf 'BGJOB_STATUS=DEAD\nBGJOB_DIAG=missing-registry\n'
    fi
    exit 0
    ;;
esac
printf 'unexpected larch command: %s\n' "$*" >&2
exit 2
LARCH
  chmod +x "$dir/scripts/larch.sh"
}

wait_for_done() {
  local tmpdir="$1" out_file="$2" plugin_root="$3" waited=0
  while [ "$waited" -lt 50 ]; do
    CLAUDE_PLUGIN_ROOT="$plugin_root" "$plugin_root/scripts/larch.sh" bgjob wait --step design-step3-review --tmpdir "$tmpdir" --max-wait-s 0 >"$out_file"
    if grep -Fq 'BGJOB_STATUS=DONE' "$out_file" || grep -Fq 'BGJOB_STATUS=DEAD' "$out_file"; then
      return 0
    fi
    sleep 0.1
    waited=$((waited + 1))
  done
  return 1
}

grep -Fq 'SUMMARY_OUTCOME=failed-postplan' "$RUST_OWNER" || fail 'failed-postplan outcome not staged'
grep -Fq 'record-escalation' "$RUST_OWNER" || fail 'record-escalation call missing'
grep -Fq -- 'step3-review' "$RUST_OWNER" || fail 'record-escalation site missing'
grep -Fq 'main-agent-vote-required' "$RUST_OWNER" || fail 'escalation/degradation status set missing'
grep -Fq 'STEP3_NORMALIZE_ALLOW_KEYS' "$RUST_OWNER" || fail 'normalizer must use the shared result key allowlist'
grep -Fq 'design-step3-review.result.env' "$RUST_OWNER" || fail 'normalizer must prefer bgjob Step 3 result env'
grep -Fq 'bgjob/design-step3-review.result.env' "$SKILL_MD" || fail 'SKILL must name bgjob Step 3 result env'
grep -Fq 'BGJOB_RC=0' "$SKILL_MD" || fail 'SKILL must gate Step 3 success on BGJOB_RC=0'
grep -Fq 'bgjob wait --step design-step3-review' "$SKILL_MD" || fail 'SKILL must use chunked bgjob wait for Step 3'
grep -Fq 'scripts/larch.sh" bgjob adapt' "$WRAPPER" || fail 'wrapper must launch through bgjob adapt'
# shellcheck disable=SC2016
grep -Fq -- '--clear-on-fresh' "$WRAPPER" || fail 'wrapper must request fresh-only clearing'
grep -Fq "\"\$DESIGN_TMPDIR/.completed/step-3\"" "$WRAPPER" || fail 'wrapper must name the Step 3 marker for fresh-only clearing'
grep -Fq -- '--bgjob-child|--merge-result-env' "$WRAPPER" || fail 'wrapper must parse the standard adapter child suffix'
if grep -Fq 'step3_review_bgjob_registry_state' "$WRAPPER" || grep -Fq 'bgjob start' "$WRAPPER"; then
  fail 'wrapper must not retain local registry policy or direct bgjob start'
fi
if grep -Fq 'plan-review write-loop-identity' "$WRAPPER" || grep -Fq 'plan-review teardown-loop-identity' "$WRAPPER"; then
  fail 'Step 3 wrapper must not retain legacy loop identity ownership after bgjob migration'
fi
pass 'Step 3 static bgjob contracts are pinned'

D_BGJOB=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob.XXXXXX")
FAKE_PLUGIN="$D_BGJOB/fake-plugin"
make_fake_step3_plugin "$FAKE_PLUGIN"
printf 'anchor\n' >"$D_BGJOB/plan-review-scope-anchor.txt"
mkdir -p "$D_BGJOB/.completed"
printf 'stale\n' >"$D_BGJOB/.completed/step-3"
mkdir -p "$D_BGJOB/registry"
start_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 \
  LARCH_BGJOB_REGISTRY_ROOT="$D_BGJOB/registry" \
  CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" DESIGN_TMPDIR="$D_BGJOB" ISSUE_NUMBER=9 \
  "$WRAPPER" --claude-pid "$$" 2>"$D_BGJOB/start.stderr")
case "$start_out" in
  BGJOB_STATUS=STARTED\ STEP=design-step3-review\ PGID=*) ;;
  *) fail "wrapper stdout must be exactly bgjob STARTED line, got: $start_out stderr=$(cat "$D_BGJOB/start.stderr")" ;;
esac
wait_for_done "$D_BGJOB" "$D_BGJOB/wait.out" "$FAKE_PLUGIN" || fail "bgjob did not finish; last wait=$(cat "$D_BGJOB/wait.out")"
grep -Fxq 'BGJOB_STATUS=DONE' "$D_BGJOB/wait.out" || fail "bgjob wait must finish DONE: $(cat "$D_BGJOB/wait.out")"
grep -Fxq 'BGJOB_RC=0' "$D_BGJOB/wait.out" || fail 'bgjob result must include BGJOB_RC=0'
grep -Fxq 'NEXT_ACTION=step3b' "$D_BGJOB/bgjob/design-step3-review.result.env" || fail 'bgjob result env must include fresh Step 3 KVs'
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=complete' "$D_BGJOB/bgjob/design-step3-review.result.env" || fail 'bgjob result env must include loop status'
test ! -s "$D_BGJOB/.completed/step-3" || fail 'fresh Step 3 start must clear stale completion-marker content'
rm -rf "$D_BGJOB"
pass 'Step 3 wrapper starts bgjob and merges fresh result KVs'

D_DONE=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob-done.XXXXXX")
FAKE_DONE="$D_DONE/fake-plugin"
make_fake_step3_plugin "$FAKE_DONE"
printf 'anchor\n' >"$D_DONE/plan-review-scope-anchor.txt"
mkdir -p "$D_DONE/bgjob"
mkdir -p "$D_DONE/.completed"
: >"$D_DONE/.completed/step-3"
printf '%s\n' 'BGJOB_RC=0' 'BGJOB_ELAPSED_S=0' 'STEP=design-step3-review' 'NEXT_ACTION=step3b' 'STEP3_REVIEW_LOOP_STATUS=complete' 'LOOP_STATUS=complete' 'ROUNDS_COMPLETED=1' >"$D_DONE/bgjob/design-step3-review.result.env"
start_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 \
  LARCH_BGJOB_REGISTRY_ROOT="$D_DONE/registry" \
  CLAUDE_PLUGIN_ROOT="$FAKE_DONE" DESIGN_TMPDIR="$D_DONE" ISSUE_NUMBER=9 \
  "$WRAPPER" --claude-pid "$$" 2>"$D_DONE/start.stderr")
case "$start_out" in
  BGJOB_STATUS=DONE*) ;;
  *) fail "wrapper must rejoin an existing completed result env, got: $start_out stderr=$(cat "$D_DONE/start.stderr")" ;;
esac
grep -Fxq 'NEXT_ACTION=step3b' "$D_DONE/bgjob/design-step3-review.result.env" || fail 'existing completion result env must remain authoritative on restart'
test -f "$D_DONE/.completed/step-3" || fail 'completed Step 3 reattachment must preserve its completion marker'
rm -rf "$D_DONE"
pass 'Step 3 wrapper reuses an existing completed result env instead of relaunching'

D_SESSION=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob-session.XXXXXX")
FAKE_SESSION="$D_SESSION/fake-plugin"
make_fake_step3_plugin "$FAKE_SESSION"
printf 'anchor\n' >"$D_SESSION/plan-review-scope-anchor.txt"
printf 'export DESIGN_TMPDIR=%s\n' "$D_SESSION" >"$D_SESSION/session-env.sh"
start_out=$(env -u DESIGN_TMPDIR -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 \
  LARCH_BGJOB_REGISTRY_ROOT="$D_SESSION/registry" \
  CLAUDE_PLUGIN_ROOT="$FAKE_SESSION" ISSUE_NUMBER=9 \
  "$WRAPPER" --claude-pid "$$" --session-env-path "$D_SESSION/session-env.sh" 2>"$D_SESSION/start.stderr")
case "$start_out" in
  BGJOB_STATUS=STARTED\ STEP=design-step3-review\ PGID=*) ;;
  *) fail "session-env launch must start Step 3, got: $start_out stderr=$(cat "$D_SESSION/start.stderr")" ;;
esac
test -f "$D_SESSION/bgjob/design-step3-review.result.env" || fail 'session-env launch must publish a result env'
rm -rf "$D_SESSION"
pass 'Step 3 wrapper resolves session-env launches'

D_RESUME=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob-resume.XXXXXX")
FAKE_RESUME="$D_RESUME/fake-plugin"
make_fake_step3_plugin "$FAKE_RESUME"
printf 'anchor\n' >"$D_RESUME/plan-review-scope-anchor.txt"
mkdir -p "$D_RESUME/bgjob"
printf '%s\n' 'BGJOB_RC=0' 'BGJOB_ELAPSED_S=0' 'STEP=design-step3-review' 'NEXT_ACTION=old-result' 'STEP3_REVIEW_LOOP_STATUS=complete' >"$D_RESUME/bgjob/design-step3-review.result.env"
printf '1\n' >"$D_RESUME/review-round-count.txt"
start_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 \
  LARCH_BGJOB_REGISTRY_ROOT="$D_RESUME/registry" \
  CLAUDE_PLUGIN_ROOT="$FAKE_RESUME" DESIGN_TMPDIR="$D_RESUME" ISSUE_NUMBER=9 \
  "$WRAPPER" --claude-pid "$$" --starting-round 1 --phase awaiting-apply 2>"$D_RESUME/start.stderr")
case "$start_out" in
  BGJOB_STATUS=STARTED\ STEP=design-step3-review\ PGID=*) ;;
  *) fail "resume replacement must start a fresh Step 3 child, got: $start_out stderr=$(cat "$D_RESUME/start.stderr")" ;;
esac
grep -Fxq 'NEXT_ACTION=step3b' "$D_RESUME/bgjob/design-step3-review.result.env" || fail 'resume replacement must replace the completed Step 3 result'
grep -Fxq 'awaiting-apply' "$D_RESUME/.step3-round-1.phase" || fail 'resume replacement must persist its phase before launch'
rm -rf "$D_RESUME"
pass 'Step 3 wrapper replaces completed results on resume'

D_PAUSE=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob-pause.XXXXXX")
D_PAUSE="$(cd "$D_PAUSE" && pwd -P)"
FAKE_PAUSE="$D_PAUSE/fake-plugin"
make_fake_step3_plugin "$FAKE_PAUSE"
printf 'anchor\n' >"$D_PAUSE/plan-review-scope-anchor.txt"
: >"$D_PAUSE/.pause-requested"
mkdir -p "$D_PAUSE/bgjob"
: >"$D_PAUSE/bgjob/design-step3-review.merge.env"
env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 \
  CLAUDE_PLUGIN_ROOT="$FAKE_PAUSE" DESIGN_TMPDIR="$D_PAUSE" ISSUE_NUMBER=9 \
  "$WRAPPER" --claude-pid "$$" --bgjob-child --merge-result-env "$D_PAUSE/bgjob/design-step3-review.merge.env" >"$D_PAUSE/child.out" 2>"$D_PAUSE/child.stderr" || fail "pause child route failed: $(cat "$D_PAUSE/child.stderr")"
test -f "$D_PAUSE/.pause-published" || fail 'pause child route must publish the pause state'
grep -Fxq 'NEXT_ACTION=pause-save' "$D_PAUSE/bgjob/design-step3-review.merge.env" || fail 'pause child route must publish its terminal merge envelope'
grep -Fxq 'PAUSE_OK=true' "$D_PAUSE/bgjob/design-step3-review.merge.env" || fail 'pause child route must mark its merge envelope successful'
rm -rf "$D_PAUSE"
pass 'Step 3 wrapper publishes pause terminal routing'

D_MERGE=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob-merge.XXXXXX")
FAKE_MERGE="$D_MERGE/fake-plugin"
make_fake_step3_plugin "$FAKE_MERGE"
printf 'anchor\n' >"$D_MERGE/plan-review-scope-anchor.txt"
mkdir -p "$D_MERGE/registry"
env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 FAKE_STEP3_MERGE_DIRECTORY=1 \
  LARCH_BGJOB_REGISTRY_ROOT="$D_MERGE/registry" \
  CLAUDE_PLUGIN_ROOT="$FAKE_MERGE" DESIGN_TMPDIR="$D_MERGE" ISSUE_NUMBER=9 \
  "$WRAPPER" --claude-pid "$$" >"$D_MERGE/start.out" 2>"$D_MERGE/start.stderr"
grep -Fxq 'BGJOB_RC=1' "$D_MERGE/bgjob/design-step3-review.result.env" || fail 'merge-publication failure must make the Step 3 child fail'
rm -rf "$D_MERGE"
pass 'Step 3 wrapper propagates merge-publication failures'

D_STALE=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob-stale.XXXXXX")
FAKE_STALE="$D_STALE/fake-plugin"
make_fake_step3_plugin "$FAKE_STALE"
printf 'anchor\n' >"$D_STALE/plan-review-scope-anchor.txt"
printf '%s\n' 'NEXT_ACTION=step3b' 'STEP3_REVIEW_LOOP_STATUS=complete' >"$D_STALE/.step3-review-result.env"
mkdir -p "$D_STALE/registry"
env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 FAKE_STEP3_EMPTY=1 \
  LARCH_BGJOB_REGISTRY_ROOT="$D_STALE/registry" \
  CLAUDE_PLUGIN_ROOT="$FAKE_STALE" DESIGN_TMPDIR="$D_STALE" ISSUE_NUMBER=9 \
  "$WRAPPER" --claude-pid "$$" >"$D_STALE/start.out" 2>"$D_STALE/start.stderr"
wait_for_done "$D_STALE" "$D_STALE/wait.out" "$FAKE_STALE" || fail "stale regression bgjob did not finish; last wait=$(cat "$D_STALE/wait.out")"
if grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=complete' "$D_STALE/bgjob/design-step3-review.result.env"; then
  fail 'stale merge input must not satisfy a fresh child that emitted no Step 3 KVs'
fi
grep -Fxq 'BGJOB_RC=1' "$D_STALE/bgjob/design-step3-review.result.env" || fail 'missing fresh KVs must route to a non-success child rc'
rm -rf "$D_STALE"
pass 'Step 3 wrapper truncates stale merge input before fresh bgjob start'

pass 'Step 3 bgjob wrapper checks passed'
