#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# Restore original stdout so progress and the installed version line reach the operator.
[ "${LARCH_QUIET_PID:-}" = "$$" ] && exec 1>&3

# Top-level repo directories shipped to consumers via the plugin install:
# every top-level tracked directory EXCEPT larch-logs/ (committed run logs,
# ~317 MB, never read from the install at runtime) and mermaid-lint/ (dev-only
# Mermaid lint toolchain — excluded so the installed plugin has no package.json
# and the installer runs no npm install). Passed to
# `claude plugin marketplace add --sparse` (git sparse-checkout, cone mode);
# cone mode always keeps top-level files, so root markdown imports ship anyway.
# MAINTENANCE: if a new top-level directory is added to the repo and must ship,
# add it here; larch-logs/ and mermaid-lint/ must NOT be added.
LARCH_SPARSE_DIRS=".claude .claude-plugin .gemini .github agents docs hooks scripts skills tests"
MARKETPLACE_CLONE="$HOME/.claude/plugins/marketplaces/larch-local"

recover() {
    larch_err ""
    larch_err "Recovery: run these commands manually to reinstall:"
    larch_err "  claude plugin marketplace remove larch-local"
    larch_err "  rm -rf '$MARKETPLACE_CLONE'"
    larch_err "  claude plugin marketplace add character-ai/larch --sparse $LARCH_SPARSE_DIRS"
    larch_err "  claude plugin install larch@larch-local"
}
trap recover ERR

warn_prune_failure() {
    local version="$1"
    larch_err "Warning: failed to prune cached larch version '${version}'."
}

warn_install_stamp_failure() {
    local version="$1"
    larch_err "Warning: failed to write install stamp for cached larch version '${version}'."
}

is_safe_version() {
    [[ "$1" =~ ^[0-9]+(\.[0-9]+)*$ ]]
}

normalize_sparse_dirs() {
    tr ' ' '\n' <<< "$LARCH_SPARSE_DIRS" | sed '/^$/d' | sort
}

marketplace_sparse_cone_matches() {
    local configured expected

    [ -d "$MARKETPLACE_CLONE/.git" ] || return 1
    [ ! -d "$MARKETPLACE_CLONE/larch-logs" ] || return 1

    configured=$(git -C "$MARKETPLACE_CLONE" sparse-checkout list 2>/dev/null | sed '/^$/d' | sort || true)
    expected=$(normalize_sparse_dirs)
    [ -n "$configured" ] || return 1
    [ "$configured" = "$expected" ]
}

warn_marketplace_remove_failure() {
    larch_err "Warning: failed to remove larch-local marketplace before sparse add."
    larch_err "Attempting automatic cleanup of the marketplace clone before sparse add."
}

remove_larch_marketplace() {
    if ! claude plugin marketplace remove larch-local 2>&1; then
        warn_marketplace_remove_failure
        return 1
    fi
}

add_sparse_larch_marketplace() {
    # shellcheck disable=SC2086  # intentional word-splitting into --sparse args
    claude plugin marketplace add character-ai/larch --sparse $LARCH_SPARSE_DIRS 2>&1
}

prepare_sparse_marketplace_add() {
    remove_larch_marketplace || true
    if [ -d "$MARKETPLACE_CLONE" ]; then
        larch_err "Removing existing larch marketplace clone before sparse add: $MARKETPLACE_CLONE"
        rm -rf -- "$MARKETPLACE_CLONE"
    fi
}

refresh_larch_marketplace() {
    # A sparse clone is valid only when both the legacy-heavy larch-logs/ dir is
    # absent and git's sparse cone exactly matches LARCH_SPARSE_DIRS. The cone
    # comparison catches future include-list additions for existing installs.
    if marketplace_sparse_cone_matches; then
        larch_err "Refreshing larch marketplace in place (sparse clone present)..."
        if ! claude plugin marketplace update larch-local 2>&1; then
            larch_err "marketplace update failed; falling back to sparse re-add..."
            prepare_sparse_marketplace_add
            add_sparse_larch_marketplace
        fi
    else
        larch_err "Adding larch marketplace (sparse checkout; excludes larch-logs)..."
        prepare_sparse_marketplace_add
        add_sparse_larch_marketplace
    fi
}

get_stable_releases() {
    gh api --paginate repos/character-ai/larch/releases \
      --jq '.[] | select(.prerelease == false and .draft == false) | .tag_name' \
      | sed 's/^v//'
}

get_installed_larch_version() {
    local plugin_record installed_version
    plugin_record=$(claude plugin list 2>/dev/null | awk '
        /larch@larch-local/ { want=1; next }
        want && /^[[:space:]]*Version:/ {
            sub(/^[[:space:]]*Version:[[:space:]]*/, "", $0)
            print
            exit
        }
    ' || true)
    if is_safe_version "${plugin_record:-}"; then
        printf '%s\n' "$plugin_record"
        return 0
    fi

    installed_version=$(grep -A6 '"larch@larch-local"' "$HOME/.claude/plugins/installed_plugins.json" 2>/dev/null | awk -F'"' '
        /"version":/ {
            print $4
            exit
        }
    ' || true)
    if is_safe_version "${installed_version:-}"; then
        printf '%s\n' "$installed_version"
        return 0
    fi

    return 1
}

stat_mtime() {
    local file="$1"
    local mt

    if mt=$(stat -c '%Y' -- "$file" 2>/dev/null) && [[ "$mt" =~ ^[0-9]+$ ]]; then
        printf '%s\n' "$mt"
        return 0
    fi
    if mt=$(stat -f '%m' -- "$file" 2>/dev/null) && [[ "$mt" =~ ^[0-9]+$ ]]; then
        printf '%s\n' "$mt"
        return 0
    fi
    printf '0\n'
    return 0
}

read_install_stamp() {
    local version_dir="$1"
    local stamp_file="$version_dir/.larch-installed-at"
    local stamp

    [ -f "$stamp_file" ] || return 1
    stamp=$(tr -d '\r\n' < "$stamp_file" 2>/dev/null || true)
    [[ "$stamp" =~ ^[0-9]+$ ]] || return 1
    printf '%s\n' "$stamp"
}

write_install_stamp() {
    local version="$1"
    local version_dir="$LARCH_CACHE_DIR/$version"
    local now

    [ -d "$version_dir" ] || return 0
    now=$(date +%s 2>/dev/null || true)
    [[ "$now" =~ ^[0-9]+$ ]] || {
        warn_install_stamp_failure "$version"
        return 0
    }
    if ! printf '%s\n' "$now" > "$version_dir/.larch-installed-at"; then
        warn_install_stamp_failure "$version"
    fi
}

list_cached_versions_by_install_stamp() {
    local dirs=()
    local dir version_dir version has_stamp ts

    shopt -s nullglob
    dirs=("$LARCH_CACHE_DIR"/[0-9]*/)
    shopt -u nullglob

    for dir in "${dirs[@]}"; do
        [ -d "$dir" ] || continue
        version_dir="${dir%/}"
        version=$(basename "$version_dir")
        is_safe_version "$version" || continue

        if read_install_stamp "$version_dir" >/dev/null 2>&1; then
            has_stamp=1
            ts=$(read_install_stamp "$version_dir")
        else
            has_stamp=0
            ts=$(stat_mtime "$version_dir")
        fi
        printf '%s\t%s\t%s\n' "$has_stamp" "$ts" "$version"
    done | sort -t $'\t' -k1,1rn -k2,2rn -k3,3rn | cut -f3-
}

version_is_retained() {
    local needle="$1"
    local retained="$2"
    local version

    for version in $retained; do
        [ "$version" = "$needle" ] && return 0
    done
    return 1
}

backfill_install_stamps() {
    # Defect C hardening: persistently stamp any unstamped cached version dir
    # from its filesystem mtime (its best "installed-at" proxy), so a recent
    # but unstamped dir no longer sorts below every stamped one. Derives from
    # mtime, not `date +%s`, so a genuinely-old legacy dir keeps an old rank
    # instead of looking freshly installed. Already-stamped dirs are skipped;
    # #3174's has_stamp-first ordering is preserved.
    local version_dir version mt
    shopt -s nullglob
    for version_dir in "$LARCH_CACHE_DIR"/[0-9]*/; do
        version_dir="${version_dir%/}"
        [ -d "$version_dir" ] || continue
        version=$(basename "$version_dir")
        is_safe_version "$version" || continue
        read_install_stamp "$version_dir" >/dev/null 2>&1 && continue
        mt=$(stat_mtime "$version_dir")
        [[ "$mt" =~ ^[0-9]+$ ]] || continue
        [ "$mt" -gt 0 ] || continue
        if ! printf '%s\n' "$mt" > "$version_dir/.larch-installed-at"; then
            warn_install_stamp_failure "$version"
        fi
    done
    shopt -u nullglob
}

prune_cached_versions() {
    local target_version="$1"
    local keep_versions=8
    local retained="" version version_dir removed=0 _protected

    larch_err "Pruning old larch versions (keeping up to ${keep_versions} most-recently-installed)..."

    backfill_install_stamps

    # Always retain (a) the just-installed target and (b) the version this
    # script runs from (INSTALLED_VERSION). Deleting the running dir mid-run
    # removes sibling helpers it sources (scripts/lib-quiet.sh,
    # scripts/redact-secrets.sh), breaking log redaction for the rest of the run.
    for _protected in "$target_version" "$INSTALLED_VERSION"; do
        [ -n "$_protected" ] || continue
        is_safe_version "$_protected" || continue
        [ -d "$LARCH_CACHE_DIR/$_protected" ] || continue
        version_is_retained "$_protected" "$retained" && continue
        retained="${retained:+$retained }$_protected"
    done

    while IFS= read -r version; do
        [ -n "$version" ] || continue
        if version_is_retained "$version" "$retained"; then
            continue
        fi
        retained="${retained:+$retained }$version"
        if [ "$(printf '%s\n' "$retained" | wc -w | tr -d ' ')" -ge "$keep_versions" ]; then
            break
        fi
    done < <(list_cached_versions_by_install_stamp)

    if [ -z "$retained" ]; then
        larch_err "  No cached versions to prune."
        return 0
    fi

    shopt -s nullglob
    for version_dir in "$LARCH_CACHE_DIR"/[0-9]*/; do
        [ -d "$version_dir" ] || continue
        version=$(basename "${version_dir%/}")
        is_safe_version "$version" || continue
        if version_is_retained "$version" "$retained"; then
            continue
        fi
        larch_err "  Removing old version: $version"
        if ! rm -rf -- "${LARCH_CACHE_DIR:?}/${version:?}"; then
            warn_prune_failure "$version"
            continue
        fi
        removed=$((removed + 1))
    done
    shopt -u nullglob

    if [ "$removed" -eq 0 ]; then
        larch_err "  No old versions to prune."
    fi
}

# Parent directory that contains one subdirectory per installed larch version.
LARCH_CACHE_DIR="$(dirname "$PLUGIN_ROOT")"
# Version string of the currently running larch installation (basename of PLUGIN_ROOT).
INSTALLED_VERSION="$(basename "$PLUGIN_ROOT")"

# shellcheck disable=SC2317 # file may be sourced; exit fallback is for direct execution.
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    return 0 2>/dev/null || exit 0
fi

# Resolve the latest stable (non-pre-release, non-draft) release from GitHub.
larch_err "Checking latest stable larch release..."
LATEST_STABLE=""
if command -v gh >/dev/null 2>&1; then
    STABLE_RELEASES=()
    GH_RELEASES_OUTPUT=""
    GH_STDERR_LOG=$(mktemp "${TMPDIR:-/tmp}/upgrade-larch-gh-stderr.XXXXXX")
    if GH_RELEASES_OUTPUT=$(get_stable_releases 2>"$GH_STDERR_LOG"); then
        while IFS= read -r release; do
            [ -n "$release" ] || continue
            STABLE_RELEASES+=("$release")
        done <<< "$GH_RELEASES_OUTPUT"

        if [ "${#STABLE_RELEASES[@]}" -eq 0 ]; then
            larch_err "Warning: gh returned no stable larch releases; upgrading without stable verification."
        else
            for release in "${STABLE_RELEASES[@]}"; do
                if ! is_safe_version "$release"; then
                    larch_err "Warning: ignoring unexpected stable tag '${release}'."
                    continue
                fi
                if [ -z "$LATEST_STABLE" ]; then
                    LATEST_STABLE="$release"
                    break
                fi
            done
            if [ -z "$LATEST_STABLE" ]; then
                larch_err "Warning: gh returned no valid stable larch release tags; upgrading without stable verification."
            fi
        fi
    else
        gh_status=$?
        larch_err "Warning: failed to query GitHub stable releases via gh (exit ${gh_status}); upgrading without stable verification."
    fi
    rm -f -- "$GH_STDERR_LOG"
fi

# Idempotency: on already-latest, stamp and prune without reinstalling.
CURRENT_INSTALLED_VERSION=$(get_installed_larch_version || true)
if ! is_safe_version "${CURRENT_INSTALLED_VERSION:-}"; then
    CURRENT_INSTALLED_VERSION="$INSTALLED_VERSION"
fi
if [ -n "$LATEST_STABLE" ] && [ "$CURRENT_INSTALLED_VERSION" = "$LATEST_STABLE" ]; then
    ACTUAL_VERSION="${CURRENT_INSTALLED_VERSION:-$INSTALLED_VERSION}"
    write_install_stamp "$ACTUAL_VERSION"
    prune_cached_versions "$ACTUAL_VERSION"
    larch_err ""
    larch_err "Already at latest stable larch release (${CURRENT_INSTALLED_VERSION}). No upgrade needed."
    exit 0
fi

if [ -n "$LATEST_STABLE" ]; then
    larch_err "Upgrading larch from ${INSTALLED_VERSION} to ${LATEST_STABLE}..."
else
    larch_err "Latest stable release could not be determined; upgrading unconditionally..."
fi

larch_err "Uninstalling larch plugin..."
claude plugin uninstall larch@larch-local 2>&1 || true

# Marketplace refresh. A valid sparse clone has the expected sparse cone and no
# larch-logs/ checkout. Full legacy clones, missing clones, and sparse-cone drift
# trigger remove + sparse re-add; valid sparse clones update in place.
refresh_larch_marketplace

larch_err "Installing larch plugin..."
claude plugin install larch@larch-local 2>&1

# Resolve the installed version up front so we can stamp it regardless of stable
# verification. The stamp records install time and drives cache-retention
# ranking; an unstamped dir sorts below every stamped version. Pruning stays
# gated on a verified stable install below (rollback safety).
VERIFIED_TARGET=false
ACTUAL_VERSION=$(get_installed_larch_version || true)
if [ -n "$LATEST_STABLE" ]; then
    if [ "$ACTUAL_VERSION" = "$LATEST_STABLE" ]; then
        VERIFIED_TARGET=true
        larch_err "Verified: larch ${LATEST_STABLE} installed successfully."
    else
        larch_err ""
        larch_err "Warning: expected version ${LATEST_STABLE} but found installed version ${ACTUAL_VERSION:-unknown}."
        larch_err "A pre-release or unexpected version may have been installed."
        larch_err "Re-run /upgrade-larch or install manually:"
        larch_err "  claude plugin marketplace remove larch-local"
        larch_err "  rm -rf '$MARKETPLACE_CLONE'"
        larch_err "  claude plugin marketplace add character-ai/larch --sparse $LARCH_SPARSE_DIRS"
        larch_err "  claude plugin install larch@larch-local"
    fi
fi

if [ "$VERIFIED_TARGET" = true ]; then
    if is_safe_version "${ACTUAL_VERSION:-}"; then
        write_install_stamp "$ACTUAL_VERSION"
    fi
    prune_cached_versions "$ACTUAL_VERSION"
else
    larch_err "Skipping prune because the expected stable version was not verified."
fi

larch_err ""
larch_err "Installed larch plugin version:"
claude plugin list 2>&1 | grep -A2 'larch@larch-local' || true

larch_err ""
if [ "$VERIFIED_TARGET" = false ] && [ -n "$LATEST_STABLE" ]; then
    larch_err "Upgrade incomplete: expected stable version ${LATEST_STABLE} was not verified."
    exit 1
fi

larch_err "Upgrade complete. Restart Claude Code to apply the new version."
