#!/usr/bin/env bash
# Detects SIGPIPE/pipefail anti-patterns in test scripts.
#
# Two dangerous patterns under set -euo pipefail:
#   1. producer | head   — head exits after N lines; SIGPIPE to producer;
#                          producer exits 141; pipefail reports failure.
#   2. bash -c "..." | grep -q   — grep-q exits after first match; SIGPIPE
#                                  to bash subprocess; bash exits 141.
#
# Safe exclusions:
#   - Lines guarded with || true
#   - Comment lines (start with #)
#   - Lines whose leftmost producer is echo or printf (both handle SIGPIPE)
#   - Lines using echo/printf inside a command substitution $(echo ...)
#   - Lines using a here-string (<<<) as the pipeline source (bounded data)
#   - Pipeline continuation lines starting with '|' (source checked elsewhere)
#   - Pattern 1: | head appears inside a single-quoted string
#   - Pattern 2: | grep-q inside a single-quoted bash -c string (not outer pipe)
set -euo pipefail

VIOLATIONS=0
SCRIPTS_CHECKED=0
SELF=$(basename "$0")

for f in scripts/test-*.sh; do
    [ -f "$f" ] || continue
    [ "$(basename "$f")" = "$SELF" ] && continue

    # Only check scripts that activate pipefail at top level.
    if ! grep -m 1 -qE \
        '^[[:space:]]*set[[:space:]]+-[a-zA-Z]*o[[:space:]]+pipefail|^[[:space:]]*set[[:space:]]+-[a-zA-Z]*eo|^[[:space:]]*set[[:space:]]+-[a-zA-Z]*euo' \
        "$f" 2>/dev/null; then
        continue
    fi

    SCRIPTS_CHECKED=$((SCRIPTS_CHECKED + 1))

    lineno=0
    while IFS= read -r line || [[ -n "$line" ]]; do
        lineno=$((lineno + 1))
        flagged=false

        # --- Pattern 1: producer | head (head as early-exit consumer) ---
        if printf '%s\n' "$line" | grep -qE '\|[[:space:]]*head([[:space:]]|$)'; then
            # Safe: comment line
            if printf '%s\n' "$line" | grep -qE '^[[:space:]]*#'; then
                :
            # Safe: guarded with || true
            elif printf '%s\n' "$line" | grep -qE '\|\|[[:space:]]*true'; then
                :
            # Safe: pipeline continuation line (source is on a previous line)
            elif printf '%s\n' "$line" | grep -qE '^[[:space:]]*\|'; then
                :
            # Safe: leftmost producer is echo or printf (SIGPIPE-safe)
            elif printf '%s\n' "$line" | grep -qE '^[[:space:]]*(echo|printf)[[:space:]]'; then
                :
            # Safe: producer inside command substitution is echo or printf
            elif printf '%s\n' "$line" | grep -qE '\$\((echo|printf)[[:space:]]'; then
                :
            # Safe: here-string provides bounded input (<<<)
            elif printf '%s\n' "$line" | grep -q '<<<'; then
                :
            # Safe: | head appears inside a single-quoted string
            elif printf '%s\n' "$line" | grep -qE "'[^']*\|[[:space:]]*head"; then
                :
            else
                flagged=true
            fi
        fi

        # --- Pattern 2: bash -c "..." | grep -q (outer pipe, not inside string) ---
        if ! $flagged && printf '%s\n' "$line" | grep -qE 'bash[[:space:]]+-c[[:space:]]+"'; then
            if printf '%s\n' "$line" | grep -qE '"[[:space:]]*\|[[:space:]]*grep[[:space:]]+-[a-zA-Z]*q'; then
                if ! printf '%s\n' "$line" | grep -qE '\|\|[[:space:]]*true'; then
                    flagged=true
                fi
            fi
        fi

        if $flagged; then
            printf '%s:%d: %s\n' "$f" "$lineno" "$line"
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
