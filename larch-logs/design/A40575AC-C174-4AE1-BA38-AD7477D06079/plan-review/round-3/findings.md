### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/review/scripts/emit-tally.sh:153-159
- **Concern**: OOS_ACCEPTED_COUNT skip guard must wrap both the oos-serialize branch and the missing-oos.md truncate branch. Scenario: Plan text says do not truncate when count > 0 but only locates the change before oos-serialize (~153-159); if the guard sits only inside the `-f "$OOS_FILE"` branch, the `else : > "$OOS_ACCEPTED_FILE"` path can still wipe tally-written accepted OOS when oos.md is absent
- **Proposed resolution**: Structure as a top-level `if count > 0; then : preserve; elif -f oos.md; then serialize; else truncate` so both post-tally branches honor the skip contract

### FINDING_2:
- **Reviewer(s)**: Cursor-dyn-oos-env-handoff
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/emit-tally.sh:153-159
- **Concern**: Plan only guards oos-serialize.sh when OOS_ACCEPTED_COUNT>0; the existing else branch still truncates oos-accepted-review.md when oos.md is missing. Scenario: After tally writes normalized accepted OOS under SESSION_ENV_PATH, a missing/removed oos.md lets emit-tally hit :> and wipe review-tmpdir content; copy_to_parent then overwrites the parent copy tally already wrote
- **Proposed resolution**: Restructure the OOS block so count>0 skips both serialize and truncate (no-op preserve); run serialize-or-truncate only when count==0

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-unscoped-oos-consumers
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1474-1479
- **Concern**: accumulated-oos.md coder-skipped append bypasses tally normalization. Scenario: Coder SKIPPED routing copies bare ### FINDING_N: blocks into accumulated-oos.md / oos-accepted-review.md (test fixture at test-review-and-fix.sh:1450-1451). Planned reader hardening only counts FINDING headers with [OUT_OF_SCOPE] (oos-non-security-block-count.awk:7-12, python/oos.py:32). Bare FINDING blocks in the dedicated OOS sink are invisible to oos-disposition-checkpoint.sh:166-173 and parse-input.sh:377 — disposition gate can pass while skipped OOS never must be filed
- **Proposed resolution**: Normalize headers when appending skipped_file to accumulated-oos (reuse the tally normalize helper or monotonic ### OOS_<seq>: rewrite); minimum one-line note in plan if intentionally deferred

### OOS_1:
- **Description**: Reader hardening (awk + python + gate doc + three test harnesses) is a third layer beyond the two production breakpoints (#3550). Scenario: Producer normalization plus emit-tally skip already canonicalize accepted output and stop the overwrite chain; layer 3 adds six-file touch surface without changing the review-core tally→emit path
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/oos.py:32-33; skills/implement/scripts/oos-non-security-block-count.awk:7-11
- **Phase**: design
