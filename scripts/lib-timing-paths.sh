# shellcheck shell=bash
# lib-timing-paths.sh — sourced-only path-validation library shared by
# scripts/timing-ledger.sh and scripts/timing-report.sh.
#
# Closes review FINDING_1 + FINDING_4: previously timing-report.sh's
# `--ledger` validator only accepted paths under TMPDIR, while
# timing-ledger.sh's resolver accepts ledgers under any of TMPDIR,
# IMPLEMENT_TMPDIR, DESIGN_TMPDIR, REVIEW_TMPDIR, or
# dirname(SESSION_ENV_PATH). A caller passing the actual on-disk path of
# a non-TMPDIR ledger to `timing-report.sh --ledger` would hit "invalid
# ledger path" even though the path is valid for ledger writes. Sharing
# one canonicalizer + one allowed-roots list keeps both scripts in sync.
#
# Sourced only. No shebang, no `set -euo pipefail`, no `main`. Consumers
# `source` this file; they pass through any errors via their own
# `set -euo pipefail` context.

# tmp_root: print the canonicalized TMPDIR (or /tmp default), or return 1
# if it cannot be resolved.
tmp_root() {
    local root="${TMPDIR:-/tmp}"
    (cd "$root" 2>/dev/null && pwd -P) || return 1
}

# canonical_parent_path: canonicalize the parent directory of `$1` and
# print `<canonical-parent>/<basename>`. Rejects `..` segments and
# unresolvable parents.
canonical_parent_path() {
    local raw="$1"
    local base parent parent_dir resolved
    [[ -n "$raw" ]] || return 1
    case "$raw" in
        */../*|../*|*/..|..) return 1 ;;
    esac
    if [[ "$raw" = /* ]]; then
        parent="$raw"
    else
        local root
        root=$(tmp_root) || return 1
        parent="$root/$raw"
    fi
    parent_dir=$(dirname "$parent")
    base=$(basename "$parent")
    mkdir -p "$parent_dir" 2>/dev/null || return 1
    resolved=$(cd "$parent_dir" 2>/dev/null && pwd -P) || return 1
    printf '%s/%s' "$resolved" "$base"
}

# canonical_dir: canonicalize an existing directory path, or return 1.
canonical_dir() {
    local raw="$1"
    [[ -n "$raw" && -d "$raw" ]] || return 1
    (cd "$raw" 2>/dev/null && pwd -P)
}

# path_under_root: succeed iff $1 is exactly $2 or beneath $2.
path_under_root() {
    local path="$1"
    local root="$2"
    [[ "$path" == "$root" || "$path" == "$root"/* ]]
}

# validate_under_roots: canonicalize $1; succeed iff its parent dir lies
# under any of the remaining root args. Print the canonical path on
# success; return 1 on any failure.
validate_under_roots() {
    local raw="$1"
    shift
    local candidate root
    candidate=$(canonical_parent_path "$raw") || return 1
    for root in "$@"; do
        [[ -n "$root" ]] || continue
        if path_under_root "$candidate" "$root"; then
            printf '%s' "$candidate"
            return 0
        fi
    done
    return 1
}

# timing_allowed_roots: print the list of canonicalized roots that
# `timing-ledger.sh` and `timing-report.sh` both accept for ledger paths,
# one per line. Roots that cannot be resolved (e.g. unset env vars) are
# silently omitted. Order is informational; consumers iterate the full
# set.
timing_allowed_roots() {
    local root dir
    root=$(tmp_root 2>/dev/null || true)
    [[ -n "$root" ]] && printf '%s\n' "$root"
    local var
    for var in IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR; do
        dir="${!var:-}"
        canonical_dir "$dir" 2>/dev/null || true
    done
    if [[ -n "${SESSION_ENV_PATH:-}" ]]; then
        canonical_dir "$(dirname "$SESSION_ENV_PATH")" 2>/dev/null || true
    fi
}
