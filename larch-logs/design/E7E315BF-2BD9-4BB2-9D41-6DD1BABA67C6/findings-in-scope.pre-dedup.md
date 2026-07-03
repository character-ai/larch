### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty_calibration.py
- **Concern**: The gc-slimmed JSONL fallback contract is incomplete for implement and review runs.. Scenario: The plan names only run-root review-findings-full.jsonl. Committed layout prefers implement round-*/review-findings-full.jsonl before the run root (docs/run-logs.md, fluff-analysis.py), and standalone review uses review-findings.ndjson before review-findings-full.jsonl (_ground_truth.py, rejected_analysis.py). JSONL rows also use id/outcome/scope, not finding_id/voting_result. A single root-only reader can undercount accepted findings or mark realized tier unknown on otherwise recoverable review runs.
- **Proposed resolution**: Pin per-skill fallback order: implement round-local then run-root JSONL; review ndjson then JSONL; design stays TSV-only. Map id to finding_id, outcome accepted to voting_result accepted, and apply the same in-scope rules as the TSV path (classification_row_is_oos inverted plus OOS_ prefix). Add fixtures for review ndjson-only and implement round-local JSONL-only recovery.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty_calibration.py
- **Concern**: Latest-round precedence needs explicit numeric round ordering.. Scenario: The plan says latest round wins on conflicting finding_id rows but does not define round ordering. Sorted glob paths like round-10 before round-2, or review-findings-classification-round-10.tsv before round-9.tsv, can let an older round override a newer one and change deduped accepted counts and realized tiers.
- **Proposed resolution**: Extract round numbers as integers from round-N directories and review-findings-classification-round-N.tsv filenames; sort numerically; apply last-wins only after numeric ordering. Add a test where round-2 rejects a finding accepted in round-10 and round-10 wins.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/calibration/difficulty_calibration.py
- **Concern**: Audit peer matching and monthly drift lack a pinned timestamp source.. Scenario: Section 6 requires peers in the same calendar month when timestamps exist, and section 8 groups by month, but the plan never names the field (manifest started_at, final-summary time, token-report time, etc.). Different choices yield different peer sets and drift tables across runs.
- **Proposed resolution**: Pin one committed timestamp per run (prefer manifest started_at, else final-summary started_at if present) for audit peer month and tier-drift bucketing; render n/a when absent. Document the field in docs/skills.md and test one audited/unaudited pair with explicit month boundaries.



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:44
- **Concern**: Audit peer matching names pre-audit `applied_tier`, but committed `difficulty-rating.json` overwrites `applied_tier` after an audit upgrade.. Scenario: An audited MODERATE run upgraded to HARD matches HARD peers, or no peers, so audit deltas are wrong or unverifiable from committed logs.
- **Proposed resolution**: Define a committed-log-only pre-audit tier derivation for matching, such as tiering from `design_tier` / `implement_tier` / `predicted_tier` plus `floors_applied`, and mark rows `n/a` when it cannot be recovered.



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:19
- **Concern**: The JSONL fallback does not require filtering by review phase before counting accepted findings.. Scenario: `review-findings-full.jsonl` can contain multiple phases; a gc-slimmed implement run could count accepted plan-review rows as code-review findings and inflate realized difficulty.
- **Proposed resolution**: Specify that JSONL fallback counts only the phase for the analyzed skill: `code-review` for implement and standalone review, `plan-review` for design, with `outcome=accepted` and OOS outcomes excluded.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty_calibration.py
- **Concern**: Pin one in-scope classifier; drop the progress_report OR branch.. Scenario: FINDING_3 fixed loose not-OOS checks, but the plan still allows `classification_row_is_oos` inverted OR `progress_report._classification_row_in_scope`. Those disagree on empty/missing `scope` cells: voting treats empty as in-scope; progress_report requires literal `in_scope`. Mixed choice skews accepted counts and realized tiers.
- **Proposed resolution**: Use `voting.classification_row_is_oos` inverted only (same as `issue/_ground_truth.py`), plus `finding_id` `OOS_` exclusion; remove the progress_report alternative.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty_calibration.py
- **Concern**: JSONL fallback paths and acceptance rules are incomplete versus committed contracts.. Scenario: The plan only names run-root `review-findings-full.jsonl`. `rejected_analysis._implement_jsonl_records` prefers `round-*/review-findings-full.jsonl` before run-root; `_review_jsonl_records` prefers `review-findings.ndjson`. GC-slimmed implement dirs keep run-root JSONL but not TSVs; without path precedence and explicit `outcome==accepted` plus OOS/id filters, fallback can miss findings or count rejected/neutral rows.
- **Proposed resolution**: Mirror per-skill JSONL precedence from `python/larch/issue/rejected_analysis.py`; define fallback accepted set as deduped ids with `outcome==accepted`, excluding `classification_row_is_oos`/`OOS_` rows; add a fixture with TSV absent and JSONL-only accepted rows.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty_calibration.py
- **Concern**: Latest-round-wins dedupe lacks a pinned round ordering key.. Scenario: Conflicts for the same `finding_id` across `round-*/`, `plan-review/round-*/`, and `review-findings-classification-round-*.tsv` need numeric ordering. Ad hoc path sorting can pick the wrong row and change deduped accepted counts.
- **Proposed resolution**: Reuse `issue/_ground_truth._ground_truth_round_num` (or equivalent) for every classification artifact path; on ties prefer the row from the higher round number.



### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty_calibration.py
- **Concern**: Audit peer month matching does not pin the timestamp source.. Scenario: FINDING_5 added peer matching, but same calendar month is undefined when runs have `manifest.started_at`, token-report timestamps, and sidecar `triaged_at`. Different picks change peer sets and audit deltas.
- **Proposed resolution**: Pin month bucketing to `manifest.started_at` UTC when present, else exclude the run from audit-delta pairing; document the rule in `docs/skills.md`.



### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/calibration/test_difficulty_calibration.py
- **Concern**: GC-slimmed implement JSONL-only realized-tier coverage is missing.. Scenario: Approach requires JSONL fallback when TSVs are absent; implement GC keep-set retains `review-findings-full.jsonl`. Tests cover missing classification as `unknown` and gc-slimmed rating rows, but not JSONL-only accepted counting into TRIVIAL/MODERATE/HARD.
- **Proposed resolution**: A fixture with only keep-set files plus JSONL (`outcome=accepted`, no TSV) should assert a non-unknown realized tier and matrix eligibility, not merely that a rating row renders.



### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:18; python/larch/review/review_collect.py:275-279; python/larch/review/review_tally.py:848-856
- **Concern**: Prior dedupe fix is incomplete: the plan dedupes accepted findings across all rounds by bare finding_id even though code-review producers restart FINDING_N numbering each round.. Scenario: Round 1 accepts FINDING_1 and round 2 accepts a different FINDING_1; latest-round-wins leaves one accepted finding, so a run with three accepted items across rounds can realize MODERATE instead of HARD.
- **Proposed resolution**: Namespace accepted-finding identities by source path or round for round-local code-review TSVs; only collapse cross-round rows when a stable cross-round identity exists.



### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:19; python/larch/review/batch_report.py:163-185; python/larch/review/compose_review.py:192-200
- **Concern**: The review-findings-full.jsonl fallback lacks the phase filter needed to match the TSV source it replaces.. Scenario: Implement fallback can read a mixed JSONL containing plan-review and code-review records; counting all accepted rows can inflate implement realized difficulty from design findings.
- **Proposed resolution**: When using review-findings-full.jsonl fallback, filter records to the skill-owned phase before counting: code-review for implement and review, plan-review only for design sources that actually have that fallback.



### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:44; python/larch/calibration/difficulty.py:413-452
- **Concern**: The audit peer contract says to match on pre-audit applied_tier, but the committed record overwrites applied_tier with the audited panel tier.. Scenario: An audit-upgraded MODERATE run is stored with applied_tier HARD; matching it against HARD peers corrupts the required audited-vs-unaudited delta.
- **Proposed resolution**: Define a committed-field derivation for the pre-audit tier, such as predicted_tier plus floors_applied when recoverable, and render n/a when it cannot be recovered instead of matching on post-audit applied_tier.



### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty_calibration.py
- **Concern**: The plan allows two incompatible in-scope predicates (`not classification_row_is_oos` OR `progress_report._classification_row_in_scope`).. Scenario: When a TSV has a `scope` column but an empty cell, inverted `classification_row_is_oos` treats the row as in-scope while `_classification_row_in_scope` excludes it. Picking the wrong helper changes accepted counts and can flip MODERATE/HARD realized tiers.
- **Proposed resolution**: Pin one rule: `voting_result==accepted` and `not classification_row_is_oos(row, header=header)`; also reject `finding_id` starting with `OOS_`. Drop the OR with `_classification_row_in_scope`.



### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty_calibration.py
- **Concern**: Latest-round precedence for duplicate `finding_id` rows is underspecified.. Scenario: The text can be read as “union accepted rows across rounds, then dedupe,” which keeps a finding accepted if an earlier round accepted it even when a later round rejected it. That overcounts accepted findings and inflates realized tiers.
- **Proposed resolution**: Define the algorithm explicitly: group by `finding_id`, keep the row from the highest numeric round (not lexicographic path order), then count only if that surviving row is in-scope and `voting_result==accepted`. Add a fixture where round 2 rejects a finding accepted in round 1.



### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty_calibration.py
- **Concern**: Round ordering for “latest round wins” is not pinned to numeric comparison.. Scenario: Sorted glob order treats `round-10` before `round-2`. A finding updated in round 10 can lose to round 2, corrupting dedupe and under-rating annotations joined by `round_num`.
- **Proposed resolution**: Parse round numbers with the same numeric helper pattern as `python/larch/issue/_ground_truth.py::_ground_truth_round_num` (or reuse it) before choosing the winning row.



### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/compose_review.py:192-205
- **Concern**: The `review-findings-full.jsonl` gc-slimmed fallback lacks a field contract.. Scenario: Without explicit filters on `outcome`, `id`, and `round_num`, an implementer may count rejected/OOS JSONL records or use the wrong identifier, making gc-slimmed runs look TRIVIAL/MODERATE instead of `unknown` or mis-tiered HARD.
- **Proposed resolution**: Document and implement fallback as: keep rows with `outcome=="accepted"` and `phase` matching the skill; exclude `out_of_scope`; dedupe on `id` with numeric `round_num` precedence matching the TSV path.



### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:18,83-89
- **Concern**: Latest-round conflict precedence is specified but not verified. Scenario: The planned duplicate test only covers accepted plus accepted. An implementation that unions accepted finding_ids across rounds would pass, but a later rejected or exonerated row for the same finding_id would still be counted and could inflate realized tier.
- **Proposed resolution**: Add one synthetic fixture where the same finding_id is accepted in an earlier round and rejected or exonerated later. Assert the latest row wins and the accepted count excludes it.



### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty_calibration.py
- **Concern**: The JSONL classification fallback contract is too thin for implement gc-slimmed runs.. Scenario: The plan only names run-root review-findings-full.jsonl. Implement GC keep-set retains that file but drops round TSVs. Without round-local-first reads, accepted/in-scope field rules (outcome, id, scope/OOS_), and latest-round dedupe by round_num, accepted counts can be wrong or TRIVIAL/MODERATE tiers can be miscomputed.
- **Proposed resolution**: Specify fallback parity with rejected_analysis._implement_jsonl_records: prefer round-*/review-findings-full.jsonl then run-root; count outcome=accepted rows that are in-scope; dedupe finding_id with latest round winning. For review, also accept review-findings.ndjson when TSVs are absent. Add a pytest fixture for gc-slimmed implement dirs where only keep-set files remain and assert accepted-count-driven realized tier.



### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-readability-preamble.tsv
- **Concern**: Register the new skill in the readability-preamble lint manifest.. Scenario: The plan adds skills/difficulty-calibration/SKILL.md with a mandatory readability preamble but does not update scripts/lint-readability-preamble.tsv. make lint-readability-preamble fails on the new SKILL.md and blocks make lint.
- **Proposed resolution**: Add skills/difficulty-calibration/SKILL.md with variant orchestrator-inline expected_count 1, and bump the __metadata__ expected_count to match the new row total (currently 42).



### FINDING_21:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:19,29-35
- **Concern**: No-classification fallback conflicts with escalation-based HARD formula. Scenario: A gc-slimmed run can retain difficulty-rating.json with non-empty escalations but no classification TSV or JSONL fallback. The plan would mark realized tier unknown and exclude it from matrices, even though the stated formula requires HARD from committed escalation evidence.
- **Proposed resolution**: Derive HARD from committed escalation/substantiality evidence before requiring a classification source. Only non-escalated runs without parseable classification should have unknown accepted count and realized tier.



