#!/usr/bin/env bash
# check-review-changes.sh — Check if the code review step modified the working tree.
#
# Detects review-induced changes via four sources:
#   - staged modifications (git diff --cached)
#   - unstaged modifications (git diff)
#   - new untracked files (current untracked set minus a pre-/review baseline)
#   - HEAD movement (current HEAD differs from a pre-/review HEAD baseline)
#
# The HEAD-movement source covers the case where review-and-fix.sh commits
# each round's fixes (per-round commits in skills/review-and-fix/scripts/
# review-and-fix.sh). Without this dimension, a clean working tree after
# per-round commits would report FILES_CHANGED=false even though the
# repository moved forward — silently skipping Step 6's lint pass.
#
# The untracked dimension requires a pre-/review baseline file (sorted list of
# untracked paths captured before /review ran). Without a readable baseline,
# the untracked dimension is ignored (UNTRACKED_BASELINE=missing) — this
# degrades gracefully rather than treating every pre-existing untracked file
# as review-created (which would reintroduce the false-positive bug from #651).
#
# A readable file (including zero-byte) means UNTRACKED_BASELINE=present and
# the delta is comm -23 (current sorted) (baseline). A zero-byte baseline
# legitimately represents "no untracked files at snapshot time," so all
# current untracked are considered review-created.
#
# Stdout contract — THREE keys ALWAYS emitted on every invocation in stable
# order. Consumers must parse with key-based grep/awk, never eval/source:
#   FILES_CHANGED=true|false
#   UNTRACKED_BASELINE=present|missing
#   GIT_PROBE_FAILED=true|false
#
# Usage:
#   check-review-changes.sh [--baseline <path>] [--head-baseline <path>] [--strict]
#
# Exit codes:
#   0 — always (including bad CLI input — see Parse-error policy below).
#
# Parse-error policy: on unknown flag or --baseline-without-path, emit an
# informational ERROR=... line on stderr and degrade to the missing-baseline
# path on stdout. The always-3-keys, exit-0 contract is preserved so callers
# (notably skills/implement/SKILL.md Step 6) parse stdout uniformly.
#
# Health-probe mode: each git probe (git diff staged, git diff unstaged,
# git ls-files untracked) captures its exit status explicitly. Any non-zero
# probe sets GIT_PROBE_FAILED=true; otherwise GIT_PROBE_FAILED=false.
# Default behavior (no --strict): a failed probe degrades to empty output
# for that source — observationally same as "no changes detected" on
# FILES_CHANGED, but GIT_PROBE_FAILED=true now exposes the unknown-state
# signal so callers can decide independently.
#
# --strict: when set AND any probe failed (GIT_PROBE_FAILED=true), force
# FILES_CHANGED=true (fail-closed: treat unknown as may-have-changed).
# Without --strict, FILES_CHANGED reflects only the observed signal,
# preserving the historical graceful-degradation behavior. See
# check-review-changes.md for the full contract.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

BASELINE=""
HEAD_BASELINE=""
STRICT="false"
PARSE_ERROR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --baseline)
            if [[ $# -lt 2 ]]; then
                PARSE_ERROR="--baseline requires a path argument"
                break
            fi
            BASELINE="$2"
            shift 2
            ;;
        --head-baseline)
            if [[ $# -lt 2 ]]; then
                PARSE_ERROR="--head-baseline requires a path argument"
                break
            fi
            HEAD_BASELINE="$2"
            shift 2
            ;;
        --strict)
            STRICT="true"
            shift
            ;;
        *)
            PARSE_ERROR="Unknown argument: $1"
            break
            ;;
    esac
done

# Parse errors short-circuit before any git probe runs. The always-emit-3-keys
# stdout contract is preserved with the conservative degraded values
# (FILES_CHANGED=false, UNTRACKED_BASELINE=missing, GIT_PROBE_FAILED=false).
# The ERROR= line on stderr is informational only — callers parse stdout, not
# stderr or exit code. Parse errors are NOT probe failures (no probe ran), and
# parse errors must NOT interact with --strict to silently force
# FILES_CHANGED=true on a CLI with a typo (e.g. "--strict --bogus").
if [[ -n "$PARSE_ERROR" ]]; then
    larch_err "ERROR=$PARSE_ERROR"
    emit_kv FILES_CHANGED false
    emit_kv UNTRACKED_BASELINE missing
    emit_kv GIT_PROBE_FAILED false
    exit 0
fi

GIT_PROBE_FAILED="false"

if UNSTAGED=$(git diff --name-only 2>/dev/null); then
    :
else
    GIT_PROBE_FAILED="true"
    UNSTAGED=""
fi

if STAGED=$(git diff --name-only --cached 2>/dev/null); then
    :
else
    GIT_PROBE_FAILED="true"
    STAGED=""
fi

UNTRACKED_BASELINE="missing"
UNTRACKED_DELTA=""

if [[ -n "$BASELINE" ]] && [[ -r "$BASELINE" ]]; then
    UNTRACKED_BASELINE="present"
    if CURRENT=$(git ls-files --others --exclude-standard 2>/dev/null | LC_ALL=C sort); then
        :
    else
        GIT_PROBE_FAILED="true"
        CURRENT=""
    fi
    UNTRACKED_DELTA=$(comm -23 <(printf '%s\n' "$CURRENT") <(LC_ALL=C sort -- "$BASELINE") | sed '/^$/d' || echo "")
fi

HEAD_MOVED="false"
if [[ -n "$HEAD_BASELINE" ]] && [[ -r "$HEAD_BASELINE" ]]; then
    baseline_head=$(tr -d '[:space:]' < "$HEAD_BASELINE" 2>/dev/null || true)
    if current_head=$(git rev-parse HEAD 2>/dev/null); then
        if [[ -n "$baseline_head" && "$baseline_head" != "$current_head" ]]; then
            HEAD_MOVED="true"
        fi
    else
        GIT_PROBE_FAILED="true"
    fi
fi

FILES_CHANGED="false"
if [[ -n "$UNSTAGED" ]] || [[ -n "$STAGED" ]] || [[ -n "$UNTRACKED_DELTA" ]] || [[ "$HEAD_MOVED" == "true" ]]; then
    FILES_CHANGED="true"
fi

# --strict fail-closed: a failed probe means the working-tree state is
# unknown. Force FILES_CHANGED=true so Step 6 enters the changes-found
# branch rather than silently skipping the post-/review checks pass.
if [[ "$STRICT" == "true" ]] && [[ "$GIT_PROBE_FAILED" == "true" ]]; then
    FILES_CHANGED="true"
fi

emit_kv FILES_CHANGED "$FILES_CHANGED"
emit_kv UNTRACKED_BASELINE "$UNTRACKED_BASELINE"
emit_kv GIT_PROBE_FAILED "$GIT_PROBE_FAILED"
