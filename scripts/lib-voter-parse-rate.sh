#!/usr/bin/env bash
# Shared helpers for voter parse-rate diagnostic files.

voter_parse_rate_diag_path() {
    local voter_path="$1"
    case "$voter_path" in
        *.txt) printf '%s\n' "${voter_path%.txt}-parse-rate-diag.txt" ;;
        *) printf '%s-parse-rate-diag.txt\n' "$voter_path" ;;
    esac
}

voter_output_sha256() {
    local voter_path="$1"
    [[ -f "$voter_path" ]] || return 1
    shasum -a 256 "$voter_path" | awk '{print $1}'
}

voter_parse_rate_diag_matches_output() {
    local diag_file="$1" voter_path="$2" recorded_path recorded_sha actual_sha
    [[ -f "$diag_file" && -f "$voter_path" ]] || return 1

    recorded_path=$(
        awk 'index($0, "voter_file=") == 1 { print substr($0, 12); exit }' "$diag_file"
    )
    recorded_sha=$(
        awk 'index($0, "voter_sha256=") == 1 { print substr($0, 14); exit }' "$diag_file"
    )
    [[ -n "$recorded_path" && -n "$recorded_sha" ]] || return 1

    actual_sha="$(voter_output_sha256 "$voter_path")" || return 1
    [[ "$recorded_path" == "$voter_path" && "$recorded_sha" == "$actual_sha" ]]
}
