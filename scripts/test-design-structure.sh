#!/bin/bash
# Structural regression test for /design skill refactor (closes skill-judge Grade-C findings)
# AND for the Step-3a removal residue pins (issue #453, follow-up to PR #454).
# Asserts that the skill's progressive-disclosure invariants survive edits:
#  - SKILL.md flag table has an adjacent MANDATORY pointer to references/flags.md placed before Step 0.
#  - SKILL.md Step 2a.5 carries BOTH Do-NOT-load guards (NO_CONTESTED_DECISIONS + zero-externals).
#  - references/dialectic-execution.md exists and its header contains a MANDATORY directive naming dialectic-debate.md.
#  - references/flags.md exists and contains the --branch-info 4-key literal AND the --step-prefix `::` delimiter literal.
#  - skills/design/ tree contains no Step-3a removal residue tokens.
#  - SKILL.md Step 3 ("all reviewers OK") and Step 3.5 auto-mode branches forward to Step 3b.
#  - SKILL.md Step 0 is branch-state-agnostic: session-setup.sh with
#    --skip-branch-check, then write-design-current-env.sh (no create-branch
#    --check or session-entry-gate.sh).
#
# Exit 0 on pass, exit 1 on any assertion failure.
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SKILL_MD="$REPO_ROOT/skills/design/SKILL.md"
FLAGS_MD="$REPO_ROOT/skills/design/references/flags.md"
DIALEXEC_MD="$REPO_ROOT/skills/design/references/dialectic-execution.md"
DESIGN_DIR="$REPO_ROOT/skills/design"
SKETCH_LAUNCH_MD="$REPO_ROOT/skills/design/references/sketch-launch.md"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

# Check 1: SKILL.md flag-table MANDATORY pointer appears before Step 0.
[[ -f "$SKILL_MD" ]] || fail "SKILL.md missing: $SKILL_MD"

flag_mandatory_line=$(grep -n 'MANDATORY — READ ENTIRE FILE before parsing argument flags' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$flag_mandatory_line" ]] || fail "SKILL.md lacks 'MANDATORY — READ ENTIRE FILE before parsing argument flags' pointer to references/flags.md"

step0_line=$(grep -n '^<!-- step:0 — Session Setup -->$' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step0_line" ]] || fail "SKILL.md lacks '<!-- step:0 — Session Setup -->' anchor"

if (( flag_mandatory_line >= step0_line )); then
  fail "flag-table MANDATORY pointer (line $flag_mandatory_line) must appear BEFORE Step 0 (line $step0_line). Flag parsing runs before Step 0; MANDATORY must be adjacent to the flag table."
fi

# Check 2: Step 2a.5 contains BOTH Do-NOT-load guards.
grep -q 'Do NOT load .*NO_CONTESTED_DECISIONS' "$SKILL_MD" \
  || fail "SKILL.md Step 2a.5 lacks the NO_CONTESTED_DECISIONS 'Do NOT load' guard"
grep -q 'Do NOT load .*zero-externals guardrail' "$SKILL_MD" \
  || fail "SKILL.md Step 2a.5 lacks the zero-externals 'Do NOT load' guard"

# Check 3: references/dialectic-execution.md exists and has header MANDATORY for dialectic-debate.md.
[[ -f "$DIALEXEC_MD" ]] || fail "references/dialectic-execution.md missing: $DIALEXEC_MD"

# The MANDATORY directive must appear in the header region (before step 2 body).
step2_line=$(grep -n '^2\. \*\*Per-decision prompt-file rendering' "$DIALEXEC_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step2_line" ]] || fail "references/dialectic-execution.md missing '2. Per-decision prompt-file rendering' body"

mandatory_line=$(grep -n 'MANDATORY — READ ENTIRE FILE before rendering debate prompts' "$DIALEXEC_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$mandatory_line" ]] || fail "references/dialectic-execution.md lacks header MANDATORY naming dialectic-debate.md"

if (( mandatory_line >= step2_line )); then
  fail "references/dialectic-execution.md header MANDATORY (line $mandatory_line) must appear BEFORE step 2 (line $step2_line)"
fi

grep -q 'dialectic-debate\.md' "$DIALEXEC_MD" \
  || fail "references/dialectic-execution.md header MANDATORY does not reference dialectic-debate.md"

# Check 4: references/flags.md exists and contains load-bearing literals.
[[ -f "$FLAGS_MD" ]] || fail "references/flags.md missing: $FLAGS_MD"

grep -q 'All 4 keys are required' "$FLAGS_MD" \
  || fail "references/flags.md lacks the --branch-info 4-key literal 'All 4 keys are required'"

# shellcheck disable=SC2016 # single quotes intentional — grep pattern is literal, includes backticks
grep -q '`::` delimiter' "$FLAGS_MD" \
  || fail "references/flags.md lacks the --step-prefix backtick-colon-delimiter literal"

# Check 4b: regular sketch launch output paths and Step 2a.3 collector paths
# must stay in sync. This pins the intentionally retained 4-slot diagonal
# after the regular-mode sketch fan-out was reduced from 8 to 4.
[[ -f "$SKETCH_LAUNCH_MD" ]] || fail "references/sketch-launch.md missing: $SKETCH_LAUNCH_MD"

regular_launch_section=$(awk '
  /^## Regular Mode/ { flag=1; next }
  /^## Quick Mode/ && flag { flag=0 }
  flag { print }
' "$SKETCH_LAUNCH_MD")
[[ -n "$regular_launch_section" ]] \
  || fail "(4b) could not extract Regular Mode section from sketch-launch.md"

regular_collector_section=$(awk '
  /^\*\*Regular mode\*\* \(4 external output files when both tools available\):$/ { flag=1; next }
  /^\*\*Quick mode\*\*/ && flag { flag=0 }
  flag { print }
' "$SKILL_MD")
[[ -n "$regular_collector_section" ]] \
  || fail "(4b) could not extract Step 2a.3 regular collector section from SKILL.md"

expected_regular_sketch_outputs=(
  'cursor-sketch-arch-output.txt'
  'cursor-sketch-edge-output.txt'
  'codex-sketch-innovation-output.txt'
  'codex-sketch-pragmatic-output.txt'
)

dropped_regular_sketch_outputs=(
  'cursor-sketch-innovation-output.txt'
  'cursor-sketch-pragmatic-output.txt'
  'codex-sketch-arch-output.txt'
  'codex-sketch-edge-output.txt'
)

# shellcheck disable=SC2016 # fixed-string grep literal intentionally contains shell syntax from markdown examples.
launch_output_count=$(printf '%s\n' "$regular_launch_section" | { grep -F -- '--output "$DESIGN_TMPDIR/' || true; } | wc -l | tr -d ' ')
[[ "$launch_output_count" == "4" ]] \
  || fail "(4b) sketch-launch.md Regular Mode must contain exactly 4 regular --output paths; found $launch_output_count"

# Count only collector output paths (`*-sketch-*-output.txt`); excludes
# breadcrumb-monitor pair env-var paths (`$DESIGN_TMPDIR/breadcrumbs/...`)
# introduced by issue #2749 Family B background+monitor wiring.
# shellcheck disable=SC2016 # fixed-string grep literal intentionally contains shell syntax from markdown examples.
collector_output_count=$(printf '%s\n' "$regular_collector_section" | { grep -E -- '"\$DESIGN_TMPDIR/[a-zA-Z0-9_-]+-sketch-[a-zA-Z0-9_-]+-output\.txt"' || true; } | wc -l | tr -d ' ')
[[ "$collector_output_count" == "4" ]] \
  || fail "(4b) SKILL.md Step 2a.3 regular collector must contain exactly 4 output paths; found $collector_output_count"

for output in "${expected_regular_sketch_outputs[@]}"; do
  launch_matches=$(printf '%s\n' "$regular_launch_section" | { grep -F -- "--output \"\$DESIGN_TMPDIR/$output\"" || true; } | wc -l | tr -d ' ')
  [[ "$launch_matches" == "1" ]] \
    || fail "(4b) sketch-launch.md Regular Mode must contain exactly one launcher output for $output; found $launch_matches"
  collector_matches=$(printf '%s\n' "$regular_collector_section" | { grep -F -- "\"\$DESIGN_TMPDIR/$output\"" || true; } | wc -l | tr -d ' ')
  [[ "$collector_matches" == "1" ]] \
    || fail "(4b) SKILL.md Step 2a.3 collector must contain exactly one output path for $output; found $collector_matches"
done

for output in "${dropped_regular_sketch_outputs[@]}"; do
  if printf '%s\n' "$regular_launch_section" | grep -Fq -- "$output"; then
    fail "(4b) sketch-launch.md Regular Mode still contains dropped output path $output"
  fi
  if printf '%s\n' "$regular_collector_section" | grep -Fq -- "$output"; then
    fail "(4b) SKILL.md Step 2a.3 regular collector still contains dropped output path $output"
  fi
done

# Check 4c: adaptive sketch budget pins. The runtime docs must preserve all
# three paths, including the zero-sketch path's collector prohibition.
grep -Fq 'sketch_budget=0' "$SKILL_MD" \
  || fail "(4c) SKILL.md missing sketch_budget=0 path"
grep -Fq 'sketch_budget=2' "$SKILL_MD" \
  || fail "(4c) SKILL.md missing sketch_budget=2 path"
grep -Fq 'sketch_budget=4' "$SKILL_MD" \
  || fail "(4c) SKILL.md missing sketch_budget=4 path"
grep -Fq 'NO_SKETCHES_CLASSIFIED_TRIVIAL' "$SKILL_MD" \
  || fail "(4c) SKILL.md missing zero-sketch approach-synthesis sentinel"
# shellcheck disable=SC2016 # literal backticked command phrase pinned in SKILL.md prose.
grep -Fq 'Do NOT call `collect-agent-results.sh`' "$SKILL_MD" \
  || fail "(4c) SKILL.md missing zero-sketch collect-agent-results prohibition"

# Check 4d: post-cutover absence pins — /design sketch phase is inline-only.
for needle in \
  'skills/design/references/heavy-worker.md' \
  'DESIGN_HEAVY=' \
  'write-design-manifest' \
  'classify-issue' \
  'ACTION=CLASSIFY' \
  ; do
  if grep -Fq "$needle" "$SKILL_MD"; then
    fail "(4d) skills/design/SKILL.md must not contain retired surface: $needle"
  fi
done
for needle in '--subagent' 'subagent_mode=true'; do
  if grep -Fq -- "$needle" "$SKILL_MD"; then
    fail "(4d) skills/design/SKILL.md must not contain retired surface: $needle"
  fi
done
if grep -Fq -- 'skills/design/references/heavy-worker.md' "$FLAGS_MD"; then
  fail "(4d) skills/design/references/flags.md must not reference skills/design/references/heavy-worker.md"
fi

# Check 5: skills/design/ tree must contain zero Step-3a removal residue tokens (issue #453).
[[ -d "$DESIGN_DIR" ]] || fail "skills/design/ directory missing: $DESIGN_DIR"

forbidden_tokens=(
  'Step 3a'
  'Post-Review Confirmation'
  'user-qa-happened'
  'qa_happened'
  'dialectic_adjudicated'
)

for token in "${forbidden_tokens[@]}"; do
  if grep -rF -- "$token" "$DESIGN_DIR" >/dev/null 2>&1; then
    matches=$(grep -m 3 -rnF -- "$token" "$DESIGN_DIR")
    fail "skills/design/ contains forbidden Step-3a-removal-residue token '$token':
$matches"
  fi
done

# Check 6: SKILL.md Step 3 'all reviewers OK' branch must reference Step 3.5 (not Step 3a/3b),
# and Step 3.5 must precede Step 3b in the file so routing cannot skip discussion r2.
grep -qF 'proceed to Step 3.5' "$SKILL_MD" \
  || fail "SKILL.md Step 3 'all reviewers OK' branch must point forward to 'Step 3.5' (issue #453: Step-3a removal residue pin)"
grep -qF '<!-- step:3b' "$SKILL_MD" \
  || fail "SKILL.md must retain the Step 3b step marker after Step 3.5 (routing fail-closed pin)"
awk '
  index($0, "<!-- step:3.5") && !s { s = NR }
  index($0, "<!-- step:3b") && !b { b = NR }
  END {
    if (!s) exit 2
    if (!b) exit 3
    if (s >= b) exit 1
  }
' "$SKILL_MD" || check6_order=$?
case "${check6_order:-0}" in
  0) ;;
  1) fail "SKILL.md must place <!-- step:3.5 before <!-- step:3b (no Step-3.5→3b routing skip)" ;;
  2) fail "SKILL.md missing <!-- step:3.5 marker (Step 3.5 routing pin)" ;;
  3) fail "SKILL.md missing <!-- step:3b marker (Step 3b routing pin)" ;;
  *) fail "unexpected Check 6 step-order awk exit: ${check6_order:-?}" ;;
esac

# Check 7 (#661): collect-agent-results substantive-validation contract must remain
# documented in plan-review.md on one line AND implemented in plan-review-loop.sh
# (Step 3 driver). Either location satisfies the pin; both are required to stay in sync.
PLAN_REVIEW_MD="$REPO_ROOT/skills/design/references/plan-review.md"
PLAN_REVIEW_LOOP_SH="$REPO_ROOT/skills/design/scripts/plan-review-loop.sh"
[[ -f "$PLAN_REVIEW_MD" ]] || fail "plan-review.md missing: $PLAN_REVIEW_MD"
[[ -f "$PLAN_REVIEW_LOOP_SH" ]] || fail "plan-review-loop.sh missing: $PLAN_REVIEW_LOOP_SH"
check7_doc_line() {
  grep 'collect-agent-results.sh' "$PLAN_REVIEW_MD" \
    | grep -F -- '--timeout 1860' \
    | grep -F -- '--substantive-validation' \
    | grep -Fq -- '--validation-mode'
}
check7_loop_tokens() {
  grep -Fq 'collect-agent-results.sh' "$PLAN_REVIEW_LOOP_SH" \
    && grep -Fqe '--timeout 1860' "$PLAN_REVIEW_LOOP_SH" \
    && grep -Fqe '--substantive-validation' "$PLAN_REVIEW_LOOP_SH" \
    && grep -Fqe '--validation-mode' "$PLAN_REVIEW_LOOP_SH" \
    && grep -Fqe '--structured-reviewer-validation' "$PLAN_REVIEW_LOOP_SH"
}
check7_doc_line || check7_loop_tokens \
  || fail "(7) collect-agent-results substantive-validation contract missing from plan-review.md single-line pin AND from plan-review-loop.sh token bundle — issue #661 regression"

# Check 7b: plan-review-quick.md must exist (structural pin alongside plan-review.md).
PLAN_REVIEW_QUICK_MD="$REPO_ROOT/skills/design/references/plan-review-quick.md"
[[ -f "$PLAN_REVIEW_QUICK_MD" ]] || fail "(7b) plan-review-quick.md missing: $PLAN_REVIEW_QUICK_MD"

# Check 8: issue-anchored plan handoff uses plan-block-write.sh.
PBW_SH="$REPO_ROOT/scripts/plan-block-write.sh"
[[ -x "$PBW_SH" ]] \
  || fail "(8) plan-block-write.sh missing or not executable at $PBW_SH"
# shellcheck disable=SC2016 # fixed-string grep literals contain shell variables/backticks
grep -Fq 'scripts/plan-block-write.sh" --issue "$ISSUE_NUMBER" --content-file' "$SKILL_MD" \
  || fail "(8) SKILL.md lacks Step 5 plan-block-write.sh --issue --content-file invocation"
grep -Fq 'PLAN_WRITE_OK=true' "$SKILL_MD" \
  || fail "(8) SKILL.md lacks Step 5 PLAN_WRITE_OK gating for cleanup"

# Check 9: load-bearing conversation-context dependency phrases are absent.
GREP_TMP=$(mktemp "${TMPDIR:-/tmp}/larch-design-structure-grep.XXXXXX")
trap 'rm -f "$GREP_TMP"' EXIT
if grep -rnE 'visible in conversation|retrieved from.*conversation' "$REPO_ROOT/skills/design" "$REPO_ROOT/skills/implement" "$REPO_ROOT/skills/shared" >"$GREP_TMP" 2>/dev/null; then
  matches=$(head -5 "$GREP_TMP")
  fail "(9) found forbidden conversation-context dependency phrase:
$matches"
fi

# Check 11: Step 0 branch-state-agnostic session setup (issue #2588). No
# create-branch.sh --check or session-entry-gate.sh; env handoff via
# write-design-current-env.sh and the PID-keyed current-design-env-$PPID.sh symlink.
step0_section=$(awk '
  /^<!-- step:0 — Session Setup -->$/ { flag=1; next }
  /^<!-- step:1c / && flag { flag=0 }
  flag { print }
' "$SKILL_MD")
[[ -n "$step0_section" ]] \
  || fail "(11) could not extract /design Step 0 section"

# First fenced ```bash … ``` inside Step 0 — writer / _wdce_args probes must
# match the executable block, not incidental prose or later-step bash excerpts.
step0_first_bash=$(printf '%s\n' "$step0_section" | awk '
  /^```bash$/ { if (!c) { c=1; next } }
  c && /^```$/ { exit }
  c { print }
')
[[ -n "$step0_first_bash" ]] \
  || fail "(11) Step 0 section has no opening \`\`\`bash fenced block"

if printf '%s\n' "$step0_section" | grep -Fq 'branch_info_supplied'; then
  fail "(11) Step 0 must not use legacy branch_info_supplied routing (removed in #2588)"
fi
if printf '%s\n' "$step0_section" | grep -Fq 'create-branch.sh --check'; then
  fail "(11) Step 0 must not invoke create-branch.sh --check (#2588: /implement owns branches)"
fi
if printf '%s\n' "$step0_section" | grep -Fq 'session-entry-gate.sh'; then
  fail "(11) Step 0 must not invoke session-entry-gate.sh (#2588)"
fi
# shellcheck disable=SC2016 # grep -F literal; backticks in markdown are not command substitution
printf '%s\n' "$step0_section" | grep -Fq '`/implement` owns the feature-branch lifecycle' \
  || fail "(11) Step 0 must document that /implement owns the feature-branch lifecycle"
# shellcheck disable=SC2016 # grep -F literal; $PPID is markdown text, not expansion
printf '%s\n' "$step0_section" | grep -Fq 'current-design-env-$PPID.sh' \
  || fail "(11) Step 0 must reference the PID-keyed current-design-env-$PPID.sh symlink"
printf '%s\n' "$step0_section" | grep -Fq 'PREFLIGHT_ERROR' \
  || fail "(11) Step 0 failure guidance must mention PREFLIGHT_ERROR"

printf '%s\n' "$step0_first_bash" | grep -Fq 'write-design-current-env.sh' \
  || fail "(11) Step 0a first bash block must invoke write-design-current-env.sh"
# shellcheck disable=SC2016 # grep -F literal; quotes are part of the SKILL.md source line
printf '%s\n' "$step0_first_bash" | grep -Fq -- '--claude-pid "$PPID"' \
  || fail "(11) Step 0a first bash block must pass --claude-pid \"\$PPID\" to write-design-current-env.sh"
printf '%s\n' "$step0_first_bash" | grep -Fq 'source-env.sh' \
  || fail "(11) Step 0a first bash block must materialize source-env.sh via write-design-current-env --output"
printf '%s\n' "$step0_first_bash" | grep -Fq '# Contract pin for CI (scripts/test-design-structure.sh): session-setup.sh --prefix claude-design --skip-branch-check --skip-repo-check --check-reviewers' \
  || fail "(11) Step 0a first bash block must retain the session-setup contract pin comment for CI"
printf '%s\n' "$step0_first_bash" | grep -Fq '_ss_args=(--prefix claude-design --skip-branch-check' \
  || fail "(11) Step 0a first bash block must build _ss_args with --prefix claude-design --skip-branch-check"
if printf '%s\n' "$step0_first_bash" | grep -Fq 'bash -c'; then
  fail "(11) Step 0a first bash block must not use bash -c (would break the \$PPID / --claude-pid contract)"
fi
printf '%s\n' "$step0_first_bash" | grep -Fq '_wdce_args=(' \
  || fail "(11) Step 0a first bash block must build _wdce_args=( ... ) for the writer"
# shellcheck disable=SC2016 # grep -F literal; SKILL.md argv-array invocation line
printf '%s\n' "$step0_first_bash" | grep -Fq '"${_wdce_args[@]}"' \
  || fail "(11) Step 0a first bash block must invoke the writer via \"\${_wdce_args[@]}\" (argv array)"

# shellcheck disable=SC2016 # fixed-string grep literal contains shell variable syntax
setup_line=$(printf '%s\n' "$step0_first_bash" | grep -nF '${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh' | head -1 | cut -d: -f1 || true)
# shellcheck disable=SC2016 # fixed-string grep literal contains shell variable syntax
wdce_line=$(printf '%s\n' "$step0_first_bash" | grep -nF '${CLAUDE_PLUGIN_ROOT}/scripts/write-design-current-env.sh' | head -1 | cut -d: -f1 || true)
[[ -n "$setup_line" && -n "$wdce_line" ]] \
  || fail "(11) could not locate session-setup.sh and write-design-current-env.sh lines in Step 0"
if (( setup_line >= wdce_line )); then
  fail "(11) Step 0 ordering must be session-setup.sh before write-design-current-env.sh"
fi

export_line=$(printf '%s\n' "$step0_first_bash" | grep -nF "export CLAUDE_PLUGIN_ROOT='\${CLAUDE_PLUGIN_ROOT}'" | head -1 | cut -d: -f1 || true)
[[ -n "$export_line" && -n "$setup_line" ]] \
  || fail "(11-A5) Step 0a first bash block must contain CLAUDE_PLUGIN_ROOT export before session-setup.sh"
if (( export_line >= setup_line )); then
  fail "(11-A5) export CLAUDE_PLUGIN_ROOT template must precede session-setup.sh in Step 0a first bash block"
fi

! grep -Eq 'SESSION_ENV_PATH' "$SKILL_MD" \
  || fail "(11-A1) SESSION_ENV_PATH must not appear in design SKILL.md"
! grep -Eq -- '--caller-env' "$SKILL_MD" \
  || fail "(11-A2) --caller-env must not appear in design SKILL.md"
! grep -rEq 'SESSION_ENV_PATH' "$REPO_ROOT/skills/design/" \
  || fail "(11-A3) SESSION_ENV_PATH must not appear under skills/design/"
! grep -rEq -- '--caller-env' "$REPO_ROOT/skills/design/" \
  || fail "(11-A4) --caller-env must not appear under skills/design/"

old_design_prose='Run the shared session setup script. This handles preflight, temp directory creation, reviewer presence check, and presence status in a single call'
if grep -Fq "$old_design_prose" "$SKILL_MD"; then
  fail "(11) SKILL.md still contains legacy unconditional Step 0 session-setup prose"
fi

# Check 13: accepted-OOS security exclusion pins. plan-review.md owns the
# `$DESIGN_TMPDIR/oos-accepted-design.md` write and the design `oos.md`
# visibility export; both public-boundary paths must explicitly exclude accepted
# security-tagged OOS blocks using the canonical token match.
grep -F 'oos-accepted-design.md' "$PLAN_REVIEW_MD" \
  | grep -F 'excluding security-tagged findings' \
  | grep -Fq 'focus-area\s*=\s*security' \
  || fail "(13a) plan-review.md oos-accepted-design.md write must exclude security-tagged OOS via canonical focus-area token"
grep -F 'oos.md' "$PLAN_REVIEW_MD" \
  | grep -F 'excluding security-tagged accepted OOS findings' \
  | grep -Fq 'focus-area\s*=\s*security' \
  || fail "(13b) plan-review.md oos.md visibility export must exclude security-tagged accepted OOS via canonical focus-area token"
grep -Fq 'Match discrimination (false-positive guard)' "$PLAN_REVIEW_MD" \
  || fail "(13c) plan-review.md missing Match discrimination (false-positive guard) procedure"
grep -Fq 'Security counter-invariant' "$PLAN_REVIEW_MD" \
  || fail "(13c) plan-review.md missing Security counter-invariant clause"

# Check 13q: plan-review-quick.md security OOS exclusion pins (#1769).
# plan-review-quick.md is a public-boundary OOS writer; these assertions ensure
# the security exclusion clause is not accidentally dropped.
grep -F 'oos-accepted-design.md' "$PLAN_REVIEW_QUICK_MD" \
  | grep -Fq 'non-security' \
  || fail "(13qa) plan-review-quick.md oos-accepted-design.md write must mention non-security OOS exclusion"
grep -F 'oos.md' "$PLAN_REVIEW_QUICK_MD" \
  | grep -Fq 'Exclude security-tagged OOS' \
  || fail "(13qb) plan-review-quick.md oos.md write must include Exclude security-tagged OOS"
grep -Fq 'security counter-invariant' "$PLAN_REVIEW_QUICK_MD" \
  || fail "(13qc) plan-review-quick.md missing security counter-invariant clause"

# Check 15: /design SKILL.md pairs Final summary emission with operator-cancel /
# plan-write-failure markers (or cites the shared ### Final summary block).
for marker in \
  '**ℹ /design cancelled by operator.**' \
  '**⚠ 5: plan-block-write failed' \
  ; do
  line=$(grep -nF "$marker" "$SKILL_MD" | head -1 | cut -d: -f1 || true)
  [[ -n "$line" ]] || fail "(15) missing stable marker: $marker"
  start=$(( line > 45 ? line - 45 : 1 ))
  window=$(sed -n "${start},${line}p" "$SKILL_MD")
  if printf '%s\n' "$window" | grep -Fq 'render-final-summary.sh'; then
    :
  elif printf '%s\n' "$window" | grep -Fq '### Final summary block'; then
    :
  else
    fail "(15) marker not paired with render-final-summary.sh / ### Final summary block within 45 lines: $marker (line $line)"
  fi
done
footer_line=$(grep -nF '➡️ 5: finalize — plan written to issue' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$footer_line" ]] || fail "(15) missing machine footer line (finalize)"
fstart=$(( footer_line > 55 ? footer_line - 55 : 1 ))
fwindow=$(sed -n "${fstart},${footer_line}p" "$SKILL_MD")
if printf '%s\n' "$fwindow" | grep -Fq 'render-final-summary.sh'; then
  :
elif printf '%s\n' "$fwindow" | grep -Fq '### Final summary block'; then
  :
else
  fail "(15) machine footer not preceded by final-summary anchor within 55 lines"
fi

# Check 15b: Step 5 finalize references render-final-summary only (encapsulation — FINDING_14).
step5_line=$(grep -nF '<!-- step:5' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step5_line" ]] || fail "(15b) missing <!-- step:5 marker"
step6_line=$(grep -nF '<!-- step:6' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step6_line" ]] || fail "(15b) missing <!-- step:6 marker"
step5_body=$(sed -n "${step5_line},${step6_line}p" "$SKILL_MD")
printf '%s\n' "$step5_body" | grep -Fq 'render-final-summary.sh' \
  || fail "(15b) Step 5 body must reference render-final-summary.sh"
if printf '%s\n' "$step5_body" | grep -Fq 'tracking-issue-summary.sh'; then
  fail "(15b) Step 5 must not reference tracking-issue-summary.sh (encapsulated in render-final-summary.sh)"
fi

# Check 15c: no render-cost-line in skills/design tree.
if grep -RIn 'render-cost-line\.sh' "$REPO_ROOT/skills/design" >/dev/null 2>&1; then
  fail "(15c) skills/design must not reference render-cost-line.sh"
fi

# Check 15d: design SKILL must not chat-print token/timing summaries.
if grep -nF 'token-report.sh --summary' "$SKILL_MD" | grep -q .; then
  fail "(15d) skills/design/SKILL.md must not invoke token-report.sh --summary"
fi
if grep -nF 'timing-report.sh --summary' "$SKILL_MD" | grep -q .; then
  fail "(15d) skills/design/SKILL.md must not invoke timing-report.sh --summary"
fi

# Check 14: design ACTION dispatcher pins. The focus-area enum must remain in
# SKILL.md because CI and prompt rendering scan the inline reviewer launch
# blocks, while scriptable mechanics route through ACTION records.
focus_anchor_count=$(grep -Fc 'Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security' "$SKILL_MD")
[[ "$focus_anchor_count" == "10" ]] \
  || fail "(14a) SKILL.md must keep 10 focus-area enum anchor comments; found $focus_anchor_count"
grep -Fq 'ACTION=EMIT_PLAN' "$SKILL_MD" \
  || fail "(14b1) SKILL.md missing ACTION=EMIT_PLAN emission"
grep -Fq 'ACTION=FINALIZE' "$SKILL_MD" \
  || fail "(14b3) SKILL.md missing ACTION=FINALIZE emission"
grep -Fq 'design-driver.sh' "$SKILL_MD" \
  || fail "(14b4) SKILL.md missing design-driver.sh dispatcher invocation"
grep -Fq 'plan-review-loop.sh' "$SKILL_MD" \
  || fail "(14c0) SKILL.md missing plan-review-loop.sh Step 3 driver invocation"
grep -Fq 'set +e' "$SKILL_MD" \
  || fail "(14c0b) SKILL.md missing set +e guard adjacent to plan-review-loop.sh"
grep -Fq '_plan_review_rc=$?' "$SKILL_MD" \
  || fail "(14c0c) SKILL.md missing _plan_review_rc capture for plan-review-loop.sh"
grep -Fq 'scout-plan-archetypes-wrapper.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c1) plan-review-loop.sh missing scout-plan-archetypes-wrapper.sh"
grep -Fq 'dispatch-plan-review-panel.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c2) plan-review-loop.sh missing dispatch-plan-review-panel.sh"
grep -Fq 'PANEL_PATHS_FILE' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c3) plan-review-loop.sh missing PANEL_PATHS_FILE handling"
[[ -x "$PLAN_REVIEW_LOOP_SH" ]] \
  || fail "(14c4) plan-review-loop.sh must be executable"
PR_LOOP_MD="$REPO_ROOT/skills/design/scripts/plan-review-loop.md"
[[ -f "$PR_LOOP_MD" ]] || fail "(14c5) plan-review-loop.md missing: $PR_LOOP_MD"
grep -Fqe '--input-mode plan' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c6) plan-review-loop.sh missing --input-mode plan aggregate invocation"
grep -Fq 'tally-plan-review.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c7) plan-review-loop.sh missing tally-plan-review.sh"
grep -Fq 'dispatch-plan-voters.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c8) plan-review-loop.sh missing dispatch-plan-voters.sh"
grep -Fq 'aggregate-findings.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c9) plan-review-loop.sh missing aggregate-findings.sh"
grep -Fq 'check-mid-run-dirty-tree.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c10) plan-review-loop.sh missing check-mid-run-dirty-tree.sh"
grep -Fq 'compose-collector-failure-log.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c11) plan-review-loop.sh missing compose-collector-failure-log.sh"
grep -Fq 'launch-claude-review.sh' "$REPO_ROOT/scripts/dispatch-plan-voters.sh" \
  || fail "(14c12) dispatch-plan-voters.sh missing launch-claude-review.sh (Voter 1)"
TR_LOOP_SH="$REPO_ROOT/skills/design/scripts/test-plan-review-loop.sh"
TR_LOOP_MD="$REPO_ROOT/skills/design/scripts/test-plan-review-loop.md"
[[ -x "$TR_LOOP_SH" ]] || fail "(14c13) test-plan-review-loop.sh missing or not executable"
[[ -f "$TR_LOOP_MD" ]] || fail "(14c14) test-plan-review-loop.md missing"

DESIGN_DRIVER_SH="$REPO_ROOT/skills/design/scripts/design-driver.sh"
grep -Fq 'VALIDATE_PLAN_COMMANDS' "$DESIGN_DRIVER_SH" \
  || fail "(14b5) design-driver.sh missing VALIDATE_PLAN_COMMANDS"
grep -Fq 'validate-plan.sh' "$DESIGN_DRIVER_SH" \
  || fail "(14b6) design-driver.sh missing validate-plan.sh dispatch arm"
grep -Fq 'ACTION=VALIDATE_PLAN_COMMANDS' "$SKILL_MD" \
  || fail "(14b7) SKILL.md missing ACTION=VALIDATE_PLAN_COMMANDS"
grep -Fq 'Fix-and-retry' "$SKILL_MD" \
  || fail "(14b8) SKILL.md missing Fix-and-retry validator option label"
grep -Fq 'Override' "$SKILL_MD" \
  || fail "(14b9a) SKILL.md missing Override validator option label"
grep -Fq 'Cancel' "$SKILL_MD" \
  || fail "(14b9b) SKILL.md missing Cancel validator option label"
step2b_mark=$(grep -nF 'mark "design Step 2b — plan"' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
emit_line=$(awk -v s="$step2b_mark" 'NR>s && /ACTION=EMIT_PLAN/ {print NR; exit}' "$SKILL_MD" || true)
val_line=$(awk -v s="$step2b_mark" 'NR>s && /invoke-plan-validator-if-not-quick\.sh/ && /plan\.txt/ {print NR; exit}' "$SKILL_MD" || true)
[[ -n "$step2b_mark" && -n "$emit_line" && -n "$val_line" && "$val_line" -gt "$emit_line" ]] \
  || fail "(14b10) VALIDATE_PLAN_COMMANDS must follow EMIT_PLAN in Step 2b block"

AG_MD="$REPO_ROOT/skills/design/references/approval-gates.md"
DR_MD="$REPO_ROOT/skills/design/references/discussion-rounds.md"
[[ -f "$AG_MD" ]] || fail "(14c14a) approval-gates.md missing: $AG_MD"
[[ -f "$DR_MD" ]] || fail "(14c14b) discussion-rounds.md missing: $DR_MD"
grep -Fq 'ACTION=EMIT_PLAN' "$AG_MD" \
  || fail "(14c14c) approval-gates.md missing ACTION=EMIT_PLAN pin"
grep -Fq 'invoke-plan-validator-if-not-quick.sh' "$AG_MD" \
  || fail "(14c14d) approval-gates.md missing invoke-plan-validator-if-not-quick.sh pin"
emit_before_val_ag=$(awk '/ACTION=EMIT_PLAN/ && !done { e=NR; done=1 } /invoke-plan-validator-if-not-quick\.sh/ && !vset { v=NR; vset=1 } END { if (e && v) print (e <= v) ? 1 : 0; else print 0 }' "$AG_MD")
[[ "$emit_before_val_ag" == "1" ]] \
  || fail "(14c14e) approval-gates.md must mention EMIT_PLAN at or before invoke-plan-validator-if-not-quick.sh"
grep -Fq 'ACTION=EMIT_PLAN' "$DR_MD" \
  || fail "(14c14f) discussion-rounds.md missing ACTION=EMIT_PLAN pin"
grep -Fq 'invoke-plan-validator-if-not-quick.sh' "$DR_MD" \
  || fail "(14c14g) discussion-rounds.md missing invoke-plan-validator-if-not-quick.sh pin"
emit_before_val_dr=$(awk '/ACTION=EMIT_PLAN/ && !done { e=NR; done=1 } /invoke-plan-validator-if-not-quick\.sh/ && !vset { v=NR; vset=1 } END { if (e && v) print (e <= v) ? 1 : 0; else print 0 }' "$DR_MD")
[[ "$emit_before_val_dr" == "1" ]] \
  || fail "(14c14h) discussion-rounds.md must mention EMIT_PLAN at or before invoke-plan-validator-if-not-quick.sh"

# Check 16: dialectic waterfall + per-side assignment contract pins (#2620).
DIALPROTO_MD="$REPO_ROOT/skills/shared/dialectic-protocol.md"
DEBATE_MD="$REPO_ROOT/skills/design/references/dialectic-debate.md"
TIMING_KINDS_SH="$REPO_ROOT/scripts/lib-timing-kinds.sh"
grep -Fq '## Per-side waterfall retry' "$DIALPROTO_MD" \
  || fail "(16) dialectic-protocol.md missing '## Per-side waterfall retry' section header"
grep -Fq 'Debater quorum gate (six tags)' "$DIALPROTO_MD" \
  || fail "(16) dialectic-protocol.md missing six-tag eligibility gate anchor"
grep -Fq '<steelman>' "$DIALPROTO_MD" \
  || fail "(16) dialectic-protocol.md missing <steelman> in six-tag gate text"
grep -Fq '5. **Per-side waterfall retry**' "$DIALEXEC_MD" \
  || fail "(16) dialectic-execution.md missing step 5 Per-side waterfall retry header"
grep -Fq 'waterfall' "$DIALEXEC_MD" \
  || fail "(16) dialectic-execution.md missing waterfall token (step 5 contract)"
grep -Fq '1. **Per-side external tool assignment**' "$DIALEXEC_MD" \
  || fail "(16) dialectic-execution.md missing step 1 per-side external tool assignment header"
grep -Fq 'OUTPUT FORMAT' "$DEBATE_MD" \
  || fail "(16) dialectic-debate.md missing OUTPUT FORMAT header"
grep -Fq 'SELF-CHECK BEFORE STOPPING' "$DEBATE_MD" \
  || fail "(16) dialectic-debate.md missing SELF-CHECK BEFORE STOPPING directive"
grep -Fq '2nd-retry' "$SKILL_MD" \
  || fail "(16) design SKILL.md NEVER #2 missing 2nd-retry Claude exception token"
for kind in \
  cursor-debate-thesis-retry1 \
  cursor-debate-antithesis-retry1 \
  codex-debate-thesis-retry1 \
  codex-debate-antithesis-retry1 \
  claude-debate-thesis-retry2 \
  claude-debate-antithesis-retry2
do
  grep -Fq "$kind" "$TIMING_KINDS_SH" \
    || fail "(16) scripts/lib-timing-kinds.sh missing timing kind: $kind"
done

grep -Fq $'2b\tfull plan' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 2b\\tfull plan row"
grep -Fq $'2b.5\tplan size' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 2b.5\\tplan size row"
grep -Fq $'5\tfinalize' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 5\\tfinalize row"
grep -Fq $'6\tcleanup' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 6\\tcleanup row"
grep -Fq '> **🔶 /design 5: finalize**' "$SKILL_MD" \
  || fail "(15b) SKILL.md missing /design 5 finalize breadcrumb"
grep -Fq '> **🔶 /design 6: cleanup**' "$SKILL_MD" \
  || fail "(15b) SKILL.md missing /design 6 cleanup breadcrumb"
step5b_line=$(grep -nF '### 5b — File accepted OOS issues' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
step5c_line=$(grep -nF "### 5c — Write \`larch:plan\` to GitHub + publish" "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step5b_line" && -n "$step5c_line" ]] || fail "(15b) missing Step 5b or 5c sub-step headers"
if (( step5b_line >= step5c_line )); then
  fail "(15b) Step 5b must appear before Step 5c in SKILL.md"
fi
red_line=$(awk -v s="$step5c_line" 'NR>s && /redact-secrets\.sh/ && /composed-plan\.md/ {print NR; exit}' "$SKILL_MD" || true)
val5=$(awk -v s="$step5c_line" 'NR>s && /invoke-plan-validator-if-not-quick\.sh/ && /composed-plan\.md/ {print NR; exit}' "$SKILL_MD" || true)
[[ -n "$red_line" && -n "$val5" && "$val5" -lt "$red_line" ]] \
  || fail "(14b11) Step 5c validator must appear before redact-secrets on composed-plan.md"
# shellcheck disable=SC2016  # literal backticks + $DESIGN_TMPDIR token must match SKILL.md prose
needle='preserve `$DESIGN_TMPDIR`, skip Step 6 cleanup'
grep -Fq "$needle" "$SKILL_MD" \
  || fail "(14b12) Step 5c validator cancel must preserve tmpdir and skip cleanup"
grep -Fq '5c.5→5c.7→5c.8→6' "$SKILL_MD" \
  || fail "(15b) anti-halt reminder must mention 5c.5→5c.7→5c.8→6 step boundary (intra-Step-5 through rename)"

upsert_line=$(awk -v s="$step5c_line" 'NR>s && /scripts\/upsert-diagrams-comment\.sh/ {print NR; exit}' "$SKILL_MD" || true)
plan_write_line=$(awk -v s="$step5c_line" 'NR>s && /plan-block-write\.sh/ {print NR; exit}' "$SKILL_MD" || true)
publish_line=$(awk -v s="${upsert_line:-0}" 'NR>s && /design-log-publish\.sh/ {print NR; exit}' "$SKILL_MD" || true)
[[ -n "$plan_write_line" && -n "$upsert_line" && -n "$publish_line" && "$plan_write_line" -lt "$upsert_line" && "$upsert_line" -lt "$publish_line" ]] \
  || fail "(15b) Step 5c.5 upsert-diagrams-comment.sh must appear after plan-block-write.sh and before design-log-publish.sh"
step3b_line=$(grep -nF '<!-- step:3b' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
step4_line=$(grep -nF '<!-- step:4 ' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step3b_line" && -n "$step4_line" ]] || fail "(15b) missing Step 3b or Step 4 marker"
step3b_between=$(sed -n "$((step3b_line + 1)),$((step4_line - 1))p" "$SKILL_MD")
grep -Fq 'architecture-diagram.skipped' <<<"$step3b_between" \
  || fail "(15b) Step 3b must document architecture-diagram.skipped sentinel creation"
step5c_between=$(sed -n "$((step5c_line + 1)),$((step5c_line + 90))p" "$SKILL_MD")
grep -Fq 'architecture-diagram.skipped' <<<"$step5c_between" \
  || fail "(15b) Step 5c.5 must document architecture-diagram.skipped sentinel handling"
grep -Fq -- '--clear-architecture' <<<"$step5c_between" \
  || fail "(15b) Step 5c.5 must invoke --clear-architecture when the skipped sentinel is present"

# Check 17: Step 5b /larch:issue summary-halt guardrails (#2681).
ORCHESTRATOR_NEVER_MD="$REPO_ROOT/skills/shared/orchestrator-never.md"
[[ -f "$ORCHESTRATOR_NEVER_MD" ]] || fail "(17) orchestrator-never.md missing: $ORCHESTRATOR_NEVER_MD"
grep -Fq '5→5a→5b→5c.1→5c.5→5c.7→5c.8→6' "$SKILL_MD" \
  || fail "(17) anti-halt reminder missing intra-Step-5 sub-step enumeration"
grep -Fq "NEVER treat a sub-skill's terminal output as the parent skill's terminal output" "$ORCHESTRATOR_NEVER_MD" \
  || fail "(17) orchestrator-never.md missing sub-skill vs parent-skill terminal-output NEVER literal"
step5_between=$(sed -n "$((step5b_line + 1)),$((step5c_line - 1))p" "$SKILL_MD")
# Pin `/larch:issue` to the continuation-banner line (not merely anywhere in the 5b→5c window).
grep -Fq $'> **Continue to Step 5c IMMEDIATELY.** The `/larch:issue` Skill tool' <<<"$step5_between" \
  || fail "(17) Step 5b→5c continuation banner missing or /larch:issue not on the same line as the banner"

# Check FINDING_21 (#2670): plan-size thresholds + --partition documentation pins.
grep -Fq "| \`-p\` / \`--partition\` |" "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md compact flag table missing -p/--partition row"
grep -Fq '[-p|--partition]' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md argument-hint missing [-p|--partition]"
grep -Fq '[--brainstorm]' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md argument-hint missing [--brainstorm]"
grep -Fq "\`-p\`, \`--partition\`" "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md public argv allowlist missing -p/--partition"
# shellcheck disable=SC2016 # Markdown literal; backticks are SKILL.md prose, not command substitution
grep -Fq '`--partition`, `--brainstorm`, `--manual`, `-m`, `--no-dedup`, and `--run-id`' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md public argv allowlist missing --brainstorm/--manual sequence"
grep -Fq "\`--trivial\` and \`-p\` / \`--partition\` are mutually exclusive" "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md missing trivial vs partition mutual-exclusion prose"
grep -Fq '### Step 2b.5 — Plan-size threshold check' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md missing Step 2b.5 header"
step2b_block=$(awk '/^<!-- step:2b /,/^<!-- step:3 /' "$SKILL_MD")
emit_line=$(printf '%s\n' "$step2b_block" | grep -nF 'ACTION=EMIT_PLAN' | head -1 | cut -d: -f1 || true)
chk_line=$(printf '%s\n' "$step2b_block" | grep -nF 'skills/design/scripts/check-plan-size.sh' | head -1 | cut -d: -f1 || true)
[[ -n "$emit_line" && -n "$chk_line" ]] || fail "(FINDING_21) could not locate ACTION=EMIT_PLAN / check-plan-size.sh inside Step 2b block"
if ! [[ "$chk_line" -gt "$emit_line" ]]; then
  fail "(FINDING_21) check-plan-size.sh must appear after ACTION=EMIT_PLAN inside Step 2b block"
fi
grep -Fq '## Plan Size — Hard Trigger' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md missing hard-trigger plan-size header"
grep -Fq '(no **Continue** option — hard triggers' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md hard branch must document no-Continue invariant"
DISCUSSION_MD="$REPO_ROOT/skills/design/references/discussion-rounds.md"
grep -Fq 'Step 1c sprawl heuristic' "$DISCUSSION_MD" \
  || fail "(FINDING_21) discussion-rounds.md missing Step 1c sprawl hook"
grep -Fq 'per Step 1d invocation' "$DISCUSSION_MD" \
  || fail "(FINDING_21) discussion-rounds.md missing Step 1d sprawl-once cap"
grep -Fq 'semantic sprawl heuristic' "$DISCUSSION_MD" \
  || fail "(FINDING_21) discussion-rounds.md missing semantic sprawl heuristic prose"
APPROVAL_MD="$REPO_ROOT/skills/design/references/approval-gates.md"
grep -Fq 'Step 2b.5' "$APPROVAL_MD" \
  || fail "(FINDING_21) approval-gates.md missing Step 2b.5 reference after Gate B EMIT_PLAN"
grep -Fq '### 5d — Gated L3 velocity deferral comment' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md missing Step 5d header"
grep -Fq -- '--repo character-ai/larch' "$SKILL_MD" \
  || fail "(FINDING_21) Step 5d must reference explicit --repo character-ai/larch guard"
grep -Fq "[ \"\$ISSUE_NUMBER\" = \"2670\" ]" "$SKILL_MD" \
  || fail "(FINDING_21) Step 5d must guard on ISSUE_NUMBER 2670"
grep -Fq 'design-l3-velocity-notified-2670' "$SKILL_MD" \
  || fail "(FINDING_21) Step 5d must reference design-l3-velocity-notified-2670 sentinel"
grep -Fq "[ \"\${REPO:-}\" = \"character-ai/larch\" ]" "$SKILL_MD" \
  || fail "(FINDING_21) Step 5d must guard on REPO character-ai/larch identity"

# Check 19 (#2754): --brainstorm / Step 1d.5 / run-params / plan-review feature-context pins.
BRAINSTORM_MD="$REPO_ROOT/skills/design/references/brainstorm.md"
BRAINSTORM_PROMPTS="$REPO_ROOT/skills/design/references/brainstorm-prompts.md"
[[ -f "$BRAINSTORM_MD" ]] || fail "(2754) brainstorm.md missing"
[[ -f "$BRAINSTORM_PROMPTS" ]] || fail "(2754) brainstorm-prompts.md missing"
# shellcheck disable=SC2016 # Markdown table cell literal
grep -Fq '| `--brainstorm` |' "$SKILL_MD" \
  || fail "(2754) SKILL.md compact flag table missing --brainstorm row"
# shellcheck disable=SC2016 # Markdown emphasis + backticks in SKILL.md
grep -Fq '**`--trivial` + `--brainstorm`** uses' "$SKILL_MD" \
  || fail "(2754) SKILL.md missing trivial+brainstorm upgrade-flow prose"
grep -Fq '<!-- step:1d.5 — Brainstorm Panel -->' "$SKILL_MD" \
  || fail "(2754) SKILL.md missing Step 1d.5 anchor"
grep -Fq '> **🔶 /design 1d.5: brainstorm**' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing 1d.5 brainstorm breadcrumb"
grep -Fq '⏩ 1d.5: brainstorm — skipped (already complete; .brainstorm-done present)' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing sentinel-hit skip breadcrumb"
grep -Fq $'1d.5\tbrainstorm' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(2754) step-name-registry.tsv missing 1d.5 brainstorm row"
grep -Fq '<BRAINSTORM_FRAMING_PROMPT>' "$BRAINSTORM_PROMPTS" \
  || fail "(2754) brainstorm-prompts.md missing <BRAINSTORM_FRAMING_PROMPT>"
grep -Fq '<BRAINSTORM_SCOPE_PROMPT>' "$BRAINSTORM_PROMPTS" \
  || fail "(2754) brainstorm-prompts.md missing <BRAINSTORM_SCOPE_PROMPT>"
grep -Fq '<BRAINSTORM_PRAGMATIC_PROMPT>' "$BRAINSTORM_PROMPTS" \
  || fail "(2754) brainstorm-prompts.md missing <BRAINSTORM_PRAGMATIC_PROMPT>"
# shellcheck disable=SC2016 # flags.md list marker uses backticks
grep -Fq '`--brainstorm`:' "$FLAGS_MD" \
  || fail "(2754) flags.md missing --brainstorm bullet anchor"
grep -Fq '1c→1d→1d.5→1e' "$SKILL_MD" \
  || fail "(2754) SKILL.md anti-halt sequence missing 1d.5 transition"
grep -Fq 'MANDATORY — READ ENTIRE FILE' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing MANDATORY directive"
grep -Fq 'skills/design/references/brainstorm-prompts.md' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing brainstorm-prompts.md path literal"
grep -Fq 'ScheduleWakeup' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing ScheduleWakeup prohibition anchor"
# shellcheck disable=SC2016 # Markdown fence literal in brainstorm.md
grep -Fq '**⚠ Background required — must be paired with breadcrumb-monitor.sh.**' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing background-pair banner in collector fence"
grep -Fq '# Background pair required: see BASH_AUTHORING.md §4' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing BASH_AUTHORING §4 in-fence comment"
# shellcheck disable=SC2016 # SKILL.md bash excerpt; quotes are literal
grep -Fq -- '--brainstorm-requested "$brainstorm_requested"' "$SKILL_MD" \
  || fail "(2754) SKILL.md write-run-params invocation missing --brainstorm-requested"
# shellcheck disable=SC2016 # SKILL.md bash excerpt
grep -Fq -- '[[ "$partition_requested" == true || "$brainstorm_requested" == true || "$manual_requested" == true ]]' "$SKILL_MD" \
  || fail "(2754) SKILL.md recovery guard missing partition OR brainstorm OR manual"
# shellcheck disable=SC2016 # jq filter literal
grep -Fq -- '.brainstorm_requested = (.brainstorm_requested == true or $merge_b)' "$SKILL_MD" \
  || fail "(2754) SKILL.md jq merge missing brainstorm_requested arm"
grep -Fq '⏩ 1d.5: brainstorm — skipped' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing skip breadcrumb literal"
grep -Fq 'plan-review-feature-context.txt' "$REPO_ROOT/skills/design/scripts/plan-review-loop.sh" \
  || fail "(2754) plan-review-loop.sh missing plan-review-feature-context merge path"
for _bk in cursor-brainstorm codex-brainstorm; do
  grep -Fq "$_bk" "$TIMING_KINDS_SH" \
    || fail "(2754) scripts/lib-timing-kinds.sh missing timing kind: $_bk"
done

# Check 21 (#2930): Gate B auto-apply default and --manual opt-out pins.
grep -Fq '[--brainstorm] [--manual|-m] [--no-dedup]' "$SKILL_MD" \
  || fail "(2930) SKILL.md argument-hint missing [--manual|-m] between brainstorm and no-dedup"
# shellcheck disable=SC2016 # Markdown literal contains backticks and "$manual" text intentionally.
grep -Fq 'Parse public flags (`--trivial|--simple|--hard`, `-p`/`--partition`, `--brainstorm`, `--manual|-m`, `--no-dedup`, `--run-id`)' "$SKILL_MD" \
  || fail "(FINDING_5) SKILL.md Step 0b public-flag parse list missing --manual|-m"
# shellcheck disable=SC2016 # Markdown table cell literal
grep -Fq '| `--manual` / `-m` |' "$SKILL_MD" \
  || fail "(2930) SKILL.md compact flag table missing --manual/-m row"
# shellcheck disable=SC2016 # SKILL.md bash excerpt; quotes are literal
grep -Fq -- '--manual-gate-b "$manual_requested"' "$SKILL_MD" \
  || fail "(2930) SKILL.md write-run-params invocation missing --manual-gate-b"
# shellcheck disable=SC2016 # Markdown literal; backticks are prose, not shell expansion.
grep -Fq 'append `--manual-requested true` only when `manual_requested=true`' "$SKILL_MD" \
  || fail "(FINDING_16) SKILL.md must omit --manual-requested on non-manual runs"
# shellcheck disable=SC2016 # jq filter literal
grep -Fq -- 'manual_gate_b = $merge_m' "$SKILL_MD" \
  || fail "(FINDING_14) SKILL.md jq merge must overwrite manual_gate_b from current argv state"
# shellcheck disable=SC2016 # SKILL.md bash excerpt; quotes are literal
grep -Fq -- '--manual-gate-b "${manual_requested:-false}"' "$SKILL_MD" \
  || fail "(2930) SKILL.md fallback write-run-params call missing --manual-gate-b"
grep -Fq 'partition, brainstorm, and/or manual requested but jq is unavailable' "$SKILL_MD" \
  || fail "(2930) SKILL.md jq-unavailable warning missing manual"
# shellcheck disable=SC2016 # flags.md list marker uses backticks
grep -Fq '`--manual` / `-m`:' "$FLAGS_MD" \
  || fail "(2930) flags.md missing --manual/-m bullet anchor"
grep -Fq '### Apply-all body' "$APPROVAL_MD" \
  || fail "(2930) approval-gates.md missing Apply-all body heading"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'Execute `### Apply-all body` verbatim' "$APPROVAL_MD" \
  || fail "(2930) approval-gates.md missing Apply-all body references"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
apply_all_reference_count=$(grep -Fc 'Execute `### Apply-all body` verbatim' "$APPROVAL_MD")
[[ "$apply_all_reference_count" -ge 2 ]] \
  || fail "(2930) approval-gates.md must reference Apply-all body from both auto-apply and manual Apply all paths"
grep -Fq 'Determine Gate B mode only after the zero-findings short-circuit above proves there is at least one accepted in-scope finding to handle.' "$APPROVAL_MD" \
  || fail "(FINDING_1) approval-gates.md must resolve Gate B mode before mode-specific presentation"
zero_findings_line=$(grep -nF '### Zero-findings short-circuit' "$APPROVAL_MD" | head -1 | cut -d: -f1 || true)
mode_line=$(grep -nF '#### Gate B mode (auto-apply vs manual)' "$APPROVAL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$zero_findings_line" && -n "$mode_line" ]] \
  || fail "(FINDING_2) approval-gates.md must contain both zero-findings and Gate B mode headings"
if (( zero_findings_line >= mode_line )); then
  fail "(FINDING_2) approval-gates.md must place zero-findings before Gate B mode resolution"
fi
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'if sourced session env exports `MANUAL_REQUESTED=true`, set `manual_gate_b=true` immediately' "$APPROVAL_MD" \
  || fail "(FINDING_2) approval-gates.md missing MANUAL_REQUESTED session-env fallback"
# shellcheck disable=SC2016 # Markdown literal; jq program is prose, not command substitution
grep -Fq "jq -r '.manual_gate_b // false'" "$APPROVAL_MD" \
  || fail "(FINDING_9) approval-gates.md must pin jq -r '.manual_gate_b // false' for missing/null coercion"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'When `manual_gate_b=false`, execute the auto-apply path:' "$APPROVAL_MD" \
  || fail "(2930) approval-gates.md missing unique auto-apply mode branch anchor"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'When `manual_gate_b=true`, print a table under the header `## Plan Review Findings — Review`' "$APPROVAL_MD" \
  || fail "(2930) approval-gates.md missing manual mode presentation branch"
grep -Fq '## Plan Review Findings — Auto-applying' "$APPROVAL_MD" \
  || fail "(FINDING_7) approval-gates.md missing Gate B auto-apply header pin"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'let `manual_requested=true` force `manual_gate_b=true`' "$APPROVAL_MD" \
  || fail "(FINDING_13) approval-gates.md missing defensive in-memory manual_requested pin"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'defaulting to auto-apply unless a true-only manual override is already present' "$APPROVAL_MD" \
  || fail "(FINDING_1) approval-gates.md missing degraded-path auto-apply fallback pin"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'Session env and in-memory state are true-only overrides; persisted `run-params.json` remains the canonical source for proving `manual_gate_b=false`.' "$APPROVAL_MD" \
  || fail "(FINDING_12) approval-gates.md must pin the Gate B mode precedence chain"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'Do not run a separate rollback pass inside Gate B based on `discussion-round2.md`.' "$APPROVAL_MD" \
  || fail "(FINDING_13) approval-gates.md must forbid Gate B rollback from discussion-round2.md"
grep -Fq '### Shared post-apply pipeline' "$APPROVAL_MD" \
  || fail "(FINDING_3) approval-gates.md missing shared post-apply pipeline heading"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'then Execute `### Shared post-apply pipeline` verbatim' "$APPROVAL_MD" \
  || fail "(FINDING_19) approval-gates.md one-by-one path must call the shared post-apply pipeline verbatim"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
shared_pipeline_reference_count=$(grep -Fc 'Execute `### Shared post-apply pipeline` verbatim' "$APPROVAL_MD")
[[ "$shared_pipeline_reference_count" -eq 2 ]] \
  || fail "(FINDING_20) approval-gates.md must reference the shared post-apply pipeline from exactly two Gate B call sites"

grep -Fq 'Gate B — Post-Review Chooser; the zero-findings short-circuit will pass straight through to Step 3b' "$PLAN_REVIEW_MD" \
  || fail "(FINDING_6) plan-review.md missing zero-findings Gate B forwarding pin"
# shellcheck disable=SC2016 # Markdown literal; backticks are plan-review prose, not command substitution
grep -Fq 'findings are surfaced to Gate B, which applies them per `manual_gate_b` mode' "$PLAN_REVIEW_MD" \
  || fail "(FINDING_6) plan-review.md missing Gate B dual-mode application pin"
# shellcheck disable=SC2016 # Markdown literal; backticks are quick-plan-review prose, not command substitution
grep -Fq 'findings flow to Gate B (Step 3.5), which applies them per `manual_gate_b` mode' "$PLAN_REVIEW_QUICK_MD" \
  || fail "(FINDING_6) plan-review-quick.md missing Gate B dual-mode application pin"
# shellcheck disable=SC2016 # Markdown literal; backticks are SKILL.md prose, not command substitution
grep -Fq 'When Gate B resolves `manual_gate_b=false`, it applies every accepted in-scope finding to `plan.txt`' "$SKILL_MD" \
  || fail "(FINDING_7) SKILL.md Step 3 missing auto-apply pin"
# shellcheck disable=SC2016 # Markdown literal; backticks are SKILL.md prose, not command substitution
grep -Fq 'it first checks the zero-findings short-circuit, then resolves `manual_gate_b` before any mode-specific presentation' "$SKILL_MD" \
  || fail "(FINDING_7) SKILL.md Step 3.5 missing zero-findings-before-mode pin"
step0b_second_bash=$(awk '
  /^### 0b / { flag=1; next }
  /^### Final summary block$/ && flag { flag=0 }
  flag && /^```bash$/ { c++; next }
  flag && c == 1 && /^```$/ { c=0; next }
  flag && c == 1 { print }
' "$SKILL_MD")
[[ -n "$step0b_second_bash" ]] \
  || fail "(FINDING_13) could not extract Step 0b run-params bash block"
printf '%s\n' "$step0b_second_bash" | grep -Fq 'write-design-current-env.sh' \
  || fail "(FINDING_13) Step 0b run-params bash block must refresh current-design-env before write-run-params"
# shellcheck disable=SC2016 # grep literal contains shell variables and quotes intentionally
printf '%s\n' "$step0b_second_bash" | grep -Fq -- '--issue-number "$ISSUE_NUMBER"' \
  || fail "(FINDING_13) Step 0b current-design-env refresh must pass --issue-number"
# shellcheck disable=SC2016 # grep literal contains shell variables and quotes intentionally
printf '%s\n' "$step0b_second_bash" | grep -Fq -- '--claude-pid "$PPID"' \
  || fail "(FINDING_13) Step 0b current-design-env refresh must pass --claude-pid \"\$PPID\""
printf '%s\n' "$step0b_second_bash" | grep -Fq '_wdce_step0b_args+=(--manual-requested true)' \
  || fail "(FINDING_13) Step 0b current-design-env refresh must add --manual-requested only on manual runs"
step0b_refresh_line=$(printf '%s\n' "$step0b_second_bash" | grep -nF 'write-design-current-env.sh' | head -1 | cut -d: -f1 || true)
step0b_run_params_line=$(printf '%s\n' "$step0b_second_bash" | grep -nF 'write-run-params.sh' | head -1 | cut -d: -f1 || true)
[[ -n "$step0b_refresh_line" && -n "$step0b_run_params_line" ]] \
  || fail "(FINDING_13) could not locate Step 0b refresh and write-run-params lines"
if (( step0b_refresh_line >= step0b_run_params_line )); then
  fail "(FINDING_13) Step 0b must refresh current-design-env before write-run-params"
fi

# Check FINDING_2678 (#2678): YES↔EXONERATE canonical anchor phrase pinned across 4 prose locations.
CANONICAL_PHRASE='When in doubt between YES and EXONERATE, prefer EXONERATE'
PLAN_REVIEW_MD="$REPO_ROOT/skills/design/references/plan-review.md"
PLAN_REVIEW_QUICK_MD="$REPO_ROOT/skills/design/references/plan-review-quick.md"
RENDER_VOTER_SH="$REPO_ROOT/skills/shared/scripts/render-voter-prompt.sh"

# Location 1: Voter 1 prompt string in plan-review.md (single-line block).
voter1_line=$(grep -n '^- \*\*Voter 1\*\*' "$PLAN_REVIEW_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$voter1_line" ]] || fail "(FINDING_2678) plan-review.md missing '- **Voter 1**' prompt anchor"
voter1_text=$(sed -n "${voter1_line}p" "$PLAN_REVIEW_MD")
grep -Fq "$CANONICAL_PHRASE" <<< "$voter1_text" \
  || fail "(FINDING_2678) plan-review.md Voter 1 prompt missing canonical phrase: $CANONICAL_PHRASE"

# Location 2: shared Voter 2/3 prompt string in plan-review.md (single-line block).
shared_line=$(grep -n '^For Codex, Cursor, and their Claude replacement voters' "$PLAN_REVIEW_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$shared_line" ]] || fail "(FINDING_2678) plan-review.md missing 'For Codex, Cursor, and their Claude replacement voters' shared-voter-prompt anchor"
shared_text=$(sed -n "${shared_line}p" "$PLAN_REVIEW_MD")
grep -Fq "$CANONICAL_PHRASE" <<< "$shared_text" \
  || fail "(FINDING_2678) plan-review.md shared Voter 2/3 prompt missing canonical phrase: $CANONICAL_PHRASE"

# Location 3: render-voter-prompt.sh — the renderer called by dispatch-plan-voters.sh make_prompt_file().
grep -Fq "$CANONICAL_PHRASE" "$RENDER_VOTER_SH" \
  || fail "(FINDING_2678) render-voter-prompt.sh missing canonical phrase (renderer behind dispatch-plan-voters.sh make_prompt_file): $CANONICAL_PHRASE"

# Location 4: plan-review-quick.md — canonical phrase on the inline accept/reject guidance line only.
quick_inline_line=$(grep -n '^For inline accept/reject (there is no separate voter panel)' "$PLAN_REVIEW_QUICK_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$quick_inline_line" ]] \
  || fail "(FINDING_2678) plan-review-quick.md missing 'For inline accept/reject … voter panel' acceptance anchor"
quick_inline_text=$(sed -n "${quick_inline_line}p" "$PLAN_REVIEW_QUICK_MD")
grep -Fq "$CANONICAL_PHRASE" <<< "$quick_inline_text" \
  || fail "(FINDING_2678) plan-review-quick.md inline accept/reject line missing canonical phrase: $CANONICAL_PHRASE"

echo "PASS: FINDING_2678 — YES↔EXONERATE canonical anchor phrase OK (4 locations)"

# Check 19 (#2672): decomposition panel replaces Split-path stub.
DECOMP_REF="$REPO_ROOT/skills/design/references/decompose-panel.md"
[[ -f "$DECOMP_REF" ]] || fail "(19) references/decompose-panel.md missing"
grep -Fq 'decompose-panel-dispatch.sh' "$DECOMP_REF" \
  || fail "(19) decompose-panel.md must retain decompose-panel-dispatch.sh anchor for structure tests"
grep -Fq 'decompose-panel-dispatch.sh' "$SKILL_MD" \
  || fail "(19) SKILL.md Split-path must reference decompose-panel-dispatch.sh"
! grep -q 'decomposition panel is in development' "$SKILL_MD" \
  || fail "(19) SKILL.md must not retain the pre-panel stub string"
echo "PASS: (19) decomposition panel Split-path anchors OK"

# Check 18 (#2702): literal plan-preview header anchors in Step 3 + Gate C prose.
step3_block=$(awk '/^<!-- step:3 /,/^<!-- step:3.5 /' "$SKILL_MD")
printf '%s\n' "$step3_block" | grep -Fq '## Plan Candidate for Review' \
  || fail "(18) SKILL.md Step 3 block missing ## Plan Candidate for Review anchor"
gate_c_block=$(awk '/^## Gate C/,/^## State invariants/' "$APPROVAL_MD")
printf '%s\n' "$gate_c_block" | grep -Fq '## Final Design Plan' \
  || fail "(18) approval-gates.md Gate C block missing ## Final Design Plan anchor"
# Check 20 (#2800): Step 0b title-eligibility filter anchors.
grep -Fq '2.5. **Title-eligibility filter**' "$SKILL_MD" \
  || fail "(20) SKILL.md missing Step 0b sub-step 2.5 Title-eligibility filter"
fetch_line=$(grep -n '^2\. \*\*Fetch issue\*\*:' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
filter_line=$(grep -n '^2\.5\. \*\*Title-eligibility filter\*\*' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
clarify_line=$(grep -n '^3\. \*\*Clarify loop\*\*' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$fetch_line" && -n "$filter_line" && -n "$clarify_line" ]] \
  || fail "(20) Step 0b sub-step 2 / 2.5 / 3 anchors missing"
if (( fetch_line >= filter_line || filter_line >= clarify_line )); then
  fail "(20) Step 0b ordering must be 2 → 2.5 → 3 (lines $fetch_line $filter_line $clarify_line)"
fi
grep -Fq 'title_has_lifecycle_reject_prefix' "$SKILL_MD" \
  || fail "(20) SKILL.md missing title_has_lifecycle_reject_prefix"
grep -Fq "Source \`\${CLAUDE_PLUGIN_ROOT}/scripts/lib-title-eligibility.sh\`." "$SKILL_MD" \
  || fail "(20) SKILL.md missing lib-title-eligibility.sh source line"
grep -Fq 'title_has_archival_report_prefix' "$SKILL_MD" \
  || fail "(20) SKILL.md missing title_has_archival_report_prefix"
grep -Fq 'title_starts_with_brainstorm' "$SKILL_MD" \
  || fail "(20) SKILL.md missing title_starts_with_brainstorm"
grep -Fq 'Mandatory predicate order: (a) lifecycle-reject' "$SKILL_MD" \
  || fail "(20) SKILL.md missing mandatory predicate ordering rule"
grep -Fq 'cancelled-title-filter' "$SKILL_MD" \
  || fail "(20) SKILL.md missing cancelled-title-filter enum"
grep -Fq 'issue title starts with managed lifecycle marker' "$SKILL_MD" \
  || fail "(20) SKILL.md missing lifecycle-reject banner text"
grep -Fq 'issue title matches archival report-prefix' "$SKILL_MD" \
  || fail "(20) SKILL.md missing archival-report-reject banner text"
grep -Fq 'detected Brainstorm title prefix — auto-enabling brainstorm mode' "$SKILL_MD" \
  || fail "(20) SKILL.md missing brainstorm info banner text"
echo "PASS: (20) Step 0b title-eligibility filter anchors OK"

echo "PASS: test-design-structure.sh — structural invariants hold (including security OOS exclusions)"
exit 0
