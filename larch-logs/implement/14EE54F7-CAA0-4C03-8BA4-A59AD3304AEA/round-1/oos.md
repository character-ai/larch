### FINDING_17: [OUT_OF_SCOPE] Branch mixes #3210 ship-pr with #3217 anti-poll hook
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Unrelated hook/polling/docs changes bundled with #3210 increase review/revert surface and can distract from or block ship-pr regression focus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] Fork `ACTION=rebase` still bypasses `run_rebase_rebump`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Two fork rebase behaviors may coexist after the CI-fix path enhancement (`ci-wait` / `ci-decide` fork rebase vs new post-fix rebump); fork `ACTION=rebase` should eventually unify under `run_rebase_rebump` when bump plumbing is fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] Recovery rebase verify ignores fork base remotes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Phase 1–4 resume recovery verify may use `origin/main` on fork instead of threaded `base_remote` / `base_ref` (pre-existing gap).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] Fetch-fail semantics differ between `ci-behind-count` and `ci-status`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `ci-status` pending vs `BEHIND_COUNT=0` fail-open can let post-fix plain-push proceed without rebase while `ci-wait` would retry; pre-existing unless policy moves to fail-closed rebase on count errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] `ci-status` / `ship-pr` behind parsing helpers not shared
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `ci-status` (`awk`) vs `ship-pr` (`kv_value`) parsing divergence is a maintenance hazard when either script is touched again (overlaps in-scope FINDING_11 for the `awk` issue on `ci-status` itself).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] `hook-anti-read-poll.sh` nosession fallback shares poll counters
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Missing session metadata can false-positive poll warnings across unrelated runs; not #3210 scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

**Merge notes (for voters, not votes):**
- Input items 1, 24, 26, 37 → **FINDING_1** (same `behind=0` + `CI_FIX_REBASE_PENDING` skip re-verify / persistence-on-failed-push cluster).
- Input items 9, 19 → **FINDING_2** (outer vendor waterfall vs push-only retry — distinct fix from FINDING_1).
- Input items 2, 10, 20, 29, 38 → **FINDING_3**.
- Input items 3, 11, 17, 28, 35 → **FINDING_4**; items 16, 36 → **FINDING_5**.
- Input items 12, 25, 27 → **FINDING_7**; item 23 + 34 → **FINDING_20** / **FINDING_21** (OOS policy vs OOS helper-sharing).
- Input items 7, 13, 22 → **FINDING_17**; items 8, 14 → **FINDING_18**.

All specialist slots used the same boilerplate **Suggested revision** line; substantive fix directions live in the normalized **Concern** text above. No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).

Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

