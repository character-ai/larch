#!/usr/bin/env bash
set -euo pipefail
TMP=$(mktemp -d)
ROOT=/Users/zhupanov/larch1
RESTORE="$TMP/restore"
mkdir -p "$RESTORE/.completed"
printf '{"brainstorm_requested":false}\n' >"$RESTORE/run-params.json"
printf 'plan\n# revised\n' >"$RESTORE/plan.txt"
printf 'feature\n' >"$RESTORE/feature-description.txt"
printf 'awaiting-post-apply\n' >"$RESTORE/.step3-round-1.phase"
: >"$RESTORE/.gate-b-postapply-ready-1"
cp "$RESTORE/plan.txt" "$RESTORE/plan-pre-apply-round-1.txt"
printf '1\n' >"$RESTORE/review-round-count.txt"
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
while [[ $# -gt 0 ]]; do
  case "$1" in --design-tmpdir) dir="${2:?}"; shift 2 ;; *) shift ;; esac
done
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
out=$(env LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" \
  RUN_STEP3_PLAN_REVIEW_LOOP_SH="$RESTORE/round-forbidden.sh" \
  RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH="$RESTORE/revise-forbidden.sh" \
  RUN_STEP3_DEDUP_PLAN_SH="$RESTORE/dedup-ok.sh" \
  RUN_STEP3_POSTPLAN_EMIT_SH="$RESTORE/postplan-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$RESTORE/continue-stop.sh" \
  python3 "$ROOT/python/cli.py" plan-review run --design-tmpdir "$RESTORE" --mode loop --starting-round 1 2>&1)
rc=$?
set -e
printf 'RC=%s\n' "$rc"
printf '%s\n' "$out"
rm -rf "$TMP"
