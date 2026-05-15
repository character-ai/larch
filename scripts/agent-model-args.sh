#!/usr/bin/env bash
# agent-model-args.sh — Output model (and optionally effort) arguments for an
# external agent tool.
#
# Returns the appropriate --model / -m flag for the given tool based on
# environment variables. Cursor defaults to composer-2 when no model is
# configured. Codex defaults to gpt-5.5 when unconfigured. Gemini defaults
# to gemini-2.5-pro when unconfigured (matching the reviewer-side default).
#
# When --with-effort is passed, also emits tool-specific reasoning-effort flags.
# The --with-effort flag is an opt-in gate: real reviewer launch call sites
# pass it; lightweight probe callers (e.g., check-reviewers.sh health probes,
# run-negotiation-round.sh) do NOT pass it, preserving the original probe
# semantics regardless of env var settings.
#
# Environment variables:
#   LARCH_CURSOR_MODEL  — Model name for Cursor (e.g., gpt-5.4-medium)
#   LARCH_CODEX_MODEL   — Model name for Codex (e.g., o3)
#   LARCH_CODEX_EFFORT  — Codex reasoning effort: minimal|low|medium|high
#                         (only consulted when --with-effort is passed)
#   LARCH_GEMINI_MODEL  — Model name for Gemini (e.g., gemini-2.5-pro, gemini-2.5-flash)
#
# Plugin userConfig fallbacks (lower priority):
#   CLAUDE_PLUGIN_OPTION_CURSOR_MODEL  → LARCH_CURSOR_MODEL
#   CLAUDE_PLUGIN_OPTION_CODEX_MODEL   → LARCH_CODEX_MODEL
#   CLAUDE_PLUGIN_OPTION_CODEX_EFFORT  → LARCH_CODEX_EFFORT  (default "high")
#   CLAUDE_PLUGIN_OPTION_GEMINI_MODEL  → LARCH_GEMINI_MODEL
#
# Cursor effort: Cursor CLI has no dedicated reasoning-effort flag. No effort
# tokens are emitted for Cursor. Substantive high-risk Cursor review launches
# use cursor-wrap-prompt.sh for max-mode, and launch-cursor-review.sh owns its
# additional high-risk prompt suffix.
#
# Cursor max-mode: Cursor supports ~/.cursor/cli-config.json for max-mode, but
# that path is user-managed. Larch enforces max-mode by wrapping Cursor prompts
# via scripts/cursor-wrap-prompt.sh, which prepends " /max-mode on. Prompt: ".
# Every substantive Cursor call site MUST use that wrapper — see its sibling
# scripts/cursor-wrap-prompt.md for the callers registry. The only exception
# is scripts/check-reviewers.sh's health probe.
#
# Gemini effort: Gemini CLI has no separate reasoning-effort flag. Reasoning
# depth is selected through the model value itself; --with-effort is a no-op.
#
# Usage:
#   agent-model-args.sh --tool cursor|codex|gemini [--with-effort] [--default-model MODEL]
#
# Output (stdout):
#   One argv token per physical line. Model flag tokens are optionally followed
#   by effort flag tokens when --with-effort is passed (Codex only).
#   Examples:
#     --model
#     gpt-5.4-medium
#         (cursor with LARCH_CURSOR_MODEL=gpt-5.4-medium)
#     --model
#     composer-2
#         (cursor default, --with-effort is a no-op for Cursor)
#     -m
#     o3
#     -c
#     model_reasoning_effort="high"
#         (codex with LARCH_CODEX_MODEL=o3 and --with-effort and default effort)
#     -m
#     gpt-5.5
#     -c
#     model_reasoning_effort="high"
#         (codex with default model and --with-effort)
#     -m
#     gpt-5.5
#         (codex with default model, no --with-effort)
#     --model
#     gemini-2.5-pro
#         (gemini default, --with-effort is a no-op for Gemini)
#
# Exit codes:
#   0 — success
#   1 — invalid arguments, invalid effort value, or rejected model value

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

# shellcheck source=scripts/external-tool-registry.sh
source "$SCRIPT_DIR/external-tool-registry.sh" || { larch_err "agent-model-args.sh: failed to source external-tool-registry.sh"; exit 1; }
[[ "${LARCH_EXTERNAL_TOOL_REGISTRY_LOADED:-}" == "1" ]] || { larch_err "agent-model-args.sh: external-tool-registry.sh sourced but sentinel missing"; exit 1; }

TOOL=""
WITH_EFFORT="false"
DEFAULT_MODEL=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) TOOL="${2:?--tool requires a value}"; shift 2 ;;
        --with-effort) WITH_EFFORT="true"; shift ;;
        --default-model) DEFAULT_MODEL="${2:?--default-model requires a value}"; shift 2 ;;
        *) larch_err "agent-model-args.sh: unknown argument: $1"; exit 1 ;;
    esac
done

if [[ -z "$TOOL" ]]; then
    larch_err "agent-model-args.sh: --tool is required"
    exit 1
fi

if ! larch_is_external_tool "$TOOL"; then
    larch_err "agent-model-args.sh: --tool must be 'cursor', 'codex', or 'gemini' (got: $TOOL)"
    exit 1
fi

reject_bad_arg() {
    local value="$1"
    local context="$2"
    if [[ "$value" == *[[:cntrl:]]* ]]; then
        larch_err "agent-model-args.sh: $context must not contain POSIX [[:cntrl:]] characters"
        exit 1
    fi
}

reject_blank_model() {
    local value="$1"
    local context="$2"
    reject_bad_arg "$value" "$context"
    case "$value" in
        *[![:space:]]*) ;;
        *)
            larch_err "agent-model-args.sh: $context must not be blank or whitespace-only"
            exit 1
            ;;
    esac
}

emit_arg() {
    local value="$1"
    reject_bad_arg "$value" "emitted argv token"
    [[ -n "$value" ]] || return 0
    emit "$value"
}

resolve_model() {
    local env_name="$1"
    local plugin_name="$2"
    local default_value="$3"
    local value=""

    if [[ -n "${!env_name+x}" ]]; then
        value="${!env_name}"
        reject_blank_model "$value" "$env_name"
    elif [[ -n "${!plugin_name+x}" ]]; then
        value="${!plugin_name}"
        reject_blank_model "$value" "$plugin_name"
    else
        value="$default_value"
        reject_blank_model "$value" "default model"
    fi
    printf '%s' "$value"
}

case "$TOOL" in
    cursor)
        MODEL=$(resolve_model LARCH_CURSOR_MODEL CLAUDE_PLUGIN_OPTION_CURSOR_MODEL composer-2)
        emit_arg "--model"
        emit_arg "$MODEL"
        # Cursor has no effort flag; --with-effort is intentionally a no-op here.
        ;;
    codex)
        MODEL=$(resolve_model LARCH_CODEX_MODEL CLAUDE_PLUGIN_OPTION_CODEX_MODEL "${DEFAULT_MODEL:-gpt-5.5}")
        emit_arg "-m"
        emit_arg "$MODEL"
        if [[ "$WITH_EFFORT" == "true" ]]; then
            EFFORT="${LARCH_CODEX_EFFORT:-${CLAUDE_PLUGIN_OPTION_CODEX_EFFORT:-high}}"
            case "$EFFORT" in
                minimal|low|medium|high) ;;
                *)
                    larch_err "agent-model-args.sh: WARN invalid codex effort '$EFFORT' (must be minimal|low|medium|high); falling back to 'high'"
                    EFFORT="high"
                    ;;
            esac
            emit_arg "-c"
            emit_arg "model_reasoning_effort=\"$EFFORT\""
        fi
        ;;
    gemini)
        MODEL=$(resolve_model LARCH_GEMINI_MODEL CLAUDE_PLUGIN_OPTION_GEMINI_MODEL "${DEFAULT_MODEL:-gemini-2.5-pro}")
        emit_arg "--model"
        emit_arg "$MODEL"
        # Gemini has no effort flag; --with-effort is intentionally a no-op here.
        ;;
    *)
        # Defensive: larch_is_external_tool gated entry above, so the registry
        # was extended without adding the matching arm here. Fail loudly with
        # exit 1 instead of silently returning empty model args (which would
        # leave callers like check-reviewers.sh launching probes with no
        # --model). Symmetric to the *) defensive arms in
        # scripts/check-reviewers.sh's switch helpers.
        larch_err "agent-model-args.sh: internal error: unsupported reviewer tool: $TOOL"
        exit 1
        ;;
esac
