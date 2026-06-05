### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/design-log-publish.sh:294-309
- **Concern**: Proposed transcript denylist omits the Claude generic .meta sidecar. Scenario: When both external reviewers are unavailable, skills/design/scripts/dispatch-plan-review-panel.sh writes claude-plan-generic-output.txt and launch-claude-subprocess.sh produces claude-plan-generic-output.txt.meta; the plan excludes the raw transcript and stderr sidecars but would still publish this producer metadata sidecar at the top level
- **Proposed resolution**: Add claude-plan-*-output*.txt.meta to the new exclusion branch, add a claude-plan-generic-output.txt.meta fixture/assertion in scripts/test-design-log-publish.sh, and include the suffix in the SECURITY.md and scripts/design-log-publish.md publication-boundary text

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/design-log-publish.sh:294-309; scripts/launch-review.sh:1140-1157; scripts/dispatch-with-waterfall.sh:191-201,459-461
- **Concern**: Plan omits codex-primary-plan-*-output*.txt.json from design_artifact_excluded. Scenario: Waterfall phase-2 runs Cursor against codex-primary-plan-*-output-phase2.txt (and ns-retry variants); launch-review.sh always copies Cursor bytes to ${OUTPUT}.json. Those sidecars still pass *-output*.json strip-and-commit, so reviewer JSON/metadata keeps publishing after transcript exclusion
- **Proposed resolution**: Add codex-primary-plan-*-output*.txt.json to the new deny branch; pin codex-primary-plan-arch-output-phase2.txt.json (or -ns-retry) in scripts/test-design-log-publish.sh; update design-log-publish.md / SECURITY.md; drop the dead-pattern claim in the plan Edge cases section

### FINDING_3:
- **Reviewer(s)**: Codex-Edge, Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/design-log-publish.sh:294-311; scripts/launch-claude-subprocess.sh:192-197
- **Concern**: Plan omits the Claude .meta sidecar from the new raw plan-review exclusion. Scenario: When both external reviewers are absent, dispatch-plan-review-panel writes claude-plan-generic-output.txt and launch-claude-subprocess always writes claude-plan-generic-output.txt.meta. design_artifact_excluded currently default-allows .meta, so the publish PR would still commit a producer sidecar while the docs/security boundary says producer-backed sidecars stay out.
- **Proposed resolution**: Add claude-plan-*-output*.txt.meta to the new exclusion branch and include a matching fixture/assertion plus doc and SECURITY.md wording.

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/design-log-publish.sh:294-309; scripts/launch-claude-subprocess.sh:188-193
- **Concern**: Plan omits claude-plan-* .meta sidecars even though the Claude subprocess producer writes them for every output. Scenario: In the both-externals-down path, claude-plan-generic-output.txt is excluded after the PR, but claude-plan-generic-output.txt.meta remains default-allowed and can still be committed as operational sidecar data, contradicting the proposed producer-backed sidecar publication boundary
- **Proposed resolution**: Add claude-plan-*-output*.txt.meta to the new exclusion branch and include matching test/doc/security coverage alongside the other claude-plan-* sidecars.

### FINDING_5:
- **Reviewer(s)**: Codex-dyn-artifact-taxonomy
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:97-121, scripts/launch-claude-subprocess.sh:187-192, scripts/design-log-publish.sh:303-308, <TMPDIR>/plan.txt:13-18
- **Concern**: Claude generic .meta sidecar is omitted from the proposed exclusion taxonomy. Scenario: The both-externals-down path writes claude-plan-generic-output.txt via launch-claude-review, and launch-claude-subprocess always writes ${OUTPUT}.meta; design_artifact_excluded does not currently deny .meta, so the proposed change would still stage claude-plan-generic-output.txt.meta into larch-logs/design despite the stated sidecar boundary
- **Proposed resolution**: Add claude-plan-*-output*.txt.meta to the proposed deny branch and add the matching publish-test fixture/docs entry

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-artifact-taxonomy
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/launch-review.sh:895-900, scripts/check-mid-run-dirty-tree.sh:67-70, scripts/check-mid-run-dirty-tree.sh:190-198, scripts/design-log-publish.sh:303-308, <TMPDIR>/plan.txt:18
- **Concern**: Dirty-tree auxiliary sidecars are producer-backed but not covered by the plan. Scenario: The plan relies on existing *.dirty-tree and *.untracked-baseline globs, but cursor plan-review launchers can write ${OUTPUT}.dirty-tree.tracked-paths and ${OUTPUT}.dirty-tree.new-untracked-paths when the dirty-tree check sees tracked or new untracked paths; those names do not match the current denylist or the proposed sidecar list and can be committed as operational path artifacts
- **Proposed resolution**: Add *.dirty-tree.tracked-paths and *.dirty-tree.new-untracked-paths to the existing suffix denylist, or add prefix-scoped cursor-plan-*-output*.txt.dirty-tree.tracked-paths and .new-untracked-paths arms, with publish-test fixtures

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-publication-boundary
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/plan-review-loop.sh:1011-1026; scripts/compose-collector-failure-log.sh:68-75
- **Concern**: Plan omits plan-review collector failure logs from the proposed publication denylist. Scenario: When a reviewer returns non-OK, plan-review-loop writes <slot>-collector.failure.log at the design tmpdir top level; compose-collector-failure-log includes the full reviewer output plus diag/stderr-tail/launch-stderr sections, and design-log-publish currently default-allows top-level files, so this raw transcript bundle can still be committed despite excluding *-output*.txt sidecars
- **Proposed resolution**: Add explicit top-level exclusions for plan-review collector failure logs in scripts/design-log-publish.sh, including static, dynamic, and generic/unknown slot names, and add fixtures/assertions in scripts/test-design-log-publish.sh

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-publication-boundary
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/dispatch-with-waterfall.sh:559-587; scripts/design-log-publish.sh:294-308
- **Concern**: Dropped-slot diagnostics remain publishable and can contain raw reviewer or stderr snippets. Scenario: dispatch-with-waterfall writes plan-review-slots.ndjson.output-files.dropped-slots with slot/tool/reason/snippet rows; snippets come from raw output or launch-stderr, but the proposed deny branch covers only per-output transcript sidecars, so degraded format/collector failures can still publish raw operational excerpts
- **Proposed resolution**: Add a narrow exclusion for the plan-review dropped-slots sidecar, for example plan-review-slots.ndjson.output-files.dropped-slots, and cover it in scripts/test-design-log-publish.sh

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-fixture-realism
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:11-15
- **Concern**: Plan-review sidecar deny arms do not explicitly require the same *-output*.txt anchor used for transcripts. Scenario: An implementer can mirror lib-design-round-artifacts.sh *-output.txt.<suffix> arms (scripts/lib-design-round-artifacts.sh:14); those miss phased names such as cursor-plan-arch-output-phase2.txt.meta and codex-primary-plan-arch-output-phase2.txt.tsv, which already appear in committed larch-logs/design/
- **Proposed resolution**: State in design_artifact_excluded() that every new sidecar arm uses cursor-plan-*-output*.txt.<suffix> / codex-primary-plan-*-output*.txt.<suffix> / claude-plan-*-output*.txt.<suffix>, not *-output.txt.<suffix>

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-fixture-realism
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/design-log-publish.sh:303-308; scripts/launch-claude-subprocess.sh:187-192
- **Concern**: Planned claude-plan sidecar deny list omits the real .meta sidecar. Scenario: When both external plan reviewers are unavailable, launch-claude-subprocess.sh always writes claude-plan-generic-output.txt.meta; the proposed claude-plan-* branch only lists .tsv/.launch-stderr/.stderr-tail/.stderr/.jsonl, so publish would still commit a producer-backed Claude metadata sidecar
- **Proposed resolution**: Add claude-plan-*-output*.txt.meta to the new deny branch and add a claude-plan-generic-output.txt.meta fixture/assertion in scripts/test-design-log-publish.sh

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-fixture-realism
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:98-121; scripts/design-log-publish.sh:303-308
- **Concern**: Plan treats .prompt sidecars as already excluded, but the real generic Claude prompt name is not matched. Scenario: The both-externals-down path writes claude-plan-generic.prompt, while the existing denylist only excludes *-output.txt.prompt and *-output-*.txt.prompt; the proposed change would still publish this raw plan-review prompt
- **Proposed resolution**: Add a narrow deny for claude-plan-generic.prompt or claude-plan-*.prompt and cover it with a real-name absent assertion in scripts/test-design-log-publish.sh
