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

LARCH_LIB_CHANGELOG_LOADED=1
