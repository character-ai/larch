#!/usr/bin/env bash
# Offline harness for /design pause save/load helpers.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
# shellcheck source=skills/design/scripts/test-step3-orchestrator-fence.sh
source "$REPO_ROOT/skills/design/scripts/test-step3-orchestrator-fence.sh"
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
  rc-ok-false) printf 'PUBLISH_OK=true\nPR_NUMBER=1\nPR_URL=https://example.test/pull/1\n'; exit 1 ;;
  rc-false-recovery) printf 'PUBLISH_OK=false\nPR_NUMBER=1\nPR_URL=https://example.test/pull/1\nRECOVERY_BRANCH=larch-log-design-%s\n' "$run_id"; exit 1 ;;
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
  DESIGN_TMPDIR="$d" LARCH_TIMING_SKILL=design LARCH_TIMING_LEDGER="$d/timing-ledger.tsv" \
    "$REPO_ROOT/scripts/timing-ledger.sh" record-round \
      --skill design --step "Step 3 — plan review" --round 1 --start-s 10 --end-s 15 \
      --accepted 0 --rejected 0 >/dev/null
}

complete_design_steps() {
  local d="$1"
  shift
  mkdir -p "$d/.completed"
  local step
  for step in "$@"; do
    : >"$d/.completed/step-$step"
  done
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
[[ -f "$SNAPSHOT_ROOT/larch-logs/design/RUNPAUSE1/timing-report-final.json" ]] || fail "pause publish must stage fresh timing-report-final.json"

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

echo "=== legacy SIMPLE Step 2a marker resumes at Step 2a.5 ==="
DESIGN_LEGACY_SIMPLE="$TMP/design-legacy-simple-2a"
make_design_tmpdir "$DESIGN_LEGACY_SIMPLE"
complete_design_steps "$DESIGN_LEGACY_SIMPLE" 1c 1d 1d.5 1d.7 1e 2a
printf 'issue body legacy simple 2a\n' >"$BODY_FILE"
out_legacy_simple_2a=$(bash "$SAVE" --design-tmpdir "$DESIGN_LEGACY_SIMPLE" --issue 9 --repo owner/repo)
[[ "$out_legacy_simple_2a" == *"PAUSE_OK=true"* && "$out_legacy_simple_2a" == *"STEP=2a.5"* ]] || fail "old SIMPLE state with step-2a only should resume at Step 2a.5 compatibility guard: $out_legacy_simple_2a"
out_legacy_simple_2a_load=$(bash "$LOAD" --design-tmpdir "$TMP/restore-legacy-simple-2a" --issue 9 --repo owner/repo)
[[ "$out_legacy_simple_2a_load" == *"LOAD_OK=true"* && "$out_legacy_simple_2a_load" == *"STEP=2a.5"* ]] || fail "old SIMPLE step-2a-only load mismatch: $out_legacy_simple_2a_load"
DESIGN_TMPDIR="$DESIGN_LEGACY_SIMPLE" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash -euo pipefail -c '
_design_classification="$("${CLAUDE_PLUGIN_ROOT}/scripts/read-design-classification.sh" "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || printf "%s\n" HARD)"
if [ "$_design_classification" = SIMPLE ]; then
  _simple_artifacts_ok=true
  if ( grep -Fxq "NO_SKETCHES_CLASSIFIED_SIMPLE" "$DESIGN_TMPDIR/approach-synthesis.txt" 2>/dev/null ); then :; else _simple_artifacts_ok=false; fi
  if ( grep -Fxq "NO_CONTESTED_DECISIONS" "$DESIGN_TMPDIR/contested-decisions.md" 2>/dev/null ); then :; else _simple_artifacts_ok=false; fi
  if [ -f "$DESIGN_TMPDIR/dialectic-resolutions.md" ]; then :; else _simple_artifacts_ok=false; fi
  _simple_artifact_conflict=false
  if [ -s "$DESIGN_TMPDIR/approach-synthesis.txt" ] && ! grep -Fxq "NO_SKETCHES_CLASSIFIED_SIMPLE" "$DESIGN_TMPDIR/approach-synthesis.txt" 2>/dev/null; then _simple_artifact_conflict=true; fi
  if [ -s "$DESIGN_TMPDIR/contested-decisions.md" ] && ! grep -Fxq "NO_CONTESTED_DECISIONS" "$DESIGN_TMPDIR/contested-decisions.md" 2>/dev/null; then _simple_artifact_conflict=true; fi
  if [ -s "$DESIGN_TMPDIR/dialectic-resolutions.md" ]; then _simple_artifact_conflict=true; fi
  if [ "$_simple_artifact_conflict" = true ]; then
    printf "%s\n" "**⚠ SIMPLE sentinel repair refused: non-sentinel sketch artifacts already exist. Inspect run-params.json before continuing.**" >&2
    exit 1
  fi
  if [ "$_simple_artifacts_ok" != true ]; then
    set -e
    printf "%s\n" "NO_SKETCHES_CLASSIFIED_SIMPLE" > "$DESIGN_TMPDIR/approach-synthesis.txt"
    printf "%s\n" "NO_CONTESTED_DECISIONS" > "$DESIGN_TMPDIR/contested-decisions.md"
    : > "$DESIGN_TMPDIR/dialectic-resolutions.md"
    mkdir -p "$DESIGN_TMPDIR/.completed"
    : > "$DESIGN_TMPDIR/.completed/step-2a"
    : > "$DESIGN_TMPDIR/.completed/step-2a.5"
  elif [ -f "$DESIGN_TMPDIR/.completed/step-2a" ] && [ ! -f "$DESIGN_TMPDIR/.completed/step-2a.5" ]; then
    mkdir -p "$DESIGN_TMPDIR/.completed"
    : > "$DESIGN_TMPDIR/.completed/step-2a.5"
  fi
fi
'
[[ -f "$DESIGN_LEGACY_SIMPLE/.completed/step-2a.5" ]] || fail "old SIMPLE Step 2a.5 compatibility guard did not write marker"
[[ "$(cat "$DESIGN_LEGACY_SIMPLE/approach-synthesis.txt")" == "NO_SKETCHES_CLASSIFIED_SIMPLE" ]] || fail "old SIMPLE Step 2a.5 compatibility guard did not repair approach sentinel"
[[ "$(cat "$DESIGN_LEGACY_SIMPLE/contested-decisions.md")" == "NO_CONTESTED_DECISIONS" ]] || fail "old SIMPLE Step 2a.5 compatibility guard did not repair contested sentinel"
[[ -f "$DESIGN_LEGACY_SIMPLE/dialectic-resolutions.md" ]] || fail "old SIMPLE Step 2a.5 compatibility guard did not repair dialectic sentinel"

echo "=== SIMPLE Step 2a.5 marker-only repair ==="
DESIGN_SIMPLE_MARKER_ONLY="$TMP/design-simple-marker-only"
make_design_tmpdir "$DESIGN_SIMPLE_MARKER_ONLY"
complete_design_steps "$DESIGN_SIMPLE_MARKER_ONLY" 1c 1d 1d.5 1d.7 1e 2a
printf '%s\n' 'NO_SKETCHES_CLASSIFIED_SIMPLE' >"$DESIGN_SIMPLE_MARKER_ONLY/approach-synthesis.txt"
printf '%s\n' 'NO_CONTESTED_DECISIONS' >"$DESIGN_SIMPLE_MARKER_ONLY/contested-decisions.md"
: >"$DESIGN_SIMPLE_MARKER_ONLY/dialectic-resolutions.md"
printf 'issue body simple marker-only\n' >"$BODY_FILE"
out_simple_marker_only=$(bash "$SAVE" --design-tmpdir "$DESIGN_SIMPLE_MARKER_ONLY" --issue 9 --repo owner/repo)
[[ "$out_simple_marker_only" == *"PAUSE_OK=true"* && "$out_simple_marker_only" == *"STEP=2a.5"* ]] || fail "SIMPLE marker-only fixture should resume at Step 2a.5: $out_simple_marker_only"
out_simple_marker_only_load=$(bash "$LOAD" --design-tmpdir "$TMP/restore-simple-marker-only" --issue 9 --repo owner/repo)
[[ "$out_simple_marker_only_load" == *"LOAD_OK=true"* && "$out_simple_marker_only_load" == *"STEP=2a.5"* ]] || fail "SIMPLE marker-only load mismatch: $out_simple_marker_only_load"
DESIGN_TMPDIR="$DESIGN_SIMPLE_MARKER_ONLY" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash -euo pipefail -c '
_design_classification="$("${CLAUDE_PLUGIN_ROOT}/scripts/read-design-classification.sh" "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || printf "%s\n" HARD)"
if [ "$_design_classification" = SIMPLE ]; then
  _simple_artifacts_ok=true
  if ( grep -Fxq "NO_SKETCHES_CLASSIFIED_SIMPLE" "$DESIGN_TMPDIR/approach-synthesis.txt" 2>/dev/null ); then :; else _simple_artifacts_ok=false; fi
  if ( grep -Fxq "NO_CONTESTED_DECISIONS" "$DESIGN_TMPDIR/contested-decisions.md" 2>/dev/null ); then :; else _simple_artifacts_ok=false; fi
  if [ -f "$DESIGN_TMPDIR/dialectic-resolutions.md" ]; then :; else _simple_artifacts_ok=false; fi
  _simple_artifact_conflict=false
  if [ -s "$DESIGN_TMPDIR/approach-synthesis.txt" ] && ! grep -Fxq "NO_SKETCHES_CLASSIFIED_SIMPLE" "$DESIGN_TMPDIR/approach-synthesis.txt" 2>/dev/null; then _simple_artifact_conflict=true; fi
  if [ -s "$DESIGN_TMPDIR/contested-decisions.md" ] && ! grep -Fxq "NO_CONTESTED_DECISIONS" "$DESIGN_TMPDIR/contested-decisions.md" 2>/dev/null; then _simple_artifact_conflict=true; fi
  if [ -s "$DESIGN_TMPDIR/dialectic-resolutions.md" ]; then _simple_artifact_conflict=true; fi
  if [ "$_simple_artifact_conflict" = true ]; then
    printf "%s\n" "**⚠ SIMPLE sentinel repair refused: non-sentinel sketch artifacts already exist. Inspect run-params.json before continuing.**" >&2
    exit 1
  fi
  if [ "$_simple_artifacts_ok" != true ]; then
    set -e
    printf "%s\n" "NO_SKETCHES_CLASSIFIED_SIMPLE" > "$DESIGN_TMPDIR/approach-synthesis.txt"
    printf "%s\n" "NO_CONTESTED_DECISIONS" > "$DESIGN_TMPDIR/contested-decisions.md"
    : > "$DESIGN_TMPDIR/dialectic-resolutions.md"
    mkdir -p "$DESIGN_TMPDIR/.completed"
    : > "$DESIGN_TMPDIR/.completed/step-2a"
    : > "$DESIGN_TMPDIR/.completed/step-2a.5"
  elif [ -f "$DESIGN_TMPDIR/.completed/step-2a" ] && [ ! -f "$DESIGN_TMPDIR/.completed/step-2a.5" ]; then
    mkdir -p "$DESIGN_TMPDIR/.completed"
    : > "$DESIGN_TMPDIR/.completed/step-2a.5"
  fi
fi
'
[[ -f "$DESIGN_SIMPLE_MARKER_ONLY/.completed/step-2a.5" ]] || fail "SIMPLE marker-only repair did not write Step 2a.5 marker"
[[ "$(cat "$DESIGN_SIMPLE_MARKER_ONLY/approach-synthesis.txt")" == "NO_SKETCHES_CLASSIFIED_SIMPLE" ]] || fail "SIMPLE marker-only repair changed approach sentinel"

echo "=== SIMPLE Step 2a.5 refuses non-sentinel artifacts ==="
DESIGN_SIMPLE_CONFLICT="$TMP/design-simple-conflict"
make_design_tmpdir "$DESIGN_SIMPLE_CONFLICT"
complete_design_steps "$DESIGN_SIMPLE_CONFLICT" 1c 1d 1d.5 1d.7 1e 2a
printf '%s\n' 'real sketch synthesis' >"$DESIGN_SIMPLE_CONFLICT/approach-synthesis.txt"
printf '%s\n' 'NO_CONTESTED_DECISIONS' >"$DESIGN_SIMPLE_CONFLICT/contested-decisions.md"
: >"$DESIGN_SIMPLE_CONFLICT/dialectic-resolutions.md"
set +e
out_simple_conflict=$(DESIGN_TMPDIR="$DESIGN_SIMPLE_CONFLICT" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash -euo pipefail -c '
_design_classification="$("${CLAUDE_PLUGIN_ROOT}/scripts/read-design-classification.sh" "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || printf "%s\n" HARD)"
if [ "$_design_classification" = SIMPLE ]; then
  _simple_artifacts_ok=true
  if ( grep -Fxq "NO_SKETCHES_CLASSIFIED_SIMPLE" "$DESIGN_TMPDIR/approach-synthesis.txt" 2>/dev/null ); then :; else _simple_artifacts_ok=false; fi
  if ( grep -Fxq "NO_CONTESTED_DECISIONS" "$DESIGN_TMPDIR/contested-decisions.md" 2>/dev/null ); then :; else _simple_artifacts_ok=false; fi
  if [ -f "$DESIGN_TMPDIR/dialectic-resolutions.md" ]; then :; else _simple_artifacts_ok=false; fi
  _simple_artifact_conflict=false
  if [ -s "$DESIGN_TMPDIR/approach-synthesis.txt" ] && ! grep -Fxq "NO_SKETCHES_CLASSIFIED_SIMPLE" "$DESIGN_TMPDIR/approach-synthesis.txt" 2>/dev/null; then _simple_artifact_conflict=true; fi
  if [ -s "$DESIGN_TMPDIR/contested-decisions.md" ] && ! grep -Fxq "NO_CONTESTED_DECISIONS" "$DESIGN_TMPDIR/contested-decisions.md" 2>/dev/null; then _simple_artifact_conflict=true; fi
  if [ -s "$DESIGN_TMPDIR/dialectic-resolutions.md" ]; then _simple_artifact_conflict=true; fi
  if [ "$_simple_artifact_conflict" = true ]; then
    printf "%s\n" "**⚠ SIMPLE sentinel repair refused: non-sentinel sketch artifacts already exist. Inspect run-params.json before continuing.**" >&2
    exit 1
  fi
fi
' 2>&1)
rc_simple_conflict=$?
set -e
[[ "$rc_simple_conflict" -ne 0 ]] || fail "SIMPLE conflict repair should exit non-zero"
[[ "$out_simple_conflict" == *"SIMPLE sentinel repair refused"* ]] || fail "SIMPLE conflict warning missing: $out_simple_conflict"
[[ "$(cat "$DESIGN_SIMPLE_CONFLICT/approach-synthesis.txt")" == "real sketch synthesis" ]] || fail "SIMPLE conflict repair clobbered non-sentinel synthesis"

echo "=== HARD zero-sketch sentinel layout does not take SIMPLE marker repair ==="
DESIGN_HARD_SENTINEL="$TMP/design-hard-sentinel"
make_design_tmpdir "$DESIGN_HARD_SENTINEL"
printf '{"design_classification":"HARD","brainstorm_requested":false}\n' >"$DESIGN_HARD_SENTINEL/run-params.json"
complete_design_steps "$DESIGN_HARD_SENTINEL" 1c 1d 1d.5 1d.7 1e 2a
printf '%s\n' 'NO_SKETCHES_CLASSIFIED_SIMPLE' >"$DESIGN_HARD_SENTINEL/approach-synthesis.txt"
printf '%s\n' 'NO_CONTESTED_DECISIONS' >"$DESIGN_HARD_SENTINEL/contested-decisions.md"
: >"$DESIGN_HARD_SENTINEL/dialectic-resolutions.md"
DESIGN_TMPDIR="$DESIGN_HARD_SENTINEL" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash -euo pipefail -c '
_design_classification="$("${CLAUDE_PLUGIN_ROOT}/scripts/read-design-classification.sh" "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || printf "%s\n" HARD)"
if [ "$_design_classification" = SIMPLE ]; then
  : > "$DESIGN_TMPDIR/.completed/step-2a.5"
fi
'
[[ ! -f "$DESIGN_HARD_SENTINEL/.completed/step-2a.5" ]] || fail "HARD sentinel layout must not take SIMPLE marker-only repair"

echo "=== legacy Step 3b marker without finalize resumes at Step 4 ==="
DESIGN_LEGACY_FINALIZE="$TMP/design-legacy-finalize"
make_design_tmpdir "$DESIGN_LEGACY_FINALIZE"
complete_design_steps "$DESIGN_LEGACY_FINALIZE" 1c 1d 1d.5 1d.7 1e 2a 2a.5 2b 2b.5 3 3.5 3.6 3b
[[ ! -f "$DESIGN_LEGACY_FINALIZE/.completed/finalize" ]] || fail "legacy finalize precondition unexpectedly has .completed/finalize"
printf 'issue body legacy finalize\n' >"$BODY_FILE"
out_legacy_finalize=$(bash "$SAVE" --design-tmpdir "$DESIGN_LEGACY_FINALIZE" --issue 9 --repo owner/repo)
[[ "$out_legacy_finalize" == *"PAUSE_OK=true"* && "$out_legacy_finalize" == *"STEP=4"* ]] || fail "old step-3b without finalize should resume at Step 4 compatibility guard: $out_legacy_finalize"
out_legacy_finalize_load=$(bash "$LOAD" --design-tmpdir "$TMP/restore-legacy-finalize" --issue 9 --repo owner/repo)
[[ "$out_legacy_finalize_load" == *"LOAD_OK=true"* && "$out_legacy_finalize_load" == *"STEP=4"* ]] || fail "old step-3b without finalize load mismatch: $out_legacy_finalize_load"
printf '12\n' >"$DESIGN_LEGACY_FINALIZE/diff-lines.txt"
DESIGN_TMPDIR="$DESIGN_LEGACY_FINALIZE" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash -euo pipefail -c '
if [ ! -f "$DESIGN_TMPDIR/.completed/finalize" ]; then
  set +e
  printf "%s\n" "ACTION=FINALIZE" \
    | "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-driver.sh" --design-tmpdir "$DESIGN_TMPDIR"
  _finalize_rc=$?
  set -e
  if [ "$_finalize_rc" -ne 0 ]; then
    printf "%s\n" "**⚠ FINALIZE failed; repair the missing artifact before Step 5.**"
    exit "$_finalize_rc"
  fi
fi
'
[[ -f "$DESIGN_LEGACY_FINALIZE/.completed/finalize" ]] || fail "old Step 4 FINALIZE compatibility guard did not write finalize marker"

DESIGN_LEGACY_FINALIZE_FAIL="$TMP/design-legacy-finalize-fail"
make_design_tmpdir "$DESIGN_LEGACY_FINALIZE_FAIL"
complete_design_steps "$DESIGN_LEGACY_FINALIZE_FAIL" 1c 1d 1d.5 1d.7 1e 2a 2a.5 2b 2b.5 3 3.5 3.6 3b
set +e
out_legacy_finalize_fail=$(DESIGN_TMPDIR="$DESIGN_LEGACY_FINALIZE_FAIL" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash -euo pipefail -c '
if [ ! -f "$DESIGN_TMPDIR/.completed/finalize" ]; then
  set +e
  printf "%s\n" "ACTION=FINALIZE" \
    | "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-driver.sh" --design-tmpdir "$DESIGN_TMPDIR"
  _finalize_rc=$?
  set -e
  if [ "$_finalize_rc" -ne 0 ]; then
    printf "%s\n" "**⚠ FINALIZE failed; repair the missing artifact before Step 5.**"
    exit "$_finalize_rc"
  fi
fi
' 2>&1)
rc_legacy_finalize_fail=$?
set -e
[[ "$rc_legacy_finalize_fail" -ne 0 ]] || fail "old Step 4 FINALIZE failure guard should exit non-zero"
[[ "$out_legacy_finalize_fail" == *"**⚠ FINALIZE failed; repair the missing artifact before Step 5.**"* ]] || fail "old Step 4 FINALIZE failure warning missing: $out_legacy_finalize_fail"

echo "=== step 3.6 and gate B bypass pause resume ==="
DESIGN_36="$TMP/design-36"
make_design_tmpdir "$DESIGN_36"
complete_design_steps "$DESIGN_36" 1c 1d 1d.5 1d.7 1e 2a 2a.5 2b 2b.5 3 3.5
printf 'issue body 36\n' >"$BODY_FILE"
out_36=$(bash "$SAVE" --design-tmpdir "$DESIGN_36" --issue 9 --repo owner/repo)
[[ "$out_36" == *"PAUSE_OK=true"* && "$out_36" == *"STEP=3.6"* ]] || fail "expected step 3.6 after step-3.5: $out_36"
out_36_load=$(bash "$LOAD" --design-tmpdir "$TMP/restore-36" --issue 9 --repo owner/repo)
[[ "$out_36_load" == *"LOAD_OK=true"* && "$out_36_load" == *"STEP=3.6"* ]] || fail "step 3.6 load mismatch: $out_36_load"

DESIGN_GATE_B="$TMP/design-gate-b-bypass"
make_design_tmpdir "$DESIGN_GATE_B"
[[ ! -f "$DESIGN_GATE_B/.completed/step-3" ]] || fail "gate B bypass empty-state precondition unexpectedly has step-3"
[[ ! -f "$DESIGN_GATE_B/.completed/step-3.5" ]] || fail "gate B bypass empty-state precondition unexpectedly has step-3.5"
[[ ! -f "$DESIGN_GATE_B/.completed/step-3.6" ]] || fail "gate B bypass empty-state precondition unexpectedly has step-3.6"
apply_gate_b_bypass_sentinels "$DESIGN_GATE_B" || fail "gate B bypass helper refused empty state"
[[ -f "$DESIGN_GATE_B/.completed/step-3" && -f "$DESIGN_GATE_B/.completed/step-3.5" && -f "$DESIGN_GATE_B/.completed/step-3.6" ]] || fail "gate B bypass helper missing triple sentinels"
printf 'issue body gate b\n' >"$BODY_FILE"
out_gate_b=$(bash "$SAVE" --design-tmpdir "$DESIGN_GATE_B" --issue 9 --repo owner/repo)
[[ "$out_gate_b" == *"PAUSE_OK=true"* && "$out_gate_b" == *"STEP=3b"* ]] || fail "gate B bypass plan-size-trigger writes triple sentinels from empty state: $out_gate_b"
out_gate_b_load=$(bash "$LOAD" --design-tmpdir "$TMP/restore-gate-b" --issue 9 --repo owner/repo)
[[ "$out_gate_b_load" == *"LOAD_OK=true"* && "$out_gate_b_load" == *"STEP=3b"* ]] || fail "gate B bypass empty-state load mismatch: $out_gate_b_load"
printf '12\n' >"$DESIGN_GATE_B/diff-lines.txt"
DESIGN_TMPDIR="$DESIGN_GATE_B" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash -euo pipefail -c '
set +e
printf "%s\n" "ACTION=FINALIZE" \
  | "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-driver.sh" --design-tmpdir "$DESIGN_TMPDIR"
_finalize_rc=$?
set -e
if [ "$_finalize_rc" -ne 0 ]; then
  printf "%s\n" "**⚠ FINALIZE failed; repair the missing artifact before Step 5.**"
  exit "$_finalize_rc"
fi
mkdir -p "$DESIGN_TMPDIR/.completed"
: > "$DESIGN_TMPDIR/.completed/step-3b"
'
[[ -f "$DESIGN_GATE_B/.completed/finalize" && -f "$DESIGN_GATE_B/.completed/step-3b" ]] || fail "gate B bypass Step 3b completion boundary did not write finalize and step-3b markers"

DESIGN_GATE_B_STEP3="$TMP/design-gate-b-step3-only"
make_design_tmpdir "$DESIGN_GATE_B_STEP3"
complete_design_steps "$DESIGN_GATE_B_STEP3" 3
[[ -f "$DESIGN_GATE_B_STEP3/.completed/step-3" ]] || fail "gate B bypass step-3-only precondition missing step-3"
[[ ! -f "$DESIGN_GATE_B_STEP3/.completed/step-3.5" ]] || fail "gate B bypass step-3-only precondition unexpectedly has step-3.5"
[[ ! -f "$DESIGN_GATE_B_STEP3/.completed/step-3.6" ]] || fail "gate B bypass step-3-only precondition unexpectedly has step-3.6"
apply_gate_b_bypass_sentinels "$DESIGN_GATE_B_STEP3" || fail "gate B bypass helper refused pre-existing step-3"
[[ -f "$DESIGN_GATE_B_STEP3/.completed/step-3.5" && -f "$DESIGN_GATE_B_STEP3/.completed/step-3.6" ]] || fail "gate B bypass helper missing supplemental sentinels"
printf 'issue body gate b step3\n' >"$BODY_FILE"
out_gate_b_step3=$(bash "$SAVE" --design-tmpdir "$DESIGN_GATE_B_STEP3" --issue 9 --repo owner/repo)
[[ "$out_gate_b_step3" == *"PAUSE_OK=true"* && "$out_gate_b_step3" == *"STEP=3b"* ]] || fail "gate B bypass with pre-existing step-3 should resume at 3b: $out_gate_b_step3"
out_gate_b_step3_load=$(bash "$LOAD" --design-tmpdir "$TMP/restore-gate-b-step3" --issue 9 --repo owner/repo)
[[ "$out_gate_b_step3_load" == *"LOAD_OK=true"* && "$out_gate_b_step3_load" == *"STEP=3b"* ]] || fail "gate B bypass step-3-only load mismatch: $out_gate_b_step3_load"

DESIGN_GATE_B_MISSING="$TMP/design-gate-b-missing-sentinels"
make_design_tmpdir "$DESIGN_GATE_B_MISSING"
complete_design_steps "$DESIGN_GATE_B_MISSING" 3
printf 'issue body gate b missing\n' >"$BODY_FILE"
out_gate_b_missing=$(bash "$SAVE" --design-tmpdir "$DESIGN_GATE_B_MISSING" --issue 9 --repo owner/repo)
[[ "$out_gate_b_missing" == *"PAUSE_OK=true"* && "$out_gate_b_missing" == *"STEP=3.5"* ]] || fail "missing gate B bypass sentinels should resume at 3.5: $out_gate_b_missing"

DESIGN_GATE_B_PARTIAL="$TMP/design-gate-b-partial-sentinel"
make_design_tmpdir "$DESIGN_GATE_B_PARTIAL"
complete_design_steps "$DESIGN_GATE_B_PARTIAL" 3.6
printf 'issue body gate b partial\n' >"$BODY_FILE"
out_gate_b_partial=$(bash "$SAVE" --design-tmpdir "$DESIGN_GATE_B_PARTIAL" --issue 9 --repo owner/repo)
[[ "$out_gate_b_partial" == *"PAUSE_OK=true"* && "$out_gate_b_partial" != *"STEP=3b"* ]] || fail "partial step-3.6 sentinel must not resume at 3b: $out_gate_b_partial"

DESIGN_GATE_B_DONE="$TMP/design-gate-b-done"
make_design_tmpdir "$DESIGN_GATE_B_DONE"
complete_design_steps "$DESIGN_GATE_B_DONE" 3 3.5 3.6
printf 'issue body gate b done\n' >"$BODY_FILE"
out_gate_b_done=$(bash "$SAVE" --design-tmpdir "$DESIGN_GATE_B_DONE" --issue 9 --repo owner/repo)
[[ "$out_gate_b_done" == *"PAUSE_OK=true"* && "$out_gate_b_done" == *"STEP=3b"* ]] || fail "gate B triple touch should resume at 3b: $out_gate_b_done"
set +e
out_step3b_boundary_fail=$(DESIGN_TMPDIR="$DESIGN_GATE_B_DONE" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash -euo pipefail -c '
set +e
printf "%s\n" "ACTION=FINALIZE" \
  | "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-driver.sh" --design-tmpdir "$DESIGN_TMPDIR"
_finalize_rc=$?
set -e
if [ "$_finalize_rc" -ne 0 ]; then
  printf "%s\n" "**⚠ FINALIZE failed; repair the missing artifact before Step 5.**"
  exit "$_finalize_rc"
fi
mkdir -p "$DESIGN_TMPDIR/.completed"
: > "$DESIGN_TMPDIR/.completed/step-3b"
' 2>&1)
rc_step3b_boundary_fail=$?
set -e
[[ "$rc_step3b_boundary_fail" -ne 0 ]] || fail "fresh Step 3b FINALIZE failure boundary should exit non-zero"
[[ "$out_step3b_boundary_fail" == *"**⚠ FINALIZE failed; repair the missing artifact before Step 5.**"* ]] || fail "fresh Step 3b FINALIZE failure warning missing: $out_step3b_boundary_fail"

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

echo "=== malformed repo fails before publish or marker ==="
make_design_tmpdir "$DESIGN"
: >"$DESIGN/.pause-requested"
printf 'body\n' >"$BODY_FILE"
out_bad_repo_save=$(bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo /abs)
[[ "$out_bad_repo_save" == *"PAUSE_OK=false"* && "$out_bad_repo_save" == *"ERROR=invalid-repo"* ]] || fail "bad --repo should fail early: $out_bad_repo_save"
[[ -f "$DESIGN/.pause-requested" ]] || fail "bad --repo must preserve .pause-requested for retry"
! grep -Fq 'larch:design-pause' "$BODY_FILE" || fail "bad --repo must not write marker"
make_design_tmpdir "$DESIGN"
printf 'export SESSION_ID=RUNPAUSE1\nexport REPO=owner/repo\n' >"$DESIGN/source-env.sh"
printf 'body\n' >"$BODY_FILE"
out_bad_repo_pre_source=$(bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo /abs)
[[ "$out_bad_repo_pre_source" == *"PAUSE_OK=false"* && "$out_bad_repo_pre_source" == *"ERROR=invalid-repo"* ]] || fail "bad argv --repo should not be overwritten by source-env: $out_bad_repo_pre_source"
! grep -Fq 'larch:design-pause' "$BODY_FILE" || fail "bad argv --repo with source-env must not write marker"
make_design_tmpdir "$DESIGN"
printf 'export SESSION_ID=RUNPAUSE1\nexport REPO=bad..repo\n' >"$DESIGN/source-env.sh"
: >"$DESIGN/.pause-requested"
printf 'body\n' >"$BODY_FILE"
out_bad_repo_source=$(bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9)
[[ "$out_bad_repo_source" == *"PAUSE_OK=false"* && "$out_bad_repo_source" == *"ERROR=invalid-repo"* ]] || fail "bad source-env REPO should fail before pause save: $out_bad_repo_source"
[[ -f "$DESIGN/.pause-requested" ]] || fail "bad source-env REPO must preserve .pause-requested for retry"
! grep -Fq 'larch:design-pause' "$BODY_FILE" || fail "bad source-env REPO must not write marker"
make_design_tmpdir "$DESIGN"
printf 'export SESSION_ID=bad/../run\nexport REPO=owner/repo\n' >"$DESIGN/source-env.sh"
: >"$DESIGN/.pause-requested"
printf 'body\n' >"$BODY_FILE"
out_bad_session_source=$(bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9)
[[ "$out_bad_session_source" == *"PAUSE_OK=false"* && "$out_bad_session_source" == *"ERROR=invalid-run-id"* ]] || fail "bad source-env SESSION_ID should fail before pause save: $out_bad_session_source"
[[ ! -e "$DESIGN/.pause-requested" ]] || fail "pause-save terminal failure must clear .pause-requested sentinel"
! grep -Fq 'larch:design-pause' "$BODY_FILE" || fail "bad source-env SESSION_ID must not write marker"

echo "=== step-5b complete with withheld step-5c resumes at 5c ==="
DESIGN_5C="$TMP/design-5c-withheld"
make_design_tmpdir "$DESIGN_5C"
complete_design_steps "$DESIGN_5C" 1c 1d 1d.5 1d.7 1e 2a 2a.5 2b 2b.5 3 3.5 3.6 3b 4 4b 5b
[[ -f "$DESIGN_5C/.completed/step-5b" ]] || fail "step-5b withheld-5c precondition missing step-5b"
[[ ! -f "$DESIGN_5C/.completed/step-5c" ]] || fail "step-5c withheld-5c precondition unexpectedly has step-5c"
printf 'issue body 5c withheld\n' >"$BODY_FILE"
out_5c=$(bash "$SAVE" --design-tmpdir "$DESIGN_5C" --issue 9 --repo owner/repo)
[[ "$out_5c" == *"PAUSE_OK=true"* && "$out_5c" == *"STEP=5c"* ]] || fail "withheld step-5c should pause at 5c: $out_5c"
out_5c_load=$(bash "$LOAD" --design-tmpdir "$TMP/restore-5c-withheld" --issue 9 --repo owner/repo)
[[ "$out_5c_load" == *"LOAD_OK=true"* && "$out_5c_load" == *"STEP=5c"* ]] || fail "withheld step-5c load mismatch: $out_5c_load"

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
out_rc_ok=$(PUBLISH_MODE=rc-ok-false bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo owner/repo)
[[ "$out_rc_ok" == *"PAUSE_OK=false"* && "$out_rc_ok" == *"ERROR=publish-and-recovery-failed"* ]] || fail "rc-ok-false contradictory envelope should fail closed: $out_rc_ok"
! grep -Fq 'larch:design-pause' "$BODY_FILE" || fail "rc-ok-false must not write marker"

make_design_tmpdir "$DESIGN"
printf 'body\n' >"$BODY_FILE"
out_rc_recovery=$(PUBLISH_MODE=rc-false-recovery bash "$SAVE" --design-tmpdir "$DESIGN" --issue 9 --repo owner/repo)
[[ "$out_rc_recovery" == *"PAUSE_OK=true"* && "$out_rc_recovery" == *"LOG_RECOVERY_BRANCH=larch-log-design-RUNPAUSE1"* ]] || fail "rc-false-recovery should stay resumable: $out_rc_recovery"
grep -Fq 'LOG_RECOVERY_BRANCH=larch-log-design-RUNPAUSE1' "$BODY_FILE" || fail "rc-false-recovery marker missing recovery branch"

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

LEGACY_HARD="$SNAPSHOT_ROOT/larch-logs/design/RUNPAUSE1"
rm -rf "$LEGACY_HARD"
mkdir -p "$LEGACY_HARD/.completed"
printf 'plan\n' >"$LEGACY_HARD/plan.txt"
printf '{"design_classification":"HARD"}\n' >"$LEGACY_HARD/run-params.json"
printf '{"run_id":"RUNPAUSE1","issue_number":"9"}\n' >"$LEGACY_HARD/manifest.json"
printf 'ISSUE_NUMBER=9\nRUN_ID=RUNPAUSE1\n' >"$LEGACY_HARD/pause-state.txt"
: >"$LEGACY_HARD/.completed/step-3"
: >"$LEGACY_HARD/.completed/step-3.5"
printf '<!-- larch:design-pause:start -->\nISSUE_NUMBER=9\nREPO=owner/repo\nRUN_ID=RUNPAUSE1\nSTEP=3b\nBODY_HASH=x\n<!-- larch:design-pause:end -->\n' >"$BODY_FILE"
out_legacy_3b=$(bash "$LOAD" --design-tmpdir "$TMP/legacy-3b" --issue 9 --repo owner/repo)
[[ "$out_legacy_3b" == *"LOAD_OK=true"* && "$out_legacy_3b" == *"STEP=3.6"* ]] || fail "legacy HARD STEP=3b without step-3.6 should resume at assessor: $out_legacy_3b"

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
