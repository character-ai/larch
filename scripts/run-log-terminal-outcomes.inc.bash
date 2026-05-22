#!/usr/bin/env bash
# run-log-terminal-outcomes.inc.bash — canonical terminal /implement outcome tokens
# for final-summary heading suffix checks (audit-scan-run, verify-run-log-completeness)
# and bail_steps_ran in write-final-report.sh. Keep these three sites in sync.

# Suffix match on the first non-empty line of final-summary.md (egrep -E pattern).
# shellcheck disable=SC2034
RUN_LOG_TERMINAL_OUTCOME_SUFFIX_EGREP='(bailed(-needs-user-input)?|stalled|design-only|forked-dry-run|pr-created(-draft)?)$'

# Whole-string match for write-final-report $OUTCOME (used with [[ =~ ]]).
# shellcheck disable=SC2034
RUN_LOG_TERMINAL_OUTCOME_NAME_EREGEX='^(bailed|bailed-needs-user-input|stalled|design-only|forked-dry-run|pr-created|pr-created-draft)$'
