### OOS_1: [OUT_OF_SCOPE] Tier A dedup marker moved into `_compose_tier_a_issue` after title heading
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `compose_report` no longer prepends `_report_marker(...)`; it passes `dedup_marker=` into `_compose_tier_a_issue` (`python/stall_recovery.py:1051-1063`). `_compose_tier_a_issue` inserts the marker immediately after `### {title}` (`python/stall_recovery.py:2091-2095`). Regression test asserts line order, marker content, and `parse_issue_input` body preservation (`python/test_stall_recovery.py:1637-1666`). `parse_issue_input` only captures body content after the first `###` heading (`PLAIN_HEADING_RE` in `python/issue_create.py:27,211-223`); content before that heading is discarded. Putting the marker on line 2 puts it in `items[0].body`, so filed GitHub issue bodies retain `<!-- larch-stall:signature=... -->` for post-filing dedup. The dedup pre-pass (`file-failure-report-cross-repo.sh` `extract_marker`) also still works because it greps the full artifact file.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] `marker` Path and dedup infrastructure remain distinct and unchanged
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Existing `marker: Path` (record-failure marker file) is unchanged and not confused with `dedup_marker`. `_report_dedup_signature`, `_report_marker`, Tier B `chat-print`, and dedup lookup logic are unchanged.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Missing `escalation-success` parity test for marker placement
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `python/test_stall_recovery.py:1637-1666` — The new regression covers `terminal-failure` only. `escalation-success` uses the same `issue-input` branch in `compose_report`, so marker placement should be identical, but a second report-kind assertion would lock that in.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a compact `escalation-success` variant of the test (or parametrize over `report_kind`) if you want explicit parity coverage.

### OOS_4: [OUT_OF_SCOPE] Pre-fix filed issues lack body markers for dedup
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/file-failure-report-cross-repo.sh:53-75` — Dedup matches the marker against **filed** GitHub issue bodies, not the pre-parse artifact. Issues filed before this fix (e.g. #5499 before manual repair) still lack the marker in their bodies, so identical future reports will not dedup against them and may file anew.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Operational backfill of markers on affected open issues, or accept gradual natural dedup only for post-fix filings.

### OOS_5: [OUT_OF_SCOPE] `_compose_tier_a_issue` join drops intentional blank lines
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `python/stall_recovery.py:2118` — `_compose_tier_a_issue` still uses `"\n".join(part for part in body if part)`, which drops intentional blank lines (including the one between marker and `## Report metadata` noted in the plan). This predates the diff and does not break dedup or parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Only if formatting matters, use a join that preserves empty strings or insert explicit `\n\n` separators.

