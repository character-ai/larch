#!/usr/bin/env bash
TMP=$(mktemp -d)
R="$TMP/r"
mkdir -p "$R"
printf 'export SESSION_ID=RUNPAUSE1\n' >"$R/source-env.sh"
printf '{"design_classification":"SIMPLE","brainstorm_requested":false}\n' >"$R/run-params.json"
printf 'plan\n# revised\n' >"$R/plan.txt"
printf 'feature\n' >"$R/feature-description.txt"
printf 'awaiting-post-apply\n' >"$R/.step3-round-1.phase"
: >"$R/.gate-b-postapply-ready-1"
cp "$R/plan.txt" "$R/plan-pre-apply-round-1.txt"
printf '1\n' >"$R/review-round-count.txt"
cat >"$R/postplan-ok.sh" <<'E'
#!/usr/bin/env bash
dir=""
while [[ $# -gt 0 ]]; do case "$1" in --design-tmpdir) dir="${2:?}"; shift 2 ;; *) shift ;; esac; done
printf 'POSTPLAN_EMIT_STATUS=ok\n' >"$dir/.design-postplan-emit-result.env"
exit 0
E
cat >"$R/continue-stop.sh" <<'E'
#!/usr/bin/env bash
printf 'PLAN_REVIEW_CONTINUE=false\n'
E
chmod +x "$R/postplan-ok.sh" "$R/continue-stop.sh"
env LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT=/Users/zhupanov/larch1 \
  RUN_STEP3_POSTPLAN_EMIT_SH="$R/postplan-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$R/continue-stop.sh" \
  bash -x /Users/zhupanov/larch1/skills/design/scripts/run-step3-review.sh --design-tmpdir "$R" --mode loop --starting-round 1 2>/tmp/dloop4.trace
tail -25 /tmp/dloop4.trace
