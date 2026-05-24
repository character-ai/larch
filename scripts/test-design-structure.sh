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

# shellcheck disable=SC2016 # fixed-string grep literal intentionally contains shell syntax from markdown examples.
collector_output_count=$(printf '%s\n' "$regular_collector_section" | { grep -F -- '"$DESIGN_TMPDIR/' || true; } | wc -l | tr -d ' ')
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

# Check 7 (#661): plan-review.md collect-agent-results.sh invocation must carry
# both --substantive-validation AND --validation-mode on the SAME line as --timeout
# 1860 so banner-only reviewer output is rejected as STATUS=NOT_SUBSTANTIVE rather
# than passing as STATUS=OK. Pipeline matches the test-review-structure.sh (13)
# pattern: each filter stage threads one literal while preserving line granularity.
# A future edit that drops either flag, or splits the invocation across multiple
# lines, fails closed under `set -o pipefail`.
PLAN_REVIEW_MD="$REPO_ROOT/skills/design/references/plan-review.md"
[[ -f "$PLAN_REVIEW_MD" ]] || fail "plan-review.md missing: $PLAN_REVIEW_MD"
grep 'collect-agent-results.sh' "$PLAN_REVIEW_MD" \
  | grep -F -- '--timeout 1860' \
  | grep -F -- '--substantive-validation' \
  | grep -Fq -- '--validation-mode' \
  || fail "(7) no single plan-review.md line carries 'collect-agent-results.sh', '--timeout 1860', '--substantive-validation', and '--validation-mode' together — issue #661 substantive-validation contract pin is broken"

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

# Check 15: /design SKILL.md pairs terminal cost emission with operator-cancel /
# plan-write-failure markers (or cites the shared ### Terminal cost line block).
for marker in \
  '**ℹ /design cancelled by operator.**' \
  '**⚠ 5: plan-block-write failed' \
  ; do
  line=$(grep -nF "$marker" "$SKILL_MD" | head -1 | cut -d: -f1 || true)
  [[ -n "$line" ]] || fail "(15) missing stable marker: $marker"
  start=$(( line > 45 ? line - 45 : 1 ))
  window=$(sed -n "${start},${line}p" "$SKILL_MD")
  if printf '%s\n' "$window" | grep -Fq 'render-cost-line.sh'; then
    :
  elif printf '%s\n' "$window" | grep -Fq '### Terminal cost line'; then
    :
  else
    fail "(15) marker not paired with render-cost-line.sh / ### Terminal cost line within 45 lines: $marker (line $line)"
  fi
done
footer_line=$(grep -nF '➡️ 5: finalize — plan written to issue' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$footer_line" ]] || fail "(15) missing machine footer line (finalize)"
fstart=$(( footer_line > 55 ? footer_line - 55 : 1 ))
fwindow=$(sed -n "${fstart},${footer_line}p" "$SKILL_MD")
if printf '%s\n' "$fwindow" | grep -Fq 'render-cost-line.sh'; then
  :
elif printf '%s\n' "$fwindow" | grep -Fq '### Terminal cost line'; then
  :
else
  fail "(15) machine footer not preceded by cost-line anchor within 55 lines"
fi

# Check 14: design ACTION dispatcher pins. The focus-area enum must remain in
# SKILL.md because CI and prompt rendering scan the inline reviewer launch
# blocks, while scriptable mechanics route through ACTION records.
focus_anchor_count=$(grep -Fc 'Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security' "$SKILL_MD")
[[ "$focus_anchor_count" == "10" ]] \
  || fail "(14a) SKILL.md must keep 10 focus-area enum anchor comments; found $focus_anchor_count"
grep -Fq 'ACTION=EMIT_PLAN' "$SKILL_MD" \
  || fail "(14b1) SKILL.md missing ACTION=EMIT_PLAN emission"
grep -Fq 'ACTION=TALLY' "$SKILL_MD" \
  || fail "(14b2) SKILL.md missing ACTION=TALLY emission"
grep -Fq 'ACTION=FINALIZE' "$SKILL_MD" \
  || fail "(14b3) SKILL.md missing ACTION=FINALIZE emission"
grep -Fq 'design-driver.sh' "$SKILL_MD" \
  || fail "(14b4) SKILL.md missing design-driver.sh dispatcher invocation"
grep -Fq 'scout-plan-archetypes-wrapper.sh' "$SKILL_MD" \
  || fail "(14c1) SKILL.md missing scout-plan-archetypes-wrapper.sh (plan-review dynamic scout)"
grep -Fq 'dispatch-plan-review-panel.sh' "$SKILL_MD" \
  || fail "(14c2) SKILL.md missing dispatch-plan-review-panel.sh (plan-review panel manifest)"
grep -Fq 'PANEL_PATHS_FILE' "$SKILL_MD" \
  || fail "(14c3) SKILL.md missing PANEL_PATHS_FILE parse contract for plan-review collection"

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
grep -Fq '5→6' "$SKILL_MD" \
  || fail "(15b) anti-halt reminder must mention 5→6 step boundary"

echo "PASS: test-design-structure.sh — structural invariants hold (including security OOS exclusions)"
exit 0
