#!/bin/bash
# Structural regression test for /research skill under the simplified
# fixed-shape topology.
#
# Asserts:
#  - The 4-reference symmetric topology survives edits:
#    skills/research/references/research-phase.md, validation-phase.md,
#    citation-validation-phase.md, and critique-loop-phase.md all exist.
#  - Each reference is named on a 'MANDATORY: READ ENTIRE FILE' line in
#    skills/research/SKILL.md, and the SAME line carries reciprocal
#    'Do NOT load <each-other-reference>' guards naming the OTHER three
#    references (line-scoped, presence-not-order).
#  - Each references/*.md opens with the Consumer / Contract / When-to-load
#    triplet in the first 20 lines.
#  - The four named angle prompts (RESEARCH_PROMPT_ARCH / _EDGE / _EXT / _SEC)
#    appear in research-phase.md.
#  - Reviewer XML wrapper tags appear in validation-phase.md.
#  - The fail-closed unknown-flag guard exists in SKILL.md and the recovery
#    hint enumerates each removed-flag CATEGORY (scale / plan / interactive /
#    adjudicate / token-budget / keep-sidecar / verbosity).
#  - SKILL.md surfaces only the --no-issue flag.
#
# Exit 0 on pass, exit 1 on any assertion failure.
# shellcheck disable=SC2016

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SKILL_MD="$REPO_ROOT/skills/research/SKILL.md"
REFS_DIR="$REPO_ROOT/skills/research/references"
RESEARCH_MD="$REFS_DIR/research-phase.md"
VALIDATION_MD="$REFS_DIR/validation-phase.md"
CITATION_MD="$REFS_DIR/citation-validation-phase.md"
CRITIQUE_LOOP_MD="$REFS_DIR/critique-loop-phase.md"

PASS=0
FAIL=0

fail() {
  echo "FAIL: $1" >&2
  FAIL=$((FAIL + 1))
}

contains() {
  local file="$1" literal="$2" label="$3"
  if grep -Fq -- "$literal" "$file"; then
    PASS=$((PASS + 1))
  else
    fail "$label"
  fi
}

line_for() {
  local file="$1" literal="$2"
  grep -nF -m 1 -- "$literal" "$file" | cut -d: -f1
}

# ---------- Check 1: SKILL.md + 4 reference files exist ----------

[[ -f "$SKILL_MD" ]]         || fail "SKILL.md missing: $SKILL_MD"
[[ -f "$RESEARCH_MD" ]]      || fail "references/research-phase.md missing: $RESEARCH_MD"
[[ -f "$VALIDATION_MD" ]]    || fail "references/validation-phase.md missing: $VALIDATION_MD"
[[ -f "$CITATION_MD" ]]      || fail "references/citation-validation-phase.md missing: $CITATION_MD"
[[ -f "$CRITIQUE_LOOP_MD" ]] || fail "references/critique-loop-phase.md missing: $CRITIQUE_LOOP_MD"

if (( FAIL > 0 )); then
  echo "test-research-structure.sh — $PASS passed, $FAIL failed" >&2
  exit 1
fi
PASS=$((PASS + 5))

# ---------- Check 2: removed reference must NOT exist ----------

removed="adjudication-phase.md"
if [[ -f "$REFS_DIR/$removed" ]]; then
  fail "references/$removed must be removed under the simplified shape"
else
  PASS=$((PASS + 1))
fi

# ---------- Check 3: 4-reference reciprocal MANDATORY topology ----------

check_mandatory_topology() {
  local target="$1"
  shift
  local -a others=("$@")
  local line
  line=$(grep -F 'MANDATORY: READ ENTIRE FILE' "$SKILL_MD" | grep -F "$target" || true)
  if [[ -z "$line" ]]; then
    fail "[topology] no MANDATORY: READ ENTIRE FILE line in SKILL.md names '$target'"
    return
  fi
  PASS=$((PASS + 1))
  for other in "${others[@]}"; do
    if echo "$line" | grep -F "Do NOT load" | grep -Fq "$other"; then
      PASS=$((PASS + 1))
    else
      fail "[topology] MANDATORY line for '$target' does not carry 'Do NOT load $other' on the same line"
    fi
  done
}

check_mandatory_topology research-phase.md            validation-phase.md citation-validation-phase.md critique-loop-phase.md
check_mandatory_topology validation-phase.md          research-phase.md   citation-validation-phase.md critique-loop-phase.md
check_mandatory_topology citation-validation-phase.md research-phase.md   validation-phase.md          critique-loop-phase.md
check_mandatory_topology critique-loop-phase.md       research-phase.md   validation-phase.md          citation-validation-phase.md

# ---------- Check 4: Consumer / Contract / When-to-load triplet ----------

for ref in "$RESEARCH_MD" "$VALIDATION_MD" "$CITATION_MD" "$CRITIQUE_LOOP_MD"; do
  for pattern in '^\*\*Consumer\*\*:' '^\*\*Contract\*\*:' '^\*\*When to load\*\*:'; do
    if head -n 20 "$ref" | grep -Eq "$pattern"; then
      PASS=$((PASS + 1))
    else
      fail "[header triplet] $(basename "$ref") must open with anchored header matching '$pattern' in the first 20 lines"
    fi
  done
done

# ---------- Check 5: angle prompt identifiers in research-phase.md ----------

for angle in ARCH EDGE EXT SEC; do
  if grep -Fq "RESEARCH_PROMPT_${angle}" "$RESEARCH_MD"; then
    PASS=$((PASS + 1))
  else
    fail "[angle prompts] research-phase.md lacks RESEARCH_PROMPT_${angle} identifier"
  fi
done

# ---------- Check 6: reviewer XML wrappers in validation-phase.md ----------

for tag in '<reviewer_research_question>' '<reviewer_research_findings>'; do
  if grep -Fq "$tag" "$VALIDATION_MD"; then
    PASS=$((PASS + 1))
  else
    fail "[reviewer wrappers] validation-phase.md lacks XML wrapper tag '$tag'"
  fi
done

# ---------- Check 7: fail-closed unknown-flag guard in SKILL.md ----------

if grep -Fq 'Fail-closed unknown-flag guard' "$SKILL_MD"; then
  PASS=$((PASS + 1))
else
  fail "[fail-closed] SKILL.md must contain 'Fail-closed unknown-flag guard' heading/marker"
fi

if grep -Fq 'unsupported flag' "$SKILL_MD"; then
  PASS=$((PASS + 1))
else
  fail "[fail-closed] SKILL.md must contain 'unsupported flag' abort message"
fi

# Recovery-hint MUST enumerate each removed-flag CATEGORY (NOT literal --foo
# tokens — those would themselves trip the unknown-flag check this guard
# enforces). The categories are scale / plan / interactive / adjudicate /
# token-budget / keep-sidecar / verbosity.
for category in scale plan interactive adjudicate token-budget keep-sidecar verbosity; do
  if grep -Fq "$category" "$SKILL_MD"; then
    PASS=$((PASS + 1))
  else
    fail "[fail-closed recovery hint] SKILL.md must mention removed-flag category '$category' in the unknown-flag-guard recovery hint"
  fi
done

# ---------- Check 8: only --no-issue is surfaced ----------

# SKILL.md must declare --no-issue.
if grep -F -- '--no-issue' "$SKILL_MD" >/dev/null; then
  PASS=$((PASS + 1))
else
  fail "[flag surface] SKILL.md must surface --no-issue"
fi

# ---------- Check 9: Stage 4 (#3119) Family-B fence absence ----------

python3 "$REPO_ROOT/python/cli.py" lint p3119-fence-absence "$SKILL_MD" "SKILL.md" || fail "(3119) SKILL.md still has removed Family-B fence tokens"
python3 "$REPO_ROOT/python/cli.py" lint p3119-fence-absence "$RESEARCH_MD" "research-phase.md" || fail "(3119) research-phase.md still has removed Family-B fence tokens"
python3 "$REPO_ROOT/python/cli.py" lint p3119-fence-absence "$VALIDATION_MD" "validation-phase.md" || fail "(3119) validation-phase.md still has removed Family-B fence tokens"
PASS=$((PASS + 3))

# ---------- Check 10: Codex auth-wired launcher pins ----------

for stem in codex-research-arch-output.txt codex-research-edge-output.txt codex-research-ext-output.txt codex-research-sec-output.txt; do
  if grep -Fq "$stem" "$RESEARCH_MD"; then
    PASS=$((PASS + 1))
  else
    fail "[codex launcher] research-phase.md must pin expected output stem '$stem'"
  fi
done

for pair in \
  "$RESEARCH_MD:codex-research-arch-output.txt" \
  "$VALIDATION_MD:codex-validation-output.txt" \
  "$REPO_ROOT/skills/shared/voting-protocol.md:codex-vote-output.txt" \
; do
  file="${pair%%:*}"
  stem="${pair#*:}"
  if grep -Fq "\${CLAUDE_PLUGIN_ROOT:?}/python/cli.py agent launch-codex-exec" "$file"; then
    PASS=$((PASS + 1))
  else
    fail "[codex launcher] $(basename "$file") must use \${CLAUDE_PLUGIN_ROOT:?}/python/cli.py agent launch-codex-exec"
  fi
  if grep -Fq "$stem" "$file"; then
    PASS=$((PASS + 1))
  else
    fail "[codex launcher] $(basename "$file") must pin expected output stem '$stem'"
  fi
done

# ---------- Check 11: Codex research telemetry wording ----------

if grep -Fq 'Non-fallback Codex lanes receive best-effort usage records' "$RESEARCH_MD" \
  && grep -Fq "\${OUTPUT}.token-record" "$RESEARCH_MD"; then
  PASS=$((PASS + 1))
else
  fail "[codex telemetry] research-phase.md must pin best-effort Codex usage records"
fi

if grep -Fqi 'Codex telemetry is unmeasurable' "$RESEARCH_MD"; then
  fail "[codex telemetry] research-phase.md must not claim Codex telemetry is unmeasurable"
else
  PASS=$((PASS + 1))
fi

# ---------- Check 12: Research/validation sidecar ingestion pins ----------

for file in "$RESEARCH_MD" "$VALIDATION_MD"; do
  base=$(basename "$file")
  contains "$file" 'token append-record' "[$base sidecar] missing token append-record"
  contains "$file" 'token record-vendor-sidecar' "[$base sidecar] missing token record-vendor-sidecar"
  contains "$file" 'env -u LARCH_TOKEN_LEDGER' "[$base sidecar] missing env -u LARCH_TOKEN_LEDGER"
  contains "$file" '-u LARCH_TOKEN_SESSION_ID' "[$base sidecar] missing -u LARCH_TOKEN_SESSION_ID"
  contains "$file" "RESEARCH_TMPDIR=\"\$RESEARCH_TMPDIR\"" "[$base sidecar] missing RESEARCH_TMPDIR binding"
done

collect_line=$(line_for "$VALIDATION_MD" "python3 \"\${CLAUDE_PLUGIN_ROOT}/python/cli.py\" agent collect-results --timeout 1860 --substantive-validation --validation-mode")
parse_line=$(line_for "$VALIDATION_MD" "1. Parse the structured output for each reviewer's \`STATUS\` and \`REVIEWER_FILE\`.")
ingest_line=$(line_for "$VALIDATION_MD" '2. **Codex/Cursor validation sidecar ingestion after collection settles**')
status_line=$(line_for "$VALIDATION_MD" '3. **Runtime fallback replacement**')
if [[ -n "$collect_line" && -n "$parse_line" && -n "$ingest_line" && -n "$status_line" \
      && "$collect_line" -lt "$parse_line" && "$parse_line" -lt "$ingest_line" && "$ingest_line" -lt "$status_line" ]]; then
  PASS=$((PASS + 1))
else
  fail "[validation sidecar] ingestion must follow collect/result parsing and precede status decisions"
fi

contains "$VALIDATION_MD" 'REVIEWER_FILE' '[validation sidecar] candidate expansion must include REVIEWER_FILE'
contains "$VALIDATION_MD" '-retry.txt' '[validation sidecar] candidate expansion must include -retry.txt'
contains "$VALIDATION_MD" 'No non-substantive retry artifacts are created' '[validation sidecar] must document no non-substantive retry artifacts'
contains "$VALIDATION_MD" 'Deduplicate candidate paths before ingestion.' '[validation sidecar] candidate expansion must dedupe paths'

# ---------- Check 13: Python CLI call-site pins ----------

contains "$RESEARCH_MD" 'python/cli.py" research run-planner' '[python cli] research-phase.md must pin research run-planner in §1.1.b'
contains "$RESEARCH_MD" 'python/cli.py research run-planner' '[python cli] research-phase.md must pin research run-planner in §1.1.c edit loop'
contains "$CITATION_MD" 'python/cli.py" research validate-citations' '[python cli] citation-validation-phase.md must pin research validate-citations'
contains "$SKILL_MD" 'python/cli.py" research validate-citations' '[python cli] SKILL.md must pin research validate-citations at Step 2.5'
contains "$RESEARCH_MD" 'python/cli.py" research banner' '[python cli] research-phase.md must pin research banner at Step 1.5'
contains "$SKILL_MD" 'python/cli.py research render-findings-batch' '[python cli] SKILL.md must pin research render-findings-batch at Step 3'

# ---------- Check 14: NOT_SUBSTANTIVE terminal behavior ----------

contains "$RESEARCH_MD" 'STATUS=NOT_SUBSTANTIVE' '[not-substantive] research-phase.md must pin terminal NOT_SUBSTANTIVE status'
contains "$RESEARCH_MD" 'do not launch a Claude replacement' '[not-substantive] research-phase.md must block Claude replacement'
contains "$RESEARCH_MD" 'do not pass the narrative file to synthesis' '[not-substantive] research-phase.md must exclude narrative output from synthesis'
contains "$RESEARCH_MD" 'No non-substantive retry artifacts are created' '[not-substantive] research-phase.md must pin absent retry artifacts'

# ---------- Check 15: synthesis gating and STATUS-gated input exclusion ----------

contains "$RESEARCH_MD" "Do NOT emit a \`## Research Synthesis\` header" '[synthesis gating] research-phase.md must pin orchestrator-owned synthesis header'
contains "$RESEARCH_MD" '[lane dropped: collector NOT_SUBSTANTIVE]' '[synthesis gating] research-phase.md must pin NOT_SUBSTANTIVE dropped-lane marker'

# ---------- Check 16: read-only hook activation sentinel ----------

contains "$SKILL_MD" 'command: "${CLAUDE_PLUGIN_ROOT}/scripts/deny-edit-write.sh research"' '[activation] SKILL.md frontmatter must pass research token'
contains "$SKILL_MD" 'RESEARCH_DENY_ACTIVE_SENTINEL="$RESEARCH_DENY_ACTIVE_DIR/research-$PPID"' '[activation] SKILL.md must create research-$PPID sentinel'
contains "$SKILL_MD" '**⚠ /research: failed to activate read-only Write/Edit hook. Aborting.**' '[activation] sentinel write failure must abort loudly'
contains "$SKILL_MD" 'A leaked hook registration without a fresh `research-*` sentinel allows with empty stdout.' '[activation] read-only contract must document inactive fail-open behavior'
contains "$SKILL_MD" 'any other active path outcome denies.' '[activation] read-only contract must keep active fail-closed path behavior'
contains "$SKILL_MD" 'Remove `"$RESEARCH_DENY_ACTIVE_SENTINEL"` before stopping.' '[activation] filing VERIFIED=false branch must remove sentinel'
contains "$SKILL_MD" 'Remove `"$RESEARCH_DENY_ACTIVE_SENTINEL"` before stopping. Research-result-filing semantics require all items to succeed' '[activation] filing ISSUES_FAILED branch must remove sentinel'
contains "$SKILL_MD" 'remove `"$RESEARCH_DENY_ACTIVE_SENTINEL"`, print `**⚠ 3.5: auto-issue: /issue failed (REASON=<token>). Research results were not archived to GitHub. Continuing.**`, and proceed to Step 4.' '[activation] auto-issue failure must remove sentinel'
contains "$SKILL_MD" 'rm -f "$RESEARCH_DENY_ACTIVE_SENTINEL"' '[activation] Step 4 cleanup must remove sentinel'
contains "$RESEARCH_MD" 'rm -f "$RESEARCH_DENY_ACTIVE_SENTINEL"' '[activation] research-phase abort branches must remove sentinel'

gate_line=$(line_for "$SKILL_MD" '**Degraded-tools gate (#3207).**')
activation_line=$(line_for "$SKILL_MD" '### 0a.5: Activate read-only Write/Edit hook')
write_line=$(line_for "$SKILL_MD" 'Write `$RESEARCH_TMPDIR/lane-status.txt`')
if [[ -n "$gate_line" && -n "$activation_line" && -n "$write_line" \
      && "$gate_line" -lt "$activation_line" && "$activation_line" -lt "$write_line" ]]; then
  PASS=$((PASS + 1))
else
  fail '[activation] sentinel creation must follow degraded-tools gate and precede first Write'
fi

# ---------- Summary ----------

if (( FAIL > 0 )); then
  echo "test-research-structure.sh — $PASS passed, $FAIL failed" >&2
  exit 1
fi

echo "PASS: test-research-structure.sh — $PASS structural invariants hold"
exit 0
