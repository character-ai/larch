# shellcheck shell=bash
# Sourced title-eligibility grammar helpers. Bash 3.2-compatible; do not execute.

# Archival / dedup jq fragment (list-issues.sh): select when title should NOT be skipped.
# shellcheck disable=SC2016
export LARCH_TITLE_ARCHIVAL_PREFIX_JQ_FILTER='select((.title // "" | ascii_downcase | sub("^[[:space:]]+"; "")) as $t | (($t | startswith("research ")) or ($t | startswith("[research] ")) or ($t | startswith("investigate ")) or ($t | startswith("[investigate] ")) or ($t | test("^\\[.*report\\] "))) | not)'

# Report-only bash ERE (/design Step 0b archival-report reject).
export LARCH_TITLE_ARCHIVAL_REPORT_REGEX_BASH='^\[.*[Rr][Ee][Pp][Oo][Rr][Tt]\] '

# Lifecycle bracket tokens that refuse /design.
export LARCH_TITLE_LIFECYCLE_REJECT_REGEX='^\[(IMPLEMENTING|DONE|DESIGNING|DESIGNED)\]'

# Brainstorm leading word (non-letter or EOS after token).
export LARCH_TITLE_BRAINSTORM_REGEX='^[Bb][Rr][Aa][Ii][Nn][Ss][Tt][Oo][Rr][Mm]([^A-Za-z]|$)'

larch_title_trim_leading_ws() {
    local title="$1"
    title="${title#"${title%%[![:space:]]*}"}"
    printf '%s' "$title"
}

title_has_archival_report_prefix() {
    local title="$1"
    [ -n "$title" ] || return 1
    title=$(larch_title_trim_leading_ws "$title")
    [[ "$title" =~ $LARCH_TITLE_ARCHIVAL_REPORT_REGEX_BASH ]]
}

title_has_lifecycle_reject_prefix() {
    local title="$1"
    local _saved_shopt
    [ -n "$title" ] || return 1
    title=$(larch_title_trim_leading_ws "$title")
    _saved_shopt="$(shopt -p nocasematch 2>/dev/null || true)"
    shopt -s nocasematch
    if [[ "$title" =~ $LARCH_TITLE_LIFECYCLE_REJECT_REGEX ]]; then
        eval "$_saved_shopt"
        printf '[%s]' "${BASH_REMATCH[1]}"
        return 0
    fi
    eval "$_saved_shopt"
    return 1
}

title_starts_with_brainstorm() {
    local title="$1"
    [ -n "$title" ] || return 1
    title=$(larch_title_trim_leading_ws "$title")
    [[ "$title" =~ $LARCH_TITLE_BRAINSTORM_REGEX ]]
}
