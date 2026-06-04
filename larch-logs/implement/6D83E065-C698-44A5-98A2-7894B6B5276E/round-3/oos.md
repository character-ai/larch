### FINDING_12: [OUT_OF_SCOPE] pr-prep disposition gate omits strict filed-URL input
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-python-bash-parity-output.txt
- **Severity**: latent
- **Concern**: The internal pr-prep disposition gate omits `--filed-urls-strict-file` used by the checkpoint/Python paths, so rare all-empty accepted-OOS cases may count filed URL evidence differently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-python-bash-parity-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_13: [OUT_OF_SCOPE] Security predicate/docs/test pins are inconsistent around materializer routing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-bash-state-output.txt, dyn-manifest-materializer-output.txt
- **Severity**: latent
- **Concern**: Out-of-scope reviewers also noted that the materializer’s broader security predicate is not consistently documented or pinned by structure tests, increasing drift risk after the policy is resolved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-bash-state-output.txt, dyn-manifest-materializer-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_17: [OUT_OF_SCOPE] Public issue/redaction stack has pre-existing coverage gaps
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-public-redaction-output.txt
- **Severity**: latent
- **Concern**: Pre-existing `/issue` and redaction boundaries still trust incomplete sanitization coverage for secrets, opaque tokens, internal URLs, and other sensitive text that may flow through public OOS paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-public-redaction-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] Python reimplements the OOS disposition gate
- **Reviewer(s)**: dyn-python-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `python/oos.py` duplicates gate behavior instead of invoking the shell gate, creating long-term drift risk outside the immediate branch regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-bash-parity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] Disjunctive gate pass can mask per-block disposition gaps
- **Reviewer(s)**: dyn-log-evidence-output.txt
- **Severity**: latent
- **Concern**: Pre-existing gate logic can pass when `filed_urls > 0` even if not every non-security OOS block has coverage. This is not introduced by the branch but interacts with all-already-filed evidence handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-log-evidence-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_32: [OUT_OF_SCOPE] Exact run-statistics command pin is brittle
- **Reviewer(s)**: dyn-grep-guards-output.txt
- **Severity**: nit
- **Concern**: The structure harness pins one long exact `larch-log.sh write … --batch run-statistics` string, so harmless flag reordering could fail CI without changing the contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-guards-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_33: [OUT_OF_SCOPE] Makefile harness registration appears consistent
- **Reviewer(s)**: dyn-grep-guards-output.txt
- **Severity**: nit
- **Concern**: The reviewer noted `test-materialize-manifest-oos` registration looked consistent with existing Makefile shard patterns and did not appear to be registration drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-guards-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] OOS grouping reference lacks executable Rule B / criteria detail
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The expanded OOS reference lacks detailed combine mechanics for Rule B and criteria 1–4, leaving operators to rely on LLM judgment beyond Rule A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] DESIGN_TMPDIR prose omits the file-exists guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 1 prose says to use `$DESIGN_TMPDIR/oos-accepted-design.md` when `$DESIGN_TMPDIR` is set, but runtime resolvers fall through unless that file exists. Prompt-side readers could choose the wrong empty path and miss `design-export/` OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

