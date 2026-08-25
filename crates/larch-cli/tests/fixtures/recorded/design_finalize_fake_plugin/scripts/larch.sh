#!/bin/sh
set -eu

value() {
  wanted=$1
  shift
  while [ "$#" -gt 1 ]; do
    if [ "$1" = "$wanted" ]; then
      printf '%s\n' "$2"
      return 0
    fi
    shift
  done
  return 1
}

allowed() {
  wanted=$1
  shift
  while [ "$#" -gt 1 ]; do
    if [ "$1" = "--allow" ] && [ "$2" = "$wanted" ]; then
      return 0
    fi
    shift
  done
  return 1
}

case "$1 $2" in
  "plan check-size")
    printf '%s\n' 'PLAN_SIZE_STATUS=ok' 'SIZE_TRIGGER_FIRED=false'
    ;;
  "design publish")
    mode=${DESIGN_FINALIZE_FAKE_MODE-}
    if [ "$mode" = success ]; then
      latest_phase=publish
      plan_write_ok=true
      publish_ok=true
      rc=0
    else
      latest_phase=plan-write
      plan_write_ok=false
      publish_ok=false
      rc=5
    fi
    body=$(printf 'PUBLISH_ATTEMPT_ID=%s\nPUBLISH_RC_SOURCE=returned\nLATEST_PHASE=%s\nPLAN_WRITE_OK=%s\nPUBLISH_OK=%s\nLOG_PUBLISH_ATTEMPTED=false\nLOG_PUBLISH_COMPLETED=false\nRENAMED=false\nVALIDATE_STATUS=ok\n' \
      "${LARCH_DESIGN_PUBLISH_ATTEMPT_ID-}" "$latest_phase" "$plan_write_ok" "$publish_ok")
    printf '%s\n' "$body"
    if [ "$mode" = success ]; then
      design_tmpdir=$(value --design-tmpdir "$@")
      printf '%s\n' "$body" > "$design_tmpdir/.design-publish-result.env"
    fi
    exit "$rc"
    ;;
  "design read-result-env")
    primary=$(value --input "$@")
    fallback=$(value --fallback-input "$@")
    output=$(value --output "$@")
    source=$fallback
    if [ -f "$primary" ] && [ ! -L "$primary" ]; then
      source=$primary
    fi
    if [ ! -f "$source" ] || [ -L "$source" ]; then
      exit 1
    fi
    : > "$output"
    while IFS= read -r row || [ -n "$row" ]; do
      key=${row%%=*}
      if [ "$key" != "$row" ] && allowed "$key" "$@"; then
        printf '%s\n' "$row" >> "$output"
      fi
    done < "$source"
    ;;
  "design stage-terminal-state")
    printf '%s\n' 'STAGED=true'
    ;;
  "design render-final-summary")
    design_tmpdir=$(value --design-tmpdir "$@")
    printf '%s\n' 'offline final summary' > "$design_tmpdir/final-summary.md"
    ;;
  *)
    printf 'design-finalize fixture: unsupported command: %s\n' "$*" >&2
    exit 2
    ;;
esac
