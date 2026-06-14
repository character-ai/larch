# Review Round 2

- Mode: `diff`
- 4 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_23: **risk-integration** `python/pr_body.py:590-596` — `write_final_report` breaks the canonical tracking-comment contract: it skips upsert for `--comment-only`, uses `larch:run-summary` instead of `larch:final-summary`, and still returns success when the upsert subprocess fails. `scripts/ship-pr.sh:1212-1227` relies on pre-PR failure to stall, and `scripts/ship-pr.sh:1275-1281` relies on `--comment-only` to refresh the live PR URL. **Suggested fix:** Use `<!-- larch:final-summary v1 runid=... -->`, upsert in comment-only mode, and return nonzero on required upsert failures.
- **Reviewer**: codex-generic-output.txt
- **Concern**: - **risk-integration** `python/pr_body.py:590-596` — `write_final_report` breaks the canonical tracking-comment contract: it skips upsert for `--comment-only`, uses `larch:run-summary` instead of `larch:final-summary`, and still returns success when the upsert subprocess fails. `scripts/ship-pr.sh:1212-1227` relies on pre-PR failure to stall, and `scripts/ship-pr.sh:1275-1281` relies on `--comment-only` to refresh the live PR URL. **Suggested fix:** Use `<!-- larch:final-summary v1 runid=... -->`, upsert in comment-only mode, and return nonzero on required upsert failures.
- **Suggested revision**: Address the concern above.


### FINDING_24: **correctness** `python/pr_body.py:587-590` — The Python final-report writer always renders `Cost: N/A` and only writes `$IMPLEMENT_TMPDIR/summary-final.md`. `scripts/ship-pr.sh:1229-1243` then commits the run-log tree without `larch-logs/implement/<RUN_ID>/final-summary.md`, so the PR tip misses the committed final summary. **Suggested fix:** Read token/timing data like the retired helper, render real costs when available, and mirror the body to `larch-logs/implement/<RUN_ID>/final-summary.md` when not `--comment-only`.
- **Reviewer**: codex-generic-output.txt
- **Concern**: - **correctness** `python/pr_body.py:587-590` — The Python final-report writer always renders `Cost: N/A` and only writes `$IMPLEMENT_TMPDIR/summary-final.md`. `scripts/ship-pr.sh:1229-1243` then commits the run-log tree without `larch-logs/implement/<RUN_ID>/final-summary.md`, so the PR tip misses the committed final summary. **Suggested fix:** Read token/timing data like the retired helper, render real costs when available, and mirror the body to `larch-logs/implement/<RUN_ID>/final-summary.md` when not `--comment-only`.
- **Suggested revision**: Address the concern above.


### FINDING_26: **correctness** `python/stall_recovery.py:601-603` — Several live stall-recovery subcommands are stubs. `skills/design/scripts/design-failure-report.sh:106-108` expects `is-larch-dev-clone` to emit `LARCH_DEV_CLONE=true`, and `skills/design/scripts/design-failure-report.sh:133-141` expects `populate-sensitive-corpus` to create the corpus file. **Suggested fix:** Implement these subcommands with the retired helper behavior, including `normalize-file-failure-report-env` and `lint`, instead of returning `STATUS=ok`.
- **Reviewer**: codex-generic-output.txt
- **Concern**: - **correctness** `python/stall_recovery.py:601-603` — Several live stall-recovery subcommands are stubs. `skills/design/scripts/design-failure-report.sh:106-108` expects `is-larch-dev-clone` to emit `LARCH_DEV_CLONE=true`, and `skills/design/scripts/design-failure-report.sh:133-141` expects `populate-sensitive-corpus` to create the corpus file. **Suggested fix:** Implement these subcommands with the retired helper behavior, including `normalize-file-failure-report-env` and `lint`, instead of returning `STATUS=ok`.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: python/finalize.py:864-873
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] --state-file is not loaded into RunContext before finalize phases run scripts/ship-pr.sh postmerge passes only --state-file, so MERGE and BRANCH_NAME default empty/false and cleanup/verify-main are skipped after a real merge Load state-file key/value pairs into the env, merge --implement-tmpdir, and wire --final-bail-reason-file
- **Suggested revision**: Address the concern above.


