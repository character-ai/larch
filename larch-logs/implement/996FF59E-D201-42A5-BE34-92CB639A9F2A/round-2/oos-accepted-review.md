### FINDING_11: [OUT_OF_SCOPE] Design run log artifacts co-present in diff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `larch-logs/design/...` noise in diff; not ship-pr runtime; policy-expected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: None (policy-expected noise)


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated


### FINDING_23: [OUT_OF_SCOPE] Stale `skills/implement/SKILL.md` exit 5 orchestration vs absorbed paths
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `SKILL.md` still documents ship-pr exit 5 while ship-pr no longer emits exit 5 for absorbed paths; operators following stale guidance may mishandle exit 4 stall streams after this lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Follow-up SKILL.md + reference doc edits to match exit 4 / waterfall contracts.

---

**Note:** `FINDING_6` (launchers exit 0, OOS) was **not** merged with `FINDING_12` (`LAUNCHER_EXIT` propagation / waterfall tier_rc): same broad theme but incompatible triage (no PR change vs explicit fix), different fixes, and different primary code paths called out.

Because this output contains one or more `### FINDING_N:` blocks, **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** anywhere in this response.

Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_5: [OUT_OF_SCOPE] Unrelated ast-grep contributor doc bundled with ship-pr work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `docs/installation-and-setup.md` (ast-grep section) is unrelated to ship-pr automation; reviewers must split attention across unrelated concerns in one PR; several slots mark as scope/triage only (no ship-pr logic change).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split doc change to its own PR or branch
  - From cursor-specialist-correctness-output.txt: None (scope/triage only)
  - From cursor-specialist-testing-output.txt: None required for this review
  - From cursor-specialist-security-output.txt: No change required for ship-pr security review
  - From cursor-specialist-edge-cases-output.txt: None for this review


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_6: [OUT_OF_SCOPE] Launchers exit 0; recovery relies on verifier not rc
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `scripts/launch-*-ci.sh` pattern (grep `LAUNCHER_EXIT`; exit 0) is described as pre-existing on main, not introduced by this PR; no change required for this PR scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: No change required for this PR scope


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated


### FINDING_7: [OUT_OF_SCOPE] `exit_transient_net` outside `with_transient_retry` for rebase / ci-wait bail
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: Same structural pattern as on main before branch (`exit_transient_net` outside `with_transient_retry` body at cited bail sites). One slot: no change unless product tightens acceptance #11 globally. Other slot: strict reading of plan acceptance #11 conflicts with legacy call sites; refactor into WTR or relax/document acceptance #11 scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: No change required unless product wants to tighten acceptance #11 globally
  - From cursor-specialist-correctness-output.txt: Refactor into WTR or relax/document acceptance #11 scope


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


