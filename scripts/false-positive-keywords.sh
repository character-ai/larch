# shellcheck shell=bash
# Sourced false-positive close-comment keyword matcher. Bash 3.2-compatible;
# do not execute directly.

false_positive_grep_ere_ci() {
    local pattern="$1"
    local text="$2"
    local rc

    printf '%s\n' "$text" | LC_ALL=C grep -Eiq "$pattern"
    rc=$?
    case "$rc" in
        0) return 0 ;;
        1) return 1 ;;
        *)
            echo "false-positive-keywords: grep failed for pattern: $pattern" >&2
            return 2
            ;;
    esac
}

# matches_false_positive_keywords <text>
# Exit 0 for match, 1 for no match, >=2 for helper failure.
matches_false_positive_keywords() {
    local text="$1"
    local pattern rc

    # Negated duplicate / false-positive phrases override positive matching.
    # "not a bug" and "not an issue" are deliberate positive close reasons.
    for pattern in \
        '(^|[^a-z])not[[:space:]]+((a|an)[[:space:]]+)?duplicate([^a-z]|$)' \
        '(^|[^a-z])not[[:space:]]+((a|an)[[:space:]]+)?false[- ]positive([^a-z]|$)'
    do
        false_positive_grep_ere_ci "$pattern" "$text"
        rc=$?
        if [ "$rc" -eq 0 ]; then
            return 1
        fi
        if [ "$rc" -ge 2 ]; then
            return "$rc"
        fi
    done

    for pattern in \
        '(^|[^a-z])won[^[:space:]]*t[[:space:]]+fix([^a-z]|$)' \
        '(^|[^a-z])wontfix([^a-z]|$)' \
        '(^|[^a-z])superseded([[:space:]]+by[[:space:]]+#[0-9]+)?([^a-z]|$)' \
        '(^|[^a-z])not[[:space:]]+an[[:space:]]+issue([^a-z]|$)' \
        '(^|[^a-z])not[[:space:]]+a[[:space:]]+bug([^a-z]|$)' \
        '(^|[^a-z])duplicate[[:space:]]+of[[:space:]]+#[0-9]+([^a-z]|$)' \
        '(^|[^a-z])false[- ]positive([^a-z]|$)'
    do
        false_positive_grep_ere_ci "$pattern" "$text"
        rc=$?
        if [ "$rc" -eq 0 ]; then
            return 0
        fi
        if [ "$rc" -ge 2 ]; then
            return "$rc"
        fi
    done

    return 1
}
