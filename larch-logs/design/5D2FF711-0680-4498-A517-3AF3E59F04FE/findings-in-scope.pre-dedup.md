### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:125-180
- **Concern**: Legacy round-meta lacks explicit OOS_ACCEPTED_COUNT semantics migration in _phase_round_from_meta. Scenario: Pre-change round-meta.json stores vote-accepted OOS in tally.OOS_ACCEPTED_COUNT. If _phase_round_from_meta treats that key as fileable whenever round_dir/review-tally.env is absent (typical for design plan-review rounds), archived runs with accepted-minor OOS overstate the OOS fileable column and can mis-sum oos_total when tally_canonical is present.
- **Proposed resolution**: Add an explicit legacy branch: when OOS_PROPOSED_COUNT is missing, treat tally.OOS_ACCEPTED_COUNT as proposed only and derive fileable from review-tally.env when present else per-row oos_fileable_from_votes on classification (or markdown-safe fallback); never reinterpret legacy OOS_ACCEPTED_COUNT as fileable without that guard.



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: security
- **Location**: python/larch/report/progress_report.py:1594-1623
- **Concern**: Security OOS filtering lacks the production design artifact lookup. Scenario: Plan requires security-tagged OOS to stay out of OOS proposed and OOS fileable, but design tally routes security OOS to $DESIGN_TMPDIR/security-oos-observations.md while round-meta writes run from plan-review/round-N. The current lookup only searches files inside round_dir, so a classification TSV row for an accepted security OOS can still be counted when no round-local public block exists.
- **Proposed resolution**: Extend the progress-report OOS security lookup used for classification and markdown rows to search production design sources, including round_dir.parent.parent/security-oos-observations.md and root findings-oos.md or ballot sources, before counting proposed/fileable; add a production-shaped design round test.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:1788-1806,1872-1885
- **Concern**: `write_implement_round_meta` still feeds vote-accepted OOS from `_canonical_decomposition` into `tally_canonical.OOS_ACCEPTED_COUNT`. Scenario: The plan makes `tally.OOS_ACCEPTED_COUNT` fileable-only and adds `OOS_PROPOSED_COUNT`, but `write_implement_round_meta` still passes the unchanged `_canonical_decomposition()` tuple into `_round_meta_object(..., canonical=canonical)`. That tuple’s OOS slot is vote-accepted. After the change, `tally` and `tally_canonical` can disagree on OOS columns whenever an accepted-`minor` OOS exists, breaking the footnote claim that both views reconcile and confusing any reader that uses `tally_canonical` alone.
- **Proposed resolution**: In the `write_implement_round_meta` / `_canonical_decomposition` path, persist vote-accepted OOS as `OOS_PROPOSED_COUNT` and fileable-only OOS as `OOS_ACCEPTED_COUNT` inside `tally_canonical` too (via `oos_fileable_from_votes` / `review-tally.env`, with the same security exclusion). Extend `test_write_implement_round_meta_records_canonical_decomposition` with an accepted-`minor` OOS row asserting `tally_canonical.OOS_PROPOSED_COUNT=1` and `tally_canonical.OOS_ACCEPTED_COUNT=0`.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:1788-1800
- **Concern**: [FINDING_3 incomplete] `tally_canonical` still derives OOS accepted from vote-accepted classification rows. Scenario: `write_implement_round_meta` calls `_canonical_decomposition` → `_parse_classification_tsv`, which counts every `voting_result=accepted` OOS row into the sixth tuple slot; `_round_meta_object` writes that slot to `tally_canonical.OOS_ACCEPTED_COUNT`. After the split, accepted-minor OOS still lands in canonical as fileable, and `_phase_round_from_meta` footnote `oos_total` still sums `canonical.OOS_ACCEPTED_COUNT + OOS_REJECTED_COUNT` (line 167) unless both the writer and reader are updated together.
- **Proposed resolution**: Explicitly update `_canonical_decomposition` (or post-process its output) so canonical OOS accepted is fileable-only via `voting.oos_fileable_from_votes(...)`, add `OOS_PROPOSED_COUNT` to `tally_canonical`, and wire `_phase_round_from_meta` `oos_total` to `OOS_PROPOSED_COUNT + OOS_REJECTED_COUNT` from the same source. Extend `test_write_implement_round_meta_records_canonical_decomposition` with an accepted-minor OOS row.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:1872-1888
- **Concern**: Implement round-meta persistence lacks the design security-OOS exclusion the plan requires. Scenario: `write_design_round_meta` runs `_adjust_design_security_oos` before persisting counts; `write_implement_round_meta` does not. The plan edge case requires security-tagged OOS in neither proposed nor fileable columns, but implement `/review` rounds can record accepted security OOS in classification/markdown. Without the same exclusion in the implement meta writer, `OOS_PROPOSED_COUNT` can include security items and the phase table overstates proposed OOS.
- **Proposed resolution**: Apply the same security skip/decrement in `write_implement_round_meta` (shared helper used by both writers, or call `_adjust_design_security_oos` on the proposed bucket before persisting). Add an implement-side regression mirroring `test_write_design_round_meta_security_oos_and_panel`.



### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:157-167
- **Concern**: Decomposition footnote `oos_total` must stay canonical-aware when raw `tally` and `tally_canonical` diverge. Scenario: The plan tells `_phase_round_from_meta` to derive `oos_total` from `OOS_PROPOSED_COUNT + OOS_REJECTED_COUNT` instead of a fileable-only count. Issue #4882 keeps scope-aware OOS in `tally_canonical` while raw `tally` can show `OOS_REJECTED_COUNT=0` (see `test_render_phase_detail_shows_canonical_decomposition_footnote`). Switching `oos_total` to raw `tally` buckets would show `0 out-of-scope` in the footnote while the table still shows 18 suggestions.
- **Proposed resolution**: When `tally_canonical` exists, compute `oos_total` from canonical OOS buckets using proposed semantics (`OOS_PROPOSED_COUNT`, else legacy vote-accepted `OOS_ACCEPTED_COUNT`) plus `OOS_REJECTED_COUNT`; use raw `tally` only when canonical is absent. Do not store fileable-only counts into `tally_canonical.OOS_ACCEPTED_COUNT` without a proposed field. Extend the plan testing strategy with an explicit regression for `test_render_phase_detail_shows_canonical_decomposition_footnote`.



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:1610-1635
- **Concern**: Security OOS adjustment must target the proposed bucket after the split. Scenario: `_adjust_design_security_oos` only decrements the single `oos_accepted` slot on accepted security rows. After `OOS_PROPOSED_COUNT` is split from fileable-only `OOS_ACCEPTED_COUNT`, a vote-accepted security OOS can still appear in the `OOS proposed` column if proposed is derived from classification before or without this decrement.
- **Proposed resolution**: Vote-accepted security OOS leaks into operator-facing `OOS proposed` despite the edge-case requirement to exclude security-tagged OOS from both columns. Extend `_adjust_design_security_oos` (or the new proposed/fileable derivation) so accepted security rows decrement `OOS_PROPOSED_COUNT` / proposed render counts as well as fileable counts; add a design meta test with accepted security OOS asserting both proposed and fileable stay zero.



