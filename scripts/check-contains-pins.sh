#!/usr/bin/env bash
# Verify canonical contains "$VAR" literal assertions against their targets.
# shellcheck disable=SC2016,SC2094
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if [ -f "$SCRIPT_DIR/lib-quiet.sh" ]; then
    # shellcheck source=scripts/lib-quiet.sh
    source "$SCRIPT_DIR/lib-quiet.sh"
    larch_quiet_init
else
    larch_err() { printf '%s\n' "$*" >&2; }
    emit() { printf '%s\n' "$*"; }
fi

usage() {
    larch_err "Usage: $0 [--changed-files FILE]"
}

CHANGED_FILES=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --changed-files)
            if [ "$#" -lt 2 ]; then
                usage
                exit 2
            fi
            CHANGED_FILES="$2"
            shift 2
            ;;
        -*)
            usage
            exit 2
            ;;
        *)
            usage
            exit 2
            ;;
    esac
done

if [ -n "$CHANGED_FILES" ] && [ ! -f "$CHANGED_FILES" ]; then
    larch_err "ERROR: --changed-files path not found: $CHANGED_FILES"
    exit 2
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$REPO_ROOT" ]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
fi
cd "$REPO_ROOT" || exit 2

normalize_rel() {
    local path="$1" part idx out_path
    local parts=()
    local out=()

    case "$path" in
        "$REPO_ROOT"/*) path="${path#"$REPO_ROOT"/}" ;;
        ./*) path="${path#./}" ;;
    esac

    IFS=/ read -r -a parts <<< "$path"
    for part in "${parts[@]}"; do
        case "$part" in
            ""|.)
                ;;
            ..)
                if [ "${#out[@]}" -gt 0 ]; then
                    idx=$((${#out[@]} - 1))
                    unset "out[$idx]"
                else
                    out+=("..")
                fi
                ;;
            *)
                out+=("$part")
                ;;
        esac
    done

    out_path=""
    for part in "${out[@]}"; do
        if [ -z "$out_path" ]; then
            out_path="$part"
        else
            out_path="$out_path/$part"
        fi
    done
    printf '%s\n' "$out_path"
}

CHANGED_RELS=()
if [ -n "$CHANGED_FILES" ]; then
    while IFS= read -r changed; do
        [ -n "$changed" ] || continue
        CHANGED_RELS+=("$(normalize_rel "$changed")")
    done < "$CHANGED_FILES"
fi

target_is_in_scope() {
    local target="$1" changed
    if [ -z "$CHANGED_FILES" ]; then
        return 0
    fi
    for changed in "${CHANGED_RELS[@]}"; do
        if [ "$changed" = "$target" ]; then
            return 0
        fi
    done
    return 1
}

assertion_is_in_scope() {
    local script="$1" var="${2:-}" target_rel

    if [ -z "$CHANGED_FILES" ]; then
        return 0
    fi

    if target_is_in_scope "$script"; then
        return 0
    fi

    if [ -n "$var" ] && target_rel="$(get_var_rel "$var" 2>/dev/null)"; then
        if target_is_in_scope "$target_rel"; then
            return 0
        fi
    fi

    return 1
}

set_var_rel() {
    local name="$1" rel="$2" i
    for i in "${!VAR_NAMES[@]}"; do
        if [ "${VAR_NAMES[$i]}" = "$name" ]; then
            VAR_RELS[i]="$rel"
            return 0
        fi
    done
    VAR_NAMES+=("$name")
    VAR_RELS+=("$rel")
}

get_var_rel() {
    local name="$1" i
    for i in "${!VAR_NAMES[@]}"; do
        if [ "${VAR_NAMES[$i]}" = "$name" ]; then
            printf '%s\n' "${VAR_RELS[$i]}"
            return 0
        fi
    done
    return 1
}

warn_unresolved() {
    local script="$1" line_no="$2" var="$3"
    larch_err "UNRESOLVED_VAR: $script:$line_no: could not resolve \$$var"
}

warn_skipped() {
    local script="$1" line_no="$2"
    larch_err "SKIPPED_NON_CANONICAL: $script:$line_no: assertion shape not in v1 grammar"
}

check_literal() {
    local script="$1" line_no="$2" var="$3" literal="$4"
    local target_rel target_path

    if ! target_rel="$(get_var_rel "$var")"; then
        if assertion_is_in_scope "$script" "$var"; then
            warn_unresolved "$script" "$line_no" "$var"
        fi
        return 0
    fi

    if ! assertion_is_in_scope "$script" "$var"; then
        return 0
    fi

    target_path="$REPO_ROOT/$target_rel"
    if [ ! -f "$target_path" ]; then
        warn_unresolved "$script" "$line_no" "$var"
        return 0
    fi

    if ! grep -Fq -- "$literal" "$target_path"; then
        emit "DEFECT: $script:$line_no: literal '$literal' not found in $target_rel"
        DEFECTS=$((DEFECTS + 1))
    fi
}

var_is_in_scope() {
    local script="$1" var="$2"
    assertion_is_in_scope "$script" "$var"
}

scan_test_script() {
    local script="$1"
    local script_dir script_parent line line_no rel var literal
    local repo_assign_re script_assign_re single_re double_re contains_prefix_re

    script_dir="${script%/*}"
    if [ "$script_dir" = "$script" ]; then
        script_dir="."
    fi
    script_parent="${script_dir%/*}"
    if [ "$script_parent" = "$script_dir" ]; then
        script_parent=""
    fi

    VAR_NAMES=()
    VAR_RELS=()
    line_no=0
    repo_assign_re='^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)="\$REPO_ROOT/([^"]*)"[[:space:]]*$'
    script_assign_re='^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)="\$SCRIPT_DIR/\.\./([^"]*)"[[:space:]]*$'
    single_re='^[[:space:]]*contains[[:space:]]+"\$([A-Za-z_][A-Za-z0-9_]*)"[[:space:]]+('\''([^'\'']*)'\'')[[:space:]]+.*$'
    double_re='^[[:space:]]*contains[[:space:]]+"\$([A-Za-z_][A-Za-z0-9_]*)"[[:space:]]+"([^"]*)"[[:space:]]+.*$'
    contains_prefix_re='^[[:space:]]*contains[[:space:]]+"\$([A-Za-z_][A-Za-z0-9_]*)"[[:space:]]+'

    while IFS= read -r line || [ -n "$line" ]; do
        line_no=$((line_no + 1))

        if [[ "$line" =~ $repo_assign_re ]]; then
            set_var_rel "${BASH_REMATCH[1]}" "$(normalize_rel "${BASH_REMATCH[2]}")"
            continue
        fi
        if [[ "$line" =~ $script_assign_re ]]; then
            if [ -n "$script_parent" ]; then
                rel="$script_parent/${BASH_REMATCH[2]}"
            else
                rel="${BASH_REMATCH[2]}"
            fi
            set_var_rel "${BASH_REMATCH[1]}" "$(normalize_rel "$rel")"
            continue
        fi

        if [[ "$line" =~ $single_re ]]; then
            var="${BASH_REMATCH[1]}"
            literal="${BASH_REMATCH[3]}"
            check_literal "$script" "$line_no" "$var" "$literal"
            continue
        fi

        if [[ "$line" =~ $double_re ]]; then
            var="${BASH_REMATCH[1]}"
            literal="${BASH_REMATCH[2]}"
            case "$literal" in
                *'$'*|*'`'*)
                    if var_is_in_scope "$script" "$var"; then
                        warn_skipped "$script" "$line_no"
                    fi
                    ;;
                *)
                    check_literal "$script" "$line_no" "$var" "$literal"
                    ;;
            esac
            continue
        fi

        if [[ "$line" =~ $contains_prefix_re ]]; then
            var="${BASH_REMATCH[1]}"
            if var_is_in_scope "$script" "$var"; then
                warn_skipped "$script" "$line_no"
            fi
        fi
    done < "$script"
}

TEST_LIST="$(mktemp "${TMPDIR:-/tmp}/check-contains-pins.XXXXXX")"
trap 'rm -f "$TEST_LIST"' EXIT

{
    if [ -d scripts ]; then
        find scripts -maxdepth 1 -type f -name 'test-*.sh'
    fi
    if [ -d skills ]; then
        find skills -path 'skills/*/scripts/test-*.sh' -type f
    fi
} | LC_ALL=C sort > "$TEST_LIST"

DEFECTS=0
while IFS= read -r test_script; do
    [ -n "$test_script" ] || continue
    scan_test_script "$test_script"
done < "$TEST_LIST"

if [ "$DEFECTS" -gt 0 ]; then
    exit 1
fi
exit 0
