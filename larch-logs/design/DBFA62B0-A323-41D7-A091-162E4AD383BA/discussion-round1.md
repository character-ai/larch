## Decision 1: Dead-code disposition for --round-num parsing
- **Question**: After the flat assignment, the --round-num flag parsing (lines 19, 26, 33-35) and the ROUND_NUM case branches become dead code. Remove or leave?
- **Resolution**: Leave in place. Issue body states "harmless to leave" — preserves the existing call sites in `dispatch-panel.sh` without further coupling.
- **Source**: issue body

## Decision 2: Documentation file update scope
- **Question**: Does the fix include updating `check-reviewer-failure-threshold.md`?
- **Resolution**: Yes — issue body explicitly names that file: 'Also update `skills/review/scripts/check-reviewer-failure-threshold.md` which still documents INTENDED_SLOTS as "12 (HARD) or 7 (SIMPLE)".'
- **Source**: issue body

## Decision 3: Out-of-scope behaviors
- **Question**: Are there other reviewer-threshold knobs or panel-size constants that should be touched?
- **Resolution**: No. The bug is localized to `STATIC_INTENDED_SLOTS` assignment plus its documentation. Do not touch `dispatch-panel.sh`, the `--round-num` flag interface, or downstream threshold math.
- **Source**: codebase + issue body
