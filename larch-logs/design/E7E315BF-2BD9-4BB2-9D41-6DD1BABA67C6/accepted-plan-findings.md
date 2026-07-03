### FINDING_1: Classification fallback needs a full per-skill contract
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The classification fallback contract is underspecified for gc-slimmed runs: implement, review, and design need different source precedence and row semantics, plus one consistent accepted/in-scope/phase/OOS filter, or the analyzer can miss accepted findings and mis-tier realized difficulty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin per-skill fallback order: implement round-local then run-root JSONL; review ndjson then JSONL; design stays TSV-only. Map id to finding_id, outcome accepted to voting_result accepted, and apply the same in-scope rules as the TSV path (classification_row_is_oos inverted plus OOS_ prefix). Add fixtures for review ndjson-only and implement round-local JSONL-only recovery.
  - From Codex-Arch: Specify that JSONL fallback counts only the phase for the analyzed skill: `code-review` for implement and standalone review, `plan-review` for design, with `outcome=accepted` and OOS outcomes excluded.
  - From Cursor-Innovation: Use `voting.classification_row_is_oos` inverted only (same as `issue/_ground_truth.py`), plus `finding_id` `OOS_` exclusion; remove the progress_report alternative.
  - From Cursor-Innovation: Mirror per-skill JSONL precedence from `python/larch/issue/rejected_analysis.py`; define fallback accepted set as deduped ids with `outcome==accepted`, excluding `classification_row_is_oos`/`OOS_` rows; add a fixture with TSV absent and JSONL-only accepted rows.
  - From Cursor-Innovation: A fixture with only keep-set files plus JSONL (`outcome=accepted`, no TSV) should assert a non-unknown realized tier and matrix eligibility, not merely that a rating row renders.
  - From Codex-Innovation: When using review-findings-full.jsonl fallback, filter records to the skill-owned phase before counting: code-review for implement and review, plan-review only for design sources that actually have that fallback.
  - From Cursor-Pragmatic: Pin one rule: `voting_result==accepted` and `not classification_row_is_oos(row, header=header)`; also reject `finding_id` starting with `OOS_`. Drop the OR with `_classification_row_in_scope`.
  - From Cursor-Pragmatic: Document and implement fallback as: keep rows with `outcome==accepted` and `phase` matching the skill; exclude `out_of_scope`; dedupe on `id` with numeric `round_num` precedence matching the TSV path.
  - From Cursor-Requirements: Specify fallback parity with rejected_analysis._implement_jsonl_records: prefer round-*/review-findings-full.jsonl then run-root; count outcome=accepted rows that are in-scope; dedupe finding_id with latest round winning. For review, also accept review-findings.ndjson when TSVs are absent. Add a pytest fixture for gc-slimmed implement dirs where only keep-set files remain and assert accepted-count-driven realized tier.


### FINDING_2: Latest-round wins needs numeric round ordering
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: Latest-round precedence is underspecified without numeric round ordering and stronger regression coverage, so older rows can override newer ones and change accepted counts or realized tiers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extract round numbers as integers from round-N directories and review-findings-classification-round-N.tsv filenames; sort numerically; apply last-wins only after numeric ordering. Add a test where round-2 rejects a finding accepted in round-10 and round-10 wins.
  - From Cursor-Innovation: Reuse `issue/_ground_truth._ground_truth_round_num` (or equivalent) for every classification artifact path; on ties prefer the row from the higher round number.
  - From Cursor-Pragmatic: Define the algorithm explicitly: group by `finding_id`, keep the row from the highest numeric round (not lexicographic path order), then count only if that surviving row is in-scope and `voting_result==accepted`. Add a fixture where round 2 rejects a finding accepted in round 1.
  - From Cursor-Pragmatic: Parse round numbers with the same numeric helper pattern as `python/larch/issue/_ground_truth.py::_ground_truth_round_num` (or reuse it) before choosing the winning row.
  - From Codex-Pragmatic: Add one synthetic fixture where the same finding_id is accepted in an earlier round and rejected or exonerated later. Assert the latest row wins and the accepted count excludes it.


### FINDING_3: Audit peer months need one timestamp source
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: Audit peer month bucketing is ambiguous unless the analyzer pins one committed timestamp source, so peer sets and drift tables can vary across runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin one committed timestamp per run (prefer manifest started_at, else final-summary started_at if present) for audit peer month and tier-drift bucketing; render n/a when absent. Document the field in docs/skills.md and test one audited/unaudited pair with explicit month boundaries.
  - From Cursor-Innovation: Pin month bucketing to `manifest.started_at` UTC when present, else exclude the run from audit-delta pairing; document the rule in `docs/skills.md`.


### FINDING_4: Audit peer tiers need pre-audit derivation
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: Audit peer matching must derive the pre-audit tier from committed logs, not the overwritten audited `applied_tier`, or audited-vs-unaudited deltas can be wrong.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Define a committed-log-only pre-audit tier derivation for matching, such as tiering from `design_tier` / `implement_tier` / `predicted_tier` plus `floors_applied`, and mark rows `n/a` when it cannot be recovered.
  - From Codex-Innovation: Define a committed-field derivation for the pre-audit tier, such as predicted_tier plus floors_applied when recoverable, and render n/a when it cannot be recovered instead of matching on post-audit applied_tier.


### FINDING_5: Round-local FINDING_N IDs need namespacing
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Bare `finding_id` is not a stable cross-round identity for code-review rows when FINDING_N numbering restarts each round, so deduping on bare ID can collapse different findings and undercount accepted items.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Namespace accepted-finding identities by source path or round for round-local code-review TSVs; only collapse cross-round rows when a stable cross-round identity exists.


### FINDING_6: Update the readability-preamble manifest for the new skill
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Adding the new difficulty-calibration skill without updating the readability-preamble manifest will make the lint target fail on the new SKILL.md.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add skills/difficulty-calibration/SKILL.md with variant orchestrator-inline expected_count 1, and bump the __metadata__ expected_count to match the new row total (currently 42).


### FINDING_7: Escalation evidence should still force HARD without classification
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: A gc-slimmed run can still prove HARD from committed escalation/substantiality evidence even when no classification artifact survives, so marking such runs unknown would drop valid HARD cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Derive HARD from committed escalation/substantiality evidence before requiring a classification source. Only non-escalated runs without parseable classification should have unknown accepted count and realized tier.


