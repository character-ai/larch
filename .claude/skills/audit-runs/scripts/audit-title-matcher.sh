#!/usr/bin/env bash
# audit-title-matcher.sh — Centralized audit-report title shape matcher.
#
# Usage (function):
#   source audit-title-matcher.sh
#   match_audit_report_title --skill <design|implement> --title "<string>"
#   echo $?  # 0 = matches, 1 = no match
#
# Usage (CLI):
#   audit-title-matcher.sh --skill <name> --title "<string>"

set -euo pipefail

_match_audit_report_title_impl() {
    local skill="${1:-}" title="${2:-}"
    case "$skill" in
        implement)
            printf '%s' "$title" | grep -qE '^\[(Run Logs Audit |Implement Run Logs Audit ).* Report\]'
            ;;
        design)
            printf '%s' "$title" | grep -qE '^\[Design Run Logs Audit .* Report\]'
            ;;
        *)
            return 1
            ;;
    esac
}

match_audit_report_title() {
    local skill="" title=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --skill) skill="$2"; shift 2 ;;
            --title) title="$2"; shift 2 ;;
            *)
                printf 'audit-title-matcher.sh: unknown argument: %s\n' "$1" >&2
                return 1
                ;;
        esac
    done
    if [ -z "$skill" ] || [ -z "$title" ]; then
        printf 'audit-title-matcher.sh: --skill and --title are required\n' >&2
        return 1
    fi
    _match_audit_report_title_impl "$skill" "$title"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    match_audit_report_title "$@"
    exit $?
fi
