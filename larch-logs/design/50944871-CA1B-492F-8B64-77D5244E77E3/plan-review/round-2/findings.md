### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:121-139
- **Concern**: Plan limits new sidecar denials to cursor-plan-* and codex-primary-plan-* and claims claude-plan-* only needs transcript exclusion because .launch-stderr is already denied. Scenario: Both-externals-down runs write claude-plan-generic-output.txt.tsv (validate-research-output --write-structured) and claude-plan-generic-output.txt.launch-stderr; neither matches existing globs or the proposed cursor/codex-only sidecar list, so structured reviewer output and launcher stderr still publish at top level after the fix
- **Proposed resolution**: Add claude-plan-*-output*.txt.tsv plus claude-plan-*-output*.txt.launch-stderr (and .stderr-tail if failures are in scope) to design_artifact_excluded and test-design-log-publish.sh deny fixtures; correct the plan prose that says launch-stderr is already covered

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:294-308; skills/design/scripts/dispatch-plan-review-panel.sh:135-139
- **Concern**: The proposed denylist excludes the generic Claude transcript but omits generic Claude sidecars, even though the producer writes claude-plan-generic-output.txt.tsv and claude-plan-generic-output.txt.launch-stderr. Scenario: In both-externals-down plan review, publish would still commit the structured reviewer sidecar or launch stderr at the top level, leaving issue #3534 only partly fixed
- **Proposed resolution**: Extend the new claude-plan exclusion to actual generic sidecars such as claude-plan-*-output*.txt.tsv and claude-plan-*-output*.txt.launch-stderr, and add matching test-design-log-publish fixtures/assertions

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/design-log-publish.sh:303-308; skills/design/scripts/dispatch-plan-review-panel.sh:97-139
- **Concern**: The proposed denylist omits sidecars that the both-externals-down generic Claude plan reviewer actually writes.. Scenario: When Codex and Cursor are both absent, dispatch-plan-review-panel.sh writes claude-plan-generic-output.txt.launch-stderr and structured validation can create claude-plan-generic-output.txt.tsv or collect-agent-results can create claude-plan-generic-output.txt.jsonl; the plan drops only the .txt transcript, so these sidecars still pass design-log-publish.sh default-allow staging and get committed.
- **Proposed resolution**: Include the real claude-plan-*-output*.txt sidecar suffixes in the new exclusion branch and add fixtures for at least .launch-stderr plus the structured sidecar path used by the generic reviewer.

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:99-138; scripts/design-log-publish.sh:303-308
- **Concern**: Plan omits real generic Claude sidecars from the new deny patterns. Scenario: When both externals are absent, dispatch-plan-review-panel writes claude-plan-generic-output.txt.launch-stderr and, on structured validation, claude-plan-generic-output.txt.tsv. The proposed deny list excludes only claude-plan-*-output*.txt, so these raw reviewer sidecars still publish at the top level.
- **Proposed resolution**: Extend the new design_artifact_excluded branch, docs, and test fixtures to exclude at least claude-plan-*-output*.txt.launch-stderr and claude-plan-*-output*.txt.tsv. Include claude .jsonl too if keeping collector-supported generic structured sidecars covered.

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/design-log-publish.sh:294-309
- **Concern**: Proposed exclusion omits claude-plan launch stderr even though generic Claude plan-review writes claude-plan-generic-output.txt.launch-stderr. Scenario: When both external reviewers are unavailable, the raw Claude transcript is skipped but its launcher stderr sidecar still publishes at the top level because existing globs do not match *.launch-stderr
- **Proposed resolution**: Add claude-plan-*-output*.txt.launch-stderr to the new deny branch and add a test fixture asserting claude-plan-generic-output.txt.launch-stderr is absent

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:121-139
- **Concern**: Plan omits claude-plan-generic reviewer sidecars from the new top-level denylist. Scenario: The both-externals-down path writes claude-plan-generic-output.txt.tsv (validate-research-output --write-structured) and claude-plan-generic-output.txt.launch-stderr; launch-claude-review can also leave claude-plan-generic-output.txt.stderr-tail. The plan only denies claude-plan-*-output*.txt transcripts and claims .done/.launch-stderr are already excluded, but design_artifact_excluded has no *.launch-stderr glob and no claude sidecar arms—so structured reviewer sidecars still publish on the degraded plan-review path after the fix
- **Proposed resolution**: Add claude-plan-*-output*.txt.tsv / .launch-stderr / .stderr-tail (or equivalent anchored arms) to design_artifact_excluded, document in design-log-publish.md, and pin with claude-plan-generic-output.txt.tsv and .launch-stderr fixtures in test-design-log-publish.sh

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-producer-names
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:121-138
- **Concern**: Plan treats claude-plan-* as transcript-only and claims .launch-stderr is already denied. Scenario: Both-externals-down runs write claude-plan-generic-output.txt.launch-stderr and .tsv at top level; neither matches claude-plan-*-output*.txt and .launch-stderr is absent from design_artifact_excluded today
- **Proposed resolution**: Extend top-level deny patterns (and test-design-log-publish.sh fixtures/assertions) to exclude claude-plan-*-output*.txt.launch-stderr and claude-plan-*-output*.txt.tsv; drop the incorrect already-covered-by-existing-globs claim in plan.txt

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-producer-names
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:97-121,135-139; scripts/collect-agent-results.sh:1284-1289; scripts/launch-claude-review.sh:162-210
- **Concern**: The plan treats claude-plan-* as transcript-only, but real producers create claude-plan generic sidecars: .launch-stderr, .stderr-tail on failure, .tsv, and collector .jsonl. Scenario: When both external reviewers are down, design-log-publish would exclude claude-plan-generic-output.txt but still stage claude-plan-generic-output.txt.launch-stderr/.stderr-tail/.tsv/.jsonl
- **Proposed resolution**: Add only the producer-backed claude-plan sidecar globs to the proposed branch and fixtures: claude-plan-*-output*.txt.launch-stderr, .stderr-tail, .tsv, and .jsonl

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-producer-names
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/collect-agent-results.sh:1284-1286,1403-1405; scripts/launch-review.sh:548-550
- **Concern**: The proposed cursor-plan-* and codex-primary-plan-* .jsonl exclusions lack producer evidence: structured validation writes .tsv for cursor/codex, while Codex JSONL is .events.jsonl already covered. Scenario: This adds a dead pattern while the issue is trying to remove stale producer names, increasing deny-list scope without a current artifact to test
- **Proposed resolution**: Drop cursor/codex .jsonl from the new sidecar list unless a real producer is added; keep existing *.events.jsonl coverage and use .jsonl only for the claude/unknown collector path if covered

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-artifact-policy
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:121-139 scripts/design-log-publish.sh:303-308
- **Concern**: Plan limits claude-plan-* to transcript-only and claims .launch-stderr is already denied by existing top-level globs, but the both-externals-down generic panel also writes claude-plan-generic-output.txt.launch-stderr and claude-plan-generic-output.txt.tsv and design_artifact_excluded has no *.launch-stderr pattern today. Scenario: When Codex and Cursor are both absent, degraded plan-review still commits generic Claude stderr/structured sidecars at larch-logs/design/<run-id>/ while cursor/codex raw outputs are excluded, leaving the top-level canonical-vs-raw contract inconsistent across panel modes
- **Proposed resolution**: Add claude-plan-*-output*.txt.launch-stderr and claude-plan-*-output*.txt.tsv (and .stderr-tail if produced) to the new design_artifact_excluded branch; extend test-design-log-publish.sh deny assertions; correct design-log-publish.md and lib-design-round-artifacts.md prose that says launch-stderr is already covered

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-artifact-policy
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:294-308; skills/design/scripts/dispatch-plan-review-panel.sh:114-121,135-139; scripts/collect-agent-results.sh:1284-1289; scripts/launch-claude-review.sh:162-210
- **Concern**: The proposed denylist treats claude-plan-* as transcript-only even though real Claude generic plan-review sidecars exist. Scenario: When both externals are absent, the producer can write claude-plan-generic-output.txt.launch-stderr and claude-plan-generic-output.txt.tsv, and failed Claude launches can write .stderr-tail. The current suffix denylist only catches .done, so the proposed cursor/codex-only sidecar branch would still publish non-canonical Claude reviewer artifacts beside findings.md and voting-tally.md.
- **Proposed resolution**: Extend the proposed top-level plan-review exclusion, docs, and tests to cover real Claude generic sidecars at minimum claude-plan-*-output*.txt.launch-stderr, .stderr-tail, and the structured .tsv/.jsonl sidecar shape, or remove the false transcript-only claim.

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-artifact-policy
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/design-log-publish.sh:331-332,524-545; scripts/design-log-publish.md:224-231
- **Concern**: Placing producer-name transcript patterns inside design_artifact_excluded changes render-cache staging too. Scenario: design_publish_stage_file calls design_artifact_excluded for render-cache files, while the plan is motivated by top-level plan-review transcripts and the render-cache contract says its open schema keeps only the existing suffix denylist. A render-cache file with a matching cursor-plan-/codex-primary-plan-/claude-plan- basename would be silently dropped outside the stated top-level scope.
- **Proposed resolution**: Keep the new producer-name transcript exclusion on the maxdepth-1 top-level staging path, or pass a context flag so render-cache keeps its current suffix-only exclusion contract unless the plan explicitly documents and tests that broader policy change.

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-fixture-realism
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:24-25,scripts/test-design-log-publish.sh:507-520
- **Concern**: Planned deny fixtures omit cursor-plan-arch-output.txt.tsv even though the new exclusion arm covers cursor-plan-* sidecars and committed runs leak that basename. Scenario: An implementer could wire codex-primary-plan-*-output*.txt.tsv but omit or typo the cursor-plan-* sidecar alternation; the happy-path deny loop would still pass because only codex .tsv is asserted absent
- **Proposed resolution**: Add cursor-plan-arch-output.txt.tsv to the fixture-creation block and deny-list assertion loop alongside codex-primary-plan-arch-output.txt.tsv

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-fixture-realism
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:24-25,scripts/dispatch-with-waterfall.sh:191-200
- **Concern**: Phased transcript deny coverage pins only codex-primary-plan-arch-output-phase2.txt; cursor-plan-arch-output-phase2.txt is a real top-level producer/commit leak but has no fixture. Scenario: Regression that drops cursor-plan-*-output*.txt while leaving codex-primary-plan-*-output*.txt would not be caught by the phased assertion (only one vendor pinned)
- **Proposed resolution**: Add cursor-plan-arch-output-phase2.txt to the new transcript fixtures and deny-loop assertions

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-fixture-realism
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:294-308; skills/design/scripts/dispatch-plan-review-panel.sh:114-121,135-139
- **Concern**: Plan omits real Claude fallback sidecars from the new exclusion/test coverage. Scenario: dispatch-plan-review-panel.sh writes claude-plan-generic-output.txt.launch-stderr and, on successful validation, claude-plan-generic-output.txt.tsv; the plan excludes only the .txt transcript for claude-plan-* and incorrectly treats launch-stderr as already covered, so both sidecars can still be staged
- **Proposed resolution**: Extend the planned branch and fixtures/assertions to exclude claude-plan-*-output*.txt.tsv and claude-plan-*-output*.txt.launch-stderr; include stderr-tail too if failed Claude reviewer tails are in scope

### OOS_1:
- **Description**: Plan states claude-plan-* .launch-stderr is already denied by existing globs, but design_artifact_excluded has no *.launch-stderr arm; the both-externals-down path also writes claude-plan-generic-output.txt.tsv which is outside the cursor/codex-only sidecar list. Scenario: Degraded runs can still flush claude-plan-generic-output.txt.launch-stderr and .tsv to larch-logs/design even after the main fix
- **Reviewer**: Cursor-dyn-fixture-realism
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:13,skills/design/scripts/dispatch-plan-review-panel.sh:99-138,scripts/design-log-publish.sh:303-308
- **Phase**: design
