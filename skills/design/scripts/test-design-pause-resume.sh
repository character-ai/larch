#!/usr/bin/env bash
# Offline harness for /design pause save/load helpers.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SAVE="$REPO_ROOT/scripts/design-pause-save.sh"
LOAD="$REPO_ROOT/scripts/design-pause-load.sh"
NBW="$REPO_ROOT/scripts/named-block-write.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[[ -x "$SAVE" && -x "$LOAD" && -x "$NBW" ]] || fail "pause scripts are not executable"

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
  jq -n --rawfile b "$BODY_FILE" '{body: $b}' | jq -c .
  exit 0
fi
if [[ "$1" == "issue" && "$2" == "edit" ]]; then
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
while [[ $# -gt 0 ]]; do
  case "$1" in
    --design-tmpdir) design_tmpdir="$2"; shift 2 ;;
    --run-id) run_id="$2"; shift 2 ;;
    *) shift ;;
  esac
done
mkdir -p "$SNAPSHOT_ROOT/larch-logs/design/$run_id"
cp -R "$design_tmpdir"/. "$SNAPSHOT_ROOT/larch-logs/design/$run_id/"
case "${PUBLISH_MODE:-ok}" in
  ok) printf 'PUBLISH_OK=true\nPR_NUMBER=1\nPR_URL=https://example.test/pull/1\n' ;;
  recovery) printf 'PUBLISH_OK=false\nPR_NUMBER=1\nPR_URL=https://example.test/pull/1\nRECOVERY_BRANCH=larch-log-design-%s\n' "$run_id" ;;
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
  printf 'export SESSION_ID=RUNPAUSE1\n' >"$d/source-env.sh"
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
[[ -f "$SNAPSHOT_ROOT/larch-logs/design/RUNPAUSE1/.completed/step-1c" ]] || fail ".completed sentinel not staged"

RESTORE="$TMP/restore1"
out_load=$(bash "$LOAD" --design-tmpdir "$RESTORE" --issue 9 --repo owner/repo)
[[ "$out_load" == *"LOAD_OK=true"* ]] || fail "load failed: $out_load"
[[ "$out_load" == *"STEP=1d"* ]] || fail "load step mismatch: $out_load"
[[ -f "$RESTORE/plan.txt" && -f "$RESTORE/run-params.json" && -f "$RESTORE/pause-state.txt" ]] || fail "restored root artifacts missing"
! grep -Fq '<!-- larch:design-pause:start -->' "$BODY_FILE" || fail "marker not deleted"

echo "=== body drift warns and continues ==="
make_design_tmpdir "$DESIGN"
printf 'body before\n' >"$BODY_FILE"
bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo owner/repo >/dev/null
printf '\noperator edit\n' >>"$BODY_FILE"
out_drift=$(bash "$LOAD" --design-tmpdir "$TMP/restore-drift" --issue 9 --repo owner/repo)
[[ "$out_drift" == *"LOAD_OK=true"* && "$out_drift" == *"WARN=body-drift"* ]] || fail "expected body drift warning: $out_drift"

echo "=== named block delete + empty content semantics ==="
printf 'x\n<!-- larch:design-pause:start -->\nA\n<!-- larch:design-pause:end -->\ny\n' >"$BODY_FILE"
out_del=$(bash "$NBW" --marker design-pause --delete --issue 9 --repo owner/repo)
[[ "$out_del" == *"MODE=removed"* ]] || fail "delete mode mismatch: $out_del"
empty="$TMP/empty"
: >"$empty"
out_empty=$(bash "$NBW" --marker plan --content-file "$empty" --issue 9 --repo owner/repo)
[[ "$out_empty" == *"MODE=appended"* ]] || fail "empty content should append markers: $out_empty"
grep -Fq '<!-- larch:plan:start -->' "$BODY_FILE" || fail "empty plan markers missing"

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
grep -Fq 'LOG_RECOVERY_BRANCH=larch-log-design-RUNPAUSE1' "$BODY_FILE" || fail "recovery branch missing from marker"
: >"$FETCH_LOG"
bash "$LOAD" --design-tmpdir "$TMP/restore-recovery" --issue 9 --repo owner/repo >/dev/null
grep -Fq 'fetch origin larch-log-design-RUNPAUSE1' "$FETCH_LOG" || fail "load did not fetch recovery branch"

make_design_tmpdir "$DESIGN"
printf 'body\n' >"$BODY_FILE"
out_hard=$(PUBLISH_MODE=hardfail bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo owner/repo)
[[ "$out_hard" == *"PAUSE_OK=false"* && "$out_hard" == *"ERROR=publish-and-recovery-failed"* ]] || fail "hard publish failure mismatch: $out_hard"
! grep -Fq 'larch:design-pause' "$BODY_FILE" || fail "hard failure must not write marker"

echo "=== value validation and missing artifact ==="
printf '<!-- larch:design-pause:start -->\nRUN_ID=../bad\nSTEP=1d\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_bad_run=$(bash "$LOAD" --design-tmpdir "$TMP/bad-run" --issue 9 --repo owner/repo)
[[ "$out_bad_run" == *"LOAD_OK=false"* && "$out_bad_run" == *"ERROR=invalid-run-id"* ]] || fail "bad run validation mismatch: $out_bad_run"
printf '<!-- larch:design-pause:start -->\nRUN_ID=RUNPAUSE1\nSTEP=nope\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_bad_step=$(bash "$LOAD" --design-tmpdir "$TMP/bad-step" --issue 9 --repo owner/repo)
[[ "$out_bad_step" == *"ERROR=invalid-step"* ]] || fail "bad step validation mismatch: $out_bad_step"
printf '<!-- larch:design-pause:start -->\nRUN_ID=RUNPAUSE1\nSTEP=1d\nLOG_RECOVERY_BRANCH=badbranch\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_bad_branch=$(bash "$LOAD" --design-tmpdir "$TMP/bad-branch" --issue 9 --repo owner/repo)
[[ "$out_bad_branch" == *"ERROR=invalid-recovery-branch"* ]] || fail "bad branch validation mismatch: $out_bad_branch"

rm -f "$SNAPSHOT_ROOT/larch-logs/design/RUNPAUSE1/plan.txt"
printf '<!-- larch:design-pause:start -->\nRUN_ID=RUNPAUSE1\nSTEP=1d\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_missing=$(bash "$LOAD" --design-tmpdir "$TMP/missing" --issue 9 --repo owner/repo)
[[ "$out_missing" == *"ERROR=missing-restored-artifact"* ]] || fail "missing artifact mismatch: $out_missing"

echo "=== marker name validation ==="
set +e
bad_marker=$(bash "$NBW" --marker BAD/NAME --delete --issue 9 --repo owner/repo 2>/dev/null)
bad_marker_rc=$?
set -e
[[ "$bad_marker_rc" == "1" ]] || fail "bad marker should exit 1: $bad_marker"

echo "All assertions passed."
