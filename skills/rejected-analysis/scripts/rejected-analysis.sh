#!/usr/bin/env bash
# Thin larch wrapper for /rejected-analysis. Logic lives in python/cli.py.
set -euo pipefail

resolve_root() {
    local script_dir
    script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    cd "$script_dir/../../.." && pwd
}

ROOT=$(resolve_root)
CLI="$ROOT/python/cli.py"

usage() {
    cat >&2 <<'USAGE'
usage: rejected-analysis.sh prepare --n DAYS [--work-dir DIR] [--log-root DIR] [--verify-cap N]
       rejected-analysis.sh ingest-verdict --work-dir DIR --candidate-id ID --output PATH --launcher-exit N [--dirty-sidecar PATH]
       rejected-analysis.sh finalize --work-dir DIR
       rejected-analysis.sh record --work-dir DIR [--issue-output PATH] [--issue-verified true|false] [--issues-failed N] [--launch-failures N] [--repo-root PATH]
USAGE
}

if [[ $# -lt 1 ]]; then
    usage
    exit 2
fi

cmd=$1
shift
case "$cmd" in
    prepare)
        args=()
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --n)
                    [[ $# -ge 2 ]] || { usage; exit 2; }
                    args+=(--days "$2")
                    shift 2
                    ;;
                --days)
                    echo "rejected-analysis.sh: public prepare flag is --n; wrapper forwards --days internally" >&2
                    exit 2
                    ;;
                --work-dir|--log-root|--verify-cap)
                    [[ $# -ge 2 ]] || { usage; exit 2; }
                    args+=("$1" "$2")
                    shift 2
                    ;;
                *)
                    usage
                    exit 2
                    ;;
            esac
        done
        exec python3 "$CLI" rejected-analysis prepare "${args[@]}"
        ;;
    ingest-verdict)
        args=()
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --work-dir)
                    [[ $# -ge 2 ]] || { usage; exit 2; }
                    args+=("$1" "$2")
                    shift 2
                    ;;
                --candidate-id)
                    [[ $# -ge 2 ]] || { usage; exit 2; }
                    args+=("$1" "$2")
                    shift 2
                    ;;
                --output)
                    [[ $# -ge 2 ]] || { usage; exit 2; }
                    args+=("$1" "$2")
                    shift 2
                    ;;
                --launcher-exit)
                    [[ $# -ge 2 ]] || { usage; exit 2; }
                    args+=("$1" "$2")
                    shift 2
                    ;;
                --dirty-sidecar)
                    [[ $# -ge 2 ]] || { usage; exit 2; }
                    args+=("$1" "$2")
                    shift 2
                    ;;
                *)
                    usage
                    exit 2
                    ;;
            esac
        done
        exec python3 "$CLI" rejected-analysis "$cmd" "${args[@]}"
        ;;
    finalize)
        exec python3 "$CLI" rejected-analysis "$cmd" "$@"
        ;;
    record)
        args=()
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --work-dir|--issue-output|--issue-verified|--issues-failed|--launch-failures|--repo-root)
                    [[ $# -ge 2 ]] || { usage; exit 2; }
                    args+=("$1" "$2")
                    shift 2
                    ;;
                *)
                    usage
                    exit 2
                    ;;
            esac
        done
        exec python3 "$CLI" rejected-analysis record "${args[@]}"
        ;;
    *)
        usage
        exit 2
        ;;
esac
