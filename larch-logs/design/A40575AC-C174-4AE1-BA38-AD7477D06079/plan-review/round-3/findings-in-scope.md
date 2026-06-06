Verifying the cited code paths so merged findings accurately reflect the behavioral risks.
### FINDING_1: emit-tally OOS_ACCEPTED_COUNT skip guard must cover serialize and truncate branches
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-oos-env-handoff
- **Severity**: important
- **Concern**: The planned `OOS_ACCEPTED_COUNT > 0` skip guard must wrap both the `oos-serialize.sh` branch and the missing-`oos.md` truncate branch in `emit-tally.sh` (~153–159). If the guard sits only inside the `-f "$OOS_FILE"` branch, the `else : > "$OOS_ACCEPTED_FILE"` path can still wipe tally-written accepted OOS when `oos.md` is absent. After tally writes normalized accepted OOS under `SESSION_ENV_PATH`, a missing or removed `oos.md` lets `emit-tally` hit `:>` and clear `review-tmpdir` content; downstream `copy_to_parent` can then overwrite the parent copy tally already wrote.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Structure as a top-level `if count > 0; then : preserve; elif -f oos.md; then serialize; else truncate` so both post-tally branches honor the skip contract
  - From Cursor-dyn-oos-env-handoff: Restructure the OOS block so count>0 skips both serialize and truncate (no-op preserve); run serialize-or-truncate only when count==0

### FINDING_2: coder-skipped OOS append bypasses tally header normalization
- **Reviewer(s)**: Cursor-dyn-unscoped-oos-consumers
- **Severity**: important
- **Concern**: The `accumulated-oos.md` coder-skipped append path in `review-and-fix.sh` (~1474–1479) bypasses tally normalization. When the coder routes `SKIPPED` findings, bare `### FINDING_N:` blocks are copied into `accumulated-oos.md` / `oos-accepted-review.md` (test fixture at `test-review-and-fix.sh:1450–1451`). Planned reader hardening only counts `FINDING` headers with `[OUT_OF_SCOPE]` (`oos-non-security-block-count.awk:7–12`, `python/oos.py:32`). Bare `FINDING` blocks in the dedicated OOS sink are invisible to `oos-disposition-checkpoint.sh:166–173` and `parse-input.sh:377`, so the disposition gate can pass while skipped OOS items that must be filed are never counted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-unscoped-oos-consumers: Normalize headers when appending skipped_file to accumulated-oos (reuse the tally normalize helper or monotonic `### OOS_<seq>:` rewrite); minimum one-line note in plan if intentionally deferred
