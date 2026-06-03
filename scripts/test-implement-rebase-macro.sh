#!/bin/bash
# Structural regression test for /implement Rebase Checkpoint Macro + probe wrappers.
# Exit 0 on pass, exit 1 on any assertion failure.
# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SKILL_MD="$REPO_ROOT/skills/implement/SKILL.md"
WRAPPER="$REPO_ROOT/scripts/rebase-checkpoint-probe.sh"
STEP7A_WRAPPER="$REPO_ROOT/skills/implement/scripts/step-7a.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[[ -f "$SKILL_MD" ]] || fail "skills/implement/SKILL.md missing: $SKILL_MD"
[[ -f "$WRAPPER" ]] || fail "scripts/rebase-checkpoint-probe.sh missing: $WRAPPER"
[[ -f "$STEP7A_WRAPPER" ]] || fail "skills/implement/scripts/step-7a.sh missing: $STEP7A_WRAPPER"

# ---------------------------------------------------------------------------
# (A) Exactly one `## Rebase Checkpoint Macro` header.
# ---------------------------------------------------------------------------
macro_header_count=$(grep -c '^## Rebase Checkpoint Macro$' "$SKILL_MD" || true)
[[ "$macro_header_count" == "1" ]] \
  || fail "(A) expected exactly one '## Rebase Checkpoint Macro' header, found $macro_header_count"

macro_header_line=$(grep -m 1 -n '^## Rebase Checkpoint Macro$' "$SKILL_MD" | cut -d: -f1)

# ---------------------------------------------------------------------------
# (F) Placement: macro header between ### Verbosity Control and the Step 0 anchor.
# ---------------------------------------------------------------------------
verbosity_line=$(grep -n '^### Verbosity Control$' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$verbosity_line" ]] || fail "(F) SKILL.md lacks '### Verbosity Control' header"

step0_line=$(grep -n '^<!-- step:0 — Session Setup -->$' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step0_line" ]] || fail "(F) SKILL.md lacks '<!-- step:0 — Session Setup -->' anchor"

if (( macro_header_line <= verbosity_line )); then
  fail "(F) macro header (line $macro_header_line) must appear AFTER '### Verbosity Control' (line $verbosity_line)"
fi
if (( macro_header_line >= step0_line )); then
  fail "(F) macro header (line $macro_header_line) must appear BEFORE Step 0 anchor (line $step0_line)"
fi

macro_section_start=$macro_header_line
macro_section_end=$step0_line

# ---------------------------------------------------------------------------
# (B) Call-site registry: four canonical rows present in macro section.
# ---------------------------------------------------------------------------
registry_rows=(
  '| 1.r  | `1.r`           | `plan materialization` |'
  '| 4.r  | `4.r`           | `commit (impl)`  |'
  '| 7.r  | `7.r`           | `commit (review)`|'
  '| 7a.r | `7a.r`          | `diagrams`       |'
)
for row in "${registry_rows[@]}"; do
  count=$(sed -n "${macro_section_start},${macro_section_end}p" "$SKILL_MD" | grep -Fc "$row" || true)
  [[ "$count" -ge 1 ]] \
    || fail "(B) macro Call-site registry missing row: $row"
done

# ---------------------------------------------------------------------------
# (C) Three direct rebase-checkpoint-probe.sh invocations in SKILL.md, with
#     7a.r reached through step-7a.sh.
# ---------------------------------------------------------------------------
wrapper_count=$(grep -cF '"${CLAUDE_PLUGIN_ROOT}/scripts/rebase-checkpoint-probe.sh"' "$SKILL_MD" || true)
[[ "$wrapper_count" == "3" ]] \
  || fail "(C) expected exactly 3 direct rebase-checkpoint-probe.sh invocations in SKILL.md, found $wrapper_count"

skill_pairs=(
  'rebase-checkpoint-probe.sh" 1.r'
  'rebase-checkpoint-probe.sh" 4.r'
  'rebase-checkpoint-probe.sh" 7.r'
)
for pair in "${skill_pairs[@]}"; do
  grep -Fq "$pair" "$SKILL_MD" \
    || fail "(C) missing canonical wrapper invocation containing: $pair"
done

step7a_wrapper_count=$(grep -cF '"$PLUGIN_ROOT/scripts/rebase-checkpoint-probe.sh" 7a.r' "$STEP7A_WRAPPER" || true)
[[ "$step7a_wrapper_count" == "1" ]] \
  || fail "(C) expected exactly 1 7a.r rebase-checkpoint-probe.sh invocation in step-7a.sh, found $step7a_wrapper_count"

# ---------------------------------------------------------------------------
# (C') forked_target BASE_ARGS guard near every wrapper line; step-7a derives
#      BASE_ARGS from module-level base_remote/base_ref before its wrapper.
# ---------------------------------------------------------------------------
while IFS= read -r line_num; do
  start=$((line_num > 10 ? line_num - 10 : 1))
  window=$(sed -n "${start},$((line_num - 1))p" "$SKILL_MD")
  echo "$window" | grep -Fq 'if [ "${forked_target:-false}" = "true" ]' \
    || fail "(C') missing forked_target guard within 10 lines above wrapper at line $line_num"
  echo "$window" | grep -Fq 'BASE_ARGS=(--base-remote upstream --base-ref main)' \
    || fail "(C') missing BASE_ARGS fork argv within 10 lines above wrapper at line $line_num"
done < <(grep -nF '"${CLAUDE_PLUGIN_ROOT}/scripts/rebase-checkpoint-probe.sh"' "$SKILL_MD" | cut -d: -f1)

while IFS= read -r line_num; do
  start=$((line_num > 10 ? line_num - 10 : 1))
  window=$(sed -n "${start},$((line_num - 1))p" "$STEP7A_WRAPPER")
  before_wrapper=$(sed -n "1,$((line_num - 1))p" "$STEP7A_WRAPPER")
  echo "$before_wrapper" | grep -Fq 'base_remote=' \
    || fail "(C') missing base_remote assignment before step-7a wrapper at line $line_num"
  echo "$before_wrapper" | grep -Fq 'base_ref=' \
    || fail "(C') missing base_ref assignment before step-7a wrapper at line $line_num"
  echo "$window" | grep -Fq 'BASE_ARGS=(--base-remote "$base_remote" --base-ref "$base_ref")' \
    || fail "(C') missing derived BASE_ARGS within 10 lines above step-7a wrapper at line $line_num"
done < <(grep -nF '"$PLUGIN_ROOT/scripts/rebase-checkpoint-probe.sh" 7a.r' "$STEP7A_WRAPPER" | cut -d: -f1)

# ---------------------------------------------------------------------------
# (E) Step 7.r: FILES_CHANGED=true prose above 7.r wrapper; wrapper before Step 7a anchor.
# ---------------------------------------------------------------------------
step7_header_line=$(grep -n '^<!-- step:7 — Second Commit (review fixes) -->$' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step7_header_line" ]] || fail "(E) SKILL.md lacks Step 7 anchor"

step7a_header_line=$(grep -n '^<!-- step:7a — Code Flow Diagram -->$' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step7a_header_line" ]] || fail "(E) SKILL.md lacks Step 7a anchor"

invoke_7r_line=$(grep -nF 'rebase-checkpoint-probe.sh" 7.r' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$invoke_7r_line" ]] || fail "(E) 7.r wrapper invocation not found"

if (( invoke_7r_line <= step7_header_line )); then
  fail "(E) 7.r invocation (line $invoke_7r_line) must be AFTER Step 7 anchor (line $step7_header_line)"
fi
if (( invoke_7r_line >= step7a_header_line )); then
  fail "(E) 7.r invocation (line $invoke_7r_line) must be BEFORE Step 7a anchor (line $step7a_header_line)"
fi

files_changed_line=$(sed -n "${step7_header_line},$((invoke_7r_line - 1))p" "$SKILL_MD" | grep -n 'FILES_CHANGED=true' | head -1 | cut -d: -f1 || true)
[[ -n "$files_changed_line" ]] \
  || fail "(E) Step 7.r: 'FILES_CHANGED=true' guard prose must appear above the 7.r wrapper invocation"

# ---------------------------------------------------------------------------
# (G) Thin-pointer macro section + FINDING_9 bail strings + FINDING_3 anti-pattern.
# ---------------------------------------------------------------------------
macro_body_tmp=$(mktemp)
sed -n "${macro_section_start},${macro_section_end}p" "$SKILL_MD" > "$macro_body_tmp"
grep -Fq 'scripts/rebase-checkpoint-probe.sh' "$macro_body_tmp" \
  || fail "(G) macro section lacks thin-pointer rebase-checkpoint-probe.sh reference"
grep -Fq 'caller_kind=early_rebase' "$macro_body_tmp" \
  || fail "(G) macro section lacks caller_kind=early_rebase"
grep -Fq '**⚠ Rebase onto main failed (non-conflict): $REBASE_ERROR. Bailing to cleanup.**' "$macro_body_tmp" \
  || fail "(G) macro section lacks non-conflict bail line"
grep -Fq '**⚠ Rebase onto main failed unexpectedly' "$macro_body_tmp" \
  || fail "(G) macro section lacks unexpected-exit bail line"
rm -f "$macro_body_tmp"

dup_phrase='After the macro returns, run the Phantom Untracked Probe'
dup_count=$(grep -cF "$dup_phrase" "$SKILL_MD" || true)
[[ "$dup_count" == "0" ]] \
  || fail "(G) FINDING_3: must not retain duplicate phantom prose ($dup_count occurrences of \"$dup_phrase\")"

# ---------------------------------------------------------------------------
# (H) rebase-push.sh flag combo: exactly once in wrapper (argv array), zero in SKILL.md.
# ---------------------------------------------------------------------------
flag_combo='rebase-push.sh --no-push --skip-if-pushed --keep-on-conflict'
skill_combo_count=$(grep -cF "$flag_combo" "$SKILL_MD" || true)
[[ "$skill_combo_count" == "0" ]] \
  || fail "(H) expected zero '$flag_combo' occurrences in SKILL.md, found $skill_combo_count"

grep -Fq 'rebase_args=(--no-push --skip-if-pushed --keep-on-conflict)' "$WRAPPER" \
  || fail "(H) rebase-checkpoint-probe.sh must define rebase_args with --no-push --skip-if-pushed --keep-on-conflict"
wrapper_push_refs=$(grep -cF 'rebase-push.sh' "$WRAPPER" || true)
[[ "$wrapper_push_refs" == "1" ]] \
  || fail "(H) expected exactly one rebase-push.sh invocation line in rebase-checkpoint-probe.sh, found $wrapper_push_refs"

SUBPROC_MD="$REPO_ROOT/skills/implement/references/conflict-resolution.md"
[[ -f "$SUBPROC_MD" ]] || fail "(H) references/conflict-resolution.md missing: $SUBPROC_MD"
grep -Fq 'Retired in Phase 1' "$SUBPROC_MD" \
  || fail "(H) conflict-resolution.md must be the Phase 1 retirement stub"

SHIP_PR_SH="$REPO_ROOT/scripts/ship-pr.sh"
[[ -f "$SHIP_PR_SH" ]] || fail "(H) scripts/ship-pr.sh missing: $SHIP_PR_SH"
grep -Fq 'rebase-push.sh" --no-push --keep-on-conflict' "$SHIP_PR_SH" \
  || fail "(H) scripts/ship-pr.sh run_rebase_rebump must invoke rebase-push.sh --no-push --keep-on-conflict"

# ---------------------------------------------------------------------------
# (I) Cross-doc pins: conflict-resolution.md + ship-pr Phase 1–4 handoff tokens.
# ---------------------------------------------------------------------------
CONFLICT_MD="$REPO_ROOT/skills/implement/references/conflict-resolution.md"
[[ -f "$CONFLICT_MD" ]] || fail "(I) skills/implement/references/conflict-resolution.md missing: $CONFLICT_MD"

grep -Fq 'rebase-push.sh" --no-push --keep-on-conflict' "$SHIP_PR_SH" \
  || fail "(I) scripts/ship-pr.sh must retain run_rebase_rebump rebase-push.sh --no-push --keep-on-conflict invocation"

grep -Fq 'RESUME_PHASE ship-pr-rrr-phase14' "$SHIP_PR_SH" \
  || fail "(I) scripts/ship-pr.sh missing RESUME_PHASE ship-pr-rrr-phase14 handoff"
grep -Fq 'CALLER_KIND ship_pr_pre_push' "$SHIP_PR_SH" \
  || fail "(I) scripts/ship-pr.sh missing CALLER_KIND ship_pr_pre_push handoff"

grep -Fq 'caller_kind=ship_pr_pre_push' "$CONFLICT_MD" \
  || fail "(I) conflict-resolution.md missing ship_pr_pre_push caller family"

grep -Fq 'rebase-push.sh --continue --no-push --keep-on-conflict' "$CONFLICT_MD" \
  || fail "(I) conflict-resolution.md must retain early_rebase/ship_pr_pre_push Phase 4 --continue --no-push --keep-on-conflict invocation"

ship_pr_exit5_count=$(grep -cE '(^|[^0-9])exit 5([^0-9]|$)' "$SHIP_PR_SH" || true)
[[ "$ship_pr_exit5_count" == "0" ]] \
  || fail "(I) scripts/ship-pr.sh must not emit exit 5 after Phase 1, found $ship_pr_exit5_count"
grep -Fq '**Exit 5**:' "$SKILL_MD" \
  && fail "(I) skills/implement/SKILL.md must route ship_pr_pre_push conflict handoff under Exit 4, not Exit 5"
grep -Fq 'RESUME_PHASE=ship-pr-rrr-phase14' "$SKILL_MD" \
  || fail "(I) SKILL.md Exit 4 must document RESUME_PHASE=ship-pr-rrr-phase14 orchestrator handoff"
grep -Fq 'caller_kind=ship_pr_pre_push' "$SKILL_MD" \
  || fail "(I) SKILL.md must document caller_kind=ship_pr_pre_push conflict-resolution handoff"

# ---------------------------------------------------------------------------
# (J) Exactly two standalone phantom-probe-with-warn.sh invocations in SKILL.md.
# ---------------------------------------------------------------------------
phantom_fence=$(grep -cF '"${CLAUDE_PLUGIN_ROOT}/scripts/phantom-probe-with-warn.sh"' "$SKILL_MD" || true)
[[ "$phantom_fence" == "2" ]] \
  || fail "(J) expected exactly 2 fenced phantom-probe-with-warn.sh invocations, found $phantom_fence"

grep -Fq 'phantom-probe-with-warn.sh" --step 2-post-dispatch' "$SKILL_MD" \
  || fail "(J) missing --step 2-post-dispatch standalone invocation"
grep -Fq 'phantom-probe-with-warn.sh" --step 8-pre-ship' "$SKILL_MD" \
  || fail "(J) missing --step 8-pre-ship standalone invocation"

echo "PASS: test-implement-rebase-macro.sh — all structural invariants hold (A-C, C', E, G-J, I)"
exit 0
