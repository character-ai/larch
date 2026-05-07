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

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

# Check 1: SKILL.md flag-table MANDATORY pointer appears before Step 0.
[[ -f "$SKILL_MD" ]] || fail "SKILL.md missing: $SKILL_MD"

flag_mandatory_line=$(grep -n 'MANDATORY — READ ENTIRE FILE before parsing argument flags' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$flag_mandatory_line" ]] || fail "SKILL.md lacks 'MANDATORY — READ ENTIRE FILE before parsing argument flags' pointer to references/flags.md"

step0_line=$(grep -n '^## Step 0' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step0_line" ]] || fail "SKILL.md lacks '## Step 0' heading"

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
    matches=$(grep -rnF -- "$token" "$DESIGN_DIR" | head -3)
    fail "skills/design/ contains forbidden Step-3a-removal-residue token '$token':
$matches"
  fi
done

# Check 6: SKILL.md Step 3 and Step 3.5 auto-mode forward-pointers must reference Step 3b (not Step 3a).
# shellcheck disable=SC2016 # single quotes intentional — pattern includes literal backticks
grep -qF 'or Step 3b if `auto_mode=true`' "$SKILL_MD" \
  || fail "SKILL.md Step 3 'all reviewers OK' branch must point forward to 'Step 3b if auto_mode=true' (issue #453: Step-3a removal residue pin)"

grep -qF 'and proceed to Step 3b' "$SKILL_MD" \
  || fail "SKILL.md Step 3.5 auto-mode branch must 'proceed to Step 3b' (issue #453: Step-3a removal residue pin)"

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

# Check 8: nested /implement design handoff must use the file-backed manifest
# writer and heavy-worker contract, while standalone mode skips the manifest.
[[ -f "$REPO_ROOT/skills/design/references/heavy-worker.md" ]] \
  || fail "(8) heavy-worker.md missing — subagent /design heavy phase has no subagent runbook"
[[ -x "$REPO_ROOT/skills/design/scripts/write-design-manifest.sh" ]] \
  || fail "(8) write-design-manifest.sh missing or not executable"
[[ -x "$REPO_ROOT/skills/design/scripts/read-design-manifest.sh" ]] \
  || fail "(8) read-design-manifest.sh missing or not executable"
# shellcheck disable=SC2016 # fixed-string grep literals contain shell variables/backticks
grep -Fq 'write-design-manifest.sh --design-tmpdir "$DESIGN_TMPDIR" --implement-tmpdir "$(dirname "$SESSION_ENV_PATH")"' "$SKILL_MD" \
  || fail "(8) SKILL.md lacks Step 5 write-design-manifest.sh invocation with DESIGN_TMPDIR + dirname(SESSION_ENV_PATH)"
# shellcheck disable=SC2016 # fixed-string grep literal contains markdown backticks
grep -Fq 'If `SESSION_ENV_PATH` is empty, skip this manifest write' "$SKILL_MD" \
  || fail "(8) SKILL.md lacks standalone-mode manifest-skip branch"
# shellcheck disable=SC2016 # fixed-string grep literal contains markdown backticks
grep -Fq 'read the Step 3 external reviewer launch Bash blocks directly from `${CLAUDE_PLUGIN_ROOT}/skills/design/SKILL.md`' "$REPO_ROOT/skills/design/references/heavy-worker.md" \
  || fail "(8) heavy-worker.md must tell the subagent to read Step 3 reviewer launch blocks from \${CLAUDE_PLUGIN_ROOT}/skills/design/SKILL.md"

# Check 9: load-bearing conversation-context dependency phrases are absent.
GREP_TMP=$(mktemp "${TMPDIR:-/tmp}/larch-design-structure-grep.XXXXXX")
trap 'rm -f "$GREP_TMP"' EXIT
if grep -rnE 'visible in conversation|retrieved from.*conversation' "$REPO_ROOT/skills/design" "$REPO_ROOT/skills/implement" "$REPO_ROOT/skills/shared" >"$GREP_TMP" 2>/dev/null; then
  matches=$(head -5 "$GREP_TMP")
  fail "(9) found forbidden conversation-context dependency phrase:
$matches"
fi

# Check 10: --subagent flag and the renamed Step 2a heavy-phase block (issue #1036).
# (10a) flags.md must carry `--subagent` and `subagent_mode=true` on the same bullet.
grep -F -- '--subagent' "$FLAGS_MD" \
  | grep -Fq -- 'subagent_mode=true' \
  || fail "(10a) flags.md must carry both '--subagent' and 'subagent_mode=true' on the same bullet (issue #1036)"
# (10b) SKILL.md must contain the literal `--subagent` AND `subagent_mode=true`.
grep -Fq -- '--subagent' "$SKILL_MD" \
  || fail "(10b) SKILL.md missing '--subagent' literal (issue #1036)"
grep -Fq -- 'subagent_mode=true' "$SKILL_MD" \
  || fail "(10b) SKILL.md missing 'subagent_mode=true' literal (issue #1036)"
# (10c) SKILL.md must carry the renamed heading `### Heavy phase dispatch` and the
#       renamed paragraph token `Subagent heavy phase`, AND must NOT carry the old
#       `Nested heavy phase` token.
grep -Fq -- '### Heavy phase dispatch' "$SKILL_MD" \
  || fail "(10c) SKILL.md missing '### Heavy phase dispatch' heading (issue #1036 — Step 2a heavy phase hoisted out of Quick mode)"
grep -Fq -- 'Subagent heavy phase' "$SKILL_MD" \
  || fail "(10c) SKILL.md missing 'Subagent heavy phase' renamed paragraph (issue #1036)"
if grep -Fq -- 'Nested heavy phase' "$SKILL_MD"; then
  fail "(10c) SKILL.md still contains legacy 'Nested heavy phase' token — should be renamed to 'Subagent heavy phase' (issue #1036)"
fi

# Check 11: clean-main Step 0 entry gate. The shared helper owns the decision:
# standalone /design derives branch facts first, nested /design uses the
# --branch-info facts, and both paths feed session-entry-gate.sh before setup.
step0_section=$(awk '
  /^## Step 0 — Session Setup$/ { flag=1; next }
  /^## / && flag { flag=0 }
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
printf '%s\n' "$step0_section" | grep -F 'session-setup.sh --prefix claude-design --skip-slack-check' >/dev/null \
  || fail "(11) Step 0 must include the no-skip claude-design session-setup.sh invocation"
printf '%s\n' "$step0_section" | grep -Fq '/design requires clean main to start' \
  || fail "(11) Step 0 must include the normalized /design clean-main failure message"
# shellcheck disable=SC2016 # fixed-string grep literal contains shell variable syntax
printf '%s\n' "$step0_section" | grep -Fq 'Only include `--caller-env "$SESSION_ENV_PATH"` and `--write-health "${SESSION_ENV_PATH}.health"` if `SESSION_ENV_PATH` is non-empty' \
  || fail "(11) Step 0 must retain the Anti-pattern #4 caller-env/write-health predicate"

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

old_design_prose='Run the shared session setup script. This handles preflight, temp directory creation, reviewer health probe, and health status file in a single call'
if grep -Fq "$old_design_prose" "$SKILL_MD"; then
  fail "(11) SKILL.md still contains legacy unconditional Step 0 session-setup prose"
fi

# Check 12: heavy-worker post-return fail-closed gate (issue #1405). The Step 2a
# fail-closed validation that runs after the heavy-worker subagent returns must
# pin the REASON token and the gated artifact paths so a future edit cannot
# silently weaken the gate. The non-empty (`-s`) tier covers the substantive
# artifacts mandated as non-empty by heavy-worker.md "Artifact Contract"; the
# existence (`-f`) tier covers may-be-empty manifest-required artifacts staged
# by `write-design-manifest.sh` via `copy_required_may_be_empty`.
grep -Fq -- 'REASON=worker-yielded-without-artifacts' "$SKILL_MD" \
  || fail "(12) SKILL.md missing REASON=worker-yielded-without-artifacts token in heavy-worker fail-closed gate (issue #1405)"
# shellcheck disable=SC2016 # fixed-string grep literals contain shell variable syntax
grep -Fq -- '! -s "$DESIGN_TMPDIR/plan.txt"' "$SKILL_MD" \
  || fail "(12) SKILL.md missing non-empty (-s) check on plan.txt in heavy-worker fail-closed gate (issue #1405)"
# shellcheck disable=SC2016
grep -Fq -- '! -s "$DESIGN_TMPDIR/approach-synthesis.txt"' "$SKILL_MD" \
  || fail "(12) SKILL.md missing non-empty (-s) check on approach-synthesis.txt in heavy-worker fail-closed gate (issue #1405)"
# shellcheck disable=SC2016
grep -Fq -- '! -s "$DESIGN_TMPDIR/voting-tally.md"' "$SKILL_MD" \
  || fail "(12) SKILL.md missing non-empty (-s) check on voting-tally.md in heavy-worker fail-closed gate (issue #1405)"
# shellcheck disable=SC2016
grep -Fq -- '! -f "$DESIGN_TMPDIR/contested-decisions.md"' "$SKILL_MD" \
  || fail "(12) SKILL.md missing existence (-f) check on contested-decisions.md in heavy-worker fail-closed gate (issue #1405)"
# shellcheck disable=SC2016
grep -Fq -- '! -f "$DESIGN_TMPDIR/oos.md"' "$SKILL_MD" \
  || fail "(12) SKILL.md missing existence (-f) check on oos.md in heavy-worker fail-closed gate (issue #1405)"
# shellcheck disable=SC2016
grep -Fq -- '! -f "$DESIGN_TMPDIR/rejected-findings.md"' "$SKILL_MD" \
  || fail "(12) SKILL.md missing existence (-f) check on rejected-findings.md in heavy-worker fail-closed gate (issue #1405)"
# shellcheck disable=SC2016
grep -Fq -- '! -f "$DESIGN_TMPDIR/accepted-plan-findings.md"' "$SKILL_MD" \
  || fail "(12) SKILL.md missing existence (-f) check on accepted-plan-findings.md in heavy-worker fail-closed gate (issue #1405)"

# Check 12b: heavy-worker.md Wait Discipline section pins the foreground-collect
# rule introduced in issue #1405. The literal subsection header and the
# "wait for notifications" anti-pattern phrase must remain so a future edit
# cannot silently drop the prompt-level rule.
grep -Fq -- '## Wait Discipline' "$REPO_ROOT/skills/design/references/heavy-worker.md" \
  || fail "(12b) heavy-worker.md missing '## Wait Discipline' subsection header (issue #1405)"
grep -Fq -- 'wait for notifications' "$REPO_ROOT/skills/design/references/heavy-worker.md" \
  || fail "(12b) heavy-worker.md missing 'wait for notifications' anti-pattern phrase in Wait Discipline section (issue #1405)"

echo "PASS: test-design-structure.sh — all 12 structural invariants hold"
exit 0
