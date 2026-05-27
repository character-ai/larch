#!/usr/bin/env bash
# Render /design plan-review prompts; vendor flag is accepted for CLI compatibility but both vendors produce the same full_role + TSV output.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
LARCH_QUIET_DISABLE=1
export LARCH_QUIET_DISABLE
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init

ARCHETYPE=""
VENDOR=""
PLAN_FILE=""
DESIGN_TMPDIR_ARG=""

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'EOF'
Usage: render-plan-review-prompt.sh --archetype <arch|edge|innovation|pragmatic|requirements> --vendor <codex|cursor> --plan-file <path> --design-tmpdir <path>
EOF
}

take_value() {
    local flag="$1"
    local value="${2:-}"
    if [[ -z "$value" || "$value" == --* ]]; then
        larch_err "render-plan-review-prompt.sh: $flag requires a non-flag value"
        exit 2
    fi
    printf '%s' "$value"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --archetype) ARCHETYPE="$(take_value --archetype "${2:-}")"; shift 2 ;;
        --vendor) VENDOR="$(take_value --vendor "${2:-}")"; shift 2 ;;
        --plan-file) PLAN_FILE="$(take_value --plan-file "${2:-}")"; shift 2 ;;
        --design-tmpdir) DESIGN_TMPDIR_ARG="$(take_value --design-tmpdir "${2:-}")"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) larch_err "render-plan-review-prompt.sh: unknown argument: $1"; usage; exit 2 ;;
    esac
done

case "$ARCHETYPE" in
    arch)
        full_role="You are an Architecture/Standards reviewer. Emphasize maintainability, engineering standards, separation of concerns, and reuse of existing patterns."
        ;;
    edge)
        full_role="You are an Edge-case/Failure-mode reviewer. Focus on boundary conditions, error handling, failure recovery, race conditions, and silent data corruption."
        ;;
    innovation)
        full_role="You are an Innovation/Exploration reviewer. Question assumptions, suggest creative alternatives, and flag plans that ignore unconventional but stronger solutions."
        ;;
    pragmatic)
        full_role="You are a Pragmatism/Safety reviewer. Minimize scope, avoid unnecessary complexity, and ensure existing features are not broken."
        ;;
    requirements)
        full_role="You are a Requirements/Completeness reviewer. Verify that every stated goal, acceptance criterion, and constraint from the feature description is addressed in the plan — flag gaps where the plan is silent, drifts from the stated requirements, or fails to mention required testing or validation for new acceptance criteria."
        ;;
    "")
        larch_err "render-plan-review-prompt.sh: --archetype is required"
        exit 2
        ;;
    *)
        larch_err "render-plan-review-prompt.sh: invalid --archetype '$ARCHETYPE'"
        exit 2
        ;;
esac

case "$VENDOR" in
    codex|cursor) ;;
    "")
        larch_err "render-plan-review-prompt.sh: --vendor is required"
        exit 2
        ;;
    *)
        larch_err "render-plan-review-prompt.sh: invalid --vendor '$VENDOR'"
        exit 2
        ;;
esac

if [[ -z "$PLAN_FILE" ]]; then
    larch_err "render-plan-review-prompt.sh: --plan-file is required"
    exit 2
fi
if [[ ! -r "$PLAN_FILE" ]]; then
    larch_err "render-plan-review-prompt.sh: --plan-file path is missing or unreadable: $PLAN_FILE"
    exit 2
fi
DESIGN_TMPDIR="${DESIGN_TMPDIR_ARG:-${DESIGN_TMPDIR:-}}"
if [[ -z "$DESIGN_TMPDIR" || ! -d "$DESIGN_TMPDIR" ]]; then
    larch_err "render-plan-review-prompt.sh: --design-tmpdir or DESIGN_TMPDIR must name a directory"
    exit 2
fi

classification=$("$SCRIPT_DIR/../../../scripts/read-design-classification.sh" "$DESIGN_TMPDIR/run-params.json")
case "$classification" in
    SIMPLE)
        tier_emphasis="**Tier emphasis: SIMPLE.** This is a minimum-change review lane. Bias your findings toward flagging **scope creep and unnecessary complexity**. Do NOT request additions unless they are materially required for correctness, security, or safety hardening. Accept YES only for findings that keep or restore that minimum-change contract. Prefer EXONERATE on nits, style concerns, and forward-looking issues. When in doubt, EXONERATE."
        ;;
    HARD|*)
        tier_emphasis="**Tier emphasis: HARD.** Bias your findings toward **thoroughness**. Flag missed considerations, edge cases, and architectural concerns. Request additions when warranted. Engage seriously with all findings."
        ;;
esac

cat <<EOF
${full_role}
${tier_emphasis}
Your response MUST begin with either the TSV header line (when you have findings) or the literal single-line JSON sentinel {"no_issues_found": true} (when you have none). Do not write any preamble, no "I'll review...", no "Examining the plan...", no "Looking at file X...". The first non-whitespace character of your response must be either \`s\` (start of \`schema_version\`) or \`{\` (start of the sentinel).
Review the implementation plan file at ${PLAN_FILE}. Explore the codebase following file paths named in the plan, then inspect adjacent files only when needed to validate contracts and integration points.
The plan describes the codebase AFTER this PR lands. Files cited in \`### NEW:\` / \`### UPDATED:\` / \`### REWRITTEN:\` subsections have NOT yet been changed when you read them — the plan PROPOSES those changes. Do NOT flag a current-state behavior as a finding when the plan already addresses it; the plan's mention of current state is motivation for the change, not a claim about post-change state. Findings should target deficiencies of the PROPOSED change: missing steps, wrong target file, incomplete contracts, conflicts with other proposed changes, or actual code paths the plan fails to address.
Walk five focus areas: code-quality / risk-integration / correctness / architecture / security.
Return numbered findings with focus-area tag, repo-relative file:line when applicable, concern, and suggested revision.
Prefix out-of-scope but worth-tracking items with [OUT_OF_SCOPE]; include affected repo-relative file paths and line ranges so downstream issue filing can detect same-file conflicts.
When you have findings, include a TSV structured-record block with this exact header (literal tab characters between fields; no markdown fences around the TSV):
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
For each finding, add one record:
1	<scope>	<severity>	<focus_area>	<location>	<what>	<scenario_or_breakage>	<suggested_fix>
Use scope in_scope or out_of_scope; severity important, nit, or latent; and replace literal tabs or newlines inside field values with spaces.
Acceptable TSV block example (one finding):

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/foo.sh:42-45	Lock acquired before parameter validation	Race between two concurrent runs	Move lock acquisition after validation passes

If no issues were identified, your entire response content MUST be exactly the single-line JSON literal {"no_issues_found": true} — no surrounding prose, no TSV records, no out-of-scope items, no trailing whitespace beyond a single newline. For Cursor's --output-format json invocation this becomes .result = "{\"no_issues_found\": true}" in Cursor's JSON envelope; the larch tooling extracts .result and JSON-parses it to detect the sentinel. For Codex (which writes plain stdout), the literal is captured verbatim. Do NOT modify files.
EOF
