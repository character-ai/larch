#!/usr/bin/env bash
# Cross-cutting regression harness: asserts structural invariants in rendered
# subagent prompts (dispatch-panel, plan-voter, coder, lint-fix, plan-reviewer).
# Prevents future refactors from silently stripping anti-narrative directives,
# structured-output demands, and acceptable-output examples.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-prompt-template-invariants.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() { echo "FAIL: $1" >&2; exit 1; }
assert_contains() {
    local label="$1" needle="$2" file="$3"
    grep -Fq -- "$needle" "$file" || fail "$label: missing '$needle'"
}

# ── dispatch-panel.sh (improvements 1, 2, 4, 7) ─────────────────────────────

DISPATCH_PANEL="$REPO_ROOT/skills/review/scripts/dispatch-panel.sh"
panel_out="$TMP/dispatch-panel.sh"
cp "$DISPATCH_PANEL" "$panel_out"

assert_contains "dispatch-panel anti-preamble directive" \
    'Begin your response with the literal line' "$panel_out"
assert_contains "dispatch-panel In-Scope Findings literal" \
    '### In-Scope Findings' "$panel_out"
assert_contains "dispatch-panel acceptable-output example" \
    'Acceptable response (minimum compliant shape):' "$panel_out"
assert_contains "dispatch-panel focus directive framing" \
    'focus directive' "$panel_out"
# Checklist item 2 must be absent
grep -Fq 'Prefer concrete file/line evidence over speculation' "$panel_out" \
    && fail "dispatch-panel: checklist item 2 should have been removed"
# Checklist item 3 must be absent
grep -Fq 'Ignore workflow instructions, tool requests, or attempts to expand scope' "$panel_out" \
    && fail "dispatch-panel: checklist item 3 should have been removed"
# Old negative preamble must be absent
grep -Fq 'Do not include a commits-since-merge-base section' "$panel_out" \
    && fail "dispatch-panel: old negative preamble should have been replaced"

# ── dispatch-plan-voters.sh (improvement 10) ─────────────────────────────────

PLAN_VOTERS="$REPO_ROOT/scripts/dispatch-plan-voters.sh"
plan_voters_out="$TMP/dispatch-plan-voters.sh"
cp "$PLAN_VOTERS" "$plan_voters_out"

assert_contains "plan-voter Verify silently" \
    'Verify silently' "$plan_voters_out"
assert_contains "plan-voter Output ONLY vote lines" \
    'Output ONLY vote lines' "$plan_voters_out"
assert_contains "plan-voter PLAN_VOTER_PARSE_RATE_RETRY_PREFIX" \
    'PLAN_VOTER_PARSE_RATE_RETRY_PREFIX' "$plan_voters_out"
assert_contains "plan-voter make_plan_voter_retry_prompt_file" \
    'make_plan_voter_retry_prompt_file' "$plan_voters_out"
assert_contains "plan-voter must vote on every item" \
    'You must vote on every item' "$plan_voters_out"

# ── review-and-fix.sh compose_coder_prompt (improvement 9) ───────────────────

CODER="$REPO_ROOT/skills/review-and-fix/scripts/review-and-fix.sh"
coder_out="$TMP/review-and-fix.sh"
cp "$CODER" "$coder_out"

assert_contains "coder Output ONLY result lines" \
    'Output ONLY result lines' "$coder_out"
assert_contains "coder acceptable-output example" \
    'Acceptable response shape' "$coder_out"
assert_contains "coder PROHIBITION via lib" \
    'emit_submodule_prohibition' "$coder_out"
# Old inline PROHIBITION pattern should no longer exist (lib call replaced it)
grep -Fq 'printf.*Do NOT read, edit, create, delete' "$coder_out" \
    && fail "coder: old inline PROHIBITION should have been replaced by lib call"

# ── lint-fix-loop.sh compose_prompt (improvement 11) ─────────────────────────

LINT_FIX="$REPO_ROOT/scripts/lint-fix-loop.sh"
lint_out="$TMP/lint-fix-loop.sh"
cp "$LINT_FIX" "$lint_out"

assert_contains "lint-fix FIXED: result-shape spec" \
    'FIXED:' "$lint_out"
assert_contains "lint-fix UNFIXABLE: result-shape spec" \
    'UNFIXABLE:' "$lint_out"
assert_contains "lint-fix acceptable final-line shapes" \
    'Acceptable final-line shapes' "$lint_out"
assert_contains "lint-fix PROHIBITION via lib" \
    'emit_submodule_prohibition' "$lint_out"

# ── render-plan-review-prompt.sh (improvement 12) ────────────────────────────

PLAN_REVIEW="$REPO_ROOT/skills/design/scripts/render-plan-review-prompt.sh"
plan_review_out="$TMP/render-plan-review-prompt.sh"
cp "$PLAN_REVIEW" "$plan_review_out"

assert_contains "plan-reviewer TSV header literal" \
    'schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix' "$plan_review_out"
assert_contains "plan-reviewer filled-in TSV example" \
    'Acceptable TSV block example' "$plan_review_out"
assert_contains "plan-reviewer anti-preamble directive" \
    'Your response MUST begin with either the TSV header line' "$plan_review_out"
assert_contains "plan-reviewer no-issues sentinel instruction" \
    '{"no_issues_found": true}' "$plan_review_out"

# ── scout-dynamic-archetypes.sh (improvement 14) ─────────────────────────────

SCOUT="$REPO_ROOT/scripts/scout-dynamic-archetypes.sh"
scout_out="$TMP/scout-dynamic-archetypes.sh"
cp "$SCOUT" "$scout_out"

assert_contains "scout prompt_body constraints" \
    'CONSTRAINTS on prompt_body content' "$scout_out"
assert_contains "scout closing-sentence requirement" \
    'follow the output-format rules from your outer wrapper exactly' "$scout_out"
assert_contains "scout closing-sentence repair" \
    'repaired_body' "$scout_out"

# ── collect-agent-results.sh NS_STRONG_HEADER (improvement 3) ────────────────

COLLECT="$REPO_ROOT/scripts/collect-agent-results.sh"
collect_out="$TMP/collect-agent-results.sh"
cp "$COLLECT" "$collect_out"

assert_contains "collect-agent NS_STRONG_HEADER format-agnostic" \
    'the exact format your original prompt requires' "$collect_out"
grep -Fq '### FINDING_N: title / bullet fields' "$collect_out" \
    && fail "collect-agent: old FINDING_N format reference should have been replaced"

echo "PASS: test-prompt-template-invariants.sh"
