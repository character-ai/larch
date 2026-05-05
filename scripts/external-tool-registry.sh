# shellcheck shell=bash
# scripts/external-tool-registry.sh - Single canonical source for external
# tool name taxonomy and implementer-coder taxonomy used across larch.
#
# Sourced by:
#   - scripts/agent-model-args.sh
#   - scripts/check-reviewers.sh
#   - skills/implement/scripts/step2-implement.sh
#
# Related (NOT sourced - permissive label-only consumer):
#   - scripts/run-external-agent.sh (uses --tool only as a log/.meta label;
#     DECISION_1 of #1099 keeps that wrapper permissive intentionally)
#
# Non-goals: per-tool model defaults, probe argv templates, launcher paths,
# capture-mode policy, runtime-failure tokens. Those stay with their owners.
#
# Canonical ordering rule: external-tool error strings use codex, cursor,
# gemini order; implementer-coder error strings use claude, codex, cursor,
# gemini order.
#
# Bash 3.2 constraint: indexed arrays only. No associative arrays, namerefs,
# mapfile/readarray, or eval.
#
# Known follow-up drift point: scripts/collect-agent-results.sh derive_tool()
# re-encodes codex|cursor|gemini|unknown - DECISION_2 of #1099 deferred this
# because the `unknown` outcome is observational classification, not dispatch
# validation. See scripts/external-tool-registry.md for tracking.

[[ -n "${LARCH_EXTERNAL_TOOL_REGISTRY_LOADED:-}" ]] && return 0

LARCH_EXTERNAL_TOOLS=(codex cursor gemini)
readonly LARCH_EXTERNAL_TOOLS

LARCH_IMPLEMENTER_CODERS=(claude codex cursor gemini)
readonly LARCH_IMPLEMENTER_CODERS

larch_is_external_tool() {
    local needle="${1-}"
    local t
    for t in "${LARCH_EXTERNAL_TOOLS[@]}"; do
        [[ "$t" == "$needle" ]] && return 0
    done
    return 1
}

larch_is_implementer_coder() {
    local needle="${1-}"
    local t
    for t in "${LARCH_IMPLEMENTER_CODERS[@]}"; do
        [[ "$t" == "$needle" ]] && return 0
    done
    return 1
}

larch_external_tools_braced() {
    local IFS=','
    printf '{%s}' "${LARCH_EXTERNAL_TOOLS[*]}"
}

larch_implementer_coders_braced() {
    local IFS=','
    printf '{%s}' "${LARCH_IMPLEMENTER_CODERS[*]}"
}

LARCH_EXTERNAL_TOOL_REGISTRY_LOADED=1
