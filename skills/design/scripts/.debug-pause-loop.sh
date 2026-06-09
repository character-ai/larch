#!/usr/bin/env bash
set -euo pipefail
export LARCH_QUIET_DISABLE=1
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
source "$REPO_ROOT/skills/design/scripts/test-step3-orchestrator-fence.sh"
SAVE="$REPO_ROOT/scripts/design-pause-save.sh"
LOAD="$REPO_ROOT/scripts/design-pause-load.sh"
TMP=$(mktemp -d)
BODY_FILE="$TMP/issue-body.md"
SNAPSHOT_ROOT="$TMP/snapshot"
FETCH_LOG="$TMP/fetch.log"
REV_PARSE_LOG="$TMP/rev-parse.log"
export BODY_FILE SNAPSHOT_ROOT FETCH_LOG REV_PARSE_LOG
STUB="$TMP/stub"
mkdir -p "$STUB" "$TMP/repo"
# minimal gh/git stubs from test file - copy key parts
cat >"$STUB/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == "repo" && "$2" == "view" ]]; then printf '%s\n' 'owner/repo'; exit 0; fi
if [[ "$1" == "issue" && "$2" == "view" ]]; then python3 - <<'PY'
import json, os
with open(os.environ["BODY_FILE"], "r", encoding="utf-8") as fh:
    print(json.dumps({"body": fh.read()}))
PY
exit 0; fi
if [[ "$1" == "issue" && "$2" == "edit" ]]; then
  for arg in "$@"; do [[ "$prev" == "--body-file" ]] && cp "$arg" "$BODY_FILE" && exit 0; [[ "$arg" == "--body-file" ]] && prev="--body-file"; done
  exit 2
fi
exit 2
GH
chmod +x "$STUB/gh"
export PATH="$STUB:$PATH"
make_design_tmpdir() {
  local d="$1"
  mkdir -p "$d/.completed"
  : >"$d/.completed/step-0c"
  printf 'export SESSION_ID=RUNPAUSE1\n' >"$d/source-env.sh"
  printf '{"run_id":"RUNPAUSE1","issue_number":"9"}\n' >"$d/manifest.json"
  printf 'plan\n' >"$d/plan.txt"
  printf '{"design_classification":"SIMPLE","brainstorm_requested":false}\n' >"$d/run-params.json"
}
complete_design_steps() { local d="$1"; shift; for s in "$@"; do : >"$d/.completed/step-$s"; done; }
DESIGN_POST_APPLY="$TMP/design"
make_design_tmpdir "$DESIGN_POST_APPLY"
complete_design_steps "$DESIGN_POST_APPLY" 1c 1d 1d.5 1d.7 1e 2a 2a.5 2b 2b.5
printf 'awaiting-post-apply\n' >"$DESIGN_POST_APPLY/.step3-round-1.phase"
: >"$DESIGN_POST_APPLY/.gate-b-postapply-ready-1"
cp "$DESIGN_POST_APPLY/plan.txt" "$DESIGN_POST_APPLY/plan-pre-apply-round-1.txt"
printf '# revised\n' >>"$DESIGN_POST_APPLY/plan.txt"
: >"$DESIGN_POST_APPLY/.pause-requested"
printf 'issue body\n' >"$BODY_FILE"
bash "$SAVE" --design-tmpdir "$DESIGN_POST_APPLY" --issue 9 --repo owner/repo >/dev/null
RESTORE="$TMP/restore"
bash "$LOAD" --design-tmpdir "$RESTORE" --issue 9 --repo owner/repo
rm -f "$RESTORE/.pause-requested"
printf '1\n' >"$RESTORE/review-round-count.txt"
printf 'feature\n' >"$RESTORE/feature-description.txt"
for s in revise-forbidden dedup-ok postplan-ok continue-stop round-forbidden; do
  cat >"$RESTORE/$s.sh" <<STUB
#!/usr/bin/env bash
STUB
done
cat >"$RESTORE/revise-forbidden.sh" <<'STUB'
#!/usr/bin/env bash
exit 99
STUB
cat >"$RESTORE/dedup-ok.sh" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
cat >"$RESTORE/postplan-ok.sh" <<'STUB'
#!/usr/bin/env bash
dir=""
while [[ $# -gt 0 ]]; do case "$1" in --design-tmpdir) dir="${2:?}"; shift 2 ;; *) shift ;; esac; done
printf 'POSTPLAN_EMIT_STATUS=ok\n' >"$dir/.design-postplan-emit-result.env"
exit 0
STUB
cat >"$RESTORE/continue-stop.sh" <<'STUB'
#!/usr/bin/env bash
printf 'PLAN_REVIEW_CONTINUE=false\nPLAN_REVIEW_CONTINUE_REASON=small-clean\n'
STUB
cat >"$RESTORE/round-forbidden.sh" <<'STUB'
#!/usr/bin/env bash
exit 99
STUB
chmod +x "$RESTORE"/*.sh
set +e
env LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
  RUN_STEP3_PLAN_REVIEW_LOOP_SH="$RESTORE/round-forbidden.sh" \
  RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH="$RESTORE/revise-forbidden.sh" \
  RUN_STEP3_DEDUP_PLAN_SH="$RESTORE/dedup-ok.sh" \
  RUN_STEP3_POSTPLAN_EMIT_SH="$RESTORE/postplan-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$RESTORE/continue-stop.sh" \
  "$REPO_ROOT/skills/design/scripts/run-step3-review.sh" --design-tmpdir "$RESTORE" --mode loop --starting-round 1 2>&1
echo RC:$?
