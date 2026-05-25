### OOS_1: [OUT_OF_SCOPE] Duplicate manual key lists without drift automation (`#2753`)

- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `write_initial_state` vs `require_key` (and related) remain as separate manual key lists without drift automation per `#2753`; future keys added only on one side could slip past review until runtime or tests fail—optional small follow-up only if this PR is intended to close that gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] `DESIGN_ONLY_DONE` state transition in `ship-pr.sh`

- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `DESIGN_ONLY_DONE` never transitions in `ship-pr.sh` today; not judged to produce wrong output from this diff unless product intent is to drive this key from `ship-pr` later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

---


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] Large `larch-logs/**` diffs alongside functional changes (review noise)

- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Large committed run-log trees/commits accompany the branch but sit outside enumerated ship-pr code edits, increasing review paging noise and time on unrelated log diffs; acceptable per repo policy, but splitting or separating log commits from functional review helps when hygiene matters; no plan-fidelity gap for the validator plan’s code requirements.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_4: [OUT_OF_SCOPE] State file trust model (`ship-pr.sh`)

- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The state file remains a high-trust writable input for the implement session; `require_key` / `is_bool` extensions do not authenticate the writer or sanitize path-like values—pre-existing trust boundary, largely unchanged beyond stricter key presence and extra boolean checks; hardening belongs to a dedicated state-integrity or path-canonicalization effort, not required for this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

---

**Merge notes (for voters, not separate findings):**

- **FINDING_1** subsumed source ids **1, 5, 14** (plan/listing/traceability and “not in three-file plan” overlap; max severity important).
- **FINDING_2** subsumed **2, 7, 10, 12** (same behavioral risk: automatic `npm ci` / Mermaid bootstrap side effects and prerequisites; max severity important).
- **FINDING_3** kept **3** alone (formatting-only).
- **FINDING_4** merged **8, 13** (same doc path and reader confusion class; max severity nit).
- **OOS_3** merged **9, 15** (both `larch-logs` volume vs functional review noise; max severity nit).

Every merged block includes exactly one `- **Severity**:` line. No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).

Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

