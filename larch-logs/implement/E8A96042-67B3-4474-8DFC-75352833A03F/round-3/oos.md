### FINDING_15: [OUT_OF_SCOPE] Pre-existing session tmpdir sourcing trust
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Pre-existing `plugin-root.env` source and session-env.sh awk in dirty-tree recovery; compromised tmpdir can execute arbitrary shell via sourced env. Out of scope for #3298.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_3: [OUT_OF_SCOPE] Non-2 wrapper exit codes fall through to envelope parse
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: [latent] Step 0 only handles wrapper exit code 2 explicitly; other non-zero codes can fall through to parse with empty or partial stdout (legacy/pre-existing). Bootstrap or wrapper may return other codes; orchestrator could continue with wrong routing. Optional hardening: exit on `_inv_rc -ne 0` (and `ne 2`) after capturing `_inv_out`.
- **Severity**: latent
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] Exit-2 handler lacks default STEP_FAILED arm (pre-existing)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Exit-2 handler has no default `STEP_FAILED` arm; unknown failure token yields exit 2 without operator message. Not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] Unquoted `IMPLEMENT_TMPDIR` in exit-2 handler
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `IMPLEMENT_TMPDIR=$_ib_tmpdir` is unquoted in the exit-2 handler. Tmpdir paths with spaces or glob characters can word-split/expand and break redacted stderr log paths or target wrong files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Quote assignment; optionally validate tmpdir path shape.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_1: [OUT_OF_SCOPE] Infra KV exports removed from Step 0 parse
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Infra KV exports removed from Step 0 parse; session-env rehydration is now source of truth. Latent only if a future prompt-side step reads infra keys from shell without rehydration. Documented; no change required for this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_2: [OUT_OF_SCOPE] Harness gap for SKILL reaction to wrapper rc=1 after bootstrap success
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `test-implement-bootstrap-invoke.sh` does not cover SKILL behavior when wrapper returns rc=1 after bootstrap success; weak regression signal for symlink/rc propagation. Optional follow-up pin in `test-implement-structure.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] Dirty-tree prose says “shared block above” but re-embeds full parse
- **Reviewer(s)**: dyn-parse-block-duplication-output.txt
- **Severity**: latent
- **Concern**: Dirty-tree item 3 says re-parse with the same block “shown above,” then re-embeds the full parse in the recovery fence instead of referencing one artifact—narrative/structure mismatch and drift class the refactor aimed to remove.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parse-block-duplication-output.txt: Address the concern above.

---

**Merge notes (for voters, not machine output):** 32 raw slots collapsed to 20 in-scope `FINDING_*` blocks plus 3 `OOS_*` round-trip items. Duplication/plan-fidelity/testing/architecture slots (1, 3, 9, 12, 23, 26, 29) → **FINDING_1** (severity **important**). Pre-existing non-2 exit propagation (4, 10) stayed **OUT_OF_SCOPE** as **FINDING_3**; in-scope edge-case variant (21) → **FINDING_16** (**important**). Exit-2 `STEP_FAILED` gaps: pre-existing default-only (5) → **FINDING_4** OOS; in-scope missing arms (8, 22) → **FINDING_7**. Unquoted tmpdir (11 OOS, 18 in-scope) merged → **FINDING_8** with **[OUT_OF_SCOPE]** on the heading per OOS+in-scope merge rule. Input **FINDING_3** (case arms) merged into **FINDING_1** as the same maintenance-risk surface.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

