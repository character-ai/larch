### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md
- **Concern**: Testing strategy misstates the issue accrual prerequisite as a single >=50-run heatmap row gate. Scenario: The binding issue blocks work until 2026-07-17 or 50 post-repair accrual runs, whichever comes first. The plan Testing strategy step 1 requires demotion candidates to show reads_observed=0 with transcript_runs_observed>=50 and never states the calendar branch, so a valid post-2026-07-17 demotion with fewer than 50 measured runs would be rejected, or implementers may treat the per-row run count as the only accrual gate.
- **Proposed resolution**: Split the gate in Testing strategy (and Edge cases): first assert accrual is satisfied (date >= 2026-07-17 OR design post-repair transcript coverage >= 50 runs), then separately assert each demotion target shows never-read heatmap evidence (reads_observed=0 with sufficient measured runs on that row).



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/skill-closure-baseline.json
- **Concern**: Plan allows manual baseline surgery though CI requires byte-exact full regeneration. Scenario: test_committed_baseline_matches_fresh_scan compares committed python/skill-closure-baseline.json to write_baseline(scan_all()) output. Step 3 allows manual metric edits; partial JSON edits often pass one-directional growth lint yet fail the byte-exact freshness test.
- **Proposed resolution**: Replace Step 3 manual-update wording with a single required command: make regen-skill-closure-baseline or python3 python/cli.py lint skill-closure-growth --write; treat manual edits as out of scope. ## Findings ### 1. Testing strategy misstates the issue accrual prerequisite (correctness, major) The issue requires accrual of **either** 14 days (2026-07-17) **or** 50 post-repair runs, whichever comes first. The plan’s Testing strategy step 1 only checks `transcript_runs_observed>=50` on demotion rows and never documents the calendar branch. That can block a valid demotion after 2026-07-17 when measured runs are still below 50, or let implementers treat the per-row run count as the sole accrual gate instead of the issue’s OR semantics. **Suggested revision:** In Testing strategy and Edge cases, separate (a) accrual readiness (`date >= 2026-07-17` OR post-repair design transcript coverage `>= 50`) from (b) per-file never-read evidence (`reads_observed=0` on the cited heatmap row). ### 2. Baseline refresh should mandate full regeneration (risk-integration, minor) `test_committed_baseline_matches_fresh_scan` in `python/tests/lint/test_lint_skill_closure_growth.py` requires the committed baseline to match `write_baseline(scan_all())` byte-for-byte. Step 3’s “manually update” path invites partial edits that may pass growth lint but still fail CI. **Suggested revision:** Require `make regen-skill-closure-baseline` or `python3 python/cli.py lint skill-closure-growth --write` as the only baseline update path. --- **Accepted prior fix looks complete:** Round 1 FINDING_1 (update `test_real_design_scan_keeps_plan_review_eager_and_branch_refs_conditional`) is already covered in `### UPDATED: python/tests/lint/test_lint_skill_closure_growth.py`. **No new in-scope gaps** on scanner patterns, degraded-tools Step 0a behavior, or the core SKILL.md demotion approach; `relay_degraded_tools_gate_stdout` in `python/larch/design/design_step0.py` already owns gate relay while the skill keeps the `STEP0_STATUS` branch table.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md
- **Concern**: The plan cites 0/70 heatmap silence but never blocks on post-repair accrual readiness. Scenario: The binding issue requires 2026-07-17 or 50 post-repair runs and says repaired capture had zero accrued runs on 2026-07-03; 0/70 can be pre-repair outage silence, so demotion can ship on invalid evidence and miss acceptance
- **Proposed resolution**: Add an implement-first gate: refuse demotion unless a fresh heatmap shows design reference_capture_status=measured and transcript_runs_observed>=50 (or the calendar prerequisite), and each demotion cites a post-repair row for that file



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/skill-closure-baseline.json
- **Concern**: Testing step 3 still allows manual baseline edits instead of the canonical regen path. Scenario: Partial JSON edits can pass one-way growth lint yet fail test_committed_baseline_matches_fresh_scan in the same pytest module because it requires byte-exact output from lint skill-closure-growth --write
- **Proposed resolution**: Replace step 3 with make regen-skill-closure-baseline (or python3 python/cli.py lint skill-closure-growth --write) and drop the manual-update option



