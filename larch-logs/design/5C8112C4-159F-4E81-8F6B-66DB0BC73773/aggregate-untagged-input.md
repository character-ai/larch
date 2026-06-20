### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-anti-polling-rule.sh:121-123
- **Concern**: Plan rewrites implement NEVER #8 away from foreground terminal-sentinel probing but omits the anti-polling harness that hard-pins that prose in skills/implement/SKILL.md. Scenario: Removing or rewording the pinned substring breaks make test-implement-anti-polling-rule (test-harnesses-5) and therefore make lint
- **Proposed resolution**: Add ### UPDATED: scripts/test-implement-anti-polling-rule.sh (and sibling .md if needed) to replace the implement SKILL assertion with notification-driven recovery pins and an explicit ban on design-only sentinel probes during /implement

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py:337-339
- **Concern**: Self-review tally fallback never runs when JSONL path is absent. Scenario: `_extract_one_implement_run` returns immediately on `not os.path.exists(jf)` before any tally read. Older or partial implement runs can have `code-review-tally.json` with `mode: self-review` but no `review-findings-full.jsonl`; Item 1 under-count persists for those runs.
- **Proposed resolution**: Invoke the planned tally helper before the missing-file return (or fold missing-file into the helper) so absent JSONL still synthesizes records when tally mode is `self-review`.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-anti-polling-rule.sh:121-123
- **Concern**: Item 6 edits remove /implement foreground sentinel-probe wording but the plan omits the anti-polling harness that pins that literal. Scenario: `make lint` runs `test-implement-anti-polling-rule` (test-harnesses-5) and requires `skills/implement/SKILL.md` to contain `only sanctioned exception to the Bash polling-loop ban is one foreground, non-sleeping terminal-sentinel probe`; deleting it without updating the harness fails CI
- **Proposed resolution**: Add `### UPDATED: scripts/test-implement-anti-polling-rule.sh` (and sync `scripts/test-implement-anti-polling-rule.md` if needed): replace the implement pin with notification-only recovery text and keep design/orchestrator-never design-probe pins unchanged

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/audit_runs.py:803-812
- **Concern**: Absent-jsonl category-stats branch not specified in plan file section. Scenario: Plan injects synthetic self-review rows into `rows` before the scan loop, but the post-loop `category-stats` path still keys only on `review-findings-full.jsonl` being a file; when the JSONL is absent and only `code-review-tally.json` exists, it still emits `partial_data` / `missing_review_findings_jsonl` with zero counts even though tests require tally-backed stats
- **Proposed resolution**: In `### UPDATED: python/audit_runs.py`, state explicitly that when JSONL is missing or empty and self-review tally fallback populates `rows`, the `category-stats` writer must use those rows (same branch as the non-malformed file-present path) instead of the missing-jsonl partial_data shortcut

### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: AGENTS.md:86; scripts/test-implement-anti-polling-rule.sh:121-123
- **Concern**: The plan changes /implement recovery guidance but omits the root contract and lint guard that still pin the old foreground design-sentinel probe. Scenario: After skills/implement/SKILL.md removes the old literal, make lint fails via test-implement-anti-polling-rule; if AGENTS.md is left unchanged, operators still get told to probe design-only sentinels for implement recovery
- **Proposed resolution**: Add UPDATED entries for AGENTS.md and scripts/test-implement-anti-polling-rule.sh; scope AGENTS.md to the design-only carve-out or the new implement no-probe rule, and update the harness assertion to pin the notification-driven implement contract
