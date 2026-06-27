### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:2007-2021
- **Concern**: Design plan-review round-meta will still count rescued neutrals as NEUTRAL_COUNT because md tallies win over classification TSV. Scenario: The plan keeps vote-table Result=neutral and sets classification scope=oos, but plan-review voting-tally.md uses a ## Findings table (plan_review_tally.py:684-700). progress_report._round_counts prefers _parse_tally_md counts whenever that table is non-zero and only falls back to _parse_classification_tsv when md is all zeros. write_design_round_meta (lines 2231-2254) never calls _canonical_decomposition, unlike write_implement_round_meta. A rescued high-severity neutral is written to oos.md and scope=oos in findings-classification.tsv, but round-meta.json tally still records it under NEUTRAL_COUNT, breaking plan-review parity with code-review stdout/env counts and the issue acceptance criterion that rescued items are recorded as OOS
- **Proposed resolution**: Add ### MAY_UPDATE: python/larch/report/progress_report.py: mirror implement in write_design_round_meta by calling _canonical_decomposition(round_dir) and passing canonical (and nit_pruned) into _round_meta_object; extend python/test_plan_review.py neutral-rescue regression to write round-meta and assert tally_canonical has OOS_REJECTED_COUNT=1 and does not count the rescued FINDING under NEUTRAL_COUNT



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:2231-2254
- **Concern**: Plan-review #4882 parity claim is incomplete: design round-meta never gets tally_canonical. Scenario: The plan routes rescued neutrals to scope=oos in findings-classification.tsv and cites #4882 parity without editing progress_report.py. write_implement_round_meta already passes canonical from _canonical_decomposition, but write_design_round_meta does not. voting-tally.md still shows Result=neutral for rescued FINDING_* rows, and _parse_tally_md counts them as in-scope neutrals. Design round-meta.json therefore keeps rescued items in tally.NEUTRAL_COUNT even though classification TSV classifies them as OOS, so /design run summaries and phase-detail counts disagree with the rescued artifacts the plan adds
- **Proposed resolution**: In write_design_round_meta, call _canonical_decomposition(round_dir) and pass canonical (and nit_pruned when present) into _round_meta_object the same way write_implement_round_meta does; add a small python/test_progress_report.py regression with a rescued neutral FINDING_* row (scope=oos, voting_result=neutral) and assert tally_canonical.OOS_REJECTED_COUNT=1 and tally_canonical.NEUTRAL_COUNT excludes it. If you want zero progress_report.py churn, narrow the plan's #4882 parity bullet to code-review/implement only and drop the progress_report alignment claim for plan-review **1. correctness — `python/larch/report/progress_report.py:2231-2254` — Plan-review #4882 parity is incomplete** The plan correctly adds `scope=oos` for rescued neutrals in `findings-classification.tsv` and cites **#4882 parity** while avoiding `progress_report.py` edits. **Implement** already reconciles raw vs canonical counts: `write_implement_round_meta` emits `tally_canonical` from `_canonical_decomposition`. **Design** does not. `write_design_round_meta` writes only the markdown-derived `tally` block. Because the plan keeps vote-table `Result=neutral`, `_parse_tally_md` still counts rescued `FINDING_*` rows as in-scope neutrals. **Breakage:** design `round-meta.json` and `/design` phase-detail headline counts can show rescued high-severity neutrals as `NEUTRAL_COUNT` while `oos.md` and classification TSV say OOS. That contradicts the plan's own parity goal. **Minimum fix:** mirror the implement path in `write_design_round_meta` (a few lines), or narrow the plan's #4882 claim to code-review only if you accept design run-summary drift.



### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_tally.py:697-814; python/larch/review/plan_review_tally.py:697-751; python/larch/report/progress_report.py:1934-2001
- **Concern**: Rescued rows keep `Result=neutral`, so the main markdown tally remains indistinguishable from an ordinary neutral finding.. Scenario: progress_report._parse_tally_md reads `voting-tally.md` before the TSV fallback, and the plan-review/code-review scoreboards key off the same `Result` column. A rescued high-severity `FINDING_*` would still show up as neutral in the live report and tally scoreboard, while only the TSV/KV path says `oos_rejected`.
- **Proposed resolution**: Either emit an OOS-aware `Result` for rescued rows or update the markdown tally consumers to read the rescue marker or scope instead of `Result`.



### FINDING_4:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:17,44-56
- **Concern**: Rescued neutrals are only written as plain `oos.md` blocks with a tally note; the plan never normalizes them into an OOS-shaped block that current downstream consumers parse.. Scenario: The rescued finding can still disappear from `review-findings-full.jsonl` and never reach the existing `/issue` filing path, so the feature remains a scratch-artifact change instead of tracked OOS work.
- **Proposed resolution**: Normalize the rescued block to the existing `### OOS_...` or `[OUT_OF_SCOPE]` shape when writing `oos.md`, or add the bridge to the accepted-OOS sink in the same patch.



### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:8-10,58-110
- **Concern**: [SCOPE-REDUCTION] The plan expands the fix to plan-review parity and a new `test_plan_review.py` case, but the requested feature is code-review neutral rescue only.. Scenario: This doubles the surface area, test cost, and prompt-rubric churn without being required for the feature to ship correctly.
- **Proposed resolution**: Keep this patch code-review only, and split plan-review parity into a separate issue if still wanted.



