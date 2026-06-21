# Review Round 3

- Mode: `diff`
- 8 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Legacy stable-id extraction uses pre-filed lookback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: `_extract_legacy_stable_ids_from_ndjson_body` scans from `min(filed_markers) - 1200` through the body end, so `OOS_N` / `FINDING_N` tokens in review prose above the filed block can be treated as filed-evidence citations for the same URL. That creates spurious score rows and wrong reviewer/block joins (e.g. ndjson mentions `OOS_3` in finding text then files one URL; lookback extracts `OOS_3` and scores the wrong reviewer).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restrict token extraction to text at/after the first filed marker or an explicit filed/disposition subsection; drop the pre-marker lookback.
  - From dyn-oos-reconciler-output.txt: Slice forward from the first filed marker only (or another explicit filed-section boundary), and only extract legacy ids from that substring; add a regression test where `#4683` or `OOS_5` appears in finding prose above `Filed URL:` and is not scored.


### FINDING_2: `fetch_main` performs two expanded `gh issue list` retries before fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `fetch_main` retries the expanded `gh issue list` JSON field set twice before switching to the reduced field set, diverging from the plan's single expanded-then-fallback contract. On `gh` builds rejecting `stateReason`/`url`, every run performs two failing expanded calls; the untested fallback/degraded path may regress without notice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: On first expanded failure switch to fallback fields; add a test where two expanded calls fail and fallback succeeds with _larch_degraded_fields.


### FINDING_3: Plan-required regression tests largely absent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Plan-required tests for cap-rollup, stable-id collisions, main-agent bridge, degraded fetch, and offline no-network behavior are largely absent despite complex new join/rollup logic. A cap-rollup with N=3 and eight unfiled same-source blocks should be ambiguous; a regression in `_expand_cap_rollup_records` would mis-report reviewer fate-adjusted totals undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the plan's focused fixtures for rollup ambiguity, collisions, main-agent bridge, fetch-failure degradation, and offline defaults.


### FINDING_5: Ambiguous cap-rollup fallback still scores partial members
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: When cap-rollup fallback cannot safely recover all N members (`expected > len(out)` and unfiled-candidate count ≠ N), the code appends an `ambiguous rollup expansion` marker but still returns existing `out` rows, which `fate_adjusted_oos_scoring` scores at +1 each. Concrete scenario: rollup titled "Aggregated rollup of 3" with `Stable ID: oos-accepted-review:OOS_1`, only one explicit member resolved, eight unfiled same-source blocks; one reviewer keeps +1 on the partial row while the rollup implied three members and may later be docked combined-away. The plan requires reporting `ambiguous_rollup_expansion` and not guessing when fallback cannot safely recover all members.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: When expected member count is not met after fallback, avoid partial scoring or clearly separate partial vs complete rollup scoring per plan intent.
  - From cursor-specialist-edge-cases-output.txt: When expected N is not fully recovered, return only ambiguous rollup expansion rows and score zero members rather than partial subsets.
  - From codex-generic-output.txt: When rollup fallback is ambiguous, return only the ambiguity bucket unless explicit member citations resolved all scored rows safely.
  - From dyn-oos-reconciler-output.txt: Treat incomplete rollup recovery as fully ambiguous: return only ambiguous bucket rows (no scored members), or score only members recovered through unambiguous explicit stable-id resolution and exclude fallback guesses from totals.


### FINDING_6: `run_main` clears repo after bulk `gh issue list` failure, skipping targeted enrichment
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `run_main` clears `repo` after bulk `gh issue list` failure, skipping targeted `gh issue view` even when `--repo` was valid. A transient bulk-fetch outage on a live `/analyze-issues` run leaves filed OOS rows without bulk or per-issue data; combined-away and NOT_PLANNED fates stay unknown/skipped and reviewer adjusted totals stay inflated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Preserve resolved repo across bulk-fetch failure; run _fetch_filed_oos_issue_details whenever repo is known; only omit targeted fetch on repo detection/validation failure.


### FINDING_7: Offline sidecar enrichment fails to clear degraded `stateReason`
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_merged_issue_index` clears degraded `stateReason` only when the detail has `__targeted_fetch_ok__`, but `--filed-issue-details-json` is documented as plain view fields and will not include that private marker. Concrete scenario: fallback dump marks `_larch_degraded_fields=["stateReason"]`, sidecar supplies `"stateReason":"NOT_PLANNED"`, and `classify_oos_issue_fate` reports provisional unknown instead of docked closed-unfixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Clear the `stateReason` degraded flag whenever merged details explicitly provide `stateReason`, not only for live targeted-fetch records.


### FINDING_8: Main-agent stable-id bridge disabled in normal join path
- **Reviewer(s)**: dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: Non-rollup ndjson rows citing `oos-accepted-main-agent:*` stable ids never bridge to same-run `round-*/oos-accepted-review.md` blocks. `_resolve_blocks_for_stable_id` calls `_stable_ids_cover(..., allow_main_agent_bridge=False)`, so a namespaced main-agent id cannot match a review-path block that only shares the bare `OOS_N` suffix. Join falls through to the recovered row and forces `reviewer="Main agent"` even when a review markdown block with the real reviewer exists, misattributing provisional and fate-adjusted points.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-reconciler-output.txt: Enable main-agent bridging in the normal join path (for example pass `allow_main_agent_bridge=True` to `_stable_ids_cover` when the ndjson stable id source is `oos-accepted-main-agent`, or call a shared resolver used by rollup expansion), and add the planned fixture where `oos-accepted-main-agent:OOS_1` joins a review-path block.


### FINDING_9: Design-run bare-URL recovery is over-broad
- **Reviewer(s)**: dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: If `oos-issues-created.md` has no `OOS_FILE_MAP` rows and no accepted-block URLs, any line starting with `http` is treated as filed OOS evidence. Non-OOS URLs in that file (headers, notes, unrelated links) become scored rows with `reviewer="unknown"`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-reconciler-output.txt: Restrict bare-URL recovery to explicit filed-OOS shapes already used elsewhere (`Filed URL:`, `Filed OOS issue:`, `Filed as #N`, or tabular filed-OOS rows), not every HTTP line in the file.


