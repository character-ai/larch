#!/usr/bin/env bash
# test-anti-improvised-wakeup.sh — Regression harness for the project-wide
# guard against improvised ScheduleWakeup calls outside skill-script direction.
#
# Asserts three contracts:
#
#   (A) The project token appears in the project-wide anchors:
#       AGENTS.md and skills/shared/orchestrator-never.md.
#   (B) The per-skill MANDATORY directive wiring is present in each skill
#       that delegates to the shared file.
#   (C) The legacy /implement-specific token remains present in
#       skills/implement/SKILL.md, preserving its stricter NEVER #9 ratchet.
#
# Invoked via:  bash scripts/test-anti-improvised-wakeup.sh
# Wired into:   make lint (via the test-anti-improvised-wakeup Makefile target).
#
# The checked substrings are fixed contract tokens. When changing the rule's
# wording in any anchor file, update the literals here in the same PR.

set -euo pipefail

LC_ALL=C
export LC_ALL

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

PROJECT_TOKEN='NEVER improvise ScheduleWakeup outside skill-script direction'
IMPLEMENT_LEGACY_TOKEN="NEVER call \`ScheduleWakeup\` anywhere in the \`/implement\` orchestrator"
IMPLEMENT_NEVER12_ARCHIVAL_TOKEN="#2487; the post-/design boundary halt rule and its archival hook scripts were deleted"
MANDATORY_TOKEN='MANDATORY at session start'

PROJECT_ANCHORS=(
  "AGENTS.md"
  "skills/shared/orchestrator-never.md"
)
IMPLEMENT_LEGACY_ANCHOR="skills/implement/SKILL.md"

MANDATORY_ANCHORS=(
  "skills/research/SKILL.md"
)

FAIL_COUNT=0
PASS_COUNT=0

check_token_present() {
  local rel="$1"
  local token="$2"
  local label="$3"
  local abs="$REPO_ROOT/$rel"

  if [[ ! -f "$abs" ]]; then
    echo "FAIL: $rel does not exist" >&2
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return
  fi

  if grep -Fq -- "$token" "$abs"; then
    echo "PASS: $rel contains $label"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "FAIL: $rel is missing $label: $token" >&2
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

echo "--- Project-wide improvised ScheduleWakeup guard ---"
for rel in "${PROJECT_ANCHORS[@]}"; do
  check_token_present "$rel" "$PROJECT_TOKEN" "project token"
done

echo ""
echo "--- Per-skill MANDATORY directive wiring ---"
for rel in "${MANDATORY_ANCHORS[@]}"; do
  check_token_present "$rel" "$MANDATORY_TOKEN" "MANDATORY directive token"
done

echo ""
echo "--- /implement legacy ScheduleWakeup ratchet ---"
check_token_present "$IMPLEMENT_LEGACY_ANCHOR" "$IMPLEMENT_LEGACY_TOKEN" "implement legacy token"

echo ""
echo "--- /implement NEVER #12 archival (post-design boundary retired) ---"
check_token_present "$IMPLEMENT_LEGACY_ANCHOR" "$IMPLEMENT_NEVER12_ARCHIVAL_TOKEN" "implement NEVER #12 archival token"

echo ""
echo "=== SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed ==="

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi

exit 0
