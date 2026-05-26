#!/usr/bin/env bash
# commit-changelog.sh — Commit a CHANGELOG.md update as its own commit.
#
# Creates a commit with subject "Update CHANGELOG for X.Y.Z". The subject is
# intentionally distinct from "Bump version to X.Y.Z" so drop-bump-commit.sh
# never treats this commit as a version bump.
#
# Usage:
#   commit-changelog.sh --version X.Y.Z [--replaces-version X.Y.Z]
#
# Output (stdout, KEY=VALUE):
#   COMMITTED=true|false
#   COMMIT_SHA=<sha>   (only when COMMITTED=true)
#   ERROR=<text>       (only on errors and selected no-op diagnostics)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
# shellcheck source=scripts/lib-changelog.sh
source "$SCRIPT_DIR/lib-changelog.sh"
larch_quiet_init

VERSION=""
REPLACES_VERSION=""

insert_version_heading() {
    local version=$1 tmp=$2 today
    today=$(date +%Y-%m-%d)
    awk -v version="$version" -v today="$today" '
        BEGIN {
            inserted = 0
            has_unreleased = 0
            in_unreleased = 0
        }
        FNR == NR {
            if (/^## \[Unreleased\]/) has_unreleased = 1
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
                print ""
                print "## [" version "] - " today
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
                print "## [" version "] - " today
                inserted = 1
            }
            next
        }
        !inserted && /^## \[/ {
            print "## [" version "] - " today
            print ""
            inserted = 1
        }
        { print }
        END {
            if (in_unreleased && !inserted) {
                print ""
                print "## [" version "] - " today
                inserted = 1
            }
            if (!inserted) exit 3
        }
    ' CHANGELOG.md CHANGELOG.md > "$tmp"
}

emit_no_commit() {
    emit_kv COMMITTED false
    [ $# -gt 0 ] && emit_kv ERROR "$1"
}

usage_error() {
    emit_no_commit "$1"
    exit 1
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --version)
            [ "$#" -ge 2 ] || usage_error "--version requires a value"
            VERSION=$2
            shift 2
            ;;
        --replaces-version)
            [ "$#" -ge 2 ] || usage_error "--replaces-version requires a value"
            REPLACES_VERSION=$2
            shift 2
            ;;
        *)
            usage_error "unknown argument: $1"
            ;;
    esac
done

[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || usage_error "invalid --version: $VERSION"
if [ -n "$REPLACES_VERSION" ]; then
    [[ "$REPLACES_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || usage_error "invalid --replaces-version: $REPLACES_VERSION"
fi

if [ ! -f CHANGELOG.md ]; then
    emit_no_commit "CHANGELOG.md not found"
    exit 1
fi

dup_count=$(changelog_duplicate_version_heading_count "$VERSION" CHANGELOG.md)
if [ "$dup_count" -gt 1 ]; then
    emit_no_commit "multiple existing ## [$VERSION] - headings"
    exit 1
fi

status_out=$(git status --porcelain --untracked-files=no 2>/dev/null || true)
if [ -n "$status_out" ]; then
    while IFS= read -r line; do
        [ -n "$line" ] || continue
        path=${line#?? }
        case "$line" in
            R*|C*) path=${path#* -> } ;;
        esac
        if [ "$path" != "CHANGELOG.md" ]; then
            emit_no_commit "tracked file dirty outside CHANGELOG.md: $path"
            exit 1
        fi
    done <<< "$status_out"
fi

if [ -n "$REPLACES_VERSION" ] && [ "$REPLACES_VERSION" != "$VERSION" ]; then
    tmp=$(mktemp "${TMPDIR:-/tmp}/larch-commit-changelog.XXXXXX")
    today=$(date +%Y-%m-%d)
    set +e
    # Two-pass awk: first pass detects whether NEW heading already exists;
    # second pass retitles OLD heading in place, preserving its body, and only
    # removes OLD when a NEW heading already exists on reruns.
    awk -v old="$REPLACES_VERSION" -v new="$VERSION" -v today="$today" '
        BEGIN { replaced = 0; dropping_old = 0; has_new = 0 }
        FNR == NR {
            if ($0 ~ "^## \\[" new "\\] - ") has_new = 1
            next
        }
        $0 ~ "^## \\[" old "\\] - " {
            if (!replaced) {
                if (!has_new) {
                    print "## [" new "] - " today
                } else {
                    dropping_old = 1
                }
                replaced = 1
            }
            next
        }
        dropping_old && /^## \[/ {
            dropping_old = 0
        }
        dropping_old { next }
        { print }
        END {
            if (!replaced) exit 3
        }
    ' CHANGELOG.md CHANGELOG.md > "$tmp"
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
        mv "$tmp" CHANGELOG.md
    elif [ "$rc" -eq 3 ]; then
        insert_version_heading "$VERSION" "$tmp"
        mv "$tmp" CHANGELOG.md
    else
        rm -f "$tmp"
        emit_no_commit "replaces-version not found: $REPLACES_VERSION"
        exit 1
    fi
fi

if git diff --quiet -- CHANGELOG.md && git diff --cached --quiet -- CHANGELOG.md; then
    # No diff: CHANGELOG already correct (idempotent re-run or content already matches).
    # Best-effort: report COMMITTED=false without error.
    emit_kv COMMITTED false
    exit 0
fi

if ! "$SCRIPT_DIR/git-commit.sh" -m "Update CHANGELOG for $VERSION" --only CHANGELOG.md >/dev/null; then
    emit_no_commit "git commit failed"
    exit 1
fi

commit_sha=$(git rev-parse HEAD)
emit_kv COMMITTED true
emit_kv COMMIT_SHA "$commit_sha"
