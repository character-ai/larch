#!/usr/bin/env bash
out=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) out="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf '%s\n' '{"schema_version":3,"design_classification":"SIMPLE","partition_requested":false,"brainstorm_requested":false,"manual_gate_b":false}' >"$out"
printf 'RUN_PARAMS_WRITTEN=%s\n' "$out"
exit 0
