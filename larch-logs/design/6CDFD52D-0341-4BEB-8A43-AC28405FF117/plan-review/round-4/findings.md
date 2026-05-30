### FINDING_1:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-collect-findings.sh:162-176
- **Concern**: Item B harness stubs collect-agent-results.sh / wait-for-reviewers.sh but collect-findings.sh hardcodes "$PLUGIN_ROOT/scripts/collect-agent-results.sh" and "$PLUGIN_ROOT/scripts/wait-for-reviewers.sh" with no env override (unlike review-core's REVIEW_CORE_AGGREGATE_FINDINGS_SH). Scenario: A stub on PATH or editing the repo copy never runs; merged 2>&1 capture can false-green while relay lines stay unsanitized
- **Proposed resolution**: Spell out a minimal temporary CLAUDE_PLUGIN_ROOT tree (stub scripts plus lib-quiet.sh and redact-secrets.sh siblings) and export it for the new failure-relay cases; mirror the ship-pr harness copy/stub pattern rather than implying PATH-only stubs

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-collect-agent-results.sh:7; skills/review/scripts/test-review-core.sh:5; skills/review/scripts/test-collect-findings.sh:30
- **Concern**: Plan treats LARCH_QUIET_DISABLE=1 as an alternative to merged 2>&1 for relay-byte assertions. Scenario: With quiet disabled, larch_err still writes only to stderr (lib-quiet.sh:127-139); stdout-only out=$(...) or run_core without 2>&1 can pass BEL/ESC grep while never exercising the sanitized relay
- **Proposed resolution**: Remove the OR wording in Item B harness steps and Failure modes; require merged 2>&1 (or a dedicated stderr capture file) for every new control-byte relay case

### FINDING_3:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-log-publish.sh:142-156
- **Concern**: Proposed make_find_ancestor_race_stub omits exit 0 after the -type f swap branch. Scenario: After printf of ANCESTOR_RACE_PATH the wrapper can fall through to exec real find (leaf stub at 151 uses exit 0), re-enumerating a mutated tree and yielding wrong file lists or a false-green publish
- **Proposed resolution**: Specify the stub heredoc must mirror make_find_symlink_race_stub: exit 0 immediately after printf on the ANCESTOR_RACE_* branch before the exec fallback
