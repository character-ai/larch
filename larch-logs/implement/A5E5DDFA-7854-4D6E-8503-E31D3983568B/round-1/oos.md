### OOS_1: [OUT_OF_SCOPE] Unused round-num parsing for static intended slots after six-slot flattening (`check-reviewer-failure-threshold.sh:203-219`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Round-number parsing remains unused for `STATIC_INTENDED_SLOTS` after flattening to six; no functional bug, slightly widens CLI surface; acceptable to leave per plan or remove in a follow-up that updates callers if desired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_2: [OUT_OF_SCOPE] Implement run log / diff noise commits alongside threshold work (`larch-logs/implement/…`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-doc-completeness-output.txt, dyn-test-slot-mismatch-output.txt
- **Severity**: nit
- **Concern**: The branch adds tracked implement run-log material (metadata, embedded plan, large trees) next to the threshold fix; orthogonal to threshold correctness if the PR is meant to be minimal script+docs-only, but policy may treat run logs as intentional noise reviewers can ignore for this review type.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-doc-completeness-output.txt, dyn-test-slot-mismatch-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] No invariant tying counted static records to six-slot intended baseline when `--launched-slots` omitted (`check-reviewer-failure-threshold.sh`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Nothing ties `COUNTED_SLOTS` to `INTENDED_SLOTS` when `--launched-slots` is omitted; all static records in the file affect `FAILED_SLOTS`, so malformed or over-long collector files could skew panel-failed vs nominal six-slot reasoning; better addressed as follow-up hardening (script/collector cap vs manifest) than in this bugfix PR alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Test harness echo comments understate round-1 six-slot denominator
- **Reviewer(s)**: dyn-doc-completeness-output.txt
- **Severity**: nit
- **Concern**: Echo comments that still say “round 2+ … uses a 6-slot intended denominator” are slightly understated because round 1 uses the same denominator; minor vs stale prose in the primary `.md` and largely predates the branch in spirit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-doc-completeness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_5: [OUT_OF_SCOPE] Arithmetic note: `INTENDED_SLOTS` is the failure-rate denominator (`half_fail_hard`, `dynamic_hard`)
- **Reviewer(s)**: dyn-test-slot-mismatch-output.txt
- **Severity**: nit
- **Concern**: Walkthrough of `half_fail_hard` (no `NEVER_LAUNCHED`, six timeouts → `THRESHOLD_OK=false` at half-plus-one) and `dynamic_hard` (`NEVER_LAUNCHED=max(0,6-16)=0`, three static failures `<4` → `THRESHOLD_OK=true` with `COUNTED_SLOTS=12`, `INTENDED_SLOTS=6`) concludes the script is designed to use **`INTENDED_SLOTS` as the failure-rate denominator**, not `COUNTED_SLOTS`, so `COUNTED_SLOTS > INTENDED_SLOTS` does not by itself flip the threshold via negative-clamp interaction—informational for reviewers, not a functional bug report against the branch’s threshold logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-slot-mismatch-output.txt: Address the concern above.

---

**Notes on subsumption**

- **FINDING_1** subsumes all in-scope concerns about **stale 12/7 STATUS prose at ~line 35** (including “correctness” vs “risk-integration” wording variants).
- **FINDING_2** subsumes the **50% / harness blurb** items at **~41-43** only.
- **FINDING_3** covers **7 vs 6** harness/fixture/label/`--launched-slots` drift; it does **not** subsume **FINDING_4**, which is a **missing test scenario** (different fix).
- **cursor-specialist-testing-output.txt** run-log **[OUT_OF_SCOPE]** item had **Suggested revision: N/A** — no bullet added under **OOS_2** per your rules.
- **dyn-doc-completeness** and **dyn-test-slot-mismatch** long concerns for **FINDING_22** were merged into **OOS_5** as one behavioral theme (arithmetic/denominator explanation); the two input blocks were **not** word-identical, but both are the same “no threshold bug from COUNTED vs INTENDED” message—presented as one normalized concern with one revision line that was identical (“Address the concern above.”). If you need **strictly no paraphrase across distinct proposals** for the concern body, treat **OOS_5** as two one-reviewer blocks in downstream tooling; here they are merged on identical behavioral conclusion and identical revision string.

Because this output contains one or more `### FINDING_N:` blocks, **do not** include `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` anywhere.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

