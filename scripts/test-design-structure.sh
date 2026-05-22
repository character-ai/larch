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
#  - SKILL.md Step 0 gates /design through session-entry-gate.sh; standalone
#    mode derives branch facts with create-branch.sh --check, while nested
#    --branch-info calls feed already-parsed facts into the shared gate.
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

# The MANDATORY directive must appear in the header region (before step 6 body).
step6_line=$(grep -n '^6\. \*\*Per-decision prompt-file rendering' "$DIALEXEC_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step6_line" ]] || fail "references/dialectic-execution.md missing '6. Per-decision prompt-file rendering' body"

mandatory_line=$(grep -n 'MANDATORY — READ ENTIRE FILE before rendering debate prompts' "$DIALEXEC_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$mandatory_line" ]] || fail "references/dialectic-execution.md lacks header MANDATORY naming dialectic-debate.md"

if (( mandatory_line >= step6_line )); then
  fail "references/dialectic-execution.md header MANDATORY (line $mandatory_line) must appear BEFORE step 6 (line $step6_line)"
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

# Check 11: clean-main Step 0 entry gate. The shared helper owns the decision:
# standalone /design derives branch facts first, nested /design uses the
# --branch-info facts, and both paths feed session-entry-gate.sh before setup.
step0_section=$(awk '
  /^<!-- step:0 — Session Setup -->$/ { flag=1; next }
  /^<!-- step:1 / && flag { flag=0 }
  flag { print }
' "$SKILL_MD")
[[ -n "$step0_section" ]] \
  || fail "(11) could not extract /design Step 0 section"

printf '%s\n' "$step0_section" | grep -Fq 'branch_info_supplied=true' \
  || fail "(11) Step 0 must define branch_info_supplied=true as the nested /implement gate"
printf '%s\n' "$step0_section" | grep -Fq 'branch_info_supplied=false' \
  || fail "(11) Step 0 must define the standalone branch_info_supplied=false gate"
# shellcheck disable=SC2016 # fixed-string grep literal contains shell variable syntax
printf '%s\n' "$step0_section" | grep -Fq '${CLAUDE_PLUGIN_ROOT}/scripts/create-branch.sh --check' \
  || fail "(11) standalone /design Step 0 must run create-branch.sh --check"
# shellcheck disable=SC2016 # fixed-string grep literal contains shell variable syntax
printf '%s\n' "$step0_section" | grep -Fq '${CLAUDE_PLUGIN_ROOT}/scripts/session-entry-gate.sh' \
  || fail "(11) /design Step 0 must invoke session-entry-gate.sh"
printf '%s\n' "$step0_section" | grep -Fq -- '--mode design' \
  || fail "(11) /design Step 0 must invoke session-entry-gate.sh with --mode design"
# shellcheck disable=SC2016 # fixed-string grep literal contains shell variable syntax
printf '%s\n' "$step0_section" | grep -Fq -- '--branch-info-supplied "$branch_info_supplied"' \
  || fail "(11) /design Step 0 must pass --branch-info-supplied to session-entry-gate.sh"
printf '%s\n' "$step0_section" | grep -Fq 'SKIP_BRANCH_CHECK' \
  || fail "(11) /design Step 0 must parse/use SKIP_BRANCH_CHECK as the authoritative key"
printf '%s\n' "$step0_section" | grep -Fq 'GATE_ERROR' \
  || fail "(11) /design Step 0 must handle GATE_ERROR separately from PREFLIGHT_ERROR"
printf '%s\n' "$step0_section" | grep -F 'session-setup.sh' \
  | grep -F -- '--skip-branch-check' >/dev/null \
  || fail "(11) Step 0 must include a session-setup.sh invocation with --skip-branch-check for SKIP_BRANCH_CHECK=true"
# shellcheck disable=SC2016 # fixed-string grep literal contains backtick-quoted token names
printf '%s\n' "$step0_section" | grep -Fq 'If `SKIP_BRANCH_CHECK=false`, run setup without `--skip-branch-check`' \
  || fail "(11) Step 0 must document the strict no-skip preflight path"
printf '%s\n' "$step0_section" | grep -F 'session-setup.sh --prefix claude-design' >/dev/null \
  || fail "(11) Step 0 must include the no-skip claude-design session-setup.sh invocation"
printf '%s\n' "$step0_section" | grep -Fq '/design requires clean main to start' \
  || fail "(11) Step 0 must include the normalized /design clean-main failure message"
# shellcheck disable=SC2016 # fixed-string grep literal contains shell variable syntax
printf '%s\n' "$step0_section" | grep -Fq 'Only include `--caller-env "$SESSION_ENV_PATH"` if `SESSION_ENV_PATH` is non-empty' \
  || fail "(11) Step 0 must retain the Anti-pattern #4 caller-env predicate"

# shellcheck disable=SC2016 # fixed-string grep literal contains shell variable syntax
create_line=$(printf '%s\n' "$step0_section" | grep -nF '${CLAUDE_PLUGIN_ROOT}/scripts/create-branch.sh --check' | head -1 | cut -d: -f1 || true)
# shellcheck disable=SC2016 # fixed-string grep literal contains shell variable syntax
gate_line=$(printf '%s\n' "$step0_section" | grep -nF '${CLAUDE_PLUGIN_ROOT}/scripts/session-entry-gate.sh' | head -1 | cut -d: -f1 || true)
# shellcheck disable=SC2016 # fixed-string grep literal contains shell variable syntax
setup_line=$(printf '%s\n' "$step0_section" | grep -nF '${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh' | head -1 | cut -d: -f1 || true)
[[ -n "$create_line" && -n "$gate_line" && -n "$setup_line" ]] \
  || fail "(11) could not locate create-branch, session-entry-gate, and session-setup lines in Step 0"
if (( create_line >= gate_line || gate_line >= setup_line )); then
  fail "(11) standalone /design Step 0 ordering must be create-branch.sh --check before session-entry-gate.sh before session-setup.sh"
fi
if (( gate_line >= setup_line )); then
  fail "(11) nested /design Step 0 ordering must be session-entry-gate.sh before session-setup.sh"
fi

old_design_prose='Run the shared session setup script. This handles preflight, temp directory creation, reviewer presence check, and presence status in a single call'
if grep -Fq "$old_design_prose" "$SKILL_MD"; then
  fail "(11) SKILL.md still contains legacy unconditional Step 0 session-setup prose"
fi

# Check 13: accepted-OOS security exclusion pins. plan-review.md owns both the
# parent `/implement` accepted-OOS artifact write and the design visibility
# export; both public-boundary paths must explicitly exclude accepted
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

# Check 14: design ACTION dispatcher pins. The focus-area enum must remain in
# SKILL.md because CI and prompt rendering scan the inline reviewer launch
# blocks, while scriptable mechanics route through ACTION records.
focus_anchor_count=$(grep -Fc 'Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security' "$SKILL_MD")
[[ "$focus_anchor_count" == "10" ]] \
  || fail "(14a) SKILL.md must keep 10 focus-area enum anchor comments; found $focus_anchor_count"
grep -Fq 'ACTION=EMIT_PLAN' "$SKILL_MD" \
  || fail "(14b) SKILL.md missing ACTION=EMIT_PLAN emission"
grep -Fq 'ACTION=TALLY' "$SKILL_MD" \
  || fail "(14b) SKILL.md missing ACTION=TALLY emission"
grep -Fq 'ACTION=FINALIZE' "$SKILL_MD" \
  || fail "(14b) SKILL.md missing ACTION=FINALIZE emission"
grep -Fq 'design-driver.sh' "$SKILL_MD" \
  || fail "(14b) SKILL.md missing design-driver.sh dispatcher invocation"

echo "PASS: test-design-structure.sh — structural invariants hold (including security OOS exclusions)"
exit 0
