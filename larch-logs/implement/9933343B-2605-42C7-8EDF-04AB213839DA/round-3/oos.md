### FINDING_12: [OUT_OF_SCOPE] `ship-pr.sh` phase-2 stall-aware retry not in this diff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Phase 2 stall policy in `scripts/ship-pr.sh` is called out as out of scope for this branch or plan gating; no breakage asserted for this review conclusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: N/A N/A
  - From cursor-specialist-edge-cases-output.txt: None


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_17: [OUT_OF_SCOPE] `launch-cursor-ci.sh` still invokes stall monitor though not the main diff hunk
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: [nit] `scripts/launch-cursor-ci.sh` unchanged in the reviewed diff but still invokes the stall monitor; architectural / plan-scope note only for this review conclusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: No code change required for review conclusion


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_19: [OUT_OF_SCOPE] `audit-scan-run.sh` only uses first column of `scans.tsv`; other columns are documentation
- **Reviewer(s)**: dyn-audit-scan-wiring-output.txt
- **Concern**: Wiring reads only the first column from `scans.tsv` and hardcodes scan paths; `type` / `pattern` columns remain documentation-only for all scans, not a regression unique to this scan row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-scan-wiring-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] `audit-compute-counters.sh` does not aggregate stall-cause scan
- **Reviewer(s)**: dyn-audit-scan-wiring-output.txt
- **Concern**: Matches the skill rule to wire counters only when a scan feeds cumulative YAML totals; batch-level stall trending would need NDJSON consumption or future counter keys if operators want that without manual NDJSON inspection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-scan-wiring-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] Static diff cannot certify executed checks / acceptance rows
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Acceptance criteria that require executed `/relevant-checks` and passing harness runs are not verifiable from a static diff in read-only review mode; certification would need logs from an implementing session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Notes on merges (for voters, not instructions):** FINDING_1 subsumed input 1, 6, and 19 (same leak surface when redactor is absent). FINDING_2 subsumed 2, 9, 14, and 24 (identical doc/`jq` concern). FINDING_3 subsumed 3 and 22 (SIGTERM–SIGKILL blocking forensics). FINDING_5 subsumed 5, 11, 17, 33, and 36 (empty diff / alternate review basis). FINDING_6 subsumed 7, 12, and 25 (unbounded git redaction in teardown). FINDING_7 subsumed 8 and 35 (`scans.tsv` column conventions). FINDING_8 subsumed 13 and 20 (`SECURITY.md` vs code). FINDING_10 subsumed 15 and 32 (`jq` and harness fixtures). FINDING_12 subsumed 10 and 27 (`ship-pr` out of scope). Input 18 was kept separate from 16 (31) because 18 is explicitly `[OUT_OF_SCOPE]` while 31 is an in-scope traceability nit. FINDING_9 (security breadth of `ps`) and FINDING_14 (plan fidelity / narrow capture) stay separate: different failure modes and different suggested directions (narrow to target tree vs broaden or re-scope the plan).

Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] Empty precomputed diff / alternate diff source for review
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-audit-scan-wiring-output.txt
- **Concern**: [nit] The launcher-supplied or cached `diff.txt` was empty (and/or merge-base `main..HEAD` empty locally), so reviewers fell back to `git diff` / `origin/main`-style ranges or general repo state instead of the capped precomputed hunks. That limits line-level branch fidelity and harness expectations for this review mode; mitigations are procedural (non-empty diff export, session cache, documentation of fallback), not necessarily in-repo code for this change set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: N/A N/A
  - From cursor-specialist-testing-output.txt: None needed in code
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-audit-scan-wiring-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

