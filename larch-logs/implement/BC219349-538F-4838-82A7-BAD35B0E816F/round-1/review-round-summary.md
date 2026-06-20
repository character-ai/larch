# Review Round 1

- Mode: `diff`
- 5 accepted, 10 rejected (9 neutral)

## Accepted Findings

### FINDING_2: architecture: skills/shared/orchestrator-never.md:9
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] NEVER #3 adds an implement notification-driven note but still instructs repeating a one-shot foreground sentinel probe on the next recovery turn when the sentinel is absent. For /implement long-running fences the sentinel is always absent, so a literal read of NEVER #3 still implies repeated foreground probes each recovery turn instead of notification-only recovery. Restrict the repeat one-shot probe sentence to /design recovery only; add an explicit /implement clause to end the turn and wait for the next task-notification with no sentinel probe.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: skills/fluff-analysis/scripts/test-fluff-analysis.sh:1174-1288
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan Item 1 acceptance requires malformed JSONL to skip self-review tally fallback with tests in both test-fluff-analysis.sh and test_audit_runs.py; only audit_runs.py has the malformed case. A regression in fluff-analysis.py malformed_jsonl handling could synthesize tally rows from corrupted JSONL and inflate report baselines while make test-fluff-analysis still passes. Add a harness fixture with malformed JSONL plus self-review tally and assert zero committed-self-review-tally records and unchanged baseline counts.
- **Suggested revision**: Address the concern above.


### FINDING_21: **correctness** `python/audit_runs.py:713-715` — The tally fallback gate treats any parsed JSONL dict as non-empty, while `skills/fluff-analysis/scripts/fluff-analysis.py:356-406` only treats rows with a non-empty `outcome` (and not `phase == "retroactive-backfill"`) as real findings. On a self-review run, if `review-findings-full.jsonl` is non-empty but contains only outcome-less or retroactive-backfill lines, `audit_runs` skips `_self_review_tally_rows` and `category-stats` under-reports volume, but fluff-analysis still synthesizes tally rows. That leaves the two consumers inconsistent for the same run. **Suggested fix:** Before the `not rows` check in `scan_run_main`, filter `rows` with the same eligibility rules as fluff-analysis (`outcome` present and `phase != "retroactive-backfill"`), then apply tally fallback when the filtered list is empty and `jsonl_err` is false; add a pytest case mirroring the fluff malformed/empty split for outcome-less JSONL lines.
- **Reviewer**: dyn-self-review-tally-output.txt
- **Concern**: - **correctness** `python/audit_runs.py:713-715` — The tally fallback gate treats any parsed JSONL dict as non-empty, while `skills/fluff-analysis/scripts/fluff-analysis.py:356-406` only treats rows with a non-empty `outcome` (and not `phase == "retroactive-backfill"`) as real findings. On a self-review run, if `review-findings-full.jsonl` is non-empty but contains only outcome-less or retroactive-backfill lines, `audit_runs` skips `_self_review_tally_rows` and `category-stats` under-reports volume, but fluff-analysis still synthesizes tally rows. That leaves the two consumers inconsistent for the same run. **Suggested fix:** Before the `not rows` check in `scan_run_main`, filter `rows` with the same eligibility rules as fluff-analysis (`outcome` present and `phase != "retroactive-backfill"`), then apply tally fallback when the filtered list is empty and `jsonl_err` is false; add a pytest case mirroring the fluff malformed/empty split for outcome-less JSONL lines.
- **Suggested revision**: Address the concern above.


### FINDING_26: **risk-integration** `skills/shared/orchestrator-never.md:9` — NEVER #3 now says `/implement` long-running fences do not use `/design` sentinels and “implement remains notification-driven until real implement terminal sentinels exist,” but the same paragraph still says: “When absent, end the turn without `ps` polling and repeat only that one-shot probe on the next explicit recovery turn.” For `/implement`, those sentinels are always absent, so the repeat-probe instruction conflicts with the notification-driven carve-out and with `skills/implement/SKILL.md:46`. **Suggested fix:** Scope the “repeat only that one-shot probe” clause to `/design` only; for `/implement`, state that premature empty notifications require ending the turn and waiting for the next `<task-notification>` with no foreground sentinel probe.
- **Reviewer**: dyn-recovery-contract-output.txt
- **Concern**: - **risk-integration** `skills/shared/orchestrator-never.md:9` — NEVER #3 now says `/implement` long-running fences do not use `/design` sentinels and “implement remains notification-driven until real implement terminal sentinels exist,” but the same paragraph still says: “When absent, end the turn without `ps` polling and repeat only that one-shot probe on the next explicit recovery turn.” For `/implement`, those sentinels are always absent, so the repeat-probe instruction conflicts with the notification-driven carve-out and with `skills/implement/SKILL.md:46`. **Suggested fix:** Scope the “repeat only that one-shot probe” clause to `/design` only; for `/implement`, state that premature empty notifications require ending the turn and waiting for the next `<task-notification>` with no foreground sentinel probe.
- **Suggested revision**: Address the concern above.


### FINDING_27: **risk-integration** `skills/shared/orchestrator-never.md:11` — NEVER #4 still treats “the foreground terminal-sentinel probe described in NEVER #3” as a cross-skill narrow exception after an early empty notification. `/implement` loads this shared file via `skills/implement/SKILL.md`, so implement orchestrators can read NEVER #4 as permission to use the NEVER #3 probe even though NEVER #3’s implement sentence and implement NEVER #8 forbid that. **Suggested fix:** Limit NEVER #4’s narrow exception to `/design` fences, or add an explicit `/implement` override pointing to notification-only recovery in implement NEVER #8.
- **Reviewer**: dyn-recovery-contract-output.txt
- **Concern**: - **risk-integration** `skills/shared/orchestrator-never.md:11` — NEVER #4 still treats “the foreground terminal-sentinel probe described in NEVER #3” as a cross-skill narrow exception after an early empty notification. `/implement` loads this shared file via `skills/implement/SKILL.md`, so implement orchestrators can read NEVER #4 as permission to use the NEVER #3 probe even though NEVER #3’s implement sentence and implement NEVER #8 forbid that. **Suggested fix:** Limit NEVER #4’s narrow exception to `/design` fences, or add an explicit `/implement` override pointing to notification-only recovery in implement NEVER #8.
- **Suggested revision**: Address the concern above.


