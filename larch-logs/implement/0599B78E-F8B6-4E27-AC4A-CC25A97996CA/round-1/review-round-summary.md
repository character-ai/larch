# Review Round 1

- Mode: `diff`
- 2 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_1: test_embedded_waterfall_dispatchers_preserve_raw_retired_markers fails; raw blobs lack retired waterfall markers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-asset-roundtrip-output.txt
- **Severity**: blocking
- **Concern**: `test_embedded_waterfall_dispatchers_preserve_raw_retired_markers` fails on the current branch (`AssertionError` for `scripts/dispatch-plan-voters.sh`: raw decoded body lacks `dispatch-with-waterfall.sh` and `DISPATCH_WATERFALL_SH` assignment form). Raw `_LEGACY_ASSETS` blobs for waterfall dispatchers already contain runtime-substituted `agent dispatch-waterfall` / `DISPATCH_WATERFALL_CMD` text, so the plan’s raw-marker round-trip acceptance criterion is unmet. `pytest python/test_plan_review.py` exits 1; `make py-test` fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align test with reality (drop marker asserts, assert raw/substituted contract) or restore marker tokens in raw blobs before re-encoding.
  - From cursor-specialist-edge-cases-output.txt: Re-encode both dispatcher blobs from raw decoded text that preserves retired waterfall markers (runtime substitution stays in `_decode_legacy_asset`), or align the test/plan if baked-in substitution is deliberate.
  - From cursor-specialist-testing-output.txt: Re-encode dispatch-plan-voters.sh and dispatch-plan-review-panel.sh from pre-substitution raw decoded text with only quiet/validate edits; verify retired markers survive
  - From dyn-asset-roundtrip-output.txt: Re-encode `scripts/dispatch-plan-voters.sh` and `skills/design/scripts/dispatch-plan-review-panel.sh` from pre-substitution bash that still references the retired waterfall shell token and `DISPATCH_WATERFALL_SH=…dispatch-with-waterfall.sh…`, applying only the quiet/validate reorder on that raw text; keep `_decode_legacy_asset` as the sole runtime substitution path and confirm the new test passes.


### FINDING_3: `_decode_legacy_asset` waterfall substitutions are no-ops; embedded substitution contract broken
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: In `python/plan_review.py:801-835`, `_decode_legacy_asset` waterfall substitutions are no-ops because raw blobs already contain substituted agent dispatch-waterfall text. Regenerated raw blobs bake in waterfall CLI substitution, so replacement logic is dead for two dispatcher assets. Future waterfall migrations cannot update embedded dispatchers via `_decode_legacy_asset`; the plan raw→runtime contract is broken. The plan item to preserve retired-marker round-trip cannot be satisfied without reintroducing markers; override hook semantics may be dead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document substitution-final blobs or restore retired markers in raw encoded assets.
  - From cursor-specialist-testing-output.txt: Restore raw blobs with retired shell tokens; keep substitution exclusively in `_decode_legacy_asset`


