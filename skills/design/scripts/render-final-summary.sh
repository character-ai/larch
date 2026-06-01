#!/usr/bin/env bash
{
  echo "render ISSUE_NUMBER=${ISSUE_NUMBER:-} SESSION_ID=${SESSION_ID:-} DESIGN_TMPDIR=${DESIGN_TMPDIR:-} $*"
} >>"${RENDER_LOG:?}"
printf '# summary\n' >"${DESIGN_TMPDIR:?}/final-summary.md"
