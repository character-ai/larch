### FINDING_1: Code-review prune caller still passes removed `--input-mode`
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The prune CLI cleanup removes `--input-mode` from parsing, but the code-review ballot path still forwards `--input-mode code`. Once the parser change lands, `/review` nit pruning will fail with argparse before voting/aggregation completes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/larch/review/review_core_body.py removing --input-mode from the prune_nits argv list; extend test_review_pipeline.py if any test asserts the old argv shape
  - From Codex-Arch: Either keep `--input-mode` accepted until `review_core_body._prune_nits_for_ballot()` is updated, or migrate that caller in the same change to stop passing it.
  - From Cursor-Innovation: Add ### UPDATED: python/larch/review/review_core_body.py to remove --input-mode from the prune argv list; extend python/tests/review/test_review_pipeline.py if any stub asserts the old argv
  - From Cursor-Pragmatic: Add ### UPDATED: python/larch/review/review_core_body.py to remove --input-mode from the prune-nit-findings argv in _prune_nits_for_ballot, and extend test_review_pipeline.py (or an equivalent caller contract test) so a stray --input-mode on the prune CLI is caught.
  - From Cursor-Requirements: Add `### UPDATED: python/larch/review/review_core_body.py` to drop `--input-mode` from `_prune_nits_for_ballot` argv (keep audit/security paths). Extend the testing strategy to cover a code-review core prune invocation, not only plan-review and unit prune tests.
  - From Codex-Requirements: Remove `--input-mode` from `_prune_nits_for_ballot` too, and update any tests that exercise the code-review prune path.


### FINDING_2: Progress-report OOS rendering still needs explicit proposed/fileable split and security filtering
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-Oos Flow Auditor
- **Severity**: major
- **Concern**: The render-time OOS derivation still conflates proposed and fileable counts, and the TSV/markdown fallback needs to keep security-tagged OOS out of the rendered fileable totals. Without that split, the issue footnote and phase table can undercount or overstate OOS after fileable-only `OOS_ACCEPTED_COUNT` lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When splitting proposed vs fileable, compute oos_total from OOS_PROPOSED_COUNT + OOS_REJECTED_COUNT (or an explicit total), store OOS_PROPOSED_COUNT in tally/tally_canonical via _round_meta_object, and add a regression in test_progress_report.py for accepted-minor OOS
  - From Cursor-Innovation: When deriving proposed/fileable from classification TSV (and any markdown fallback), skip or decrement security-tagged OOS via voting.is_security_block on the row block, mirroring _adjust_design_security_oos; keep write_design_round_meta behavior intact
  - From Cursor-dyn-Oos Flow Auditor: Refactor _phase_round_from_meta to bind proposed from OOS_PROPOSED_COUNT (fallback: classification/markdown vote-accepted count) and fileable from OOS_ACCEPTED_COUNT preferring round_dir/review-tally.env when present; rename the rendered header from OOS accepted to OOS fileable per the plan.


### FINDING_3: Round-meta persistence still writes vote-accepted counts into `OOS_ACCEPTED_COUNT`
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Oos Flow Auditor
- **Severity**: major
- **Concern**: The meta writers still persist vote-accepted OOS into the canonical `OOS_ACCEPTED_COUNT`, so fresh `round-meta.json` can disagree with `review-tally.env` and overstate fileable OOS for readers that use meta alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Also update write_implement_round_meta/_round_meta_object to store fileable-only OOS_ACCEPTED_COUNT (prefer round_dir/review-tally.env when present) plus a distinct OOS_PROPOSED_COUNT; keep legacy readers defaulting missing proposed fields
  - From Cursor-Innovation: In the same progress_report.py change, update _round_meta_object/write_implement_round_meta (and write_design_round_meta if needed) to persist OOS_PROPOSED_COUNT as vote-accepted, set tally OOS_ACCEPTED_COUNT from review-tally.env when present, and add/adjust write_round_meta tests for accepted-minor vs fileable split.
  - From Cursor-dyn-Oos Flow Auditor: Extend the progress_report.py work to update _round_meta_object plus both write_*_round_meta callers: add OOS_PROPOSED_COUNT for vote-accepted OOS; set OOS_ACCEPTED_COUNT from review-tally.env when present else oos_fileable_from_votes on classification rows; never copy raw classification accepted counts into OOS_ACCEPTED_COUNT.


### FINDING_1: Unify OOS proposed/fileable semantics across writer, reader, and legacy meta
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The new OOS proposed/fileable split is not applied through one consistent contract: current canonical writes can still keep vote-accepted OOS in `tally_canonical.OOS_ACCEPTED_COUNT`, `_phase_round_from_meta` can still compute `oos_total` from the wrong bucket, and legacy round-meta without `OOS_PROPOSED_COUNT` can be misread as fileable, so accepted-minor OOS can overstate fileable counts or drift between `tally` and `tally_canonical`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit legacy branch: when OOS_PROPOSED_COUNT is missing, treat tally.OOS_ACCEPTED_COUNT as proposed only and derive fileable from review-tally.env when present else per-row oos_fileable_from_votes on classification (or markdown-safe fallback); never reinterpret legacy OOS_ACCEPTED_COUNT as fileable without that guard.
  - From Cursor-Innovation: In the `write_implement_round_meta` / `_canonical_decomposition` path, persist vote-accepted OOS as `OOS_PROPOSED_COUNT` and fileable-only OOS as `OOS_ACCEPTED_COUNT` inside `tally_canonical` too (via `oos_fileable_from_votes` / `review-tally.env`, with the same security exclusion). Extend `test_write_implement_round_meta_records_canonical_decomposition` with an accepted-`minor` OOS row asserting `tally_canonical.OOS_PROPOSED_COUNT=1` and `tally_canonical.OOS_ACCEPTED_COUNT=0`.
  - From Cursor-Pragmatic: Explicitly update `_canonical_decomposition` (or post-process its output) so canonical OOS accepted is fileable-only via `voting.oos_fileable_from_votes(...)`, add `OOS_PROPOSED_COUNT` to `tally_canonical`, and wire `_phase_round_from_meta` `oos_total` to `OOS_PROPOSED_COUNT + OOS_REJECTED_COUNT` from the same source. Extend `test_write_implement_round_meta_records_canonical_decomposition` with an accepted-minor OOS row.
  - From Cursor-Requirements: When `tally_canonical` exists, compute `oos_total` from canonical OOS buckets using proposed semantics (`OOS_PROPOSED_COUNT`, else legacy vote-accepted `OOS_ACCEPTED_COUNT`) plus `OOS_REJECTED_COUNT`; use raw `tally` only when canonical is absent. Do not store fileable-only counts into `tally_canonical.OOS_ACCEPTED_COUNT` without a proposed field. Extend the plan testing strategy with an explicit regression for `test_render_phase_detail_shows_canonical_decomposition_footnote`.


