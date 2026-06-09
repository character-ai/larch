#!/usr/bin/env bash
TMP=$(mktemp -d)
R="$TMP/r"
mkdir -p "$R/.completed"
printf '{"design_classification":"SIMPLE","brainstorm_requested":false}\n' >"$R/run-params.json"
printf 'export SESSION_ID=RUNPAUSE1\n' >"$R/source-env.sh"
printf '{"run_id":"RUNPAUSE1"}\n' >"$R/manifest.json"
printf 'plan\n# revised\n' >"$R/plan.txt"
printf 'feature\n' >"$R/feature-description.txt"
printf 'awaiting-post-apply\n' >"$R/.step3-round-1.phase"
: >"$R/.gate-b-postapply-ready-1"
cp "$R/plan.txt" "$R/plan-pre-apply-round-1.txt"
printf '1\n' >"$R/review-round-count.txt"
cat >"$R/revise-forbidden.sh" <<'E'
#!/usr/bin/env bash
exit 99
E
cat >"$R/round-forbidden.sh" <<'E'
#!/usr/bin/env bash
exit 99
E
cat >"$R/dedup-ok.sh" <<'E'
#!/usr/bin/env bash
exit 0
E
cat >"$R/postplan-ok.sh" <<'E'
#!/usr/bin/env bash
dir=""
while [[ $# -gt 0 ]]; do case "$1" in --design-tmpdir) dir="${2:?}"; shift 2 ;; *) shift ;; esac; done
printf 'POSTPLAN_EMIT_STATUS=ok\n' >"$dir/.design-postplan-emit-result.env"
exit 0
E
cat >"$R/continue-stop.sh" <<'E'
#!/usr/bin/env bash
printf 'PLAN_REVIEW_CONTINUE=false\nPLAN_REVIEW_CONTINUE_REASON=small-clean\n'
E
chmod +x "$R/revise-forbidden.sh" "$R/round-forbidden.sh" "$R/dedup-ok.sh" "$R/postplan-ok.sh" "$R/continue-stop.sh"
env CLAUDE_PLUGIN_ROOT=/Users/zhupanov/larch1 LARCH_QUIET_DISABLE=1 \
  RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH="$R/revise-forbidden.sh" \
  RUN_STEP3_DEDUP_PLAN_SH="$R/dedup-ok.sh" \
  RUN_STEP3_POSTPLAN_EMIT_SH="$R/postplan-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$R/continue-stop.sh" \
  /Users/zhupanov/larch1/skills/design/scripts/run-step3-review.sh --design-tmpdir "$R" --mode loop --starting-round 1
echo RC:$?
