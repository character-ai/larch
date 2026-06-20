### FINDING_1: Item 6 plan omits lint harness and root-contract updates for implement sentinel-probe rewrite
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Generic
- **Severity**: blocking
- **Concern**: The plan rewrites `/implement` NEVER #8 away from foreground terminal-sentinel probing but does not update `scripts/test-implement-anti-polling-rule.sh` (lines 121–123), which hard-pins the literal `only sanctioned exception to the Bash polling-loop ban is one foreground, non-sleeping terminal-sentinel probe` in `skills/implement/SKILL.md`. `make lint` runs that harness via `test-harnesses-5` (`test-implement-anti-polling-rule`), so removing or rewording the pinned substring without updating the harness breaks CI. `AGENTS.md` (line 86) still documents design-only foreground sentinel probes as the sanctioned recovery path for implement-style premature notifications; if left unchanged while implement guidance moves to notification-only recovery, operators get contradictory operator-facing contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: scripts/test-implement-anti-polling-rule.sh (and sibling .md if needed) to replace the implement SKILL assertion with notification-driven recovery pins and an explicit ban on design-only sentinel probes during /implement
  - From Cursor-Pragmatic: Add `### UPDATED: scripts/test-implement-anti-polling-rule.sh` (and sync `scripts/test-implement-anti-polling-rule.md` if needed): replace the implement pin with notification-only recovery text and keep design/orchestrator-never design-probe pins unchanged
  - From Codex-Generic: Add UPDATED entries for AGENTS.md and scripts/test-implement-anti-polling-rule.sh; scope AGENTS.md to the design-only carve-out or the new implement no-probe rule, and update the harness assertion to pin the notification-driven implement contract

### FINDING_2: Self-review tally fallback skipped when JSONL file is absent in fluff-analysis
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: In `skills/fluff-analysis/scripts/fluff-analysis.py`, `_extract_one_implement_run` returns immediately on `not os.path.exists(jf)` (lines 337–339) before any tally read. Older or partial implement runs can have `code-review-tally.json` with `mode: self-review` but no `review-findings-full.jsonl`; Item 1 under-count persists for those runs because the planned tally helper never runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Invoke the planned tally helper before the missing-file return (or fold missing-file into the helper) so absent JSONL still synthesizes records when tally mode is `self-review`.

### FINDING_3: audit_runs category-stats ignores tally-backed rows when JSONL is absent
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan injects synthetic self-review rows into `rows` before the scan loop in `python/audit_runs.py`, but the post-loop `category-stats` path (lines 803–812) still keys only on `review-findings-full.jsonl` being a file. When JSONL is absent and only `code-review-tally.json` exists, the writer still emits `partial_data` / `missing_review_findings_jsonl` with zero counts even though tests require tally-backed stats from populated `rows`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In `### UPDATED: python/audit_runs.py`, state explicitly that when JSONL is missing or empty and self-review tally fallback populates `rows`, the `category-stats` writer must use those rows (same branch as the non-malformed file-present path) instead of the missing-jsonl partial_data shortcut
