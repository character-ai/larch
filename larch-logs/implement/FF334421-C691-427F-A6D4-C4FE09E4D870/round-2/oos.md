### FINDING_16: [OUT_OF_SCOPE] test_main_stalled_metadata_write_failure pins STALLED→INTERNAL_ERROR escalation
- **Reviewer(s)**: dyn-exception-escalation-contract-output.txt
- **Severity**: latent
- **Concern**: `test_main_stalled_metadata_write_failure_surfaces_internal_error` (`python/test_ship.py:2224-2241`) intentionally pins the STALLED→INTERNAL_ERROR escalation; if gap-fill is restored to best-effort per FINDING_2, this test should flip to assert the stall outcome is preserved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-exception-escalation-contract-output.txt: if gap-fill is restored to best-effort, this test should flip to assert the stall outcome is preserved.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] possible double-JSON emit_result on argparse failure inside outer try/except
- **Reviewer(s)**: dyn-exception-escalation-contract-output.txt
- **Severity**: latent
- **Concern**: Prior review notes (`larch-logs/implement/A6172AC2-…/round-1/`) flagged a possible double-JSON `emit_result` path when the argparse failure branch sits inside the outer `try/except`; that is adjacent to `main()`’s exception envelope but not introduced by the `_persist_stall_metadata_if_needed` / outer-handler changes reviewed here.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot provided a concrete fix direction beyond noting adjacency to `main()`’s exception envelope)

Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

