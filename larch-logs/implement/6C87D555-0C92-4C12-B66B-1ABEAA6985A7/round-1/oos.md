### FINDING_13: [OUT_OF_SCOPE] compose_prompt mktemp failure without LINT_FIX_STATUS KV
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Same excerpt `mktemp` failure class as in-scope FINDING_1, flagged out of scope for this review pass: rare temp failure aborts with generic exit 1 only instead of `fail_status` with a dedicated `FAILURE_REASON` (e.g. `prompt-excerpt-failed`).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_14: [OUT_OF_SCOPE] concatenated multi-run logs could mis-infer phase
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Not introduced by this branch; `scripts/relevant-checks.sh` unchanged (lines 317–322). Concatenated multi-run logs could mis-infer phase; address only if the capture layer appends multiple runs.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_15: [OUT_OF_SCOPE] committed implement run-log tree outside plan scope
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `larch-logs/implement/6C87D555-…` — committed run-log tree from `/implement` is outside this feature’s plan scope; per review policy, not treated as plan drift.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] Case 15 fixtures weaker than plan “on-disk fixture” wording
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan Case 15 describes on-disk fixtures with backtick/leading-dash names; the harness only places those strings in the checks log (filters still exercised). Acceptable for prompt-composition coverage; slightly weaker than plan fixture wording.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_17: [OUT_OF_SCOPE] spaced-path edge case and acceptance runs not executed
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `In [^ ]+ line` cannot extract shellcheck paths with spaces; plan lists this as an acceptable under-match failure mode. Acceptance items requiring `bash scripts/test-lint-fix-loop.sh`, `test-prompt-template-invariants.sh`, `test-implement-structure.sh`, and `relevant-checks.sh` were not executed in read-only review; test structure matches the plan on inspection only.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (for voters, not machine output):**

| Merged inputs | Rationale |
|---|---|
| 1 + 18 | Same mktemp/`fail_status` gap at `compose_prompt` / line 526 |
| 2 + 6 + 16 | Same broad slash grep at line 111 |
| 5 + 12 | Same missing phase-gating test |
| 7 + 15 | Same spaced-path regex gap at line 99 |
| 9 + 14 | Same process-substitution status swallowing at lines 150–153 |
| 11 kept OOS | Same risk as FINDING_1 but source tagged `[OUT_OF_SCOPE]` — not merged into in-scope block per OOS heading rule |

Input FINDING_11 (OOS duplicate of FINDING_1) is retained as FINDING_13 rather than subsumed, because the OOS tag must remain visible for Piece 2 round-trip. All other inputs are accounted for in the table above.

No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line — structured findings are present.

Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

