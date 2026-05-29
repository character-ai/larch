#!/usr/bin/env bash
# Shared Stage-4 (#3119) Family-B fence absence checks for orchestrator markdown.
# Source from structure harnesses; requires caller-defined fail().

# assert_p3119_family_b_fence_absent FILE LABEL [ship-pr-invocation]
# When the optional third argument is "ship-pr-invocation", also reject
# background+monitor ship-pr invocation prose (implement SKILL.md pin).
assert_p3119_family_b_fence_absent() {
  local file="$1" label="$2" ship_pr="${3:-}"
  local _p3119_bc_mon _p3119_bg_pair _p3119_auth_doc _p3119_pair_banner _p3119_bg_mon
  local _p3119_larch _p3119_done_sent _p3119_status_file _p3119_paired_pid
  local _p3119_bc_stream _p3119_bc_mon_sh _p3119_bc_surf _p3119_mon_rc
  local _p3119_q_append _p3119_q_paired _p3119_token

  # shellcheck disable=SC2016 # Stage 4: Family-B fence shape removed from orchestrator docs
  _p3119_bc_mon=$(printf '%b' '\x62\x72\x65\x61\x64\x63\x72\x75\x6d\x62-\x6d\x6f\x6e\x69\x74\x6f\x72')
  _p3119_bg_pair=$(printf '%s %s' 'Background pair' 'required')
  _p3119_auth_doc=$(printf '%s%s.md §4' 'BASH_AUTHORING' '')
  _p3119_pair_banner=$(printf '%s%s.sh.**' '**⚠ Background required — must be paired with ' "$_p3119_bc_mon")
  _p3119_larch=$(printf '%s' 'LARCH_')
  _p3119_done_sent=$(printf '%s%s' "$_p3119_larch" 'DONE_SENTINEL')
  _p3119_status_file=$(printf '%s%s' "$_p3119_larch" 'STATUS_FILE')
  _p3119_paired_pid=$(printf '%s%s' "$_p3119_larch" 'PAIRED_PID_FILE')
  _p3119_bc_stream=$(printf '%s%s%s' "$_p3119_larch" 'BREADCRUMB' '_STREAM')
  _p3119_bc_mon_sh=$(printf '%s%s%s' "$_p3119_larch" 'BREADCRUMB' '_MONITOR_SH')
  _p3119_bc_surf=$(printf '%s%s' "$_p3119_larch" 'BREADCRUMBS_SURFACED_FILE')
  _p3119_mon_rc=$(printf '%s%s' 'monitor' '_rc')
  _p3119_q_append=$(printf '%s%s' 'larch_quiet_append' '_done_trap')
  _p3119_q_paired=$(printf '%s%s' 'larch_quiet_write' '_paired_pid_file')
  if grep -Fq "$_p3119_pair_banner" "$file"; then
    fail "(3119) $label still has background-pair banner in a skill fence"
  fi
  if grep -Fq "# ${_p3119_bg_pair}: see ${_p3119_auth_doc}" "$file"; then
    fail "(3119) $label still has BASH_AUTHORING §4 in-fence comment"
  fi
  if grep -Fq "${_p3119_bc_mon}.sh" "$file"; then
    fail "(3119) $label still references the removed Family-B monitor script"
  fi
  for _p3119_token in \
    "$_p3119_done_sent" \
    "$_p3119_status_file" \
    "$_p3119_paired_pid" \
    "$_p3119_bc_stream" \
    "$_p3119_bc_mon_sh" \
    "$_p3119_bc_surf" \
    "$_p3119_mon_rc" \
    "$_p3119_q_append" \
    "$_p3119_q_paired"; do
    if grep -Fq "$_p3119_token" "$file"; then
      fail "(3119) $label still references removed Family-B token"
    fi
  done
  if [[ "$ship_pr" == ship-pr-invocation ]]; then
    _p3119_bg_mon=$(printf '%s+%s' 'background' 'monitor')
    if grep -Fq "${_p3119_bg_mon} invocation" "$file"; then
      fail "(3119) $label still mandates background+monitor ship-pr invocation"
    fi
  fi
}
