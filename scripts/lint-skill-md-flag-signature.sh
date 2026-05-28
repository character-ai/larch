#!/usr/bin/env bash
# Check that flags used in SKILL.md script invocations exist in target scripts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"

usage() {
    printf '%s\n' "Usage: lint-skill-md-flag-signature.sh [--root <repo-or-fixture-root>]" >&2
}

take_value() {
    local flag="$1"
    local value="${2:-}"
    if [ -z "$value" ] || [ "${value#--}" != "$value" ]; then
        printf '%s\n' "lint-skill-md-flag-signature.sh: $flag requires a value" >&2
        exit 2
    fi
    printf '%s' "$value"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --root)
            ROOT="$(take_value --root "${2:-}")"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf '%s\n' "lint-skill-md-flag-signature.sh: unknown argument: $1" >&2
            usage
            exit 2
            ;;
    esac
done

finding=0
# shellcheck disable=SC2016 # literal plugin-root token recognized in SKILL.md fences.
CLAUDE_PLUGIN_ROOT_BRACED='${CLAUDE_PLUGIN_ROOT}'
# shellcheck disable=SC2016 # literal plugin-root token recognized in SKILL.md fences.
CLAUDE_PLUGIN_ROOT_PLAIN='$CLAUDE_PLUGIN_ROOT'

resolve_script_path() {
    local token="$1"
    token="${token%\\}"
    token="${token#\"}"
    token="${token%\"}"
    token="${token#\'}"
    token="${token%\'}"

    case "$token" in
        "$CLAUDE_PLUGIN_ROOT_BRACED"/*)
            printf '%s\n' "$ROOT/${token#"$CLAUDE_PLUGIN_ROOT_BRACED"/}"
            ;;
        "$CLAUDE_PLUGIN_ROOT_PLAIN"/*)
            printf '%s\n' "$ROOT/${token#"$CLAUDE_PLUGIN_ROOT_PLAIN"/}"
            ;;
        "$ROOT"/*)
            printf '%s\n' "$token"
            ;;
        /*/scripts/*.sh)
            printf '%s\n' "$token"
            ;;
        *)
            return 1
            ;;
    esac
}

script_from_command() {
    local command="$1"
    local token

    for token in $command; do
        token="${token%\\}"
        token="${token#\"}"
        token="${token%\"}"
        token="${token#\'}"
        token="${token%\'}"
        case "$token" in
            */scripts/*.sh)
                resolve_script_path "$token"
                return 0
                ;;
        esac
    done
    return 1
}

declare_case_arm_exists() {
    local script="$1"
    local flag="$2"
    grep -Eq "(^|[[:space:]])--${flag}([|)])" "$script"
}

report_command_flags() {
    local skill_file="$1"
    local line_no="$2"
    local command="$3"
    local previous_line="$4"
    local script
    local rel_skill="${skill_file#"$ROOT"/}"
    local rel_script
    local flags=""
    local flag
    local remainder="$command"

    [[ "$command" == *"--"* ]] || return 0
    script="$(script_from_command "$command" || true)"
    [ -n "$script" ] || return 0

    while [[ "$remainder" =~ (^|[[:space:]])--([A-Za-z0-9][A-Za-z0-9_-]*) ]]; do
        flag="${BASH_REMATCH[2]}"
        flags="${flags}${flag}
"
        remainder="${remainder#*"--$flag"}"
    done
    [ -n "$flags" ] || return 0

    if [[ "$command" == *"# lint-skill-md-flag-signature: ok "* ]] || [[ "$previous_line" == *"# lint-skill-md-flag-signature: ok "* ]]; then
        return 0
    fi

    if [ ! -f "$script" ]; then
        rel_script="${script#"$ROOT"/}"
        printf '%s\n' "${rel_skill}:${line_no}: WARN target script not found: ${rel_script}" >&2
        return 0
    fi

    rel_script="${script#"$ROOT"/}"
    while IFS= read -r flag; do
        [ -n "$flag" ] || continue
        if ! declare_case_arm_exists "$script" "$flag"; then
            printf '%s\n' "${rel_skill}:${line_no}: invocation uses --${flag} but ${rel_script} does not declare it" >&2
            finding=1
        fi
    done <<EOF
$flags
EOF
}

scan_skill_file() {
    local file="$1"
    local line
    local previous=""
    local lineno=0
    local in_fence=false
    local logical=""
    local logical_start=0
    local logical_previous=""

    # shellcheck disable=SC2094 # report helper reads target scripts, not this SKILL.md stream.
    while IFS= read -r line || [ -n "$line" ]; do
        lineno=$((lineno + 1))

        if [[ "$line" =~ ^[[:space:]]*\`\`\`(bash|sh|shell)([[:space:]].*)?$ ]]; then
            in_fence=true
            previous="$line"
            continue
        fi
        if [[ "$line" =~ ^[[:space:]]*\`\`\` ]]; then
            if [ "$in_fence" = true ] && [ -n "$logical" ]; then
                # shellcheck disable=SC2094 # report helper reads target scripts, not this SKILL.md stream.
                report_command_flags "$file" "$logical_start" "$logical" "$logical_previous"
                logical=""
            fi
            in_fence=false
            previous="$line"
            continue
        fi
        if [ "$in_fence" != true ]; then
            previous="$line"
            continue
        fi

        if [ -z "$logical" ]; then
            logical="$line"
            logical_start="$lineno"
            logical_previous="$previous"
        else
            logical="${logical} ${line}"
        fi

        if [[ "$line" == *\\ ]]; then
            previous="$line"
            continue
        fi

        # shellcheck disable=SC2094 # report helper reads target scripts, not this SKILL.md stream.
        report_command_flags "$file" "$logical_start" "$logical" "$logical_previous"
        logical=""
        logical_start=0
        logical_previous=""
        previous="$line"
    done < "$file"
}

if [ -d "$ROOT/skills" ]; then
    while IFS= read -r file; do
        scan_skill_file "$file"
    done < <(find "$ROOT/skills" -mindepth 2 -maxdepth 2 -type f -name SKILL.md | sort)
fi

exit "$finding"
