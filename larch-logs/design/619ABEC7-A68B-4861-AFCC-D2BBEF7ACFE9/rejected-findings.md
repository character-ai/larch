### [Plan Review] FINDING_3

### FINDING_3: Child merge publication drops launch identity
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Child mode captures checks or composite stdout with `tee` and replaces `merge.env`, which discards the launch identity seeded before `bgjob start`. Since terminal result publication reads the post-`mv` merge file and checks output does not include the identity fields, completed results lack the identity required for valid rejoin and reuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Refactor child mode like step-8-assessment.sh run_child: read launch identity from seeded merge.env, run checks, then write_merge_kvs that preserves identity KVs plus child NEXT_ACTION output; apply the same pattern in step-6-entry.sh child mode
  - From Cursor-Pragmatic: Pin the step-8 pattern: in BGJOB_CHILD read launch identity from the seeded merge env, then after `tee` re-write identity KVs into the terminal merge envelope via a shared helper (for example `checks_result_identity` merge writer) before `mv`; mirror the same contract in `step-6-entry.sh` and cover it in subprocess tests.
  - From Cursor-Requirements: `implement checks-commit-route`, `checks run-relevant`, and `implement step-6-entry` emit only checks/commit KVs. Child mode tees that stdout into a temp file and then `mv` replaces `merge.env`. Seeding identity before `bgjob start` survives only while the job is live; terminal `bgjob write_result` reads the post-`mv` merge file. Without an explicit union step, completed `*.result.env` rows lack identity, so matching completed rejoin never works and the planned subprocess regressions for identity-valid reuse cannot pass. In both launchers' `--bgjob-child` paths, after the composite `tee` finishes, merge the precomputed launch identity KVs into the temp merge envelope (prepend or helper merge) before promoting it to `merge.env`, and add a structure assertion that child mode cannot promote tee-only output without identity fields.


### [Plan Review] FINDING_4

### FINDING_4: Live rejoin identity lookup precedence is unspecified
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: Live-row identity lookup may read an absent or stale `result.env` before the valid seeded `merge.env`, causing valid live rejoin attempts to fail closed or be misrouted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin merge.env-first, result.env-fallback identity lookup for live rejoin, matching step-8-assessment.sh lines 734-738


