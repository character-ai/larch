#!/usr/bin/env bash
# aggregate-findings-phrases.inc.bash — round-relative "See …" phrases for aggregator warnings.
#
# Callers must set:
#   REVIEW_TMPDIR_CANON — absolute path to the review tmpdir (often a round-* directory)
# Optional:
#   SESSION_ENV_PATH — when set, map tmpdir-sidecar stderr paths to committed round-relative names

committed_ref() {
    local failure_log="$1"
    if [[ -n "${SESSION_ENV_PATH:-}" ]]; then
        local round_name flbase
        round_name="$(basename "$REVIEW_TMPDIR_CANON")"
        flbase="$(basename "$failure_log")"
        case "$round_name" in
            round-*)
                case "$flbase" in
                    aggregator-dispatch.stderr | aggregator-validate.stderr)
                        printf '%s/%s' "$round_name" "$flbase"
                        return
                        ;;
                esac
                ;;
        esac
    fi
    printf '%s' "$failure_log"
}

failure_see_phrase() {
    local failure_log="$1" cref
    cref="$(committed_ref "$failure_log")"
    if [[ "$cref" == "$failure_log" ]]; then
        printf 'See %s.' "$cref"
    else
        printf 'See %s in the committed run log.' "$cref"
    fi
}
