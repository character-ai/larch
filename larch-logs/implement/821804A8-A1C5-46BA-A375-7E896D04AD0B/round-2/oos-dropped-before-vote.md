### OOS_1: [OUT_OF_SCOPE] Preflight bundle conflates missing vs unreadable keychain failures
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The review preflight bundle still reports the Cursor keychain entry as missing even when preflight fails on unreadable `-w` access. Operators may delete and recreate the secret instead of fixing keychain ACL on that failure path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Reuse the actual preflight verdict text or split the bundle message into distinct missing versus unreadable cases.

### OOS_2: [OUT_OF_SCOPE] In-process auth failure not detected before transient retry
- **Reviewer(s)**: dyn-dyn-cursor-degraded-calibration-output.txt
- **Severity**: latent
- **Concern**: Work item 3’s “detect in-process auth failure before retry” is not implemented. `_review_run_with_retries` continues to transient-retry Cursor exit-1 / zero-byte failures without checking sidecar auth patterns first, so a first-attempt auth failure can be retried into a later exit-0 canned sentinel (more likely to evade the input-token floor after plan inlining).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-cursor-degraded-calibration-output.txt: Before transient retry on `exit_code != 0` with empty output, scan sidecar/diag for cursor auth patterns (`_AUTH_RE["cursor"]`) and fail closed or mark degraded instead of retrying.

### OOS_3: [OUT_OF_SCOPE] No-work input-token floor applied to all Cursor review slots
- **Reviewer(s)**: dyn-dyn-cursor-degraded-calibration-output.txt
- **Severity**: latent
- **Concern**: `_CURSOR_NO_WORK_INPUT_TOKEN_FLOOR` is applied in `_review_cursor_write_result` for every `launch_review` Cursor slot, not only plan-review. A non-plan-review slot with a legitimately tiny prompt and a real clean sentinel reporting ≤64 input-work tokens can be falsely marked `CURSOR_DEGRADED_RESPONSE`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-cursor-degraded-calibration-output.txt: Gate the no-work floor on plan-review (or another site flag) rather than all review launches.

### OOS_4: [OUT_OF_SCOPE] Inlined plan lacks untrusted-stream escaping (duplicate security observation)
- **Reviewer(s)**: dyn-dyn-cursor-degraded-calibration-output.txt
- **Severity**: important
- **Concern**: Cursor plan-review still inlines raw `plan.txt` inside `<larch_plan_under_review>` without `issue_wire.redact_untrusted_stream` or delimiter escaping used elsewhere for untrusted bodies. Plan text containing `</larch_plan_under_review>` or instruction-like lines can break the bounded block or steer Cursor to emit `{"no_issues_found": true}` without reviewing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-cursor-degraded-calibration-output.txt: Wrap inlined plan content with the same untrusted redaction/escaping path used for issue-wire literals, or choose a delimiter scheme that cannot appear in plan text.
