## Goal

Prevent larch-log writes from polluting the git working tree during a run by staging in $IMPLEMENT_TMPDIR until commit is explicitly called.

## Implementation Plan

See design-export/plan.txt for full plan (SIMPLE quick-mode).

## Test plan

- Run /relevant-checks after implementing.
- Existing test-larch-log.sh and test-larch-logs-manifest.sh set LARCH_LOG_ROOT and are unaffected.
