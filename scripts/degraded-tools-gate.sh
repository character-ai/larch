#!/usr/bin/env bash
# degraded-tools-gate.sh — issue #3207 degraded-external-tools gate detector.
#
# Given the four Step-0 presence keys (from session-setup.sh --check-reviewers),
# decide whether the session is running in a DEGRADED external-tool posture
# (Codex and/or Cursor unavailable) and compose a human-readable explanation of
# what is down, why, and what the backup waterfall will do about it.
#
# This script is a PURE DETECTOR. It never prompts and never blocks. The skill
# orchestrator consumes the KV output and, when DEGRADED=true, presents the
# explanation and asks the operator (via AskUserQuestion) whether to continue
# with the degraded waterfall or abort — see skills/shared/external-reviewers.md
# "Degraded-tools gate (Step 0)".
#
# A tool is AVAILABLE only when its binary is found AND its runtime probe
# passed (binary-found=true AND present=true), matching the codex_available /
# cursor_available rule in skills/shared/external-reviewers.md.
#
# Output (stdout KV; explanation block only emitted when DEGRADED=true):
#   DEGRADED=true|false
#   CODEX_STATE=ok|binary-missing|probe-failed
#   CURSOR_STATE=ok|binary-missing|probe-failed
#   DEGRADED_EXPLANATION_BEGIN
#   <multi-line explanation lines>
#   DEGRADED_EXPLANATION_END
#
# Exit code is always 0 on valid argv; exit 2 on argv error (caller bug).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh" || { echo "degraded-tools-gate.sh: failed to source lib-quiet.sh" >&2; exit 1; }
larch_quiet_init

CODEX_BINARY_FOUND="${CODEX_BINARY_FOUND:-unknown}"
CODEX_PRESENT="${CODEX_PRESENT:-}"
CURSOR_BINARY_FOUND="${CURSOR_BINARY_FOUND:-unknown}"
CURSOR_PRESENT="${CURSOR_PRESENT:-}"
SKILL_LABEL="this"
CODEX_BINARY_FOUND_SET=false
CODEX_PRESENT_SET=false
CURSOR_BINARY_FOUND_SET=false
CURSOR_PRESENT_SET=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --codex-binary-found)  CODEX_BINARY_FOUND="${2-}"; CODEX_BINARY_FOUND_SET=true; shift 2 ;;
        --codex-present)       CODEX_PRESENT="${2-}"; CODEX_PRESENT_SET=true; shift 2 ;;
        --cursor-binary-found) CURSOR_BINARY_FOUND="${2-}"; CURSOR_BINARY_FOUND_SET=true; shift 2 ;;
        --cursor-present)      CURSOR_PRESENT="${2-}"; CURSOR_PRESENT_SET=true; shift 2 ;;
        --skill)               SKILL_LABEL="${2-}"; shift 2 ;;
        *) larch_err "degraded-tools-gate.sh: unknown argument: $1"; exit 2 ;;
    esac
done

if [[ "$CODEX_BINARY_FOUND_SET" == "false" && "$CODEX_BINARY_FOUND" != "unknown" ]]; then
    larch_err "degraded-tools-gate.sh: WARNING: --codex-binary-found omitted; using CODEX_BINARY_FOUND from environment"
fi
if [[ "$CODEX_PRESENT_SET" == "false" && -n "${CODEX_PRESENT:-}" ]]; then
    larch_err "degraded-tools-gate.sh: WARNING: --codex-present omitted; using CODEX_PRESENT from environment"
fi
if [[ "$CURSOR_BINARY_FOUND_SET" == "false" && "$CURSOR_BINARY_FOUND" != "unknown" ]]; then
    larch_err "degraded-tools-gate.sh: WARNING: --cursor-binary-found omitted; using CURSOR_BINARY_FOUND from environment"
fi
if [[ "$CURSOR_PRESENT_SET" == "false" && -n "${CURSOR_PRESENT:-}" ]]; then
    larch_err "degraded-tools-gate.sh: WARNING: --cursor-present omitted; using CURSOR_PRESENT from environment"
fi

# Normalize. Presence is always known (every skill parses it): true|false.
# Binary-found is OPTIONAL — skills that do not parse it leave it `unknown`,
# which yields a generic `unavailable` state instead of a precise reason.
norm_bool() { case "${1:-}" in true) printf 'true' ;; *) printf 'false' ;; esac; }
norm_tristate() { case "${1:-}" in true) printf 'true' ;; false) printf 'false' ;; *) printf 'unknown' ;; esac; }
CODEX_BINARY_FOUND="$(norm_tristate "$CODEX_BINARY_FOUND")"
CODEX_PRESENT="$(norm_bool "$CODEX_PRESENT")"
CURSOR_BINARY_FOUND="$(norm_tristate "$CURSOR_BINARY_FOUND")"
CURSOR_PRESENT="$(norm_bool "$CURSOR_PRESENT")"

# Classify each tool: ok | binary-missing | probe-failed | unavailable.
# Binary-gate wins (available requires binary-found AND present, per
# skills/shared/external-reviewers.md). `unavailable` is the generic
# down-state used when binary-found was not supplied.
classify_state() {
    local binary_found=$1 present=$2
    if [ "$binary_found" = "false" ]; then
        printf 'binary-missing'
    elif [ "$present" = "true" ]; then
        printf 'ok'
    elif [ "$binary_found" = "true" ]; then
        printf 'probe-failed'
    else
        printf 'unavailable'
    fi
}
CODEX_STATE="$(classify_state "$CODEX_BINARY_FOUND" "$CODEX_PRESENT")"
CURSOR_STATE="$(classify_state "$CURSOR_BINARY_FOUND" "$CURSOR_PRESENT")"

DEGRADED=false
if [ "$CODEX_STATE" != "ok" ] || [ "$CURSOR_STATE" != "ok" ]; then
    DEGRADED=true
fi

emit_kv DEGRADED "$DEGRADED"
emit_kv CODEX_STATE "$CODEX_STATE"
emit_kv CURSOR_STATE "$CURSOR_STATE"

[ "$DEGRADED" = "true" ] || exit 0

# Human-readable per-tool status line.
state_phrase() {
    case "$1" in
        ok)             printf 'available' ;;
        binary-missing) printf 'UNAVAILABLE — CLI binary not found on PATH' ;;
        probe-failed)   printf 'UNAVAILABLE — runtime health probe failed (binary present but the auth/quota check did not pass)' ;;
        unavailable)    printf 'UNAVAILABLE — session health probe did not pass' ;;
        *)              printf 'unknown' ;;
    esac
}

emit DEGRADED_EXPLANATION_BEGIN
emit "⚠ Degraded external-tool availability for this /${SKILL_LABEL} run:"
emit ""
emit "  • Codex:  $(state_phrase "$CODEX_STATE")"
emit "  • Cursor: $(state_phrase "$CURSOR_STATE")"
emit ""
if [[ "$SKILL_LABEL" == "design" ]]; then
    emit "What this means for /design: plan-review, decomposition, assessor, and plan-voter"
    emit "panels use availability-gated single launch (--no-fallback). Absent tools are"
    emit "omitted from the manifest; failed slots are dropped without cross-tool or Claude"
    emit "padding. When both externals are absent, plan-review uses one generic Claude"
    emit "reviewer covering all archetype lenses. Expect fewer reviewers and possible"
    emit "zero-findings / degraded tally paths — not per-slot Codex→Cursor→Claude waterfall."
    emit ""
    emit "Continue in this degraded mode, or abort and retry once the tool is healthy?"
else
    emit "What this means: multi-tool roles (reviewer/voter panels, decomposition, the"
    emit "implementer, and CI/fix coders) run through the per-slot backup waterfall —"
    emit "Codex roles fall through to Cursor then Claude, and Cursor roles fall through"
    emit "to Codex then Claude — so the run will still COMPLETE. The cost is reduced"
    emit "model-family diversity: an unavailable tool's slots are covered by the other"
    emit "external tool (or Claude), and a few tool-specific roles are dropped rather"
    emit "than substituted (e.g. /design Codex dialectic buckets and Codex sketch"
    emit "personalities when Codex is down)."
    emit ""
    emit "Continue in this degraded mode (backup waterfall), or abort and retry once"
    emit "the tool is healthy?"
fi
emit DEGRADED_EXPLANATION_END

exit 0
