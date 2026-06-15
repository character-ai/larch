#!/usr/bin/env bash
# Sourced by design-step3-review.sh for pre-launch plan-review failures.
# shellcheck shell=bash

_step3_review_write_prelaunch_failure() {
  local _result_env="$DESIGN_TMPDIR/.step3-review-result.env"
  local _tmp=""
  # Drop any prior loop envelope before publishing the pre-launch failure state.
  rm -f "$_result_env" 2>/dev/null || true
  _tmp="$(mktemp "$DESIGN_TMPDIR/.step3-review-result.env.XXXXXX" 2>/dev/null || true)"
  if [[ -n "$_tmp" ]]; then
    if {
      printf '%s\n' 'STEP3_REVIEW_LOOP_STATUS=panel-failed'
      printf '%s\n' 'LOOP_STATUS=panel-failed'
      printf '%s\n' 'REASON=monitor-mode-unavailable'
      printf '%s\n' 'TALLY_PLAN_REVIEW_STATUS=panel-failed'
      printf '%s\n' 'STEP3_REVIEW_CAP_REACHED=false'
      printf '%s\n' 'STEP3_REVIEW_ROUND_NUM='
      printf '%s\n' 'ROUND_NUM='
      printf '%s\n' 'ROUNDS_COMPLETED=0'
      printf '%s\n' 'REVIEW_ROUND_COUNT=0'
    } >"$_tmp"; then
      mv "$_tmp" "$_result_env" 2>/dev/null || {
        rm -f "$_tmp" "$_result_env" 2>/dev/null || true
      }
    else
      rm -f "$_tmp" "$_result_env" 2>/dev/null || true
    fi
  fi
  printf '%s\n' 'STEP3_REVIEW_LOOP_STATUS=panel-failed'
  printf '%s\n' 'LOOP_STATUS=panel-failed'
  printf '%s\n' 'REASON=monitor-mode-unavailable'
  printf '%s\n' 'TALLY_PLAN_REVIEW_STATUS=panel-failed'
  printf '%s\n' 'STEP3_REVIEW_CAP_REACHED=false'
  printf '%s\n' 'ROUNDS_COMPLETED=0'
  printf '%s\n' 'REVIEW_ROUND_COUNT=0'
  exit 0
}
