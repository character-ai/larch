#!/usr/bin/env bash
# breadcrumb-monitor.sh — Stage 3 no-op compatibility shim.
# Consumes all historical flags and exits 0. See scripts/breadcrumb-monitor.md.

set -euo pipefail

usage() {
    printf 'Usage: %s --stream PATH --done-sentinel PATH --status-file PATH --quiet-log PATH --surfaced-sentinel PATH [--paired-pid-file PATH] [--poll-interval=SEC] [--rate-cap=N] [--final-tail-lines=N] [--mode=tail|monitor] [-h|--help]\n' "$(basename "$0")" >&2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --stream)              shift 2 ;;
        --done-sentinel)       shift 2 ;;
        --status-file)         shift 2 ;;
        --quiet-log)           shift 2 ;;
        --surfaced-sentinel)   shift 2 ;;
        --paired-pid-file)     shift 2 ;;
        --poll-interval=*|--rate-cap=*|--final-tail-lines=*|--mode=*)
            shift ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            shift ;;
    esac
done

exit 0
