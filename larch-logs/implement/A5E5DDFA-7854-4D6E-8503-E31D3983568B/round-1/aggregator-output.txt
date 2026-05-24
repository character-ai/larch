Here is the normalized aggregator output. In-scope items are merged by shared behavioral risk; out-of-scope items are separate `### OOS_N:` blocks with `[OUT_OF_SCOPE]` preserved on the first line. Severity uses **important** > **latent** > **nit**. Verbatim revision lines only; slots with **N/A** or no revision line beyond what you gave are omitted where the spec says not to fabricate.

---

### FINDING_1: STATUS prose still describes 12/7 static baseline vs flat 6-slot contract (`check-reviewer-failure-threshold.md:35`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-doc-completeness-output.txt, dyn-test-slot-mismatch-output.txt
- **Severity**: important
- **Concern**: The STATUS classification paragraph still frames the threshold as whether a legacy **12-slot or 7-slot** static panel failed, while Args/Output/Threshold (and the branch’s intended contract) describe a unified **6-slot** static specialist baseline for both `hard` and `simple`. That makes the doc internally contradictory and can mislead operators or maintainers about what is measured, how to read `COUNTED_SLOTS` vs `INTENDED_SLOTS`, and how to triage panel-failed behavior; dynamic-scout wording should remain clearly outside that static denominator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-doc-completeness-output.txt: **correctness** `skills/review/scripts/check-reviewer-failure-threshold.md:35` — The **STATUS classification** paragraph still says the threshold answers whether the **baseline 12-slot or 7-slot** panel failed, while the same file’s Args/Output/Threshold sections were updated to a **flat 6-slot** model. That leaves the sibling doc internally contradictory and misstates what the script measures after the branch change. **Suggested fix:** Rewrite the closing clause to describe the **6-slot static specialist baseline for both `hard` and `simple`** (or neutral wording like “the static specialist panel”), and keep the contrast with optional dynamic scouts.
  - From dyn-test-slot-mismatch-output.txt: **correctness** `skills/review/scripts/check-reviewer-failure-threshold.md:35` — After the branch updates Args, Output, and Threshold to a flat **6**-slot panel, the STATUS classification paragraph still says the script answers whether the baseline **12-slot or 7-slot** panel failed, which contradicts the new contract and can mislead anyone tuning collectors or interpreting `COUNTED_SLOTS` vs `INTENDED_SLOTS`. **Suggested fix:** Rewrite that clause so it refers to the same **6**-slot static specialist baseline for both panels (keeping the point that dynamic scouts are out of scope for that question).

### FINDING_2: Harness blurb ties “exactly 50%” / boundary coverage to old half_fail_hard mental model (`check-reviewer-failure-threshold.md:41-43`)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The harness description still reads like classic “half the intended panel” / “exactly 50%” boundary coverage, which no longer matches a **six-of-six** intended static failure scenario for `half_fail_hard` under the six-slot denominator; the blurb should describe multi-record fixtures and threshold edge cases under the six-slot math (or drop the “exactly 50%” phrasing).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Update the Harness sentence to describe threshold edge cases under the six-slot denominator or avoid the phrase exactly 50%.

### FINDING_3: SIMPLE harness still uses seven-record fixtures and `--launched-slots 7` against a six-slot intended model (`test-check-reviewer-failure-threshold.sh`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Harness paths still use **seven** collector records and/or **`--launched-slots 7`** with labels like “2 of 7” / “4 of 7” while `INTENDED_SLOTS` is **6**, so expectations can depend on **never-launched** clamping rather than mirroring production dispatch; maintainers may assume seven static SIMPLE slots or that launched-slots must exceed intended. Clarifying labels vs aligning launched-slots/record counts to six addresses the drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: No regression anchor for six launched slots with NOT_SUBSTANTIVE-only failure mix (`test-check-reviewer-failure-threshold.sh`)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no dedicated regression case for **six launched** static slots combined with a **NOT_SUBSTANTIVE-only** failure mix of the kind that motivated the issue; if never-launched / denominator math regresses, the bug class could slip back without a direct harness anchor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional minimal case mirroring issue-style six-slot launched NOT_SUBSTANTIVE scenario

### OOS_1: [OUT_OF_SCOPE] Unused round-num parsing for static intended slots after six-slot flattening (`check-reviewer-failure-threshold.sh:203-219`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Round-number parsing remains unused for `STATIC_INTENDED_SLOTS` after flattening to six; no functional bug, slightly widens CLI surface; acceptable to leave per plan or remove in a follow-up that updates callers if desired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Implement run log / diff noise commits alongside threshold work (`larch-logs/implement/…`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-doc-completeness-output.txt, dyn-test-slot-mismatch-output.txt
- **Severity**: nit
- **Concern**: The branch adds tracked implement run-log material (metadata, embedded plan, large trees) next to the threshold fix; orthogonal to threshold correctness if the PR is meant to be minimal script+docs-only, but policy may treat run logs as intentional noise reviewers can ignore for this review type.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-doc-completeness-output.txt, dyn-test-slot-mismatch-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] No invariant tying counted static records to six-slot intended baseline when `--launched-slots` omitted (`check-reviewer-failure-threshold.sh`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Nothing ties `COUNTED_SLOTS` to `INTENDED_SLOTS` when `--launched-slots` is omitted; all static records in the file affect `FAILED_SLOTS`, so malformed or over-long collector files could skew panel-failed vs nominal six-slot reasoning; better addressed as follow-up hardening (script/collector cap vs manifest) than in this bugfix PR alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Test harness echo comments understate round-1 six-slot denominator
- **Reviewer(s)**: dyn-doc-completeness-output.txt
- **Severity**: nit
- **Concern**: Echo comments that still say “round 2+ … uses a 6-slot intended denominator” are slightly understated because round 1 uses the same denominator; minor vs stale prose in the primary `.md` and largely predates the branch in spirit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-doc-completeness-output.txt: Address the concern above.

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
