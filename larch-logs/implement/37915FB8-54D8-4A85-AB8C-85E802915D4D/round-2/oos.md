### FINDING_1: [OUT_OF_SCOPE] Issue body redaction and trim measure a different body than gh posts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-issue-body-output.txt
- **Severity**: important
- **Concern**: Issue body assembly applies redundant redaction passes before trimming, and `gh.issue_create` may redact again before posting. This violates the single-pass contract and can make byte-limit trimming or PEM fail-closed behavior diverge from the exact body sent to GitHub.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-issue-body-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_10: [OUT_OF_SCOPE] Plot child accepts malformed series/schema and can succeed with partial or empty plots
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: `plot-cost-over-time.py` does not fully validate the documented payload contract and skips malformed series entries, allowing wrong labels, missing version/skill, extra series, or zero PNG output to appear successful.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-plot-isolation-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_11: [OUT_OF_SCOPE] LARCH_REPORT_TOKENS_LIMIT counts raw directories instead of valid/unique runs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-scan-pipeline-output.txt
- **Severity**: latent
- **Concern**: The scan limit is applied to immediate child directories before eligibility filtering and without unique issue semantics, so placeholder or invalid directories can consume the limit and hide valid runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-scan-pipeline-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] Report-tokens operator failures reuse the stalled/bail exit code
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Report-tokens errors use an exit code that overlaps with stalled/bail constants, so wrappers cannot reliably distinguish operator or gh failures from stalled runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_26: [OUT_OF_SCOPE] Cache JSON stdout path can leak temp/session paths
- **Reviewer(s)**: dyn-issue-body-output.txt
- **Severity**: latent
- **Concern**: Stdout still appends an unredacted `Cache JSON: {temp_path}` line, which can expose session temp paths in terminal transcripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-body-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_29: [OUT_OF_SCOPE] Missing timing/run-params warnings are a plan/parity drift
- **Reviewer(s)**: dyn-scan-pipeline-output.txt
- **Severity**: latent
- **Concern**: Missing timing or run-params JSON still defaults workflow to unknown without warning; this matches prior bash behavior but conflicts with stricter plan wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scan-pipeline-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_31: [OUT_OF_SCOPE] Plot subprocess contract is not exercised by tests
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: Plot tests rely on fake Runner paths or optional smoke coverage, so the real child contract, especially design dual-series behavior and `MPLCONFIGDIR`, can drift without mandatory CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_32: [OUT_OF_SCOPE] LARCH_REPORT_TOKENS_NO_OPEN flag parsing is inconsistent
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: nit
- **Concern**: `LARCH_REPORT_TOKENS_NO_OPEN` treats any nonempty value as truthy/falsey via raw env lookup semantics, unlike the more explicit flag parsing used for `NO_PLOT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] Non-object manifest.json reports the wrong skip reason
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A malformed `manifest.json` with a non-dict JSON value is reported as lacking a numeric `issue_number` instead of as an invalid manifest shape, making corrupt manifests harder to diagnose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

