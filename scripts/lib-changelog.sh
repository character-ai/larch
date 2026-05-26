#!/usr/bin/env bash
# Shared CHANGELOG helpers.

changelog_first_version_heading() {
    local path=${1:-CHANGELOG.md}
    [ -f "$path" ] || return 1
    awk '
        /^## \[Unreleased\]/ { next }
        match($0, /^## \[([0-9]+\.[0-9]+\.[0-9]+)\] - /, m) {
            print m[1]
            exit 0
        }
    ' "$path"
}

changelog_duplicate_version_heading_count() {
    local version=$1 path=${2:-CHANGELOG.md}
    [ -n "$version" ] || return 1
    [ -f "$path" ] || return 1
    awk -v version="$version" '
        $0 ~ "^## \\[" version "\\] - " { count++ }
        END { print count + 0 }
    ' "$path"
}

# Extract the body lines that appear under `## [version] - YYYY-MM-DD` (heading
# excluded) in CHANGELOG.md, up to but not including the next `## [` heading
# (or end-of-file). Trims a single trailing blank line if present so callers
# can pass the result straight to write_changelog_entry as a categories file.
#
# Args: version, dest_file, [path=CHANGELOG.md]
# Returns 0 with body written to dest_file when the heading was found and the
# extracted body is non-empty (at least one non-blank line); 1 otherwise. On
# failure dest_file is removed.
changelog_extract_version_body() {
    local version=$1 dest=$2 path=${3:-CHANGELOG.md}
    [ -n "$version" ] || return 1
    [ -n "$dest" ] || return 1
    [ -f "$path" ] || return 1
    [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
    awk -v version="$version" '
        BEGIN { in_section = 0; non_blank = 0; seen_non_blank = 0 }
        $0 ~ "^## \\[" version "\\] - " {
            in_section = 1
            next
        }
        in_section && /^## \[/ {
            in_section = 0
        }
        in_section {
            if ($0 ~ /^[[:space:]]*$/) {
                # Buffer blank lines so leading blanks are dropped and only
                # interior blanks are preserved.
                if (seen_non_blank) pending_blanks++
            } else {
                while (pending_blanks-- > 0) print ""
                pending_blanks = 0
                print
                seen_non_blank = 1
                non_blank = 1
            }
        }
        END { if (!non_blank) exit 1 }
    ' "$path" > "$dest" 2>/dev/null || { rm -f "$dest"; return 1; }
    [ -s "$dest" ]
}

# Insert a new "## [version] - today" entry into CHANGELOG.md and write the
# result to output. The entry body is read from categories_file (typically
# `### Changed\n\n- bullet\n...`); pass /dev/null for an empty entry.
#
# When replaces_version is provided and differs from version, the existing
# `## [replaces_version]` section (if any) is replaced wholesale; otherwise
# the new entry is inserted directly under `## [Unreleased]` (or anchored to
# the "Semantic Versioning" introduction line for changelogs that omit the
# Unreleased section).
#
# Args: version, categories_file, output, [replaces_version=""]
# Returns 0 on success, 3 when no anchor was found, 4 when CHANGELOG.md has
# multiple existing `## [version]` headings (duplicate target). Mirrors the
# contract callers in scripts/implement-finalize.sh and scripts/ship-pr.sh
# rely on.
write_changelog_entry() {
    local version=$1 categories_file=$2 output=$3 replaces_version=${4:-} today tmp rc
    today=$(date +%Y-%m-%d)
    tmp="$output.entry.$$"
    {
        printf '## [%s] - %s\n\n' "$version" "$today"
        cat "$categories_file"
    } > "$tmp"
    awk -v version="$version" -v replaces_version="$replaces_version" -v entry="$tmp" '
        BEGIN {
            while ((getline line < entry) > 0) e[++en] = line
            close(entry)
            has_unreleased = 0
            inserted = 0
            skipping = 0
            in_unreleased = 0
            match_count = 0
            entry_from_version_match = 0
        }
        FNR == NR {
            if (/^## \[Unreleased\]/) has_unreleased = 1
            next
        }
        ($0 ~ "^## \\[" version "\\] - ") || (replaces_version != "" && replaces_version != version && $0 ~ "^## \\[" replaces_version "\\] - ") {
            match_count++
            if (match_count > 1) exit 4
            if (in_unreleased) {
                in_unreleased = 0
            }
            if (!inserted) {
                for (i = 1; i <= en; i++) print e[i]
                inserted = 1
                entry_from_version_match = 1
            }
            skipping = 1
            next
        }
        skipping && /^## \[/ {
            if (entry_from_version_match) print ""
            skipping = 0
        }
        skipping {
            next
        }
        /^## \[Unreleased\]/ {
            print
            in_unreleased = 1
            next
        }
        in_unreleased && /^## \[/ {
            in_unreleased = 0
            if (!inserted) {
                for (i = 1; i <= en; i++) print e[i]
                print ""
                inserted = 1
            }
            print
            next
        }
        in_unreleased {
            print
            next
        }
        !has_unreleased && /and this project adheres to \[Semantic Versioning\]/ {
            print
            if (!inserted) {
                print ""
                for (i = 1; i <= en; i++) print e[i]
                inserted = 1
            }
            next
        }
        !inserted && /^## \[/ {
            for (i = 1; i <= en; i++) print e[i]
            print ""
            inserted = 1
        }
        { print }
        END {
            if (in_unreleased && !inserted) {
                print ""
                for (i = 1; i <= en; i++) print e[i]
                inserted = 1
            }
            if (!inserted) exit 3
        }
    ' CHANGELOG.md CHANGELOG.md > "$output"
    rc=$?
    rm -f "$tmp"
    return "$rc"
}

# shellcheck disable=SC2034
LARCH_LIB_CHANGELOG_LOADED=1
