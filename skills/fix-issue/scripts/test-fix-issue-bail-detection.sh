#!/usr/bin/env bash
# test-fix-issue-bail-detection.sh — Regression harness for /fix-issue Step 5a
# bail-detection prose (Phase 4 of umbrella #348; renumbered to Step 5a from
# Step 6a by the fold-find-and-lock refactor closes #496).
#
# Asserts that skills/fix-issue/SKILL.md Step 5a block contains the load-bearing
# literals the runtime behavior depends on. The skill is prose; this harness is
# a CI guard against accidental removal of pinned strings, not a runtime
# conformance test. Runtime enforcement is the LLM-level orchestration of
# Step 5a per the prose contract.
#
# Thirteen assertions against the extracted Step 5a block:
#   (a1) Invocation forwards "--issue $ISSUE_NUMBER".
#   (a2) Invocation forwards "--no-admin-fallback" (branch-protection bypass
#        safety flag; issue #559).
#   (a3) Invocation forwards "--coder=$coder" (pass-through implementer flag).
#   (a4) Invocation forwards "[--auto if auto_mode]" (autonomous-mode flag).
#   (a5) Invocation contains "[--hard if hard_mode]" — /fix-issue forwards --hard
#        when the operator sets it; otherwise no HARD/SIMPLE control flag is sent
#        and /implement uses its normal routing.
#   (a6) Invocation contains "[--inline if inline_mode and hard_mode]" — encodes
#        that --inline is forwarded only when --hard is also set (--inline only matters
#        when /design runs, which requires HARD mode).
#   (b)  Literal token "IMPLEMENT_BAIL_REASON=adopted-issue-closed" present.
#   (c)  Warning prefix "/implement bailed: issue #" present.
#   (d)  Specific directive "Do NOT call `issue-lifecycle.sh close`" present
#        (skip-Step-6 contract guard). The full phrase — not a bare
#        "Do NOT call" substring — is required because the awk extraction
#        window also includes section 5b, which contains the unrelated
#        sentence "Do NOT call `/implement`"; a bare match would false-pass.
#   (e)  Literal "Skip to Step 8" present (cleanup redirect guard).
#   (f)  Delegation mandate "Invoke `/implement` via the Skill tool" present
#        (anti-pattern #5 guard against inline implementation at Step 5a).
#   (g)  Skill name "larch:implement" present — confirms the correct Skill name
#        appears in the Step 5a block (anti-pattern #9 guard against accidentally
#        using larch:fix-issue or any other name as the skill: field).
#   (h)  Skill name "larch:fix-issue" absent — guards against the Step 5a block
#        ever containing the recursive self-invocation skill name that caused
#        issue #2136 to be permanently stuck in [IN PROGRESS].
#
# Block extraction boundary: "### 5a " (start) through the Step 6 anchor.
#
# Wired into `make lint` via the `test-fix-issue-bail-detection` target.
# Referenced in agent-lint.toml's exclude list (Makefile-only harness pattern).
#
# Run manually:
#   bash skills/fix-issue/scripts/test-fix-issue-bail-detection.sh
#
# Exits 0 on success, 1 on the first failed assertion.

# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
SKILL_MD="$REPO_ROOT/skills/fix-issue/SKILL.md"

if [[ ! -f "$SKILL_MD" ]]; then
    echo "ERROR: SKILL.md not found: $SKILL_MD" >&2
    exit 1
fi

# Extract the Step 5a block: from "### 5a " up to (but not including) the
# next Step 6 anchor. awk range using two regexes.
STEP5A_BLOCK=$(awk '
    /^### 5a / { in_block=1 }
    /^<!-- step:6 / { in_block=0 }
    in_block { print }
' "$SKILL_MD")

if [[ -z "$STEP5A_BLOCK" ]]; then
    echo "FAIL: Step 5a block extraction produced empty output." >&2
    echo "  Boundary regexes: '^### 5a ' (start) and '^<!-- step:6 ' (end)." >&2
    exit 1
fi

PASS_COUNT=0

# Assertion helper — literal-substring presence check.
# Usage: assert_contains <label> <literal>
assert_contains() {
    local label="$1" literal="$2"
    if grep -qF -- "$literal" <<<"$STEP5A_BLOCK"; then
        PASS_COUNT=$((PASS_COUNT + 1))
        echo "  PASS: $label"
    else
        echo "  FAIL: $label" >&2
        echo "    missing literal: $literal" >&2
        exit 1
    fi
}

# Assertion helper — literal-substring absence check.
# Usage: assert_not_contains <label> <literal>
assert_not_contains() {
    local label="$1" literal="$2"
    if ! grep -qF -- "$literal" <<<"$STEP5A_BLOCK"; then
        PASS_COUNT=$((PASS_COUNT + 1))
        echo "  PASS: $label"
    else
        echo "  FAIL: $label" >&2
        echo "    unexpected literal found: $literal" >&2
        exit 1
    fi
}

echo "Running test-fix-issue-bail-detection against $SKILL_MD"

# (a1) --issue $ISSUE_NUMBER must appear in the /implement invocation.
assert_contains "a1: invocation forwards --issue \$ISSUE_NUMBER" '--issue $ISSUE_NUMBER'

# (a2) --no-admin-fallback forwarding — branch-protection bypass safety flag (issue #559).
# Without this guard, a future refactor could silently strip the forward, leaving
# /fix-issue --no-admin-fallback callers exposed to the silent --admin override.
assert_contains "a2: invocation forwards --no-admin-fallback" '--no-admin-fallback'

# (a3) --coder forwarding — pass-through implementer-selection flag.
# Without this guard, /fix-issue --coder=<value> callers would silently fall
# back to /implement's default coder.
assert_contains "a3: invocation forwards --coder=\$coder" '--coder=$coder'

# (a4) --auto forwarding — pass-through autonomous-mode flag.
assert_contains "a4: invocation forwards [--auto if auto_mode]" '[--auto if auto_mode]'

# (a5) [--hard if hard_mode] — when the operator passes --hard, /fix-issue forwards it;
# otherwise no workflow forcing flag is sent.
assert_contains "a5: invocation contains [--hard if hard_mode]" '[--hard if hard_mode]'

# (a6) [--inline if inline_mode and hard_mode] — encodes that --inline is only
# forwarded when --hard is also set (--inline only matters when /design runs,
# which requires HARD mode).
assert_contains "a6: invocation forwards [--inline if inline_mode and hard_mode]" '[--inline if inline_mode and hard_mode]'

# (b) Bail-token literal present.
assert_contains "b: IMPLEMENT_BAIL_REASON=adopted-issue-closed literal" 'IMPLEMENT_BAIL_REASON=adopted-issue-closed'

# (c) User-visible warning prefix present.
assert_contains "c: warning prefix '/implement bailed: issue #'" '/implement bailed: issue #'

# (d) Skip-Step-6 directive present — guard against silent re-route back to Step 6.
# The specific phrase "Do NOT call `issue-lifecycle.sh close`" is required; a
# bare "Do NOT call" substring would false-pass on section 5b's unrelated
# "Do NOT call `/implement`" line (the awk window includes 5b up to the Step 6 anchor).
assert_contains "d: 'Do NOT call \`issue-lifecycle.sh close\`' directive (Step-6-skip guard)" 'Do NOT call `issue-lifecycle.sh close`'

# (e) Cleanup redirect present.
assert_contains "e: 'Skip to Step 8' cleanup redirect" 'Skip to Step 8'

# (f) Delegation mandate present — guards anti-pattern #5 (NEVER implement inline
# at Step 5a using Edit/Write/Bash file-modification tools instead of delegating
# to /implement via the Skill tool). Without this literal the orchestrator has no
# prose anchor stating that the Skill tool is the required dispatch mechanism.
assert_contains "f: delegation mandate 'Invoke \`/implement\` via the Skill tool'" 'Invoke `/implement` via the Skill tool'

# (g) Correct skill name "larch:implement" present — guards anti-pattern #9
# (NEVER use larch:fix-issue or any other name as the skill: field at Step 5a).
# The prose anchor "larch:implement as the skill: field" ensures the canonical
# name appears in the block so the LLM has an unambiguous reference.
assert_contains "g: correct skill name 'larch:implement' present in Step 5a block" 'larch:implement'

# (h) Wrong skill name "larch:fix-issue" absent from Step 5a block — guards
# against the recursive self-invocation failure (issue #2136) where the
# orchestrator used skill: "larch:fix-issue" instead of "larch:implement".
# The explanatory NEVER #9 prose lives in the Anti-patterns section, outside
# the awk extraction window, so this check is not confused by that prose.
assert_not_contains "h: wrong skill name 'larch:fix-issue' absent from Step 5a block" 'larch:fix-issue'

echo
echo "All $PASS_COUNT assertions passed."
