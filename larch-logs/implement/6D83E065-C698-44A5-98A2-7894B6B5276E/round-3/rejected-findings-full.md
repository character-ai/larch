### [rejected] FINDING_15

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_15: `has_title` passes untrusted titles through `awk -v`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Manifest titles are passed into awk via `-v wanted="$key"` without escaping. Quotes or metacharacters in untrusted manifest input can break deduplication or cause incorrect skip/merge behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Materialization has no upper bound on manifest OOS array size
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `materialize-manifest-oos.sh` processes `oos_observations[]` without a count/size cap, allowing large manifests to exhaust disk or CPU before later issue-cap logic runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Duplicate normalized titles can silently drop distinct manifest OOS
- **Reviewer(s)**: dyn-manifest-materializer-output.txt
- **Severity**: latent
- **Concern**: Idempotency skips observations whose normalized title already exists in accepted markdown. Distinct entries with colliding titles/descriptions are silently dropped without warnings or tool-failure evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-manifest-materializer-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Sentinel-recovery NDJSON writing ownership is duplicated
- **Reviewer(s)**: dyn-log-evidence-output.txt
- **Severity**: latent
- **Concern**: `oos-pipeline.md` assigns sentinel-recovery NDJSON append responsibility in both step 3 and step 6. An orchestrator following both can append duplicate evidence rows and skew run-log statistics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-log-evidence-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: Security-relevant manifest prose without a field marker can enter public OOS
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: Manifest descriptions that discuss a real security issue but lack the exact dedicated focus-area field line can be written to `oos-accepted-main-agent.md` and become eligible for public filing, despite schema expectations that manifest OOS excludes security findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: Step 2 structure guard does not prove materialization runs on the complete path
- **Reviewer(s)**: dyn-grep-guards-output.txt
- **Severity**: latent
- **Concern**: The structure test only checks that `step2-implement.sh` mentions the materializer, not that it runs inside the `STATUS=complete` branch and before final completion emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-guards-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Design OOS path resolution is triplicated across bash, Python, and docs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The design OOS accepted-file resolver appears independently in bash, Python, and prose. A future resolver change could fix one path while leaving another stale, recreating the class of regression under review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: Partial-failure negative check uses a narrow line window
- **Reviewer(s)**: dyn-grep-guards-output.txt
- **Severity**: latent
- **Concern**: The assertion around `ISSUES_FAILED>0` scans only a small window, so later prose could reintroduce forbidden accepted-disposition appends outside that window without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-guards-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_31: Global OOS-pipeline load count is an imprecise wiring signal
- **Reviewer(s)**: dyn-grep-guards-output.txt
- **Severity**: nit
- **Concern**: `load_count >= 3` counts any `oos-pipeline.md` mention, including cross-references, rather than only mandatory Step 9a.1 entry-point directives. It can give false confidence if scoped guards are weakened.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-guards-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Manifest OOS count logic is duplicated at multiple hook sites
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Identical jq-based manifest OOS counting is duplicated in multiple runtime paths. Future policy changes could require coordinated edits in several places.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Python tool-failure appending can diverge from the shell helper and drop repeated failures
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `_append_execution_tool_failure` duplicates `append-tool-failure.sh` behavior and deduplicates weakly by tool name, so repeated failures at different sites can be skipped or logged inconsistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Structure tests rely on brittle line-window scanners for mandatory OOS-pipeline loads
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: New structure assertions use fixed awk line windows. Prompt refactors that move load directives outside the window could fail CI without semantic regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

