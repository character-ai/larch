Here is the normalized aggregator output. Eighteen raw inputs are merged into nine findings. Every input `Suggested revision` was the generic phrase “Address the concern above.” with no distinct fix text, so the **Suggested revisions** blocks are omitted per your rules (no fabricated bullets).

### FINDING_1: Design skill title lifecycle around clarify 3.5 vs Step 5b/5.5
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The clarify sub-step 3.5 flow can rename to `--state designed` before Step 5b completes, opening a window where the issue title reads `[DESIGNED]` while `/design` is still mid–Step 0 / tier gating / not yet at Gate C / Step 5b semantics. In that window a concurrent `/implement` can satisfy admission (`has_designed_prefix`) and Preflight using a clarify-time `larch:plan` that may still be superseded until Step 5b’s composed plan exists—so implementation could proceed off the wrong plan until Step 5.5 demotes the title back to `[DESIGNING]`. Separately, the success path can run designing→designed renames back-to-back; a partial failure after publish/clarify can leave the title at `[DESIGNING]` while the skill treats publish/clarify as complete, so later `/implement` fails managed-prefix checks and operators may believe `/design` is still active. Prose in 3.5 also ties the `[DESIGNED]` rename to `needs-design-clarification` still being present even though 3.4 removes that label, and it mixes rationale in ways that contradict Step 5b’s meaning of `[DESIGNED]`, so operators cannot tell when `[DESIGNED]` is authoritative vs “still in flight.” Finally, `[DESIGNING]` is touched in both 3.5 and Step 5.5, which is redundant and adds extra `gh` traffic unless intentionally documented.

### FINDING_2: Unrelated changes stacked with prefix/state-machine work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The divergent branch range mixes unrelated items (e.g. #2595 argv/doc cleanup, MAJOR semver bump, large `larch-logs/` flush) with tracking-prefix / title state-machine behavior. That raises bisect/revert cost, muddles the consumer-facing semver story, and forces reviewers to untangle multiple issue tracks in one PR instead of reviewing a focused change.

### FINDING_3: Written “zero grep hits” acceptance vs allow-listed literals and harness
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Written acceptance still reads like a naive “`git grep` finds no `[IN PROGRESS]` / `[PLANNED]` outside CHANGELOG/`larch-logs`” rule, but the branch deliberately keeps literals in runtime files and gates behind an allow list exercised by `scripts/test-legacy-title-prefix-literals-scope.sh`. Checklists or reviewers running the literal naive grep therefore get non-zero hits despite a green harness. The harness’s allow list is also reported to omit some files that still contain those literals (e.g. `combinable-issues-title-filter.jq` comments and the harness itself), which can make `make test-legacy-title-prefix-literals-scope` / lint shard `test-harnesses-5` fail until paths are allow-listed or literals are removed from comments. Documentation (`docs/linting.md`) and tracking-plan acceptance bullets are not consistently pointed at the harness as the source of truth, so plan-vs-branch reviewers may mark work “incomplete” against stale acceptance language.

### FINDING_4: [OUT_OF_SCOPE] Resume sentinel skips stricter admission checks
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: In `scripts/implement-admission.sh`, the resume sentinel path still skips audit-label and `[DESIGNED]` checks while re-checking blockers/report title—an intentional historical trade-off for crash resume, with semantics otherwise unchanged aside from new documentation bullets. Tightening resume gates is a product decision, not implied by the prefix work alone.

### FINDING_5: `combinable-issues-title-filter.jq` legacy titles and canonical formatting assumptions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The jq title filter excludes legacy `[PLANNED]` / `[IN PROGRESS]` busy prefixes beyond the four-token plan snippet, so operators with only legacy planned titles may expect combine-issues to treat them like `[DESIGNED]` candidates but they are filtered out—product intent should be confirmed and the alternation list plus `scripts/test-fetch-combinable-issues-filter.sh` fixtures kept in sync. Separately, exclusion logic that requires `] ` after the managed prefix token means legacy or hand-edited titles missing that canonical spacing can bypass exclusion and be merged incorrectly; tightening the regex or adding targeted fixture coverage trades false-positive risk for stricter matching.

### FINDING_6: `implement-admission` diagnostic ordering (`has-blockers` vs missing designed prefix)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: The blocker gate runs before the missing-`[DESIGNED]`-prefix style checks, so issues that never completed `/design` can surface `has-blockers` first, wasting operator time clearing blockers on issues that are not `/implement`-eligible until `/design` finishes. Either document precedence or reorder non-resume checks if clearer diagnostics justify behavior change.

### FINDING_7: [OUT_OF_SCOPE] Run-log version bump reasoning mixes unrelated MAJOR evidence
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `larch-logs/implement/94F28FCE-9328-44FD-8A55-4FF078A45188/version-bump-reasoning.md` cites dynamic-archetypes argv removal as MAJOR evidence in a committed run log, which reads as unrelated noise versus why `40.0.0` shipped for the prefix feature. Optional curation if implement artifacts are edited before merge.

### FINDING_8: `implement-admission.sh` header comment incomplete vs Step-0 gate contract
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The script banner omits the newer `[DESIGNED]` precondition from the summarized validation set, so operators who read only the header miss part of the Step-0 gate contract; it should mirror the bullet list in `implement-admission.md`.

### FINDING_9: [OUT_OF_SCOPE] `agents/` audit scope has no branch diff
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The plan listed `agents/` in audit scope, but the tree has no legacy literals and no agent file changes on this branch—pre-existing layout, not introduced here.

---

Because this output contains one or more `### FINDING_N:` blocks, **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** anywhere in this response.
