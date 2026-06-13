### OOS_2: [OUT_OF_SCOPE] risk-integration: python/test_rendering.py
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Plan-listed scope-anchor boundary pytest cases (symlink, empty, oversized, CR/LF path) are not all present _regressions in _scope_anchor_common_shape_ok could slip without dedicated cases_ Add pytest for symlink, zero-byte, >65536-byte, and CR/LF-in-path rejection
- **Suggested revision**: Address the concern above.


### OOS_3: risk-integration: python/test_plan_scout.py:72-99
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Pytest does not replace deleted 873-line scout-dynamic-archetypes harness coverage /review diff-mode scout can regress in staging launcher argv or JSON salvage without CI failure Port key E2E cases from deleted harness: diff-mode happy path with --read-tools assertions fence-wrapped JSON through scout_dynamic_archetypes over-cap and Claude failure paths
- **Suggested revision**: Address the concern above.


### OOS_4: **correctness** `python/plan_scout.py:455-506` — **Important**: the dynamic scout no longer removes `${OUTPUT}.raw.cap-hit` before each tier. `_raw_is_scout_json()` rejects any raw file with a sibling `.cap-hit` at `python/plan_scout.py:344-346`, so a Cursor cap-hit can leave that marker behind, Claude can then write valid JSON to the same `.raw`, and the code still falls through to write an empty manifest with `SCOUT_STATUS=empty`. **Suggested fix:** unlink `Path(str(raw) + ".cap-hit")` before launching Cursor and again before launching Claude, matching the deleted shell helper’s per-tier cleanup.
- **Reviewer**: codex-generic-output.txt
- **Concern**: - **correctness** `python/plan_scout.py:455-506` — **Important**: the dynamic scout no longer removes `${OUTPUT}.raw.cap-hit` before each tier. `_raw_is_scout_json()` rejects any raw file with a sibling `.cap-hit` at `python/plan_scout.py:344-346`, so a Cursor cap-hit can leave that marker behind, Claude can then write valid JSON to the same `.raw`, and the code still falls through to write an empty manifest with `SCOUT_STATUS=empty`. **Suggested fix:** unlink `Path(str(raw) + ".cap-hit")` before launching Cursor and again before launching Claude, matching the deleted shell helper’s per-tier cleanup.
- **Suggested revision**: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-migration-equivalence-output.txt
- **Concern**: - **risk-integration** `python/test_rendering.py` — The plan called for pytest coverage of scope-anchor rejection paths (CR/LF paths, symlinks, empty/oversized files, outside-root). `_scope_anchor_common_shape_ok` in `python/rendering.py:229-243` implements those checks, but there are no matching CLI-level tests; regressions on those guards would not be caught by the new harness.
- **Suggested revision**: Address the concern above.


