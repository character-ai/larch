#!/usr/bin/env bash
# Detects SIGPIPE/pipefail anti-patterns in test scripts.
#
# Two dangerous patterns under set -euo pipefail:
#   1. producer | head   — head exits after N lines; SIGPIPE to producer;
#                          producer exits 141; pipefail reports failure.
#   2. bash -c "..." | grep -q   — grep-q exits after first match; SIGPIPE
#                                  to bash subprocess; bash exits 141.
#
# Safe exclusions (applied in order, all in native bash regex — no subprocesses):
#   - Comment lines (start with #)
#   - Lines guarded with || true
#   - Pipeline continuation lines starting with '|' (source checked elsewhere)
#   - Lines whose leftmost producer is echo or printf (both handle SIGPIPE)
#   - Lines using echo/printf inside a command substitution $(echo ...)
#   - Lines using a here-string (<<<) as the pipeline source (bounded data)
#   - Pattern 1: | head appears inside a single-quoted string
#   - Pattern 2: | grep-q inside a single-quoted bash -c string (not outer pipe)
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
VIOLATIONS=0
SCRIPTS_CHECKED=0
SELF=$(basename "$0")

# Pre-compile regexes as variables so bash =~ uses ERE without quoting pitfalls.
RE_PIPEFAIL='^[[:space:]]*(set[[:space:]]+-[a-zA-Z]*o[[:space:]]+pipefail|set[[:space:]]+-[a-zA-Z]*eo|set[[:space:]]+-[a-zA-Z]*euo)'
RE_HEAD_CONSUMER='\|[[:space:]]*head([[:space:]]|$)'
RE_OR_TRUE='\|\|[[:space:]]*true'
RE_COMMENT='^[[:space:]]*#'
RE_CONTINUATION='^[[:space:]]*\|'
RE_ECHO_PRINTF_FIRST='^[[:space:]]*(echo|printf)[[:space:]]'
RE_ECHO_PRINTF_SUBSHELL='\$\((echo|printf)[[:space:]]'
RE_HEREDOC='<<<'
RE_HEAD_IN_SQUOTE="'[^']*\|[[:space:]]*head"
RE_BASH_C_DQUOTE='bash[[:space:]]+-c[[:space:]]+"'
RE_DQUOTE_PIPE_GREP='"[[:space:]]*\|[[:space:]]*grep[[:space:]]+-[a-zA-Z]*q'

for f in "$REPO_ROOT"/scripts/test-*.sh; do
    [ -f "$f" ] || continue
    [ "$(basename "$f")" = "$SELF" ] && continue

    # Only check scripts that activate pipefail at top level (grep uses -m 1
    # and reads the file once; no per-line subprocess needed here).
    grep -m 1 -qE "$RE_PIPEFAIL" "$f" 2>/dev/null || continue

    SCRIPTS_CHECKED=$((SCRIPTS_CHECKED + 1))

    lineno=0
    while IFS= read -r line || [[ -n "$line" ]]; do
        lineno=$((lineno + 1))
        flagged=false

        # --- Pattern 1: producer | head (head as early-exit consumer) ---
        if [[ "$line" =~ $RE_HEAD_CONSUMER ]]; then
            if   [[ "$line" =~ $RE_COMMENT ]]; then          : # comment line
            elif [[ "$line" =~ $RE_OR_TRUE ]]; then          : # || true guard
            elif [[ "$line" =~ $RE_CONTINUATION ]]; then     : # continuation
            elif [[ "$line" =~ $RE_ECHO_PRINTF_FIRST ]]; then  : # echo/printf leftmost
            elif [[ "$line" =~ $RE_ECHO_PRINTF_SUBSHELL ]]; then : # echo/printf in $()
            elif [[ "$line" =~ $RE_HEREDOC ]]; then          : # here-string source
            elif [[ "$line" =~ $RE_HEAD_IN_SQUOTE ]]; then   : # inside single-quoted string
            else flagged=true
            fi
        fi

        # --- Pattern 2: bash -c "..." | grep -q (outer pipe, not inside string) ---
        if ! $flagged \
            && [[ "$line" =~ $RE_BASH_C_DQUOTE ]] \
            && [[ "$line" =~ $RE_DQUOTE_PIPE_GREP ]] \
            && ! [[ "$line" =~ $RE_OR_TRUE ]]; then
            flagged=true
        fi

        if $flagged; then
            printf '%s:%d: %s\n' "${f#"$REPO_ROOT"/}" "$lineno" "$line"
            VIOLATIONS=$((VIOLATIONS + 1))
        fi
    done < "$f"
done

if [ "$VIOLATIONS" -gt 0 ]; then
    printf '\nERROR: %d SIGPIPE/pipefail violation(s) found in %d script(s) checked.\n' \
        "$VIOLATIONS" "$SCRIPTS_CHECKED" >&2
    printf 'Fix: use grep -m N instead of grep | head -N, or restructure to avoid early-exit consumers.\n' >&2
    exit 1
fi

printf 'OK: no SIGPIPE/pipefail violations found (%d script(s) checked).\n' "$SCRIPTS_CHECKED"
