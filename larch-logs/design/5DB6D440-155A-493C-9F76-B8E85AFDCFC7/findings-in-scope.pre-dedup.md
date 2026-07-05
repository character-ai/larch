### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_tally.py:1381-1401
- **Concern**: emit_tally preserve guard must short-circuit before the oos.md serialize branch. Scenario: The plan adds preserve when sink_count >= OOS_ACCEPTED_COUNT, but the current elif chain rebuilds from oos.md whenever that file exists. After aggregate promotion with OOS_ACCEPTED_COUNT=0 and a non-empty promoted sink, a lingering round oos.md can still trigger serialize and overwrite the authoritative sink on re-entry.
- **Proposed resolution**: State the preserve branch explicitly runs before any oos.md rebuild path, and add a regression where oos.md is present while sink_count exceeds OOS_ACCEPTED_COUNT.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review_round.py
- **Concern**: Plan fail-closed security test still targets Path.read_text inside the classifier. Scenario: Item 3 deletes plan_review_tally._is_security and classifies voting.is_security_block_text(artifact_text) instead. The mandated test that forces Path.read_text to fail inside the security classifier no longer matches the implementation surface, so the regression may pass without exercising fail-closed behavior.
- **Proposed resolution**: Retarget the test to raise from block read in _artifact_text_for_item or from voting.is_security_block_text, and assert plan-review tally aborts non-zero without routing the item to public pools. ## Findings 1. **correctness** (`python/larch/review/review_tally.py:1381-1401`): The new `sink_count >= OOS_ACCEPTED_COUNT` preserve rule must be ordered before the `oos.md` serialize/rebuild branch. Today, a promoted non-empty sink with `OOS_ACCEPTED_COUNT=0` can still hit the serialize path when round `oos.md` exists. 2. **correctness** (`python/tests/review/test_plan_review_round.py`): The planned fail-closed security regression still describes `Path.read_text` failing inside the classifier. After consolidation onto `is_security_block_text(artifact_text)`, the test needs to force failure at block read or classifier call instead. Accepted round-1 items (artifact_text security routing, fail-closed policy, emit_tally preserve intent) look addressed in the plan text. I did not re-raise them. **[OUT_OF_SCOPE]** `python/larch/design/design_oos.py:120-128` still carries a third local `_is_security_block_text` duplicate outside Item 3 scope; worth a follow-up issue, not this minimum-change batch.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:425-435,858-872
- **Concern**: [SCOPE-REDUCTION] Structured sidecar failure handling is broader than the no-findings rescue the feature needs. Scenario: The plan removes collector structured validation, then keeps any OK reviewer as zero parsed rows when lazy structured generation returns non-zero. A malformed structured TSV that still passes substantive validation by length and provenance would stop being NOT_SUBSTANTIVE and could make real findings disappear as a clean zero-findings round.
- **Proposed resolution**: Limit the zero-row fallback to recognized no-findings prose or sentinel outputs. For structured-looking output or other sidecar generation failures, keep a degraded or failed record equivalent to the current structured-validation failure path.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:419-469
- **Concern**: Lazy structured sidecar materialization must use the collector tool-aware sidecar path contract. Scenario: The plan adds compose-time sidecar generation when files are absent but does not pin the output path to `collect_results._structured_sidecar_path` (`{reviewer_file}.tsv` for cursor/codex, `{reviewer_file}.jsonl` otherwise). Writing the wrong suffix or only checking one fallback can leave compose reading a missing or wrong-format file and silently parsing zero rows while the reviewer stays OK.
- **Proposed resolution**: In `plan_review_round.py`, derive the sidecar path from `TOOL` with the same rule as `collect_results._structured_sidecar_path`, generate only when neither that path nor `STRUCTURED_SIDECAR` exists, and add a regression that a non-cursor/codex OK record materializes `{reviewer_file}.jsonl`.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-entry.sh:37-39
- **Concern**: Step 3 `--reentry` must reset stale structured sidecars, not only the aggregate pool. Scenario: Removing `--structured-reviewer-validation` from design `collect-results` stops collector-side sidecar refresh. `--reentry` already deletes `oos-aggregate-pool.md` but leaves prior `{reviewer_file}.tsv`/`.jsonl` files. On Gate C / Gate A review re-entry, compose can reuse stale structured rows from an earlier round against freshly rewritten reviewer output, producing false findings or masking real ones.
- **Proposed resolution**: Extend the existing `--reentry` cleanup in `design-step3-entry.sh` (and the planned harness case) to remove stale structured sidecars for launched reviewer outputs, or regenerate when reviewer output is newer than the sidecar; do not rely on absence-only lazy generation alone.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: python/larch/review/plan_review_tally.py:731-734
- **Concern**: [ALREADY_ADDRESSED] Fail-closed security handling conflicts with text-only classification and replace-decoded reads. Scenario: Item 3 removes `_is_security` path reads and plans fail-closed aborts, but `_artifact_text_for_item` still uses `block.read_text(..., errors="replace")`, so decode corruption cannot raise, and the planned fail-closed test still targets a read inside the removed classifier. A corrupted or unreadable block can still be classified as non-security and reach public OOS pools.
- **Proposed resolution**: Before `voting.is_security_block_text(artifact_text)`, read the block with strict decode semantics and raise on `OSError`/decode failure; update the planned regression to force failure at that read/assembly site, not inside `is_security_block_text`.



### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:859-868
- **Concern**: [SCOPE-REDUCTION] Structured sidecar failures are fail-open for every OK reviewer, not just prose no-findings. Scenario: A reviewer emits a prose finding or malformed structured row that passes substantive validation but cannot materialize a structured sidecar; the plan records OK with zero parsed rows, so the round can finish as zero-findings and drop a real review failure
- **Proposed resolution**: Narrow the fail-open branch to outputs that match the no-findings prose or sentinel case; keep existing NOT_SUBSTANTIVE or failed handling for structured-looking outputs or finding prose when sidecar generation fails



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:466-469
- **Concern**: Lazy sidecar generation only when a sidecar file is absent does not replace collector-side regeneration removed with `--structured-reviewer-validation`. Scenario: `collect_results._validate_structured` currently rewrites `{reviewer_file}.tsv` on every collect from the latest reviewer output. The plan removes that flag and materializes sidecars only when missing. On Step 3 re-entry or a later round that reuses the same reviewer output path, a prior `.tsv` can survive while `*-output.txt` is overwritten with prose no-findings or new content; `_compose_findings_from_collector` will still parse the stale sidecar and can resurrect old findings or miss the zero-findings path Item 8 is meant to fix
- **Proposed resolution**: In `plan_review_round.py`, before `_rows_from_structured`, regenerate the structured sidecar for each `OK` record when the sidecar is missing or older than `REVIEWER_FILE` (or unconditionally overwrite for `OK` records), using the same tool-aware path as `collect_results._structured_sidecar_path`. Add a regression in `python/tests/review/test_plan_review_round.py` that seeds a stale `.tsv`, runs compose/collect with fresh prose-only reviewer output, and asserts zero parsed rows ## Findings ### 1. [correctness] `python/larch/review/plan_review_round.py:466-469` — Stale structured sidecars survive after removing collector validation Item 8 correctly drops `--structured-reviewer-validation` from the design `collect-results` call, but today that path also refreshes structured sidecars on every collect via `collect_results._validate_structured`. The plan’s lazy helper only runs when neither `STRUCTURED_SIDECAR` nor the `{reviewer_file}.tsv` / `.jsonl` fallback exists. That leaves a real gap on re-entry and multi-round Step 3 runs: reviewer output paths are reused, prior sidecars are not cleared by `step3-state --direct-review-entry`, and compose will keep reading an old `.tsv` even when substantive validation accepted fresh prose-only output. Item 8’s prose no-findings regression covers the absent-sidecar case only, not stale-sidecar reuse. **Suggested revision:** Regenerate (or delete-then-regenerate) the tool-aware sidecar for each `OK` record when it is missing or older than the reviewer file, then add a test with a pre-seeded stale `.tsv` plus fresh prose-only reviewer output. --- **Accepted-round coverage looks complete:** FINDING_1 (`artifact_text` before security classification) and FINDING_4 (fail-closed classifier) are both spelled out in the plan with targeted regressions. I did not re-raise them. **Prior OOS/neutral items not re-raised:** explicit preserve-branch wording (FINDING_3), zero-count security sink authority (FINDING_7), `design_oos` classifier consolidation (OOS_3–OOS_5), and duplicate security-pool coverage in `test_plan_review.py` (FINDING_6/OOS_7). The plan’s `sink_count >= OOS_ACCEPTED_COUNT` preserve rule matches the aggregate-promotion re-entry bug in Item 1.



### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:425-464
- **Concern**: Lazy sidecar materialization trusts existing fallback sidecars. Scenario: The plan removes `--structured-reviewer-validation` but only generates a sidecar when no `STRUCTURED_SIDECAR` or fallback sidecar exists. A stale `{reviewer_file}.tsv` from an earlier round can be parsed for a current prose no-findings reviewer, so `/design` can resurrect old findings instead of preserving the accepted zero-findings output.
- **Proposed resolution**: When the collector did not provide a current `STRUCTURED_SIDECAR`, regenerate a deterministic helper-owned sidecar for each OK reviewer before parsing, overwriting or bypassing fallback files. Add the prose no-findings regression with a stale fallback sidecar present.



