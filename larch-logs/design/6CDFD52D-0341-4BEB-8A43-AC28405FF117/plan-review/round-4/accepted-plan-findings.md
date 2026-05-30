### FINDING_1: Item B harness cannot override hardcoded collector/wait scripts
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: Item B harness text is expected to stub `collect-agent-results.sh` and `wait-for-reviewers.sh`, but `collect-findings.sh` invokes `"$PLUGIN_ROOT/scripts/collect-agent-results.sh"` and `"$PLUGIN_ROOT/scripts/wait-for-reviewers.sh"` with no env override (unlike `review-core.sh`, which honors `REVIEW_CORE_AGGREGATE_FINDINGS_SH`). A PATH-only stub or an in-repo edit of the real scripts may never run; merged `2>&1` capture can false-green while failure-relay lines on stderr stay unsanitized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Spell out a minimal temporary CLAUDE_PLUGIN_ROOT tree (stub scripts plus lib-quiet.sh and redact-secrets.sh siblings) and export it for the new failure-relay cases; mirror the ship-pr harness copy/stub pattern rather than implying PATH-only stubs


### FINDING_2: LARCH_QUIET_DISABLE must not substitute for merged stderr capture
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Plan wording treats `LARCH_QUIET_DISABLE=1` as an alternative to merged `2>&1` for control-byte relay assertions. With quiet disabled, `larch_err` still writes only to stderr (`lib-quiet.sh` diagnostic path); stdout-only `out=$(...)` or `run_core` without `2>&1` can satisfy BEL/ESC greps on stdout while never exercising the sanitized relay on stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Remove the OR wording in Item B harness steps and Failure modes; require merged 2>&1 (or a dedicated stderr capture file) for every new control-byte relay case


### FINDING_3: Proposed ancestor-race find stub must exit after swap branch
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: Proposed `make_find_ancestor_race_stub` omits `exit 0` after the `-type f` swap branch. After `printf` of `ANCESTOR_RACE_PATH`, the wrapper can fall through to `exec` the real `find` (the leaf stub at `make_find_symlink_race_stub` uses `exit 0`), re-enumerating a mutated tree and yielding wrong file lists or a false-green publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Specify the stub heredoc must mirror `make_find_symlink_race_stub`: `exit 0` immediately after `printf` on the `ANCESTOR_RACE_*` branch before the `exec` fallback

**Code context (informational):** Production hardcoding is in `collect-findings.sh` (e.g. lines 208 and 232); `make_find_symlink_race_stub` in `scripts/test-design-log-publish.sh` already ends the race branch with `exit 0` (lines 147–151). `ANCESTOR_RACE` is not present in the tree yet — this finding targets planned stub text.

