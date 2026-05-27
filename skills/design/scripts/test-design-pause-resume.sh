#!/usr/bin/env bash
# Offline harness for /design pause save/load helpers.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SAVE="$REPO_ROOT/scripts/design-pause-save.sh"
LOAD="$REPO_ROOT/scripts/design-pause-load.sh"
NBW="$REPO_ROOT/scripts/named-block-write.sh"
WDCE="$REPO_ROOT/scripts/write-design-current-env.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[[ -x "$SAVE" && -x "$LOAD" && -x "$NBW" && -x "$WDCE" ]] || fail "pause scripts are not executable"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-design-pause.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

BODY_FILE="$TMP/issue-body.md"
EDIT_CAPTURE="$TMP/edit-body.md"
SNAPSHOT_ROOT="$TMP/snapshot"
FETCH_LOG="$TMP/fetch.log"
export BODY_FILE EDIT_CAPTURE SNAPSHOT_ROOT FETCH_LOG

STUB="$TMP/stub"
mkdir -p "$STUB"
REAL_GIT=$(command -v git)

cat >"$STUB/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == "repo" && "$2" == "view" ]]; then
  printf '%s\n' 'owner/repo'
  exit 0
fi
if [[ "$1" == "issue" && "$2" == "view" ]]; then
  python3 - <<'PY'
import json, os
with open(os.environ["BODY_FILE"], "r", encoding="utf-8") as fh:
    print(json.dumps({"body": fh.read()}))
PY
  exit 0
fi
if [[ "$1" == "issue" && "$2" == "edit" ]]; then
  if [[ "${GH_EDIT_FAIL:-0}" == "1" ]]; then
    echo "stub gh issue edit forced failure" >&2
    exit 97
  fi
  prev=""
  for arg in "$@"; do
    if [[ "$prev" == "--body-file" ]]; then
      cp "$arg" "$BODY_FILE"
      cp "$arg" "$EDIT_CAPTURE"
      exit 0
    fi
    [[ "$arg" == "--body-file" ]] && prev="--body-file"
  done
  exit 2
fi
echo "unhandled gh $*" >&2
exit 2
GH
chmod +x "$STUB/gh"

cat >"$STUB/git" <<GIT
#!/usr/bin/env bash
set -euo pipefail
if [[ "\${1:-}" == "rev-parse" ]]; then
  printf '%s\n' "$TMP/repo"
  exit 0
fi
if [[ "\${1:-}" == "symbolic-ref" ]]; then
  printf '%s\n' 'refs/remotes/origin/main'
  exit 0
fi
if [[ "\${1:-}" == "check-ref-format" ]]; then
  exec "$REAL_GIT" "\$@"
fi
if [[ "\${1:-}" == "-C" ]]; then
  shift 2
  case "\${1:-}" in
    rev-parse) printf '%s\n' "$TMP/repo"; exit 0 ;;
    symbolic-ref) printf '%s\n' 'refs/remotes/origin/main'; exit 0 ;;
    fetch) printf '%s\n' "\$*" >>"$FETCH_LOG"; exit 0 ;;
    show-ref)
      if [[ "\${2:-}" == "--verify" && "\${3:-}" == "--quiet" && "\${4:-}" == "refs/heads/larch-log-design-recovery-RUNPAUSE1" ]]; then
        exit 0
      fi
      exit 1
      ;;
    archive)
      ref="\$2"
      path="\$3"
      run="\${path#larch-logs/design/}"
      run="\${run%/}"
      tar -C "$SNAPSHOT_ROOT" -cf - "larch-logs/design/\$run"
      exit 0
      ;;
  esac
fi
exec "$REAL_GIT" "\$@"
GIT
chmod +x "$STUB/git"

cat >"$STUB/publish" <<'PUB'
#!/usr/bin/env bash
set -euo pipefail
design_tmpdir=""
run_id=""
issue=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --design-tmpdir) design_tmpdir="$2"; shift 2 ;;
    --run-id) run_id="$2"; shift 2 ;;
    --issue) issue="$2"; shift 2 ;;
    *) shift ;;
  esac
done
mkdir -p "$SNAPSHOT_ROOT/larch-logs/design/$run_id"
cp -R "$design_tmpdir"/. "$SNAPSHOT_ROOT/larch-logs/design/$run_id/"
printf '{"run_id":"%s","issue_number":"%s"}\n' "$run_id" "$issue" >"$SNAPSHOT_ROOT/larch-logs/design/$run_id/manifest.json"
case "${PUBLISH_MODE:-ok}" in
  ok) printf 'PUBLISH_OK=true\nPR_NUMBER=1\nPR_URL=https://example.test/pull/1\n' ;;
  recovery) printf 'PUBLISH_OK=false\nPR_NUMBER=1\nPR_URL=https://example.test/pull/1\nRECOVERY_BRANCH=larch-log-design-%s\n' "$run_id" ;;
  local-recovery) printf 'PUBLISH_OK=false\nPR_NUMBER=\nPR_URL=\nRECOVERY_BRANCH=larch-log-design-recovery-%s\n' "$run_id" ;;
  hardfail) printf 'PUBLISH_OK=false\nPR_NUMBER=\nPR_URL=\n' ;;
esac
PUB
chmod +x "$STUB/publish"

export PATH="$STUB:$PATH"
export LARCH_DESIGN_LOG_PUBLISH="$STUB/publish"
mkdir -p "$TMP/repo"

make_design_tmpdir() {
  local d="$1"
  mkdir -p "$d/.completed"
  : >"$d/.completed/step-0c"
  printf 'export SESSION_ID=RUNPAUSE1\n' >"$d/source-env.sh"
  printf '{"run_id":"RUNPAUSE1","issue_number":"9"}\n' >"$d/manifest.json"
  printf 'plan\n' >"$d/plan.txt"
  printf '{"design_classification":"SIMPLE","brainstorm_requested":false}\n' >"$d/run-params.json"
}

echo "=== clean save/load round trip ==="
DESIGN="$TMP/design1"
make_design_tmpdir "$DESIGN"
: >"$DESIGN/.completed/step-1c"
printf 'issue body\n' >"$BODY_FILE"
out=$(bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo owner/repo)
[[ "$out" == *"PAUSE_OK=true"* ]] || fail "save failed: $out"
[[ "$out" == *"STEP=1d"* ]] || fail "expected registry-order STEP=1d: $out"
grep -Fq '<!-- larch:design-pause:start -->' "$BODY_FILE" || fail "pause marker missing"
grep -Fq 'ISSUE_NUMBER=9' "$BODY_FILE" || fail "pause marker missing issue binding"
grep -Fq 'REPO=owner/repo' "$BODY_FILE" || fail "pause marker missing repo binding"
[[ -f "$SNAPSHOT_ROOT/larch-logs/design/RUNPAUSE1/.completed/step-1c" ]] || fail ".completed sentinel not staged"

RESTORE="$TMP/restore1"
out_load=$(bash "$LOAD" --design-tmpdir "$RESTORE" --issue 9 --repo owner/repo)
[[ "$out_load" == *"LOAD_OK=true"* ]] || fail "load failed: $out_load"
[[ "$out_load" == *"STEP=1d"* ]] || fail "load step mismatch: $out_load"
[[ -f "$RESTORE/plan.txt" && -f "$RESTORE/run-params.json" && -f "$RESTORE/pause-state.txt" ]] || fail "restored root artifacts missing"
[[ -f "$RESTORE/.resume-loaded" ]] || fail "resume sentinel missing after restore"
grep -Fq '<!-- larch:design-pause:start -->' "$BODY_FILE" || fail "marker should remain until terminal cleanup"
HOME="$TMP/home" bash "$WDCE" --output "$RESTORE/source-env.sh" --design-tmpdir "$RESTORE" --session-id RUNPAUSE1 --issue-number 9 --claude-pid 12345 >/dev/null
grep -Fq 'export ISSUE_NUMBER=9' "$RESTORE/source-env.sh" || fail "issue refresh missing after restore"

echo "=== restore install failure keeps marker ==="
make_design_tmpdir "$DESIGN"
printf 'body install fail\n' >"$BODY_FILE"
bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo owner/repo >/dev/null
RESTORE_FAIL="$TMP/restore-fail"
mkdir -p "$RESTORE_FAIL"
chmod 500 "$RESTORE_FAIL"
set +e
out_install_fail=$(bash "$LOAD" --design-tmpdir "$RESTORE_FAIL" --issue 9 --repo owner/repo)
rc_install_fail=$?
set -e
chmod 700 "$RESTORE_FAIL"
[[ "$rc_install_fail" == "0" && "$out_install_fail" == *"LOAD_OK=false"* && ( "$out_install_fail" == *"ERROR=tmpdir-create-failed"* || "$out_install_fail" == *"ERROR=restore-install-failed"* ) ]] \
  || fail "restore install failure mismatch: rc=$rc_install_fail out=$out_install_fail"
grep -Fq '<!-- larch:design-pause:start -->' "$BODY_FILE" || fail "restore install failure should keep marker"

echo "=== multi-sentinel registry order and multi-cycle idempotency ==="
DESIGN_MULTI="$TMP/design-multi"
make_design_tmpdir "$DESIGN_MULTI"
: >"$DESIGN_MULTI/.completed/step-1c"
: >"$DESIGN_MULTI/.completed/step-1d"
printf 'issue body multi\n' >"$BODY_FILE"
out_multi=$(bash "$SAVE" --design-tmpdir "$DESIGN_MULTI" --issue 9 --repo owner/repo)
[[ "$out_multi" == *"STEP=1d.5"* ]] || fail "expected next step 1d.5 with multiple sentinels: $out_multi"
[[ -f "$SNAPSHOT_ROOT/larch-logs/design/RUNPAUSE1/.completed/step-1d" ]] || fail "multi-sentinel staging missed step-1d"
RESTORE_MULTI="$TMP/restore-multi"
out_multi_load=$(bash "$LOAD" --design-tmpdir "$RESTORE_MULTI" --issue 9 --repo owner/repo)
[[ "$out_multi_load" == *"LOAD_OK=true"* && "$out_multi_load" == *"STEP=1d.5"* ]] || fail "multi-sentinel load mismatch: $out_multi_load"
printf 'issue body cycle\n' >"$BODY_FILE"
out_cycle=$(bash "$SAVE" --design-tmpdir "$RESTORE_MULTI" --issue 9 --repo owner/repo)
[[ "$out_cycle" == *"PAUSE_OK=true"* && "$out_cycle" == *"STEP=1d.5"* ]] || fail "multi-cycle save mismatch: $out_cycle"
out_cycle_load=$(bash "$LOAD" --design-tmpdir "$TMP/restore-cycle-2" --issue 9 --repo owner/repo)
[[ "$out_cycle_load" == *"LOAD_OK=true"* && "$out_cycle_load" == *"STEP=1d.5"* ]] || fail "multi-cycle load mismatch: $out_cycle_load"

echo "=== registry order beats sparse later sentinels ==="
DESIGN_REGISTRY="$TMP/design-registry"
make_design_tmpdir "$DESIGN_REGISTRY"
: >"$DESIGN_REGISTRY/.completed/step-1c"
: >"$DESIGN_REGISTRY/.completed/step-2a"
printf 'issue body registry\n' >"$BODY_FILE"
out_registry=$(bash "$SAVE" --design-tmpdir "$DESIGN_REGISTRY" --issue 9 --repo owner/repo)
[[ "$out_registry" == *"STEP=1d"* ]] || fail "expected missing step-1d before sparse later sentinel: $out_registry"
out_registry_load=$(bash "$LOAD" --design-tmpdir "$TMP/restore-registry" --issue 9 --repo owner/repo)
[[ "$out_registry_load" == *"LOAD_OK=true"* && "$out_registry_load" == *"STEP=1d"* ]] || fail "registry-order load mismatch: $out_registry_load"

echo "=== body drift warns and continues ==="
make_design_tmpdir "$DESIGN"
printf 'body before\n' >"$BODY_FILE"
bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo owner/repo >/dev/null
printf '\noperator edit\n' >>"$BODY_FILE"
out_drift=$(bash "$LOAD" --design-tmpdir "$TMP/restore-drift" --issue 9 --repo owner/repo)
[[ "$out_drift" == *"LOAD_OK=true"* && "$out_drift" == *"WARN=body-drift"* ]] || fail "expected body drift warning: $out_drift"
grep -Fq '<!-- larch:design-pause:start -->' "$BODY_FILE" || fail "body-drift restore should keep marker"

echo "=== named block delete + empty content semantics ==="
printf 'x\n<!-- larch:design-pause:start -->\nA\n<!-- larch:design-pause:end -->\ny\n' >"$BODY_FILE"
out_del=$(bash "$NBW" --marker design-pause --delete --issue 9 --repo owner/repo)
[[ "$out_del" == *"MODE=removed"* ]] || fail "delete mode mismatch: $out_del"
out_del_absent=$(bash "$NBW" --marker design-pause --delete --issue 9 --repo owner/repo)
[[ "$out_del_absent" == *"MODE=absent-noop"* ]] || fail "absent delete mode mismatch: $out_del_absent"
empty="$TMP/empty"
: >"$empty"
out_empty=$(bash "$NBW" --marker plan --content-file "$empty" --issue 9 --repo owner/repo)
[[ "$out_empty" == *"MODE=appended"* ]] || fail "empty content should append markers: $out_empty"
grep -Fq '<!-- larch:plan:start -->' "$BODY_FILE" || fail "empty plan markers missing"

echo "=== pause-state redaction keeps secrets out of marker payload ==="
make_design_tmpdir "$DESIGN"
printf 'issue body secret ghp_topsecret1234567890\n' >"$BODY_FILE"
out_redact=$(bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo owner/repo)
[[ "$out_redact" == *"PAUSE_OK=true"* ]] || fail "redaction save failed: $out_redact"
marker_payload=$(awk '
  /<!-- larch:design-pause:start -->/ { in_block=1; next }
  /<!-- larch:design-pause:end -->/ { in_block=0; exit }
  in_block { print }
' "$BODY_FILE")
[[ "$marker_payload" != *"ghp_topsecret1234567890"* ]] || fail "marker payload leaked secret body content"
grep -Fq 'BODY_HASH=' "$DESIGN/pause-state.txt" || fail "pause-state missing body hash"
! grep -Fq 'ghp_topsecret1234567890' "$DESIGN/pause-state.txt" || fail "pause-state leaked secret body content"

echo "=== malformed marker tokens ==="
for token_body in multiple-start multiple-end start-without-end end-without-start end-before-start; do
  case "$token_body" in
    multiple-start) printf '<!-- larch:design-pause:start -->\na\n<!-- larch:design-pause:end -->\n<!-- larch:design-pause:start -->\nb\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE" ;;
    multiple-end) printf '<!-- larch:design-pause:start -->\na\n<!-- larch:design-pause:end -->\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE" ;;
    start-without-end) printf '<!-- larch:design-pause:start -->\na\n' >"$BODY_FILE" ;;
    end-without-start) printf '<!-- larch:design-pause:end -->\n' >"$BODY_FILE" ;;
    end-before-start) printf '<!-- larch:design-pause:end -->\n<!-- larch:design-pause:start -->\n' >"$BODY_FILE" ;;
  esac
  set +e
  bad_out=$(bash "$NBW" --marker design-pause --delete --issue 9 --repo owner/repo)
  rc=$?
  set -e
  [[ "$rc" == "1" && "$bad_out" == *"MALFORMED=$token_body"* ]] || fail "malformed $token_body mismatch: rc=$rc out=$bad_out"
done

echo "=== recovery branch and hard publish failure ==="
make_design_tmpdir "$DESIGN"
printf 'body\n' >"$BODY_FILE"
out_rec=$(PUBLISH_MODE=recovery bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo owner/repo)
[[ "$out_rec" == *"PAUSE_OK=true"* ]] || fail "recovery save should write marker: $out_rec"
[[ "$out_rec" == *"WARN=recovery-branch-only"* ]] || fail "recovery save should warn on recovery-only publish: $out_rec"
[[ "$out_rec" == *"LOG_RECOVERY_BRANCH=larch-log-design-RUNPAUSE1"* ]] || fail "recovery save should surface recovery branch: $out_rec"
grep -Fq 'LOG_RECOVERY_BRANCH=larch-log-design-RUNPAUSE1' "$BODY_FILE" || fail "recovery branch missing from marker"
: >"$FETCH_LOG"
bash "$LOAD" --design-tmpdir "$TMP/restore-recovery" --issue 9 --repo owner/repo >/dev/null
grep -Fq 'fetch origin larch-log-design-RUNPAUSE1' "$FETCH_LOG" || fail "load did not fetch recovery branch"

make_design_tmpdir "$DESIGN"
printf 'body\n' >"$BODY_FILE"
out_hard=$(PUBLISH_MODE=hardfail bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo owner/repo)
[[ "$out_hard" == *"PAUSE_OK=false"* && "$out_hard" == *"ERROR=publish-and-recovery-failed"* ]] || fail "hard publish failure mismatch: $out_hard"
! grep -Fq 'larch:design-pause' "$BODY_FILE" || fail "hard failure must not write marker"

make_design_tmpdir "$DESIGN"
printf 'body\n' >"$BODY_FILE"
out_local_recovery=$(PUBLISH_MODE=local-recovery bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo owner/repo)
[[ "$out_local_recovery" == *"LOG_RECOVERY_BRANCH=larch-log-design-recovery-RUNPAUSE1"* ]] || fail "local recovery branch should surface to caller: $out_local_recovery"
[[ "$out_local_recovery" == *"PAUSE_OK=true"* && "$out_local_recovery" == *"WARN=recovery-branch-only"* ]] || fail "local recovery publish should stay resumable: $out_local_recovery"
grep -Fq 'LOG_RECOVERY_BRANCH=larch-log-design-recovery-RUNPAUSE1' "$BODY_FILE" || fail "local recovery branch missing from marker"
: >"$FETCH_LOG"
bash "$LOAD" --design-tmpdir "$TMP/restore-local-recovery" --issue 9 --repo owner/repo >/dev/null
! grep -Fq 'fetch origin larch-log-design-recovery-RUNPAUSE1' "$FETCH_LOG" || fail "local recovery load should not fetch origin"

echo "=== mismatched recovery branch and jq missing fail closed ==="
make_design_tmpdir "$DESIGN"
printf 'body\n' >"$BODY_FILE"
PUBLISH_MODE=recovery bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo owner/repo >/dev/null
python3 - <<'PY' "$BODY_FILE"
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace("LOG_RECOVERY_BRANCH=larch-log-design-RUNPAUSE1", "LOG_RECOVERY_BRANCH=larch-log-design-OTHER"))
PY
out_bad_branch=$(bash "$LOAD" --design-tmpdir "$TMP/restore-bad-branch" --issue 9 --repo owner/repo)
[[ "$out_bad_branch" == *"LOAD_OK=false"* && "$out_bad_branch" == *"ERROR=invalid-recovery-branch"* ]] || fail "bad recovery branch mismatch: $out_bad_branch"

# Reset body to a valid recovery branch for the jq-missing test (the bad-branch
# test above modified BODY_FILE to have an invalid ref; restore it first).
make_design_tmpdir "$DESIGN"
printf 'body\n' >"$BODY_FILE"
PUBLISH_MODE=recovery bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo owner/repo >/dev/null
# Add a broken jq stub so command -v jq finds it but running it exits non-zero.
cat >"$STUB/jq" <<'JQ'
#!/bin/sh
exit 127
JQ
chmod +x "$STUB/jq"
out_no_jq=$(PATH="$STUB:/bin:/usr/bin:/usr/sbin:/sbin" bash "$LOAD" --design-tmpdir "$TMP/restore-no-jq" --issue 9 --repo owner/repo)
rm -f "$STUB/jq"
[[ "$out_no_jq" == *"LOAD_OK=false"* && "$out_no_jq" == *"ERROR=jq-missing"* ]] || fail "jq missing mismatch: $out_no_jq"

echo "=== tmpdir unset fails closed ==="
out_tmpdir_unset=$(bash "$SAVE" --issue 9 --repo owner/repo)
[[ "$out_tmpdir_unset" == *"PAUSE_OK=false"* && "$out_tmpdir_unset" == *"ERROR=tmpdir-unset"* ]] \
  || fail "tmpdir unset mismatch: $out_tmpdir_unset"

echo "=== prelude pause-requested path ==="
PRELUDE_ROOT="$TMP/prelude-root"
PRELUDE_HOME="$TMP/prelude-home"
PRELUDE_PLUGIN="$PRELUDE_ROOT/plugin"
PRELUDE_DESIGN="$PRELUDE_ROOT/design"
mkdir -p "$PRELUDE_PLUGIN/scripts" "$PRELUDE_DESIGN" "$PRELUDE_HOME/.cache/larch/sessions"
cat >"$PRELUDE_PLUGIN/scripts/design-pause-save.sh" <<'PRELUDE'
#!/usr/bin/env bash
set -euo pipefail
printf 'PRELUDE_SAVE=%s\n' "$*"
PRELUDE
chmod +x "$PRELUDE_PLUGIN/scripts/design-pause-save.sh"
cat >"$PRELUDE_HOME/.cache/larch/sessions/current-design-env-$$.sh" <<PRELUDEENV
export DESIGN_TMPDIR="$PRELUDE_DESIGN"
export CLAUDE_PLUGIN_ROOT="$PRELUDE_PLUGIN"
export ISSUE_NUMBER=9
export REPO=owner/repo
PRELUDEENV
: >"$PRELUDE_DESIGN/.pause-requested"
prelude_out=$(
  HOME="$PRELUDE_HOME" bash -c '
    [ -f ~/.cache/larch/sessions/current-design-env-$PPID.sh ] && source ~/.cache/larch/sessions/current-design-env-$PPID.sh
    [ -f "$DESIGN_TMPDIR/.pause-requested" ] && LARCH_PAUSE_REQUIRE_SUCCESS=1 exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
    printf "PRELUDE_CONTINUED\n"
  '
)
[[ "$prelude_out" == *"PRELUDE_SAVE=--design-tmpdir $PRELUDE_DESIGN --issue 9 --repo owner/repo"* ]] || fail "prelude did not exec save helper with repo binding: $prelude_out"
[[ "$prelude_out" != *"PRELUDE_CONTINUED"* ]] || fail "prelude should exec instead of continuing"

cat >"$PRELUDE_PLUGIN/scripts/design-pause-save.sh" <<'PRELUDEFAIL'
#!/usr/bin/env bash
set -euo pipefail
printf 'PAUSE_OK=false\nERROR=stubbed-failure\n'
exit "${LARCH_PAUSE_REQUIRE_SUCCESS:-0}"
PRELUDEFAIL
chmod +x "$PRELUDE_PLUGIN/scripts/design-pause-save.sh"
set +e
HOME="$PRELUDE_HOME" bash -c '
  [ -f ~/.cache/larch/sessions/current-design-env-$PPID.sh ] && source ~/.cache/larch/sessions/current-design-env-$PPID.sh
  [ -f "$DESIGN_TMPDIR/.pause-requested" ] && LARCH_PAUSE_REQUIRE_SUCCESS=1 exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
  printf "PRELUDE_CONTINUED\n"
' >/dev/null
prelude_fail_rc=$?
set -e
[[ "$prelude_fail_rc" == "1" ]] || fail "prelude should fail closed when pause save returns PAUSE_OK=false"

echo "=== value validation and missing artifact ==="
printf '<!-- larch:design-pause:start -->\nISSUE_NUMBER=8\nREPO=owner/repo\nRUN_ID=RUNPAUSE1\nSTEP=1d\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_bad_issue=$(bash "$LOAD" --design-tmpdir "$TMP/bad-issue" --issue 9 --repo owner/repo)
[[ "$out_bad_issue" == *"ERROR=issue-mismatch"* ]] || fail "issue binding mismatch failed open: $out_bad_issue"
printf '<!-- larch:design-pause:start -->\nISSUE_NUMBER=9\nREPO=other/repo\nRUN_ID=RUNPAUSE1\nSTEP=1d\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_bad_repo=$(bash "$LOAD" --design-tmpdir "$TMP/bad-repo" --issue 9 --repo owner/repo)
[[ "$out_bad_repo" == *"ERROR=repo-mismatch"* ]] || fail "repo binding mismatch failed open: $out_bad_repo"
printf '<!-- larch:design-pause:start -->\nISSUE_NUMBER=9\nREPO=owner/repo\nRUN_ID=../bad\nSTEP=1d\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_bad_run=$(bash "$LOAD" --design-tmpdir "$TMP/bad-run" --issue 9 --repo owner/repo)
[[ "$out_bad_run" == *"LOAD_OK=false"* && "$out_bad_run" == *"ERROR=invalid-run-id"* ]] || fail "bad run validation mismatch: $out_bad_run"
printf '<!-- larch:design-pause:start -->\nISSUE_NUMBER=9\nREPO=owner/repo\nRUN_ID=RUNPAUSE1\nSTEP=nope\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_bad_step=$(bash "$LOAD" --design-tmpdir "$TMP/bad-step" --issue 9 --repo owner/repo)
[[ "$out_bad_step" == *"ERROR=invalid-step"* ]] || fail "bad step validation mismatch: $out_bad_step"
printf '<!-- larch:design-pause:start -->\nISSUE_NUMBER=9\nREPO=owner/repo\nRUN_ID=RUNPAUSE1\nSTEP=1d\nLOG_RECOVERY_BRANCH=badbranch\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_bad_branch=$(bash "$LOAD" --design-tmpdir "$TMP/bad-branch" --issue 9 --repo owner/repo)
[[ "$out_bad_branch" == *"ERROR=invalid-recovery-branch"* ]] || fail "bad branch validation mismatch: $out_bad_branch"

rm -f "$SNAPSHOT_ROOT/larch-logs/design/RUNPAUSE1/plan.txt"
printf '<!-- larch:design-pause:start -->\nISSUE_NUMBER=9\nREPO=owner/repo\nRUN_ID=RUNPAUSE1\nSTEP=1d\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_missing=$(bash "$LOAD" --design-tmpdir "$TMP/missing" --issue 9 --repo owner/repo)
[[ "$out_missing" == *"LOAD_OK=true"* && "$out_missing" == *"STEP=1d"* ]] || fail "early-step restore should not require plan.txt: $out_missing"

printf '<!-- larch:design-pause:start -->\nISSUE_NUMBER=9\nREPO=owner/repo\nRUN_ID=RUNPAUSE1\nSTEP=3\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_missing_plan_late=$(bash "$LOAD" --design-tmpdir "$TMP/missing-plan-late" --issue 9 --repo owner/repo)
[[ "$out_missing_plan_late" == *"ERROR=missing-restored-artifact"* ]] || fail "late-step restore should require plan.txt: $out_missing_plan_late"

printf '<!-- larch:design-pause:start -->\nISSUE_NUMBER=9\nREPO=owner/repo\nRUN_ID=RUNPAUSE1\nSESSION_ID=RUNPAUSE1\nTIER=SIMPLE\nBRAINSTORM_DONE=true\nSTEP=1d\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_valid_marker=$(bash "$LOAD" --design-tmpdir "$TMP/valid-marker-fields" --issue 9 --repo owner/repo)
[[ "$out_valid_marker" == *"LOAD_OK=true"* && "$out_valid_marker" == *"SESSION_ID=RUNPAUSE1"* && "$out_valid_marker" == *"TIER=SIMPLE"* && "$out_valid_marker" == *"BRAINSTORM_DONE=true"* ]] \
  || fail "valid marker fields mismatch: $out_valid_marker"
printf '<!-- larch:design-pause:start -->\nISSUE_NUMBER=9\nREPO=owner/repo\nRUN_ID=RUNPAUSE1\nSESSION_ID=OTHER\nSTEP=1d\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_bad_session=$(bash "$LOAD" --design-tmpdir "$TMP/bad-session" --issue 9 --repo owner/repo)
[[ "$out_bad_session" == *"ERROR=invalid-session-id"* ]] || fail "bad session validation mismatch: $out_bad_session"
printf '<!-- larch:design-pause:start -->\nISSUE_NUMBER=9\nREPO=owner/repo\nRUN_ID=RUNPAUSE1\nTIER=bad\nSTEP=1d\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_bad_tier=$(bash "$LOAD" --design-tmpdir "$TMP/bad-tier" --issue 9 --repo owner/repo)
[[ "$out_bad_tier" == *"ERROR=invalid-tier"* ]] || fail "bad tier validation mismatch: $out_bad_tier"
printf '<!-- larch:design-pause:start -->\nISSUE_NUMBER=9\nREPO=owner/repo\nRUN_ID=RUNPAUSE1\nBRAINSTORM_DONE=maybe\nSTEP=1d\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_bad_brainstorm=$(bash "$LOAD" --design-tmpdir "$TMP/bad-brainstorm" --issue 9 --repo owner/repo)
[[ "$out_bad_brainstorm" == *"ERROR=invalid-brainstorm-done"* ]] || fail "bad brainstorm validation mismatch: $out_bad_brainstorm"

echo "=== unloadable snapshot clears marker ==="
make_design_tmpdir "$DESIGN"
printf 'body\n' >"$BODY_FILE"
bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo owner/repo >/dev/null
rm -rf "$SNAPSHOT_ROOT/larch-logs/design/RUNPAUSE1"
FAIL_RESTORE="$TMP/unloadable-restore"
mkdir -p "$FAIL_RESTORE"
out_unloadable=$(bash "$LOAD" --design-tmpdir "$FAIL_RESTORE" --issue 9 --repo owner/repo)
[[ "$out_unloadable" == *"ERROR=snapshot-extract-failed"* ]] || fail "unloadable snapshot mismatch: $out_unloadable"
! grep -Fq '<!-- larch:design-pause:start -->' "$BODY_FILE" || fail "unloadable snapshot should clear marker"
! [[ -f "$FAIL_RESTORE/.resume-loaded" ]] || fail "unloadable snapshot should not install resume sentinel"

echo "=== marker name validation ==="
set +e
bad_marker=$(bash "$NBW" --marker BAD/NAME --delete --issue 9 --repo owner/repo 2>/dev/null)
bad_marker_rc=$?
set -e
[[ "$bad_marker_rc" == "1" ]] || fail "bad marker should exit 1: $bad_marker"

echo "All assertions passed."
