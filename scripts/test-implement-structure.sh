#!/usr/bin/env bash
# shellcheck disable=SC2016
# Structural regression test for /implement SKILL.md + larch-log migration.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
# shellcheck source=scripts/lib-p3119-fence-absence.sh
source "$REPO_ROOT/scripts/lib-p3119-fence-absence.sh"
SKILL_MD="$REPO_ROOT/skills/implement/SKILL.md"
REFS_DIR="$REPO_ROOT/skills/implement/references"
RESTORE_FINALIZE_SH="$REPO_ROOT/scripts/restore-finalize-state.sh"
LIB_FINALIZE_KEYS_SH="$REPO_ROOT/scripts/lib-finalize-state-keys.sh"
SHIP_PR_SH="$REPO_ROOT/scripts/ship-pr.sh"
LINT_FIX_LOOP_SH="$REPO_ROOT/scripts/lint-fix-loop.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[[ -f "$SKILL_MD" ]] || fail "skills/implement/SKILL.md missing"
[[ -d "$REFS_DIR" ]] || fail "skills/implement/references missing"

assert_degraded_tools_gate_fence() {
  local tmp region
  tmp=$(mktemp "${TMPDIR:-/tmp}/implement-degraded-gate.XXXXXX")
  awk '
    /\*\*Degraded-tools gate \(#3207\)\.\*\*/ { in_region = 1 }
    in_region && /^Step 0 dirty-tree recovery gate:/ { in_region = 0 }
    in_region { print }
  ' "$SKILL_MD" >"$tmp.region"
  region=$(cat "$tmp.region")
  [[ -n "$region" ]] || fail "SKILL.md missing Degraded-tools gate (#3207) region"
  if printf '%s\n' "$region" | grep -Fq 'from the bootstrap parse above'; then
    rm -f "$tmp" "$tmp.region"
    fail "Degraded-tools gate region must not rely on bootstrap parse variables"
  fi
  awk '
    /\*\*Degraded-tools gate \(#3207\)\.\*\*/ { start = 1; next }
    start && /^```bash$/ { in_fence = 1; next }
    start && in_fence && /^```$/ { exit }
    start && in_fence { print }
  ' "$SKILL_MD" >"$tmp"
  [[ -s "$tmp" ]] || fail "Degraded-tools gate region missing bash fence"
  for needle in \
    'export IMPLEMENT_TMPDIR' \
    'plugin-root.env' \
    'LARCH_CLAUDE_PLUGIN_ROOT' \
    'export CLAUDE_PLUGIN_ROOT' \
    '--file "$IMPLEMENT_TMPDIR/session-env.sh" --key CODEX_PRESENT --default ""' \
    '--file "$IMPLEMENT_TMPDIR/session-env.sh" --key CURSOR_PRESENT --default ""' \
    '--file "$IMPLEMENT_TMPDIR/session-env.sh" --key CODEX_BINARY_FOUND --default ""' \
    '--file "$IMPLEMENT_TMPDIR/session-env.sh" --key CURSOR_BINARY_FOUND --default ""' \
    '"$CLAUDE_PLUGIN_ROOT/scripts/degraded-tools-gate.sh" --skill implement' \
    '--codex-present "$CODEX_PRESENT"' \
    '--cursor-present "$CURSOR_PRESENT"' \
    '--codex-binary-found "$CODEX_BINARY_FOUND"' \
    '--cursor-binary-found "$CURSOR_BINARY_FOUND"'
  do
    grep -Fq -- "$needle" "$tmp" || { rm -f "$tmp" "$tmp.region"; fail "Degraded-tools gate fence missing: $needle"; }
  done
  rm -f "$tmp" "$tmp.region"
}

# Issue #2497: /implement docs must not reintroduce removed --auto / --auto-mode flag surfaces.
if grep -Eq '(^|[[:space:]])--auto([^A-Za-z0-9_-]|$)' "$SKILL_MD"; then
  fail "SKILL.md must not document standalone --auto flag token (issue #2497 structural pin)"
fi
grep -Fq -- '--auto-mode' "$SKILL_MD" \
  && fail "SKILL.md must not document --auto-mode flag (issue #2497 structural pin)"

for heading in "## Load-Bearing Invariants" "## NEVER List" "## Rebase Checkpoint Macro"; do
  count="$(grep -c "^$heading$" "$SKILL_MD" || true)"
  [[ "$count" == "1" ]] || fail "expected exactly one $heading heading, found $count"
done

for ref in summary-comment-template.md conflict-resolution.md codex-manifest-schema.md pr-body-template.md; do
  [[ -f "$REFS_DIR/$ref" ]] || fail "missing reference: $ref"
done

grep -Fq 'Two invariants enforced across multiple steps' "$SKILL_MD" \
  || fail "SKILL.md must document two Load-Bearing Invariants after Phase 1 (#3364)"
grep -Fq 'Version Bump Freshness' "$SKILL_MD" \
  && fail "SKILL.md must not retain retired Invariant #1 (Version Bump Freshness)"
grep -Fq 'Degraded-Git Fail-Closed' "$SKILL_MD" \
  && fail "SKILL.md must not retain retired Invariant #3 (Degraded-Git Fail-Closed)"
grep -Fq 'caller_kind=ship_pr_pre_push' "$REFS_DIR/conflict-resolution.md" \
  || fail "conflict-resolution.md must retain the active ship_pr_pre_push conflict handoff"
grep -Fq 'caller_kind=early_rebase' "$REFS_DIR/conflict-resolution.md" \
  || fail "conflict-resolution.md must retain the active early_rebase conflict handoff"
grep -Fq '### Step 8a' "$SKILL_MD" \
  && fail "SKILL.md must not retain a Step 8a release notes section after Phase 1 (#3364)"
grep -Fq "NEVER end the turn after \`/release\`" "$SKILL_MD" \
  && fail "SKILL.md must not retain retired NEVER #15 (post-/release sub-procedure halt)"
grep -Fq 'caller_kind=step8b_rebase' "$SKILL_MD" \
  && fail "SKILL.md must not retain retired NEVER #8 (step8b_rebase caller_kind pin)"
grep -Fq "NEVER call \`/release\` as a direct Skill invocation" "$SKILL_MD" \
  && fail "SKILL.md must not retain retired NEVER #11 (orchestrator /release Skill pin)"
# shellcheck disable=SC2016 # Intentional literal probe of SKILL.md content.
grep -Fq 'if [ "${LARCH_SHIP_PR_IMPL:-python}" != "bash" ]; then' "$SKILL_MD" \
  || fail "SKILL.md Step 8+ Invoke fence must default to Python unless LARCH_SHIP_PR_IMPL=bash"
grep -Fq "sys.version_info >= (3, 11)" "$SKILL_MD" \
  || fail "SKILL.md Step 8+ Invoke fence must pin the Python 3.11 ship-driver guard"
grep -Fq '"outcome":"STALLED"' "$SKILL_MD" \
  || fail "SKILL.md Step 8+ Python version guard must emit structured JSON on stdout"
grep -Fq 'phantom-probe-with-warn.sh" --step 8-pre-ship' "$SKILL_MD" \
  || fail "SKILL.md must retain 8-pre-ship phantom-probe invocation"
grep -Fq 'phantom-probe-with-warn.sh" --step 8-pre-bump' "$SKILL_MD" \
  && fail "SKILL.md must not use retired 8-pre-bump phantom-probe token"

grep -Fq 'default `LARCH_SHIP_PR_IMPL=python` runs' "$SKILL_MD" \
  || fail "SKILL.md must document Python ship driver as the default"
grep -Fq 'Critical boundary: after the active Step 8+ driver (`python3 …/python/ship.py` unless `LARCH_SHIP_PR_IMPL=bash`) exits on the default Python path, route only from process exit code + JSON stdout per the Python driver selector' "$SKILL_MD" \
  || fail "SKILL.md anti-halt reminder must pin default-Python JSON routing"
grep -Fq 'Immediately before the active Step 8+ driver unless `LARCH_SHIP_PR_IMPL=bash` (then before `ship-pr.sh` first invocation): `--step 8-pre-ship` via `phantom-probe-with-warn.sh`.' "$SKILL_MD" \
  || fail "Phantom Probe registry must name the active Step 8+ driver before bash opt-in"
grep -Fq 'on the default path, `python/ship.py` writes `$IMPLEMENT_TMPDIR/finalize-state.sh` on terminal driver outcomes' "$SKILL_MD" \
  || fail "SKILL.md NEVER #11 must pin default-Python finalize-state writer"
grep -Fq 'When `LARCH_SHIP_PR_IMPL=bash`, run the bash contract below byte-for-byte' "$SKILL_MD" \
  || fail "SKILL.md must document bash as explicit opt-in"
grep -Fq 'driven by the **Python driver selector** below' "$SKILL_MD" \
  || fail "SKILL.md must route Step 8+ through the Python selector"
grep -Fq 'Unless `LARCH_SHIP_PR_IMPL=bash`, do not run the fenced' "$SKILL_MD" \
  || fail "SKILL.md must prohibit default-path fallthrough to bash fence"
grep -Fq 'ship-pr-net-retries-python.count' "$SKILL_MD" \
  || fail "SKILL.md must use the Python Exit 6 retry counter"
if grep -Fq 'default `LARCH_SHIP_PR_IMPL=bash` runs the bash contract' "$SKILL_MD"; then
  fail "SKILL.md must not retain bash-default selector prose"
fi
python_selector_window=$(awk '
  /\*\*Python driver selector:\*\*/ { in_region = 1 }
  in_region && /^Invoke:[[:space:]]*$/ { exit }
  in_region { print }
' "$SKILL_MD")
[[ -n "$python_selector_window" ]] || fail "missing Python driver selector window"
printf '%s
' "$python_selector_window" | grep -Fq 'python3 "${CLAUDE_PLUGIN_ROOT}/python/ship.py"' \
  || fail "Python selector window must include python/ship.py argv"
printf '%s
' "$python_selector_window" | grep -Fq -- '--state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"' \
  || fail "Python selector window must include --state-file"
printf '%s
' "$python_selector_window" | grep -Fq 'needs_user_reason' \
  || fail "Python selector window must include needs_user_reason routing"
printf '%s
' "$python_selector_window" | grep -Fq 'oos-filing' \
  || fail "Python selector window must include oos-filing routing"
printf '%s
' "$python_selector_window" | grep -Fq '4th failure → treat as Exit 4 stall and seed stall keys with `stall-recovery-report.sh seed-terminal-state`' \
  || fail "Python selector window must pin fourth Exit 6 stall-state persistence"

bash_matrix_gate_window=$(awk '
  /Apply the following exit matrix \*\*only when `LARCH_SHIP_PR_IMPL=bash`\*\*/ { in_region = 1 }
  in_region { print }
  in_region && /\*\*Exit 6\*\*/ { exit }
' "$SKILL_MD")
printf '%s
' "$bash_matrix_gate_window" | grep -Fq 'Apply the following exit matrix **only when `LARCH_SHIP_PR_IMPL=bash`**' \
  || fail "SKILL.md must gate bash exit matrix behind LARCH_SHIP_PR_IMPL=bash"
printf '%s
' "$bash_matrix_gate_window" | grep -Fq 'Phase 4 exit 0 re-invokes the active Step 8+ selector: default Python foreground argv including `--state-file`, no `--resume-phase`; only when `LARCH_SHIP_PR_IMPL=bash`, re-invoke `ship-pr.sh --resume-phase ship-pr-rrr-phase14`' \
  || fail "SKILL.md Exit 4 ship_pr_pre_push handoff must document Python selector plus bash-only --resume-phase"
if printf '%s
' "$bash_matrix_gate_window" | grep -Fq 'Phase 4 exit 0 re-invokes `ship-pr.sh --resume-phase ship-pr-rrr-phase14`'; then
  fail "SKILL.md Exit 4 must not make bash --resume-phase the sole Phase 4 resume instruction"
fi


grep -Fq 'scripts/larch-log.sh' "$SKILL_MD" \
  || fail "SKILL.md must reference scripts/larch-log.sh"
grep -Fq 'tracking-issue-summary.sh' "$SKILL_MD" \
  || fail "SKILL.md must reference tracking-issue-summary.sh"
grep -Fq 'summary-comment-template.md' "$SKILL_MD" \
  || fail "SKILL.md must reference summary-comment-template.md"

# Pin post-dispatch branch assertion with stable tokens (not "Step 2.2" prose),
# matching `skills/implement/SKILL.md` §2.2 `STATUS=complete` bullet.
# shellcheck disable=SC2016
grep -Fq 'then run **post-dispatch branch assertion** (external-implementer path only): `${CLAUDE_PLUGIN_ROOT}/scripts/git-current-branch.sh` — parse `BRANCH=<name>` into `CURRENT_BRANCH_POST_DISPATCH`' "$SKILL_MD" \
  || fail "SKILL.md must retain post-dispatch branch assertion contract (git-current-branch.sh + CURRENT_BRANCH_POST_DISPATCH)"
grep -Fq 'FINAL_BAIL_REASON=main-branch-post-dispatch' "$SKILL_MD" \
  || fail "SKILL.md must document FINAL_BAIL_REASON=main-branch-post-dispatch (post-dispatch mismatch bail)"
grep -Fq 'set `FINAL_BAIL_REASON=orchestrator-envelope-invalid`, set `IMPLEMENT_BAIL_REASON=orchestrator-envelope-invalid`, set `STALL_STEP=2`, set `PHASE=implementation`, set `STALL_TRACKING=true`' "$SKILL_MD" \
  || fail "SKILL.md must mirror orchestrator-envelope-invalid into IMPLEMENT_BAIL_REASON and preserve Step 2 context before Step 12d"
grep -Fq 'mirror dispatcher `REASON` into both `FINAL_BAIL_REASON` and `IMPLEMENT_BAIL_REASON`, set `STALL_STEP=2`, set `PHASE=implementation`, set `STALL_TRACKING=true` unconditionally, and bail to Step 12d' "$SKILL_MD" \
  || fail "SKILL.md STATUS=bailed must mirror REASON into bail variables and preserve Step 2 hard-bail context"
grep -Fq 'set `FINAL_BAIL_REASON=main-branch-post-dispatch`, set `IMPLEMENT_BAIL_REASON=main-branch-post-dispatch`, set `STALL_STEP=2`, set `PHASE=implementation`, set `STALL_TRACKING=true`' "$SKILL_MD" \
  || fail "SKILL.md post-dispatch branch mismatch must mirror IMPLEMENT_BAIL_REASON and preserve Step 2 context"
grep -Fq '### Step 18a — Stall recovery gate' "$SKILL_MD" \
  || fail "SKILL.md must retain Step 18a stall recovery heading"
grep -Fq '### Step 18b — Teardown' "$SKILL_MD" \
  || fail "SKILL.md must retain Step 18b teardown heading"
grep -Fq '⏩ 18a: stall recovery — no stall detected' "$SKILL_MD" \
  || fail "SKILL.md must retain the Step 18a no-stall fast-path line"
step18_restore_window=$(awk '
  /_restore_finalize=false/ { in_region = 1 }
  in_region { print }
  in_region && /implement-finalize.sh" teardown/ { exit }
' "$SKILL_MD")
printf '%s
' "$step18_restore_window" | grep -Fq '_restore_finalize=false' \
  || fail "SKILL.md Step 18 restore gate must initialize _restore_finalize"
printf '%s
' "$step18_restore_window" | grep -Fq '[ "${LARCH_SHIP_PR_IMPL:-python}" = "bash" ]' \
  || fail "SKILL.md Step 18 restore gate must retain bash-only restore qualifier"
printf '%s
' "$step18_restore_window" | grep -Fq '_ship_stall_truthy' \
  || fail "SKILL.md Step 18 restore gate must evaluate truthy stall tracking"
printf '%s
' "$step18_restore_window" | grep -Fq '_ship_bail_truthy' \
  || fail "SKILL.md Step 18 restore gate must evaluate truthy bail user-input"
printf '%s
' "$step18_restore_window" | grep -Fq '[ "$_ship_step" != "$_final_step" ]' \
  || fail "SKILL.md Step 18 restore gate must restore on differing STALL_STEP"
STALL_RECOVERY_MD="$REPO_ROOT/skills/implement/references/stall-recovery.md"
STALL_RECOVERY_HELPER_SH="$REPO_ROOT/skills/implement/scripts/stall-recovery-report.sh"
grep -Fq 'BAIL_FAILURE_DETAIL_LOG' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must route BAIL_FAILURE_DETAIL_LOG into Step 18a classification"
# shellcheck disable=SC2016
grep -Fq '[--failure-detail-log "$VALIDATED_BAIL_FAILURE_DETAIL_LOG"]' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must document validated --failure-detail-log handoff for classify"
# shellcheck disable=SC2016
grep -Fq -- '--bail-reason "${IMPLEMENT_BAIL_REASON:-${FINAL_BAIL_REASON:-}}"' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must coalesce IMPLEMENT_BAIL_REASON and FINAL_BAIL_REASON for classify"
stall_step4_window=$(awk '
  /^4\. \*\*First-detection issue filing\.\*\*/ { in_step = 1 }
  /^5\. \*\*Dispatch on `RESUME_HINT`\.\*\*/ { in_step = 0 }
  in_step { print }
' "$STALL_RECOVERY_MD")
[[ -n "$stall_step4_window" ]] || fail "stall-recovery.md must retain Step 4 first-detection issue filing"
printf '%s\n' "$stall_step4_window" | grep -Fq 'stall-recovery-report.sh is-larch-dev-clone' \
  || fail "stall-recovery.md Step 4 must preserve the dev-clone discriminator"
printf '%s\n' "$stall_step4_window" | grep -Fq 'bug-body' \
  || fail "stall-recovery.md Step 4 must compose the sanitized bug body"
printf '%s\n' "$stall_step4_window" | grep -Fq 'issue-input-file' \
  || fail "stall-recovery.md Step 4 must compose the heading-bearing issue input file"
printf '%s\n' "$stall_step4_window" | grep -Eq '/larch:issue --input-file.*stall-recovery-issue-input\.md' \
  || fail "stall-recovery.md Step 4 must file stall-recovery-issue-input.md via /larch:issue --input-file"
printf '%s\n' "$stall_step4_window" | grep -Fq 'Skill tool' \
  || fail "stall-recovery.md Step 4 must describe /larch:issue as a Skill tool invocation"
printf '%s\n' "$stall_step4_window" | grep -Fq 'stall-recovery-issue.stdout' \
  || fail "stall-recovery.md Step 4 must capture /larch:issue stdout to stall-recovery-issue.stdout"
printf '%s\n' "$stall_step4_window" | grep -Fq 'normalize-issue-env' \
  || fail "stall-recovery.md Step 4 must normalize /larch:issue stdout through normalize-issue-env"
# shellcheck disable=SC2016
printf '%s\n' "$stall_step4_window" | grep -Fq -- '--issue-exit-code "$ISSUE_RC"' \
  || fail "stall-recovery.md Step 4 must pass the captured ISSUE_RC to normalize-issue-env"
printf '%s\n' "$stall_step4_window" | grep -Fq 'ISSUE_ENV_WRITTEN' \
  || fail "stall-recovery.md Step 4 must parse ISSUE_ENV_WRITTEN from normalize-issue-env"
stall_step4_order_line=$(printf '%s\n' "$stall_step4_window" | tr '\n' ' ')
stall_step4_dev_pos=$(printf '%s\n' "$stall_step4_order_line" | awk '{print index($0, "stall-recovery-report.sh is-larch-dev-clone")}')
stall_step4_bug_pos=$(printf '%s\n' "$stall_step4_order_line" | awk '{print index($0, "bug-body")}')
stall_step4_input_pos=$(printf '%s\n' "$stall_step4_order_line" | awk '{print index($0, "issue-input-file")}')
stall_step4_issue_pos=$(printf '%s\n' "$stall_step4_order_line" | awk '{print index($0, "/larch:issue --input-file")}')
stall_step4_stdout_pos=$(printf '%s\n' "$stall_step4_order_line" | awk '{print index($0, "stall-recovery-issue.stdout")}')
stall_step4_normalize_pos=$(printf '%s\n' "$stall_step4_order_line" | awk '{print index($0, "normalize-issue-env")}')
if [ "$stall_step4_dev_pos" -le 0 ] || [ "$stall_step4_bug_pos" -le 0 ] || [ "$stall_step4_input_pos" -le 0 ] || [ "$stall_step4_issue_pos" -le 0 ] \
  || [ "$stall_step4_dev_pos" -ge "$stall_step4_bug_pos" ] || [ "$stall_step4_dev_pos" -ge "$stall_step4_input_pos" ] || [ "$stall_step4_dev_pos" -ge "$stall_step4_issue_pos" ]; then
    fail "stall-recovery.md Step 4 must run is-larch-dev-clone before report composition and /larch:issue filing"
fi
if [ "$stall_step4_bug_pos" -ge "$stall_step4_input_pos" ] || [ "$stall_step4_input_pos" -ge "$stall_step4_issue_pos" ]; then
    fail "stall-recovery.md Step 4 must compose bug-body before issue-input-file and issue-input-file before /larch:issue filing"
fi
if [ "$stall_step4_stdout_pos" -le 0 ] || [ "$stall_step4_normalize_pos" -le 0 ] \
  || [ "$stall_step4_issue_pos" -ge "$stall_step4_stdout_pos" ] || [ "$stall_step4_stdout_pos" -ge "$stall_step4_normalize_pos" ]; then
    fail "stall-recovery.md Step 4 must capture /larch:issue stdout before normalize-issue-env"
fi
# shellcheck disable=SC2016
grep -Fq 'retry-policy --class "$FAILURE_CLASS"' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must mechanically gate dispatch with retry-policy"
# shellcheck disable=SC2016
grep -Fq 'If `attempt_count >= MAX_ATTEMPTS`, do not dispatch; continue directly to terminal-failure handling.' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must fail closed when retry caps are exhausted before dispatch"
grep -Fq 'PHASE=ci-initial' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md terminal-failure path must seed canonical Step-8-shaped state"
grep -Fq 'BAIL_FAILURE_DETAIL_LOG=' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md terminal-failure path must preserve or seed BAIL_FAILURE_DETAIL_LOG"
grep -Fq 'stall-recovery-report.sh clear-stall' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must delegate stall clearing through stall-recovery-report.sh clear-stall"
grep -Fq 'stall-recovery-report.sh seed-terminal-state' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must delegate terminal seeding through stall-recovery-report.sh seed-terminal-state"
grep -Fq '### Step 18a — Stall recovery gate' "$SKILL_MD" \
  || fail "SKILL.md must retain Step 18a heading"
grep -Fq '### Step 18b — Teardown' "$SKILL_MD" \
  || fail "SKILL.md must retain Step 18b heading"
# shellcheck disable=SC2016
grep -Fq 'If in-memory `STALL_TRACKING=false`, `STALL_TRACKING_DISK` is false or empty, `STALL_TRACKING_FINALIZE` is false or empty, and `STALL_TRACKING_SESSION` is false or empty, print `⏩ 18a: stall recovery — no stall detected` and continue to Step 18b.' "$SKILL_MD" \
  || fail "SKILL.md must require all four stall-tracking layers false before the Step 18a no-stall fast path"

stall_step18a_tmp=$(mktemp -d "${TMPDIR:-/tmp}/larch-step18a-structure.XXXXXX")
cat >"$stall_step18a_tmp/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
STALL_TRACKING=true
STALL_STEP=8
BAIL_REASON=
EXIT_CODE=4
NOTE=network timeout
EOF
mkdir -p "$stall_step18a_tmp/bin"
printf '#!/usr/bin/env bash\necho "$@" >>"%s/gh.calls"\n' "$stall_step18a_tmp" >"$stall_step18a_tmp/bin/gh"
chmod +x "$stall_step18a_tmp/bin/gh"
LARCH_QUIET_DISABLE=1 "$STALL_RECOVERY_HELPER_SH" init-attempts --implement-tmpdir "$stall_step18a_tmp" --attempts-file "$stall_step18a_tmp/attempts.env" >/dev/null
LARCH_QUIET_DISABLE=1 "$STALL_RECOVERY_HELPER_SH" classify --implement-tmpdir "$stall_step18a_tmp" --attempts-file "$stall_step18a_tmp/attempts.env" >"$stall_step18a_tmp/class.env"
PATH="$stall_step18a_tmp/bin:$PATH" LARCH_QUIET_DISABLE=1 LARCH_STALL_RECOVERY_DRY_RUN=1 "$STALL_RECOVERY_HELPER_SH" bug-body --implement-tmpdir "$stall_step18a_tmp" --classification-file "$stall_step18a_tmp/class.env" >"$stall_step18a_tmp/body.out"
PATH="$stall_step18a_tmp/bin:$PATH" LARCH_QUIET_DISABLE=1 LARCH_STALL_RECOVERY_DRY_RUN=1 "$STALL_RECOVERY_HELPER_SH" issue-input-file --implement-tmpdir "$stall_step18a_tmp" --classification-file "$stall_step18a_tmp/class.env" --body-file "$stall_step18a_tmp/stall-recovery-bug-body.md" >"$stall_step18a_tmp/input.out"
grep -Fq '## Action required — file larch bug' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must retain the consumer Action-required print path"
grep -Fq '### [Bug] /implement stall: transient-infra at 8' "$stall_step18a_tmp/stall-recovery-issue-input.md" \
  || fail "Step 18a dry-run integration must generate the expected /larch:issue title"
grep -Fq '## Sanitized stall report' "$stall_step18a_tmp/stall-recovery-bug-body.md" \
  || fail "Step 18a dry-run integration must generate the consumer chat body"
if [ -f "$stall_step18a_tmp/gh.calls" ]; then
  fail "Step 18a dry-run integration must not invoke gh"
fi
rm -rf "$stall_step18a_tmp"

if grep -Eiq '(^|[^[:alpha:]])user has( made| fixed)?([^[:alpha:]]|$)' \
    "$SKILL_MD" \
    "$REPO_ROOT/skills/review-and-fix/scripts/review-and-fix.md" \
    "$REPO_ROOT/skills/review-and-fix/scripts/review-and-fix.sh"; then
  fail "orchestrator/review-fix docs must not attribute coder work as 'user has...'"
fi

old_surfaces=(anchor-section-markers.sh assemble-anchor.sh hydrate-anchor.sh refresh-anchor.sh upsert-anchor find-anchor ANCHOR_COMMENT_ID "\$IMPLEMENT_TMPDIR/anchor-sections")
for old in "${old_surfaces[@]}"; do
  if grep -Fq "$old" "$SKILL_MD"; then
    fail "SKILL.md still references removed anchor surface: $old"
  fi
done

grep -Fq 'code-quality / risk-integration / correctness / architecture' "$SKILL_MD" \
  || fail "focus-area enum missing"
grep 'code-quality / risk-integration / correctness / architecture' "$SKILL_MD" | grep -q 'security' \
  || fail "focus-area enum line must include security"

grep -Fq 'scripts/larch-log-batches.md' "$REPO_ROOT/docs/run-logs.md" "$REPO_ROOT/scripts/implement-bootstrap.md" \
  || fail "run-log docs must retain larch-log batch table pointer"
# shellcheck disable=SC2016
grep -qE 'NEVER write, recreate, or modify .\$IMPLEMENT_TMPDIR/finalize-state\.sh' "$SKILL_MD" \
  || fail "SKILL.md must contain NEVER bullet for finalize-state.sh write prohibition"

step18_order_status=0
awk '
  /<!-- step:18/ {
    in_step = 1
    next
  }
  in_step && /<!-- step:/ {
    in_step = 0
    in_bash = 0
  }
  in_step && /^```(bash|sh|shell)[[:space:]]*$/ {
    in_bash = 1
    next
  }
  in_step && in_bash && /^```[[:space:]]*$/ {
    in_bash = 0
    next
  }
  in_step && in_bash && restore_line == 0 && /\/scripts\/restore-finalize-state\.sh/ {
    restore_line = NR
  }
  in_step && in_bash && teardown_line == 0 && /\/scripts\/implement-finalize\.sh.*teardown/ {
    teardown_line = NR
  }
  END {
    if (restore_line == 0) exit 10
    if (teardown_line == 0) exit 11
    if (restore_line >= teardown_line) exit 12
  }
' "$SKILL_MD" || step18_order_status=$?
case "$step18_order_status" in
  0) ;;
  10) fail "restore-finalize-state.sh not found in Step 18 region" ;;
  11) fail "implement-finalize.sh teardown not found in Step 18 region" ;;
  12) fail "restore-finalize-state.sh must appear before implement-finalize.sh teardown in Step 18" ;;
  *) fail "unexpected Step 18 finalize-state order check failure: $step18_order_status" ;;
esac

# Python Step 8+ cutover contract pins (#3446).
grep -Fq 'Default-path routing uses only stdout JSON plus the process exit code; do not parse `ship-pr-state.sh` for driver continuation and do not apply the bash exit matrix.' "$SKILL_MD" \
  || fail "SKILL.md must document JSON-only default-path continuation routing"
grep -Fq 'Scoped `ship-pr-state.sh` reads remain valid for OOS checkpoint inputs and Exit 4 `ship_pr_pre_push` classification evidence after Python refreshed it via `--state-file`; for that Python Exit 4 handoff, read `CONFLICT_FILES` from `ship-pr-state.sh` after the merge.' "$SKILL_MD" \
  || fail "SKILL.md must document scoped ship-pr-state reads for Python"
grep -Fq 'Python-only exit `1` with `outcome=INTERNAL_ERROR` is a driver bug path' "$SKILL_MD" \
  || fail "SKILL.md must route Python INTERNAL_ERROR exit 1 as hard tool failure"
grep -Fq 'on the Python path, dispatch on stdout JSON `needs_user_reason` and read JSON `failed_run_id` for autonomous CI-fix.' "$SKILL_MD" \
  || fail "SKILL.md must dispatch Python Exit 3 from JSON needs_user_reason and failed_run_id"
grep -Fq 'on the Python path, read `STALL_TRACKING` and `STALL_STEP` from `finalize-state.sh` when present, with stdout JSON `detail` as the fallback when `finalize-state.sh` is absent (invalid-tmpdir JSON-only edge).' "$SKILL_MD" \
  || fail "SKILL.md must document Python Exit 4 finalize-state stall keys plus JSON-only fallback"
grep -Fq 'Read `RESUME_PHASE`, `CALLER_KIND`, and `CONFLICT_FILES` from `ship-pr-state.sh` on both paths.' "$SKILL_MD" \
  || fail "SKILL.md must document Exit 4 RESUME_PHASE/CALLER_KIND/CONFLICT_FILES scoped ship-pr-state reads"
grep -Fq 'Read `PHASE` from `ship-pr-state.sh` for bash orchestrator-side per-phase retry budgeting only; `ship.py` does not read `PHASE` on startup.' "$SKILL_MD" \
  || fail "SKILL.md must document Exit 6 PHASE as orchestrator retry input only"
grep -Fq 'On the Python path, read `OOS_PENDING`, `FORKED_TARGET`, and `REPO_UNAVAILABLE` from `ship-pr-state.sh`, then re-invoke the same `python3 "${CLAUDE_PLUGIN_ROOT}/python/ship.py"` foreground fence without `--resume-phase`; do not substitute `finalize-state.sh` for those OOS gate inputs.' "$SKILL_MD" \
  || fail "SKILL.md must document Python OOS checkpoint scoped ship-pr-state reads and no --resume-phase re-entry"
grep -Fq 'on the Python path, re-invoke the same `python3 "${CLAUDE_PLUGIN_ROOT}/python/ship.py"` foreground fence without `--resume-phase`.' "$SKILL_MD" \
  || fail "SKILL.md must document Python Exit 0/OOS re-entry without --resume-phase"
grep -Fq 'Restore finalize-state.sh only when required. Bash opt-in always restores from' "$SKILL_MD" \
  || fail "SKILL.md must document conditional Step 18 restore gate"
grep -Fq 'if [ "${LARCH_SHIP_PR_IMPL:-python}" = "bash" ]; then' "$SKILL_MD" \
  || fail "SKILL.md Step 18 restore gate must cover bash opt-in"
grep -Fq 'elif [ ! -f "$IMPLEMENT_TMPDIR/finalize-state.sh" ]; then' "$SKILL_MD" \
  || fail "SKILL.md Step 18 restore gate must cover missing finalize-state on Python path"
grep -Fq '[ -n "$_ship_step" ] && [ "$_ship_step" != "$_final_step" ]' "$SKILL_MD" \
  || fail "SKILL.md Step 18 restore gate must cover stale finalize-state on Python path"
python_fence=$(awk '
  /if \[ "\$\{LARCH_SHIP_PR_IMPL:-python\}" != "bash" \]; then/ { in_py=1 }
  in_py { print }
  in_py && /^else$/ { exit }
' "$SKILL_MD")
printf '%s\n' "$python_fence" | grep -Fq -- '--no-logs-commit "$no_logs_commit"' \
  || fail "SKILL.md Python invoke fence must include --no-logs-commit inside python branch"
grep -Fq 'existing_stall_tracking=$(read_finalize STALL_TRACKING "")' "$RESTORE_FINALIZE_SH" \
  || fail "restore-finalize-state.sh must read existing finalize STALL_TRACKING"
grep -Fq 'STALL_TRACKING) value=true ;;' "$RESTORE_FINALIZE_SH" \
  || fail "restore-finalize-state.sh must preserve existing finalize STALL_TRACKING=true"
grep -Fq 'STALL_TRACKING=false' "$REPO_ROOT/scripts/test-restore-finalize-state.sh" \
  || fail "restore-finalize-state harness must seed ship-pr STALL_TRACKING=false"

[[ -f "$RESTORE_FINALIZE_SH" ]] || fail "scripts/restore-finalize-state.sh missing"
[[ -x "$RESTORE_FINALIZE_SH" ]] || fail "scripts/restore-finalize-state.sh must be executable"
[[ -f "$REPO_ROOT/scripts/restore-finalize-state.md" ]] || fail "scripts/restore-finalize-state.sh must have sibling restore-finalize-state.md"

[[ -f "$LINT_FIX_LOOP_SH" ]] || fail "scripts/lint-fix-loop.sh missing"
[[ -x "$LINT_FIX_LOOP_SH" ]] || fail "scripts/lint-fix-loop.sh must be executable"
[[ -f "$REPO_ROOT/scripts/lint-fix-loop.md" ]] || fail "scripts/lint-fix-loop.sh must have sibling lint-fix-loop.md"
grep -qE '^[[:space:]]*(source|\.)[[:space:]].*lib-quiet\.sh' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must source lib-quiet.sh"
grep -qE '^[[:space:]]*(source|\.)[[:space:]].*lib-cursor-launcher-common\.sh' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must source lib-cursor-launcher-common.sh"
grep -Fq 'launch-codex-exec.sh' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must dispatch Codex through launch-codex-exec.sh"
grep -Fq 'run-external-agent.sh' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must dispatch Cursor through run-external-agent.sh"

step3_lint_status=0
awk '
  /<!-- step:3/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0 }
  in_step && /lint-fix-loop\.sh/ { found = 1 }
  END { if (!found) exit 1 }
' "$SKILL_MD" || step3_lint_status=$?
[[ "$step3_lint_status" == "0" ]] || fail "Step 3 region must reference lint-fix-loop.sh"

step6_lint_status=0
awk '
  /<!-- step:6/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0 }
  in_step && /lint-fix-loop\.sh/ { found = 1 }
  END { if (!found) exit 1 }
' "$SKILL_MD" || step6_lint_status=$?
[[ "$step6_lint_status" == "0" ]] || fail "Step 6 region must reference lint-fix-loop.sh"

step5_lint_status=0
awk '
  /<!-- step:5/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0 }
  in_step && /lint-fix-loop\.sh/ { found = 1 }
  END { if (!found) exit 1 }
' "$SKILL_MD" || step5_lint_status=$?
[[ "$step5_lint_status" == "0" ]] || fail "Step 5 region must reference lint-fix-loop.sh"

step5_fence_tmp=$(mktemp "${TMPDIR:-/tmp}/larch-step5-fence.XXXXXX")
awk '
  /<!-- step:5/ { in_step = 1; next }
  in_step && /^```bash$/ { in_fence = 1; next }
  in_step && in_fence && /^```$/ { exit }
  in_step && in_fence { print }
' "$SKILL_MD" >"$step5_fence_tmp"
[[ -s "$step5_fence_tmp" ]] || fail "SKILL.md Step 5 telemetry fence missing"
for needle in \
  '--count-prior-degraded "$IMPLEMENT_TMPDIR" 1' \
  "printf 'DYNAMIC_ARCHETYPES_CAP=%s\\n'" \
  "printf 'PRIOR_DEGRADED_ROUNDS=%s\\n'" \
  "printf 'ROUND_CAP=%s\\n'" \
  "printf 'EFFECTIVE_ROUND_CAP=%s\\n'"
do
  grep -Fq -- "$needle" "$step5_fence_tmp" || fail "Step 5 telemetry fence missing: $needle"
done
if grep -Fq 'dynamic_archetypes_value' "$step5_fence_tmp"; then
  fail "Step 5 telemetry fence must not read dead dynamic_archetypes_value state"
fi
step5_session_cap_line=$(grep -n 'LARCH_DYNAMIC_ARCHETYPES_MAX=' "$step5_fence_tmp" | head -1 | cut -d: -f1 || true)
step5_ambient_cap_line=$(grep -n 'LARCH_DYNAMIC_ARCHETYPES_MAX:-' "$step5_fence_tmp" | head -1 | cut -d: -f1 || true)
if [ -z "$step5_session_cap_line" ] || [ -z "$step5_ambient_cap_line" ] || [ "$step5_session_cap_line" -ge "$step5_ambient_cap_line" ]; then
  fail "Step 5 telemetry fence must resolve session-env dynamic archetypes before ambient env"
fi

step5_cap_tmp=$(mktemp -d "${TMPDIR:-/tmp}/larch-step5-cap.XXXXXX")
cat >"$step5_cap_tmp/session-env.sh" <<EOF
LARCH_CLAUDE_PLUGIN_ROOT=$REPO_ROOT
CODEX_PRESENT=true
CURSOR_PRESENT=false
LARCH_TOKEN_SESSION_ID=step5-cap-run
LARCH_TIMING_LEDGER=$step5_cap_tmp/timing-ledger.tsv
LARCH_DYNAMIC_ARCHETYPES_MAX=2
EOF
printf '%s\n' "step5-cap-run" >"$step5_cap_tmp/session-id"
printf '%s\n' "Feature description" >"$step5_cap_tmp/feature-description.txt"
printf '%s\n' "Plan body for Step 5 cap structure regression." >"$step5_cap_tmp/plan.txt"
set +e
step5_fence_out=$(CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$step5_cap_tmp" LARCH_DYNAMIC_ARCHETYPES_MAX=7 bash "$step5_fence_tmp" 2>&1)
step5_fence_rc=$?
set -e
[[ "$step5_fence_rc" == "0" ]] || fail "Step 5 telemetry fence must execute in harness (rc=$step5_fence_rc, output=$step5_fence_out)"
step5_banner_cap=$(printf '%s\n' "$step5_fence_out" | awk -F= '$1 == "DYNAMIC_ARCHETYPES_CAP" {print $2; exit}')
[[ "$step5_banner_cap" == "2" ]] || fail "Step 5 banner cap must prefer session-env over ambient env (got: ${step5_banner_cap:-<empty>})"
step5_spy="$step5_cap_tmp/review-spy.sh"
cat >"$step5_spy" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$RUN_STEP5_ARGV_FILE"
printf 'STEP5_REVIEW_STATUS=complete\n'
EOF
chmod +x "$step5_spy"
step5_argv_file="$step5_cap_tmp/review.argv"
RUN_STEP5_REVIEW_SH="$step5_spy" RUN_STEP5_ARGV_FILE="$step5_argv_file" LARCH_DYNAMIC_ARCHETYPES_MAX=7 \
  "$REPO_ROOT/scripts/run-step5-review.sh" --implement-tmpdir "$step5_cap_tmp" --mode loop >/dev/null
step5_forwarded_cap=$(awk 'prev == "--dynamic-archetypes" {print; exit} {prev = $0}' "$step5_argv_file")
[[ "$step5_forwarded_cap" == "$step5_banner_cap" ]] || fail "Step 5 banner cap must match forwarded CLI dynamic-archetypes cap"
rm -rf "$step5_cap_tmp"
rm -f "$step5_fence_tmp"

if grep -Eiq 'diagnose([[:space:]]*,[[:space:]]*|[[:space:]]*\+[[:space:]]*)fix' "$SKILL_MD"; then
  fail "SKILL.md must not contain bare diagnose/fix relevant-checks loops without lint-fix-loop.sh routing"
fi

# Pin that ship-pr.sh run_checks_phase calls lint-fix-loop.sh internally, so the
# orchestrator never needs to fix PHASE=checks failures via main-agent Edit/Write.
grep -q 'lint-fix-loop\.sh' "$SHIP_PR_SH" \
  || fail "ship-pr.sh must reference lint-fix-loop.sh (run_checks_phase call site)"
grep -q 'ship-pr-ci-initial' "$SHIP_PR_SH" \
  || fail "ship-pr.sh run_checks_phase must pass --site ship-pr-ci-initial to lint-fix-loop.sh"
grep -q 'ship-pr-ci-initial' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must accept --site ship-pr-ci-initial"
grep -q 'ship-pr-ci-merge' "$SHIP_PR_SH" \
  || fail "ship-pr.sh CI failure recovery must pass --site ship-pr-ci-merge to lint-fix-loop.sh"
grep -q 'ship-pr-ci-merge' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must accept --site ship-pr-ci-merge"

# Step 8+ Exit 3: first-fixer-non-health autonomous sub-procedure (ordered 1–12) must be documented.
step8_exit3_status=0
awk '
  /## Step 8\+/ { in8 = 1; next }
  in8 && /^## / { in8 = 0 }
  in8 && /\*\*Exit 3\*\*/ { in_exit3 = 1 }
  in_exit3 && /^- \*\*Exit [0-9]/ && !/\*\*Exit 3\*\*/ { in_exit3 = 0 }
  in_exit3 {
    if ($0 ~ /first-fixer-non-health/) f = 1
    if ($0 ~ /^  1\./) s1 = 1
    if ($0 ~ /^  12\./) s12 = 1
  }
  END { if (!(f && s1 && s12)) exit 1 }
' "$SKILL_MD" || step8_exit3_status=$?
[[ "$step8_exit3_status" == "0" ]] || fail "SKILL.md Step 8+ Exit 3 must document first-fixer-non-health and autonomous sub-steps 1 through 12"

# Pin LAUNCHER_FAILURE_* canonical tokens across classifier, launchers, and ship-pr guard.
for _pin in none health other auth quota binary-missing health-probe timeout parse refusal unknown; do
  grep -Fq "$_pin" "$REPO_ROOT/scripts/lib-external-launcher-common.sh" \
    || fail "lib-external-launcher-common.sh must contain canonical token: $_pin"
done
for _pin in none health other auth quota binary-missing health-probe timeout parse refusal unknown; do
  grep -Fq "$_pin" "$REPO_ROOT/scripts/launch-cursor-ci.sh" \
    || fail "launch-cursor-ci.sh must contain canonical token: $_pin"
  grep -Fq "$_pin" "$REPO_ROOT/scripts/launch-codex-ci.sh" \
    || fail "launch-codex-ci.sh must contain canonical token: $_pin"
  grep -Fq "$_pin" "$REPO_ROOT/scripts/launch-claude-ci.sh" \
    || fail "launch-claude-ci.sh must contain canonical token: $_pin"
done
grep -Fq 'first-fixer-non-health' "$REPO_ROOT/scripts/ship-pr.sh" \
  || fail "ship-pr.sh must reference first-fixer-non-health"
grep -Fq 'LAUNCHER_FAILURE_CLASS' "$REPO_ROOT/scripts/ship-pr.sh" \
  || fail "ship-pr.sh must reference LAUNCHER_FAILURE_CLASS"

[[ -f "$LIB_FINALIZE_KEYS_SH" ]] || fail "scripts/lib-finalize-state-keys.sh missing"
[[ -f "$REPO_ROOT/scripts/lib-finalize-state-keys.md" ]] || fail "scripts/lib-finalize-state-keys.sh must have sibling lib-finalize-state-keys.md"
grep -qE '^[[:space:]]*(source|\.)[[:space:]].*lib-finalize-state-keys\.sh' "$RESTORE_FINALIZE_SH" \
  || fail "restore-finalize-state.sh must source lib-finalize-state-keys.sh"
grep -qE '^[[:space:]]*(source|\.)[[:space:]].*lib-finalize-state-keys\.sh' "$SHIP_PR_SH" \
  || fail "ship-pr.sh must source lib-finalize-state-keys.sh"

! grep -Fq -- '--workflow-path' "$REPO_ROOT/scripts/implement-bootstrap.sh" \
  || fail "implement-bootstrap.sh must not persist workflow path"
! grep -Fq 'workflow-path' "$REPO_ROOT/scripts/implement-bootstrap.sh" \
  || fail "implement-bootstrap.sh must not call timing-ledger workflow-path"
! grep -Fq -- '--workflow' "$REPO_ROOT/skills/implement/scripts/run-step2-dispatch.sh" \
  || fail "run-step2-dispatch.sh must not pass --workflow"
! grep -Fq 'conventional hard workflow path' "$REPO_ROOT/.claude-plugin/plugin.json" \
  || fail "plugin.json must not advertise a retired /implement hard workflow path"
grep -Fq '/implement` has no workflow tier/path dimension' "$REPO_ROOT/.claude-plugin/plugin.json" \
  || fail "plugin.json must describe /implement as having no workflow tier/path dimension"
# Post-cutover: /implement no longer accepts --hard, so hard_mode references must be gone.
! grep -Fq 'hard_mode' "$SKILL_MD" \
  || fail "Post-plan router must not reference hard_mode (--hard flag removed in cutover)"
# Post-cutover: plan materialization uses conventional $IMPLEMENT_TMPDIR/plan.txt; do not resurrect persist-post-plan-keys.
! grep -Fq 'persist-post-plan-keys' "$SKILL_MD" \
  || fail "skills/implement/SKILL.md must not reference persist-post-plan-keys (retired #2487)"
! grep -Fq 'post-design-boundary.sh' "$SKILL_MD" \
  || fail "skills/implement/SKILL.md must not reference post-design-boundary.sh (retired #2487)"
grep -Fq 'persist-implement-run-flags.sh' "$REPO_ROOT/scripts/implement-bootstrap.sh" \
  || fail "implement-bootstrap.sh must invoke persist-implement-run-flags.sh"

step17_status=0
awk '
  /<!-- step:17/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0 }
  in_step && /Fork CI Dry-Run Complete/ { bad = 1 }
  in_step && /--draft was set/ { bad = 1 }
  in_step && /--merge was not set/ { bad = 1 }
  in_step && /--design-only was set/ { bad = 1 }
  in_step && /write-final-report\.sh.*--print-stdout/ { good = 1 }
  END { if (bad) exit 2; if (!good) exit 1 }
' "$SKILL_MD" || step17_status=$?
[[ "$step17_status" == "0" ]] || fail "SKILL.md Step 17 must drop branched prose and use write-final-report.sh --print-stdout"

step18_status=0
awk '
  /<!-- step:18/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0; in_bash = 0 }
  in_step && /^```(bash|sh|shell)[[:space:]]*$/ { in_bash = 1; next }
  in_step && in_bash && /^```[[:space:]]*$/ { in_bash = 0; next }
  in_step && /step-18b-final-report\.sh/ && /--implement-tmpdir "\$IMPLEMENT_TMPDIR"/ { wrapper = 1 }
  in_step && /EMIT_BODY=\$\(printf/ { emit_parse = 1 }
  in_step && /WFR_RC=\$\(printf/ { wfr_parse = 1 }
  in_step && /STEP17_EMITTED_PRESENT=\$\(printf/ { step17_parse = 1 }
  in_step && in_bash && /write-final-report\.sh/ && /--print-stdout/ { bad_print = 1 }
  in_step && /EMIT_BODY=true/ && /WFR_RC=0/ && /summary-final\.md/ { emit_guard = 1 }
  END {
    if (!wrapper || !emit_parse || !wfr_parse || !step17_parse || bad_print || !emit_guard) exit 1
    exit 0
  }
' "$SKILL_MD" || step18_status=$?
[[ "$step18_status" == "0" ]] || fail "SKILL.md Step 18 must delegate to step-18b-final-report.sh and gate orchestrator emit on EMIT_BODY=true with WFR_RC=0"

COMMIT_IMPL_SH="$REPO_ROOT/skills/implement/scripts/commit-implementation.sh"
COMMIT_REVIEW_SH="$REPO_ROOT/skills/implement/scripts/commit-review-fixes.sh"
STEP_7A_SH="$REPO_ROOT/skills/implement/scripts/step-7a.sh"
GEN_DIAGRAM_SH="$REPO_ROOT/skills/implement/scripts/generate-code-flow-diagram.sh"

[[ -f "$COMMIT_IMPL_SH" ]] || fail "skills/implement/scripts/commit-implementation.sh missing"
grep -qF 'LARCH_TIMING_SKILL=implement "$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 4 — commit implementation"' "$COMMIT_IMPL_SH" \
  || fail "commit-implementation.sh must contain Step 4 timing-ledger mark pinned to implement"

[[ -f "$COMMIT_REVIEW_SH" ]] || fail "skills/implement/scripts/commit-review-fixes.sh missing"
grep -qF 'LARCH_TIMING_SKILL=implement "$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 7 — commit review fixes"' "$COMMIT_REVIEW_SH" \
  || fail "commit-review-fixes.sh must contain Step 7 timing-ledger mark pinned to implement"

[[ -f "$STEP_7A_SH" ]] || fail "skills/implement/scripts/step-7a.sh missing"
grep -qF 'LARCH_TIMING_SKILL=implement "$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 7a — code flow diagram"' "$STEP_7A_SH" \
  || fail "step-7a.sh must contain Step 7a timing-ledger mark pinned to implement"
grep -qF "DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement \"\$PLUGIN_ROOT/scripts/timing-report.sh\" --full --format json" "$STEP_7A_SH" \
  || fail "step-7a.sh must render timing-report with design tmpdir cleared and skill pinned to implement"
[[ -f "$GEN_DIAGRAM_SH" ]] || fail "skills/implement/scripts/generate-code-flow-diagram.sh missing"
grep -qF 'timing-ledger.sh" mark "Step 7a — code flow diagram"' "$GEN_DIAGRAM_SH" \
  && fail "generate-code-flow-diagram.sh must not contain Step 7a timing-ledger mark (consolidated into step-7a.sh)"

REFRESH_RUN_LOGS_SH="$REPO_ROOT/scripts/refresh-run-logs.sh"
IMPLEMENT_FINALIZE_SH="$REPO_ROOT/scripts/implement-finalize.sh"
IMPLEMENT_BOOTSTRAP_SH="$REPO_ROOT/scripts/implement-bootstrap.sh"
[[ -f "$REFRESH_RUN_LOGS_SH" ]] || fail "scripts/refresh-run-logs.sh missing"
grep -qF "DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement \"\$SCRIPT_DIR/timing-report.sh\" --full --format json" "$REFRESH_RUN_LOGS_SH" \
  || fail "refresh-run-logs.sh must render timing-report with design tmpdir cleared and skill pinned to implement"
[[ -f "$IMPLEMENT_FINALIZE_SH" ]] || fail "scripts/implement-finalize.sh missing"
grep -qF 'LARCH_TIMING_SKILL=implement "$SCRIPT_DIR/timing-ledger.sh" mark "$label"' "$IMPLEMENT_FINALIZE_SH" \
  || fail "implement-finalize.sh must contain timing-ledger marks pinned to implement"
grep -qF "DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement \"\$SCRIPT_DIR/timing-report.sh\" --since-last-mark --terse" "$IMPLEMENT_FINALIZE_SH" \
  || fail "implement-finalize.sh must render timing-report with design tmpdir cleared and skill pinned to implement"
[[ -f "$IMPLEMENT_BOOTSTRAP_SH" ]] || fail "scripts/implement-bootstrap.sh missing"
grep -qF 'LARCH_TIMING_SKILL=implement "$SCRIPT_DIR/timing-ledger.sh" mark "Step 0 — preflight"' "$IMPLEMENT_BOOTSTRAP_SH" \
  || fail "implement-bootstrap.sh must contain Step 0 preflight timing-ledger mark pinned to implement"
grep -qF 'LARCH_TIMING_SKILL=implement "$SCRIPT_DIR/timing-ledger.sh" mark "Step 0 — tracking issue"' "$IMPLEMENT_BOOTSTRAP_SH" \
  || fail "implement-bootstrap.sh must contain Step 0 tracking issue timing-ledger mark pinned to implement"
grep -qF 'LARCH_TIMING_SKILL=implement "$SCRIPT_DIR/timing-ledger.sh" mark "implement Step 0 — plan materialization"' "$IMPLEMENT_BOOTSTRAP_SH" \
  || fail "implement-bootstrap.sh must contain plan materialization timing-ledger mark pinned to implement"

implement_timing_emitters=(
  "scripts/implement-bootstrap.sh"
  "skills/implement/scripts/step2-implement.sh"
  "skills/implement/scripts/commit-implementation.sh"
  "skills/implement/scripts/commit-review-fixes.sh"
  "skills/implement/scripts/step-7a.sh"
  "scripts/refresh-run-logs.sh"
  "scripts/implement-finalize.sh"
  "scripts/step-telemetry-mark.sh"
  "scripts/run-step5-review.sh"
  "scripts/run-relevant-checks-captured.sh"
  "scripts/launch-codex-implement.sh"
  "scripts/launch-cursor-implement.sh"
  "scripts/launch-codex-ci.sh"
  "scripts/launch-cursor-ci.sh"
  "scripts/launch-claude-ci.sh"
)

for rel in "${implement_timing_emitters[@]}"; do
  path="$REPO_ROOT/$rel"
  [[ -f "$path" ]] || fail "implement timing emitter missing: $rel"
  awk -v rel="$rel" '
    function is_timing_call(line) {
      return ((index(line, "timing-ledger.sh") > 0 && (index(line, " mark ") > 0 || index(line, " record-vendor-task") > 0)) || index(line, "timing-report.sh") > 0)
    }
    is_timing_call($0) && index($0, "LARCH_TIMING_SKILL=implement") == 0 {
      printf "%s:%d timing invocation lacks same-line LARCH_TIMING_SKILL=implement pin: %s\n", rel, NR, $0 > "/dev/stderr"
      offending = 1
    }
    END { exit offending }
  ' "$path" || fail "implement timing emitter lacks same-line LARCH_TIMING_SKILL=implement pin: $rel"
  if grep -Fq 'workflow_path' "$path"; then
    fail "production implement timing emitter must not read workflow_path: $rel"
  fi
done

for rel in "skills/implement/scripts/run-step2-dispatch.sh" "skills/implement/scripts/step2-implement.sh"; do
  path="$REPO_ROOT/$rel"
  [[ -f "$path" ]] || fail "Step 2 dispatch stack file missing: $rel"
  ! grep -Fq 'workflow_path' "$path" \
    || fail "Step 2 dispatch stack must not reference workflow_path: $rel"
  ! grep -Fq -- '--workflow' "$path" \
    || fail "Step 2 dispatch stack must not pass workflow flags: $rel"
  ! grep -Eq '(^|[^A-Za-z0-9_])(HARD|SIMPLE)([^A-Za-z0-9_]|$)' "$path" \
    || fail "Step 2 dispatch stack must not branch on HARD/SIMPLE workflow tokens: $rel"
done

# Pin Exit 4 handling in SKILL.md: must direct orchestrator to "Continue to Step 16"
exit4_step16_status=0
awk '
  /\*\*Exit 4\*\*/ { window = 15 }
  window > 0 && /Continue to Step 16/ { found = 1 }
  window > 0 { window-- }
  END { if (!found) exit 1 }
' "$SKILL_MD" || exit4_step16_status=$?
[[ "$exit4_step16_status" == "0" ]] || fail "SKILL.md Exit 4 prose must direct orchestrator to 'Continue to Step 16'"

# Pin that ship-pr.sh STALL_STEP=12d branch emits the branch-local diagnostic.
stall12d_directive_status=0
awk '
  /policy_denied\|admin_failed\|error\)/ { in_branch = 1 }
  in_branch && /ORCHESTRATOR DIRECTIVE \(STALL_STEP=12d\)/ { found_banner = 1 }
  in_branch && /DO NOT improvise recovery\./ { found_directive = 1 }
  in_branch && /exit 4/ {
    if (found_banner && found_directive) {
      success = 1
      exit 0
    }
    exit 1
  }
  END { if (!success) exit 1 }
' "$SHIP_PR_SH" || stall12d_directive_status=$?
[[ "$stall12d_directive_status" == "0" ]] \
  || fail "ship-pr.sh must emit the ORCHESTRATOR DIRECTIVE (STALL_STEP=12d) DO NOT improvise diagnostic on the STALL_STEP=12d exit 4 path"

# shellcheck disable=SC2016
grep -Fq 'if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then main' "$SHIP_PR_SH" \
  || fail "ship-pr.sh must gate main behind BASH_SOURCE vs argv0 (source-safe entry)"
grep -Fq 'recovery_waterfall_paths_delta_revert' "$SHIP_PR_SH" \
  || fail "ship-pr.sh must define recovery_waterfall_paths_delta_revert (rollback helper)"
# shellcheck disable=SC2016
grep -Fq 'git restore --staged -- "$path"' "$SHIP_PR_SH" \
  || fail "ship-pr recovery rollback must use git restore --staged with a quoted path operand (FINDING_14/F23)"
grep -Fq 'while IFS= read -r path' "$SHIP_PR_SH" \
  || fail "ship-pr recovery rollback must iterate paths with IFS= read -r (safe for spaces/globs)"

grep -Fq '**Terminal disposition invariant:**' "$SKILL_MD" \
  || fail "SKILL.md must retain OOS Terminal disposition invariant paragraph"

grep -Fq 'NEVER silently drop a voted-in OOS finding' "$SKILL_MD" \
  || fail "SKILL.md must retain NEVER rule prohibiting silent OOS drops"

# shellcheck disable=SC2016
grep -Fq 'NEVER set `OOS_PENDING=false` without a passing `oos-disposition-checkpoint.sh` invocation' "$SKILL_MD" \
  || fail "SKILL.md must retain NEVER #15 checkpoint-before-clear pin (OOS_PENDING vs oos-disposition-checkpoint.sh)"
# shellcheck disable=SC2016
grep -Fq '${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/oos-disposition-checkpoint.sh' "$SKILL_MD" \
  || fail "SKILL.md Step 8+ must reference oos-disposition-checkpoint.sh"


OOS_PIPELINE_MD="$REFS_DIR/oos-pipeline.md"
MATERIALIZE_OOS_SH="$REPO_ROOT/skills/implement/scripts/materialize-manifest-oos.sh"
MATERIALIZE_OOS_MD="$REPO_ROOT/skills/implement/scripts/materialize-manifest-oos.md"
STEP2_IMPLEMENT_SH="$REPO_ROOT/skills/implement/scripts/step2-implement.sh"
PY_SHIP="$REPO_ROOT/python/ship.py"

[[ -f "$OOS_PIPELINE_MD" ]] || fail "oos-pipeline.md must exist under skills/implement/references"
# shellcheck disable=SC2016
load_count=$(grep -Fc '${CLAUDE_PLUGIN_ROOT}/skills/implement/references/oos-pipeline.md' "$SKILL_MD" || true)
[[ "${load_count:-0}" -ge 3 ]] || fail "SKILL.md must load oos-pipeline.md at least three Step 9a.1 entry points"
! grep -Fq 'Out-of-Scope Handling' "$SKILL_MD" \
  || fail "SKILL.md must not retain phantom Out-of-Scope Handling section citations"
# shellcheck disable=SC2016
grep -Fq '**MANDATORY — READ ENTIRE FILE before executing the OOS pipeline**: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/oos-pipeline.md`' "$SKILL_MD" \
  || fail "SKILL.md must contain the mandatory oos-pipeline.md load directive"
grep -Fq 'needs_user_reason` (`oos-filing` requires' "$SKILL_MD" \
  || fail "Python oos-filing dispatch must mention oos-pipeline.md load context"
grep -Fq '**OOS checkpoint**: when `OOS_PENDING=true`' "$SKILL_MD" \
  || fail "OOS checkpoint paragraph missing"
grep -Fq '**Exit 0**: if `OOS_PENDING=true`' "$SKILL_MD" \
  || fail "Exit 0 OOS_PENDING branch missing"
awk '
  /\*\*Exit 0\*\*: if `OOS_PENDING=true`/ { in_exit = 1; seen_exit = 0; n_exit = 0 }
  in_exit && /\*\*MANDATORY — READ ENTIRE FILE before executing the OOS pipeline\*\*: `\$\{CLAUDE_PLUGIN_ROOT\}\/skills\/implement\/references\/oos-pipeline\.md`/ { seen_exit = 1 }
  in_exit { n_exit++; if (n_exit > 8) in_exit = 0 }
  /\*\*OOS checkpoint\*\*: when `OOS_PENDING=true`/ { in_checkpoint = 1; seen_checkpoint = 0; n_checkpoint = 0 }
  in_checkpoint && /\*\*MANDATORY — READ ENTIRE FILE before executing the OOS pipeline\*\*: `\$\{CLAUDE_PLUGIN_ROOT\}\/skills\/implement\/references\/oos-pipeline\.md`/ { seen_checkpoint = 1 }
  in_checkpoint { n_checkpoint++; if (n_checkpoint > 8) in_checkpoint = 0 }
  /needs_user_reason` \(`oos-filing` requires/ { in_python = 1; seen_python = 0; n_python = 0 }
  in_python && /\*\*MANDATORY — READ ENTIRE FILE before executing the OOS pipeline\*\*: `\$\{CLAUDE_PLUGIN_ROOT\}\/skills\/implement\/references\/oos-pipeline\.md`/ { seen_python = 1 }
  in_python { n_python++; if (n_python > 8) in_python = 0 }
  END { exit(seen_exit && seen_checkpoint && seen_python ? 0 : 1) }
' "$SKILL_MD" || fail "SKILL.md must keep mandatory oos-pipeline.md load directive scoped to Exit 0, OOS checkpoint, and Python oos-filing dispatch"

grep -Fq '3.4. **Combine pass**' "$OOS_PIPELINE_MD" \
  || fail "oos-pipeline.md must define step 3.4"
grep -Fq '3.4b. **Per-run cap pre-pass**' "$OOS_PIPELINE_MD" \
  || fail "oos-pipeline.md must define step 3.4b"
grep -Fq '## oos-issues-created.md sentinel format' "$OOS_PIPELINE_MD" \
  || fail "oos-pipeline.md must pin oos-issues-created.md sentinel format"
grep -Fq '| OOS title | Issue | URL |' "$OOS_PIPELINE_MD" \
  || fail "sentinel table header missing"
grep -Fq -- '- **Filed**: <N>' "$OOS_PIPELINE_MD" \
  || fail "sentinel filed tally missing"
grep -Fq 'issues/<n>' "$OOS_PIPELINE_MD" \
  || fail "sentinel URL token issues/<n> missing"
grep -Fq 'oos-issue-cap.sh --input-file' "$OOS_PIPELINE_MD" \
  || fail "oos-pipeline.md must invoke oos-issue-cap.sh --input-file"
grep -Fq 'oos-file-conflict-deps.sh --input-file' "$OOS_PIPELINE_MD" \
  || fail "oos-pipeline.md must invoke oos-file-conflict-deps.sh --input-file"
# shellcheck disable=SC2016
grep -Fq -- '--output "$IMPLEMENT_TMPDIR/oos-intra-batch-deps.tsv"' "$OOS_PIPELINE_MD" \
  || fail "oos-pipeline.md must pin oos-intra-batch-deps.tsv output"
grep -Fq 'ISSUE_<i>_DUPLICATE_OF_URL=' "$OOS_PIPELINE_MD" \
  || fail "oos-pipeline.md must parse duplicate-of URL"
grep -Fq 'ISSUE_<i>_DUPLICATE_OF_NUMBER=' "$OOS_PIPELINE_MD" \
  || fail "oos-pipeline.md must parse duplicate-of number"
grep -Fq 'ISSUES_FAILED>0`, do not write `$IMPLEMENT_TMPDIR/oos-issues-created.md`' "$OOS_PIPELINE_MD" \
  || fail "partial failure must suppress sentinel write"
grep -Fq 'do **not** append accepted disposition URL rows to the `oos-issues` NDJSON batch' "$OOS_PIPELINE_MD" \
  || fail "partial failure must suppress gate-visible accepted oos-issues rows"
awk '
  /ISSUES_FAILED>0/ { window = 8 }
  window > 0 && /append accepted disposition URL rows/ && $0 !~ /do \*\*not\*\* append accepted disposition URL rows/ {
    exit 1
  }
  window > 0 { window-- }
' "$OOS_PIPELINE_MD" \
  || fail "ISSUES_FAILED>0 guidance must not sit near positive accepted-URL append instructions"

never5_block=$(awk '/^5\. \*\*NEVER let the Step 9a\.1 sentinel/{flag=1; print; next} flag && /^6\. \*\*/{exit} flag{print}' "$SKILL_MD")
if printf '%s\n' "$never5_block" | grep -Fq 'write --log-root "$IMPLEMENT_TMPDIR/larch-logs" --batch run-statistics'; then
  fail "NEVER #5 How to apply must not write run-statistics"
fi
printf '%s\n' "$never5_block" | grep -Fq 'append --log-root "$IMPLEMENT_TMPDIR/larch-logs" --batch oos-issues' \
  || fail "NEVER #5 How to apply must append oos-issues"
grep -Fq 'do not write `run-statistics` here' "$OOS_PIPELINE_MD" \
  || fail "oos-pipeline.md step 3 must forbid run-statistics on sentinel recovery"
grep -Fq 'larch-log.sh write --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --batch run-statistics' "$SKILL_MD" \
  || fail "post-checkpoint run-statistics write must remain in OOS checkpoint prose"

grep -Fq 'dedicated `- **focus-area**:` field line whose value begins with `security`' "$OOS_PIPELINE_MD" \
  || fail "security predicate must use dedicated focus-area line beginning with security"
grep -Fq 'Prose such as `focus-area = security` inside a `**Description**` line does **not** mark' "$OOS_PIPELINE_MD" \
  || fail "security predicate must not treat Description prose as security-routed"
# shellcheck disable=SC2016
grep -Fq '$DESIGN_TMPDIR/oos-accepted-design.md' "$OOS_PIPELINE_MD" \
  || fail "design source resolver must mention DESIGN_TMPDIR"
grep -Fq 'design-export/oos-accepted-design.md' "$OOS_PIPELINE_MD" \
  || fail "design source resolver must mention design-export path"
# shellcheck disable=SC2016
grep -Fq '$IMPLEMENT_TMPDIR/oos-accepted-design.md' "$OOS_PIPELINE_MD" \
  || fail "design source resolver must mention flat implement tmpdir path"
grep -Fq 'Still run step 6' "$OOS_PIPELINE_MD" \
  || fail "all-already-filed branch must still run step 6"
grep -Fq 'Treat both created URLs and duplicate-of URLs as valid disposition URLs' "$OOS_PIPELINE_MD" \
  || fail "duplicate-of URLs must count as disposition URLs"
grep -Fq 'Rule A — same logical concern' "$OOS_PIPELINE_MD" \
  || fail "combine substance must include Rule A"
grep -Fq 'oos-grouping-worksheet.md' "$OOS_PIPELINE_MD" \
  || fail "combine substance must include worksheet"
grep -Fq 'INPUT_<i>' "$OOS_PIPELINE_MD" \
  || fail "worksheet contract must pin INPUT_<i>"
[[ -x "$MATERIALIZE_OOS_SH" ]] || fail "materialize-manifest-oos.sh must exist and be executable"
grep -Fq 'materialize-manifest-oos.sh' "$STEP2_IMPLEMENT_SH" \
  || fail "step2-implement.sh must invoke materialize-manifest-oos.sh"
grep -Fq 'materialize-manifest-oos.sh' "$SHIP_PR_SH" \
  || fail "ship-pr.sh must invoke materialize-manifest-oos.sh"
grep -Fq 'materialize-manifest-oos.sh' "$PY_SHIP" \
  || fail "python/ship.py must invoke materialize-manifest-oos.sh"
python_materialize_order=0
awk '
  /^def run_ship\(/ { in_fn=1; next }
  in_fn && /^def / { exit }
  in_fn && /_materialize_manifest_oos/ && mat == 0 { mat = NR }
  in_fn && /_oos_gate/ && gate == 0 { gate = NR }
  END { if (mat == 0 || gate == 0 || mat >= gate) exit 1 }
' "$PY_SHIP" || python_materialize_order=$?
[[ "$python_materialize_order" == "0" ]] \
  || fail "python/ship.py must materialize manifest OOS before _oos_gate"
ship_pr_materialize_order=0
awk '
  /^run_pr_prep_phase\(\)/ { in_fn=1; next }
  in_fn && /^}/ { exit }
  in_fn && /bash "\$materialize_oos"/ && mat == 0 { mat = NR }
  in_fn && /state_set OOS_PENDING true/ && pend == 0 { pend = NR }
  END { if (mat == 0 || pend == 0 || mat >= pend) exit 1 }
' "$SHIP_PR_SH" || ship_pr_materialize_order=$?
[[ "$ship_pr_materialize_order" == "0" ]] \
  || fail "ship-pr.sh must materialize manifest OOS before first pr-prep OOS_PENDING=true"
step1_block=$(awk '/^1\. \*\*Resolve accepted-OOS inputs\*\*/{flag=1; print; next} flag && /^2\. \*\*/{exit} flag{print}' "$OOS_PIPELINE_MD")
if printf '%s\n' "$step1_block" | grep -Fq 'harvest' && printf '%s\n' "$step1_block" | grep -Fq 'MANIFEST_PATH'; then
  fail "oos-pipeline.md step 1 must not harvest MANIFEST_PATH"
fi
if printf '%s\n' "$step1_block" | grep -Fq 'jq' && printf '%s\n' "$step1_block" | grep -Fq 'manifest'; then
  fail "oos-pipeline.md step 1 must not parse manifest JSON with jq"
fi
grep -Fq 'full Step 9a.1 steps 1–7' "$SKILL_MD" \
  || fail "Python oos-filing dispatch must mention full steps 1–7"
grep -Fq '<REDACTED-TOKEN>' "$OOS_PIPELINE_MD" \
  || fail "oos-pipeline.md must pin redaction token"
grep -Fq '<INTERNAL-URL>' "$OOS_PIPELINE_MD" \
  || fail "oos-pipeline.md must pin internal URL redaction"
grep -Fq '<REDACTED-PII>' "$OOS_PIPELINE_MD" \
  || fail "oos-pipeline.md must pin PII redaction token"
grep -Fq 'monotonic `OOS_N`' "$MATERIALIZE_OOS_MD" \
  || fail "materialize-manifest-oos contract must pin monotonic OOS_N allocation"

# Folded Step 0 / admission structural pins (fix-issue removal; Step 0 + Preflight admission)
grep -Fq 'scripts/implement-admission.sh' "$SKILL_MD" \
  || fail "SKILL.md must reference scripts/implement-admission.sh"
grep -Fq '1. **Admission gate**' "$SKILL_MD" \
  || fail "SKILL.md Preflight must contain numbered Admission gate step"
grep -Fq '**Preflight — admission gate known limitation (D3)**' "$SKILL_MD" \
  || fail "SKILL.md must document admission gate fail-open limitation (D3)"
# shellcheck disable=SC2016
grep -Fq '6. **On `AUDIT=pass` or emergency-bypassed `AUDIT=refuse` — semantic materiality (comment-only)**' "$SKILL_MD" \
  || fail "SKILL.md Preflight must retain semantic materiality step (item 6)"
grep -Fq 'semantic stale notice posted at Preflight item 6' "$SKILL_MD" \
  || fail "SKILL.md exit table must pin Preflight item 6 semantic stale path"
! grep -Fq '### Step 0 — tracking issue adoption' "$SKILL_MD" \
  || fail "SKILL.md must not reintroduce prompt-side Step 0 tracking issue adoption heading"
! grep -Fq '### Plan materialization from issue body' "$SKILL_MD" \
  || fail "SKILL.md must not reintroduce prompt-side plan materialization heading"
! grep -Fq '### Implementer waterfall' "$SKILL_MD" \
  || fail "SKILL.md must not reintroduce prompt-side implementer waterfall heading"
read -r tok0_plan_bootstrap <<'EOF'
"$SCRIPT_DIR/token-ledger.sh" mark "implement Step 0 — plan materialization"
EOF
read -r time0_plan_bootstrap <<'EOF'
"$SCRIPT_DIR/timing-ledger.sh" mark "implement Step 0 — plan materialization"
EOF
grep -Fq "$tok0_plan_bootstrap" "$REPO_ROOT/scripts/implement-bootstrap.sh" \
  || fail "implement-bootstrap.sh must retain token-ledger implement Step 0 — plan materialization mark"
grep -Fq "$time0_plan_bootstrap" "$REPO_ROOT/scripts/implement-bootstrap.sh" \
  || fail "implement-bootstrap.sh must retain timing-ledger implement Step 0 — plan materialization mark"
grep -Fq 'phase_coder_select' "$SKILL_MD" \
  || fail "SKILL.md must pin coder selection ownership to implement-bootstrap.sh"
assert_degraded_tools_gate_fence
grep -Fq 'mark "implement Step 0 — coder select"' "$REPO_ROOT/scripts/implement-bootstrap.sh" \
  || fail "implement-bootstrap.sh must contain coder-select token/timing mark"
[ -f "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" ] \
  || fail "scripts/implement-bootstrap-invoke.sh must exist"
[ -f "$REPO_ROOT/scripts/implement-bootstrap-invoke.md" ] \
  || fail "scripts/implement-bootstrap-invoke.md must exist"
grep -Fq 'implement-bootstrap-invoke.sh --mode initial' "$SKILL_MD" \
  || fail "SKILL.md must call implement-bootstrap-invoke.sh --mode initial"
if [ "$(grep -oF 'implement-bootstrap-invoke.sh --mode initial' "$SKILL_MD" 2>/dev/null | wc -l | tr -d ' ')" -lt 1 ]; then
  fail "SKILL.md must reference implement-bootstrap-invoke.sh --mode initial"
fi
if [ "$(grep -oF 'implement-bootstrap-invoke.sh --mode resume' "$SKILL_MD" 2>/dev/null | wc -l | tr -d ' ')" -lt 1 ]; then
  fail "SKILL.md must call implement-bootstrap-invoke.sh --mode resume (dirty-tree)"
fi
grep -Fq 'implement-bootstrap-invoke.sh --mode initial' "$SKILL_MD" \
  || fail "Protocol Execution Directive must name implement-bootstrap-invoke.sh --mode initial"
grep -Fq '_ib_preflight=()' "$SKILL_MD" \
  && fail "SKILL.md must not retain inline _ib_preflight argv array"
grep -Fq '_ib_emergency=()' "$SKILL_MD" \
  && fail "SKILL.md must not retain inline _ib_emergency argv array"
true
grep -Fq -- '--resume-plan-tail' "$REPO_ROOT/scripts/implement-bootstrap.md" \
  || fail "implement-bootstrap.md must document --resume-plan-tail"
grep -Fq -- '--resume-plan-tail' "$SKILL_MD" \
  || fail "SKILL.md must retain dirty-tree resume-tail routing"
grep -Fq '## Step 0 — Session Setup' "$SKILL_MD" \
  || fail "SKILL.md must retain Step 0 Session Setup heading"
grep -Fq "**⚠ Foreground required — do NOT set \`run_in_background: true\`.**" "$SKILL_MD" \
  || fail "SKILL.md must retain the Step 0 foreground-required warning"
{ grep -Fq 'Dirty-tree recovery bootstrap fence:' "$SKILL_MD" || \
  grep -Fq 'Step 0 dirty-tree recovery gate:' "$SKILL_MD"; } \
  || fail "SKILL.md must retain the dirty-tree recovery bootstrap fence"
grep -Fq 'Resume-tail idempotency' "$REPO_ROOT/scripts/implement-bootstrap.md" \
  || fail "implement-bootstrap.md must document resume-tail idempotency invariant"
grep -Fq 'the first pass bails at this checkpoint' "$REPO_ROOT/scripts/implement-bootstrap.md" \
  || fail "implement-bootstrap.md must pin the dirty-tree first-pass-bail-before-helpers invariant"
grep -Fq '_ib_caller_env=()' "$SKILL_MD" \
  && fail "SKILL.md must not retain inline _ib_caller_env argv assembly"
grep -Fq '_ib_issue=()' "$SKILL_MD" \
  && fail "SKILL.md must not retain inline _ib_issue argv assembly"
grep -Fq '_ib_fork=()' "$SKILL_MD" \
  && fail "SKILL.md must not retain inline _ib_fork argv assembly"
grep -Fq '_ib_run_id=()' "$SKILL_MD" \
  && fail "SKILL.md must not retain inline _ib_run_id argv assembly"
grep -Fq '_ib_run_bootstrap() {' "$SKILL_MD" \
  && fail "SKILL.md must not retain _ib_run_bootstrap helper"
grep -Fq '_ib_parse_bootstrap_out() {' "$SKILL_MD" \
  && fail "SKILL.md must not retain dead _ib_parse_bootstrap_out helper"
grep -Fq '_ib_run_bootstrap --resume-plan-tail' "$SKILL_MD" \
  && fail "SKILL.md must not call _ib_run_bootstrap --resume-plan-tail"
grep -Fq '_ib_parse_bootstrap_out' "$SKILL_MD" \
  && fail "SKILL.md must not reference _ib_parse_bootstrap_out"
if grep -Fq 'not-yet-implemented-phase-' "$SKILL_MD"; then
  fail "SKILL.md must not reintroduce not-yet-implemented phase bail placeholders"
fi
# shellcheck disable=SC2016 # literal source text, not shell.
grep -Fq 'larch_err "→ step0: coder=${coder}"' "$REPO_ROOT/scripts/implement-bootstrap.sh" \
  || fail "implement-bootstrap.sh must retain the coder breadcrumb literal"
grep -Fq 'Review/fix and other fixer lanes remain Codex-first' "$REPO_ROOT/SECURITY.md" \
  || fail "SECURITY.md must document Codex-first fixer adjacency"
grep -Fq "Operators who want Codex on \`/implement\` can pin it explicitly with \`--coder=codex\`." "$REPO_ROOT/SECURITY.md" \
  || fail "SECURITY.md must document explicit --coder=codex pinning"
# shellcheck disable=SC2016 # literal removed-helper pin.
grep -Fq '_ib_target_issue="${TARGET_ISSUE_NUMBER:-${ISSUE_NUMBER:-}}"' "$SKILL_MD" \
  && fail "SKILL.md must not retain _ib_target_issue helper"
if [ "$(grep -oF '_ib_rc' "$SKILL_MD" 2>/dev/null | wc -l | tr -d ' ')" -ge 1 ]; then
  fail "SKILL.md must not retain _ib_rc (use _inv_rc)"
fi
if [ "$(grep -oF '_inv_rc' "$SKILL_MD" 2>/dev/null | wc -l | tr -d ' ')" -lt 2 ]; then
  fail "SKILL.md must use _inv_rc at initial Step 0 and dirty-tree recovery"
fi
if [ "$(grep -cF '_inv_rc=$?' "$SKILL_MD" || true)" -lt 2 ]; then
  fail "SKILL.md must capture _inv_rc after each wrapper call"
fi
step0_wrapper_fence_status=0
awk '
  /<!-- step:0/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0; in_bash = 0 }
  in_step && /^```(bash|sh|shell)[[:space:]]*$/ { in_bash = 1; next }
  in_step && in_bash && /^```[[:space:]]*$/ { in_bash = 0; next }
  in_step && in_bash && /^[[:space:]]*#/ { prev2 = prev1; prev1 = $0; next }
  in_step && in_bash && /^[[:space:]]*_inv_out=\$\(.+implement-bootstrap-invoke\.sh" --mode (initial|resume)/ {
    mode = ($0 ~ /--mode initial/) ? "initial" : "resume"
    if (prev1 != "set +e") exit 20
    getline rc_line
    if (rc_line != "_inv_rc=$?") exit 21
    getline sete_line
    if (sete_line != "set -e") exit 22
    seen[mode]++
    prev2 = prev1
    prev1 = sete_line
    next
  }
  in_step && in_bash {
    prev2 = prev1
    prev1 = $0
  }
  END {
    if (seen["initial"] < 1) exit 23
    if (seen["resume"] < 1) exit 24
  }
' "$SKILL_MD" || step0_wrapper_fence_status=$?
case "$step0_wrapper_fence_status" in
  0) ;;
  20) fail "each implement-bootstrap-invoke.sh call must be immediately preceded by set +e" ;;
  21) fail "each implement-bootstrap-invoke.sh call must be immediately followed by _inv_rc=\$?" ;;
  22) fail "each implement-bootstrap-invoke.sh _inv_rc capture must be immediately followed by set -e" ;;
  23) fail "Step 0 wrapper fence check did not see initial invocation" ;;
  24) fail "Step 0 wrapper fence check did not see resume invocation" ;;
  *) fail "unexpected Step 0 wrapper fence check failure: $step0_wrapper_fence_status" ;;
esac
if [ "$(grep -cE '^[[:space:]]*_inv_out=\$\("\$\{CLAUDE_PLUGIN_ROOT\}/scripts/implement-bootstrap-invoke\.sh"' "$SKILL_MD" || true)" -lt 2 ]; then
  fail "SKILL.md must contain at least two uncommented _inv_out= implement-bootstrap-invoke.sh call sites"
fi
[ -f "$REPO_ROOT/scripts/parse-bootstrap-routing-envelope.sh" ] \
  || fail "scripts/parse-bootstrap-routing-envelope.sh must exist"
[ -f "$REPO_ROOT/scripts/parse-bootstrap-routing-envelope.md" ] \
  || fail "scripts/parse-bootstrap-routing-envelope.md must exist"
grep -Fq 'parse-bootstrap-routing-envelope.sh' "$SKILL_MD" \
  || fail "SKILL.md must source parse-bootstrap-routing-envelope.sh"
# shellcheck disable=SC2016 # literal source text, not shell.
if [ "$(grep -cF '. "${CLAUDE_PLUGIN_ROOT}/scripts/parse-bootstrap-routing-envelope.sh"' "$SKILL_MD" || true)" -ne 2 ]; then
  fail "SKILL.md must source parse-bootstrap-routing-envelope.sh exactly twice (initial + resume)"
fi
grep -Fq 'parse-bootstrap-routing-envelope.sh" --preserve-coder' "$SKILL_MD" \
  || fail "SKILL.md dirty-tree resume must source parse-bootstrap-routing-envelope.sh --preserve-coder"
grep -Fq '_inv_routing_keys=' "$SKILL_MD" \
  && fail "SKILL.md must not duplicate _inv_routing_keys (owned by parse-bootstrap-routing-envelope.sh)"
grep -Fq '_inv_apply_routing_line()' "$SKILL_MD" \
  && fail "SKILL.md must not define _inv_apply_routing_line (owned by parse-bootstrap-routing-envelope.sh)"
grep -Fq '_inv_apply_routing_line_if_empty()' "$SKILL_MD" \
  && fail "SKILL.md must not define _inv_apply_routing_line_if_empty (owned by parse-bootstrap-routing-envelope.sh)"
# shellcheck disable=SC2016 # literal source text, not shell.
if [ "$(grep -cF 'if [ "$_inv_rc" -ne 0 ]; then' "$SKILL_MD" || true)" -lt 2 ]; then
  fail "SKILL.md must exit on non-zero wrapper rc before routing parse (both call sites)"
fi
grep -Fq 'unset IMPLEMENT_BAIL_REASON STALL_TRACKING PLAN_FILE coder coder_fallback' "$REPO_ROOT/scripts/parse-bootstrap-routing-envelope.sh" \
  || fail "parse-bootstrap-routing-envelope.sh initial unset must include coder coder_fallback"
grep -Fq 'unset IMPLEMENT_BAIL_REASON STALL_TRACKING PLAN_FILE REPO_UNAVAILABLE' "$REPO_ROOT/scripts/parse-bootstrap-routing-envelope.sh" \
  || fail "parse-bootstrap-routing-envelope.sh resume unset must omit coder coder_fallback"
grep -Fq '_ib_kv_scan()' "$SKILL_MD" \
  && fail "SKILL.md must not retain _ib_kv_scan helper"
grep -Fq '_ib_handle_bootstrap_exit2()' "$SKILL_MD" \
  && fail "SKILL.md must not retain _ib_handle_bootstrap_exit2 helper"
expected_routing_keys='IMPLEMENT_TMPDIR IMPLEMENT_BAIL_REASON STALL_TRACKING PLAN_FILE coder coder_fallback REPO_UNAVAILABLE DEFERRED ISSUE_NUMBER REPO CODEX_PRESENT CURSOR_PRESENT CODEX_BINARY_FOUND CURSOR_BINARY_FOUND codex_available cursor_available RUN_ID BRANCH_NAME BRANCH_ACTION SELF_REVIEW_REQUESTED'
parse_keys=$(awk -F"'" '/^_inv_routing_keys=/ {print $2; exit}' "$REPO_ROOT/scripts/parse-bootstrap-routing-envelope.sh")
invoke_keys=$(awk -F"'" '/^_inv_routing_keys=/ {print $2; exit}' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh")
if [ "$parse_keys" != "$expected_routing_keys" ] || [ "$invoke_keys" != "$expected_routing_keys" ]; then
  fail "parse-bootstrap-routing-envelope.sh and implement-bootstrap-invoke.sh _inv_routing_keys must match canonical list"
fi
if [ "$parse_keys" != "$invoke_keys" ]; then
  fail "parse-bootstrap-routing-envelope.sh and implement-bootstrap-invoke.sh _inv_routing_keys literals must be identical"
fi
grep -Fq "BRANCH_NAME=*) BRANCH_NAME=\${_ib_tok#BRANCH_NAME=} ;;" "$SKILL_MD" \
  && fail "SKILL.md must not retain BRANCH_NAME _ib_kv_scan case arm"
grep -Fq "BRANCH_ACTION=*) BRANCH_ACTION=\${_ib_tok#BRANCH_ACTION=} ;;" "$SKILL_MD" \
  && fail "SKILL.md must not retain BRANCH_ACTION _ib_kv_scan case arm"
grep -Fq "PLAN_FILE=*) PLAN_FILE=\${_ib_tok#PLAN_FILE=} ;;" "$SKILL_MD" \
  && fail "SKILL.md must not retain PLAN_FILE _ib_kv_scan case arm"
grep -Fq "coder=*) coder=\${_ib_tok#coder=} ;;" "$SKILL_MD" \
  && fail "SKILL.md must not retain coder _ib_kv_scan case arm"
grep -Fq 'BRANCH_NAME' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must include BRANCH_NAME in routing envelope key set"
grep -Fq 'PLAN_FILE' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must include PLAN_FILE in routing envelope key set"
grep -Fq 'coder_fallback' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must include coder_fallback in routing envelope key set"
grep -Fq 'copy-plan)' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must retain copy-plan exit-2 handler"
grep -Fq 'gh-issue-view)' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must retain gh-issue-view exit-2 handler"
grep -Fq 'create-branch)' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must retain create-branch exit-2 handler"
grep -Fq 'write-session-env)' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must retain write-session-env exit-2 handler"
grep -Fq 'emergency-bypass-log)' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must retain emergency-bypass-log exit-2 handler"
grep -Fq '*)' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must retain default exit-2 handler"
# shellcheck disable=SC2016
grep -Fq 'run-step2-dispatch.sh` always passes `--plan-file "$IMPLEMENT_TMPDIR/plan.txt"`' "$SKILL_MD" \
  || fail "SKILL.md must retain Step 2 conventional plan-file wording"
# shellcheck disable=SC2016
grep -Fq 'launcher must fail closed if session-env later says `CURSOR_PRESENT!=true`' "$SKILL_MD" \
  || fail "SKILL.md must document fail-closed cursor selection drift handling"

step0_plan_structure_status=0
awk '
  /<!-- step:0/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0; in_bash = 0 }
  in_step && /^```(bash|sh|shell)[[:space:]]*$/ { in_bash = 1; next }
  in_step && in_bash && /^```[[:space:]]*$/ { in_bash = 0; next }
  in_step && in_bash {
    if ($0 ~ /implement-bootstrap\.sh/) direct_bootstrap++
    if ($0 ~ /--up-to-phase coder/) coder_literal++
    if ($0 ~ /--resume-plan-tail/) resume_literal++
    if ($0 ~ /^[[:space:]]*#/) next
    if ($0 ~ /^[[:space:]]*_inv_out=\$\(.+implement-bootstrap-invoke\.sh" --mode initial/) mode_initial++
    if ($0 ~ /^[[:space:]]*_inv_out=\$\(.+implement-bootstrap-invoke\.sh" --mode resume/) mode_resume++
    if ($0 ~ /snapshot-untracked\.sh" --output|\$SCRIPT_DIR\/persist-implement-run-flags\.sh|check-mid-run-dirty-tree\.sh" --mode checkpoint|create-branch\.sh" --branch|git-current-branch\.sh"|run-step1-plan-log\.sh"|write-tally\.sh"|tracking-issue-summary\.sh" .*upsert-summary|gh issue view "\$gh_issue_arg"|gh issue view "\$ISSUE_NUMBER"/) banned++
  }
  END {
    if (direct_bootstrap != 0) exit 10
    if (coder_literal != 0) exit 12
    if (resume_literal != 0) exit 13
    if (mode_initial < 1) exit 14
    if (mode_resume < 1) exit 15
    if (banned != 0) exit 11
  }
' "$SKILL_MD" || step0_plan_structure_status=$?
case "$step0_plan_structure_status" in
  0) ;;
  10) fail "Step 0 bash blocks must not call implement-bootstrap.sh directly" ;;
  12) fail "Step 0 bash blocks must not contain --up-to-phase coder literal (wrapper-owned)" ;;
  13) fail "Step 0 bash blocks must not contain --resume-plan-tail literal (wrapper-owned)" ;;
  14) fail "Step 0 bash blocks must call implement-bootstrap-invoke.sh --mode initial" ;;
  15) fail "Step 0 bash blocks must call implement-bootstrap-invoke.sh --mode resume" ;;
  11) fail "Step 0 bash blocks must not reintroduce absorbed plan-materialization helper calls" ;;
  *) fail "unexpected Step 0 structure check failure: $step0_plan_structure_status" ;;
esac
if grep -Fq '<!-- step:0.5' "$SKILL_MD"; then
  fail "SKILL.md must not reintroduce <!-- step:0.5 session anchor"
fi
if grep -Fq '<!-- step:1 —' "$SKILL_MD"; then
  fail "SKILL.md must not reintroduce retired <!-- step:1 — session anchor"
fi
if grep -Fq '### /fix-issue coordination' "$SKILL_MD"; then
  fail "SKILL.md must not contain /fix-issue coordination subsection"
fi

# Drift guard: ship-pr write_initial_state printf keys vs SKILL.md Required keys bullets
# (pinned region between <!-- write-initial-state-keys:begin/end --> markers).
if ! grep -Fq '<!-- write-initial-state-keys:begin -->' "$SKILL_MD"; then
  fail "skills/implement/SKILL.md missing <!-- write-initial-state-keys:begin --> marker (ship-pr state-key drift guard)"
fi
if ! grep -Fq '<!-- write-initial-state-keys:end -->' "$SKILL_MD"; then
  fail "skills/implement/SKILL.md missing <!-- write-initial-state-keys:end --> marker (ship-pr state-key drift guard)"
fi

skill_keys=$(
  awk '/<!-- write-initial-state-keys:begin -->/{flag=1; next} /<!-- write-initial-state-keys:end -->/{flag=0} flag' "$SKILL_MD" \
    | sed 's/^- //' \
    | grep -oE '`[A-Z_][A-Z0-9_]*' | tr -d '`' | sort -u
)

ship_keys=$(
  awk '/^write_initial_state\(\) \{/,/\} > "\$tmp" && mv/' "$SHIP_PR_SH" \
    | grep -E "^[[:space:]]*printf '[A-Z_][A-Z0-9_]*=" \
    | sed -E "s/^[[:space:]]*printf '//; s/=.*//" | sort -u
)

skill_n=$(printf '%s\n' "$skill_keys" | grep -c . || true)
ship_n=$(printf '%s\n' "$ship_keys" | grep -c . || true)
[[ "$skill_n" -ge 20 ]] \
  || fail "write-initial-state drift guard: extracted only ${skill_n} SKILL.md keys (<20) — parser regression or empty marker region"
[[ "$ship_n" -ge 20 ]] \
  || fail "write-initial-state drift guard: extracted only ${ship_n} ship-pr.sh keys (<20) — write_initial_state() structure may have changed"

diff_ship_not_skill=$(comm -23 <(printf '%s\n' "$ship_keys") <(printf '%s\n' "$skill_keys") || true)
diff_skill_not_ship=$(comm -13 <(printf '%s\n' "$ship_keys") <(printf '%s\n' "$skill_keys") || true)
if [[ -n "$diff_ship_not_skill" ]]; then
  echo "Keys in ship-pr.sh missing from SKILL.md:" >&2
  printf '%s\n' "$diff_ship_not_skill" >&2
fi
if [[ -n "$diff_skill_not_ship" ]]; then
  echo "Keys in SKILL.md missing from ship-pr.sh:" >&2
  printf '%s\n' "$diff_skill_not_ship" >&2
fi
if [[ -n "$diff_ship_not_skill" || -n "$diff_skill_not_ship" ]]; then
  fail "write_initial_state key set drift between skills/implement/SKILL.md (write-initial-state-keys region) and scripts/ship-pr.sh write_initial_state()"
fi

grep -Fq "seed \`\$IMPLEMENT_TMPDIR/ship-pr-state.sh\` from the canonical Step 8 \`<!-- write-initial-state-keys:begin/end -->\` required-key block" "$SKILL_MD" \
  || fail "SKILL.md Step 5 stall path must pin the canonical write-initial-state-keys block as the ship-pr-state seed source"
grep -Fq 'copy the full canonical key set' "$SKILL_MD" \
  || fail "SKILL.md Step 5 stall path must require copying the full canonical ship-pr-state key set"

# Stage 4 (#3119): Family-B fence shape must stay absent from implement orchestrator docs.
assert_p3119_family_b_fence_absent "$SKILL_MD" "SKILL.md" ship-pr-invocation
assert_p3119_family_b_fence_absent "$STALL_RECOVERY_MD" "stall-recovery.md"
# conflict-resolution.md is active again for early rebase and ship-pr pre-push
# handoffs; Family-B fence absence is enforced on the live orchestrator docs only.
grep -Fq "treat the foreground Bash tool exit code as \`writer_rc\`" "$SKILL_MD" \
  || fail "(3119) SKILL.md Step 8+ must pin foreground writer_rc routing (post ship-pr return)"
grep -Fq "Treat the foreground Bash tool exit code as \`writer_rc\`" "$SKILL_MD" \
  || fail "(3119) SKILL.md Exit 4 must pin foreground writer_rc routing"
grep -Fq "treat the foreground Bash tool exit code as \`writer_rc\`" "$STALL_RECOVERY_MD" \
  || fail "(3119) stall-recovery.md step8-shippr must pin foreground writer_rc routing"

guard_tmp="$(mktemp -d "${TMPDIR:-/tmp}/larch-ship-python-guard.XXXXXX")"
real_python3="$(command -v python3)"
[[ -n "$real_python3" ]] || fail "python3 required for ship-driver guard runtime probe"
cat > "$guard_tmp/python3" <<SHIM
#!/usr/bin/env bash
if [ "\$1" = "-c" ] && printf '%s\n' "\$2" | grep -Fq 'sys.version_info >= (3, 11)'; then
  exit 1
fi
exec "$real_python3" "\$@"
SHIM
chmod +x "$guard_tmp/python3"
set +e
PATH="$guard_tmp:$PATH" bash -c '
if ! python3 -c '"'"'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'"'"' 2>/dev/null; then
  echo "ERROR: Python ship driver requires Python 3.11 or newer" >&2
  printf "%s\n" '"'"'{"detail":"Python ship driver requires Python 3.11 or newer","failed_run_id":"","merge_result":"","needs_user_reason":"","outcome":"STALLED","pr_number":null,"pr_url":""}'"'"'
  exit 4
fi
exit 0
' >"$guard_tmp/stdout.txt" 2>"$guard_tmp/stderr.txt"
guard_rc=$?
set -e
[[ "$guard_rc" -eq 4 ]] \
  || fail "ship-driver Python version guard must exit 4 when python3 is below 3.11 (got $guard_rc)"
grep -Fq '"outcome":"STALLED"' "$guard_tmp/stdout.txt" \
  || fail "ship-driver Python version guard must emit STALLED JSON on stdout"
grep -Fq 'Python ship driver requires Python 3.11 or newer' "$guard_tmp/stderr.txt" \
  || fail "ship-driver Python version guard must emit operator-visible stderr"
rm -rf "$guard_tmp"

echo "All assertions passed."
