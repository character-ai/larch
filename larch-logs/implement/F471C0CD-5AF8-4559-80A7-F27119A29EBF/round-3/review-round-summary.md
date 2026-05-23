# Review Round 3

- Mode: `diff`
- Accepted findings: 2
- Rejected findings: 0
- Exonerated findings: 4
- Neutral findings: 0

## Accepted Findings

### FINDING_1: Design skill title lifecycle around clarify 3.5 vs Step 5b/5.5
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The clarify sub-step 3.5 flow can rename to `--state designed` before Step 5b completes, opening a window where the issue title reads `[DESIGNED]` while `/design` is still mid–Step 0 / tier gating / not yet at Gate C / Step 5b semantics. In that window a concurrent `/implement` can satisfy admission (`has_designed_prefix`) and Preflight using a clarify-time `larch:plan` that may still be superseded until Step 5b’s composed plan exists—so implementation could proceed off the wrong plan until Step 5.5 demotes the title back to `[DESIGNING]`. Separately, the success path can run designing→designed renames back-to-back; a partial failure after publish/clarify can leave the title at `[DESIGNING]` while the skill treats publish/clarify as complete, so later `/implement` fails managed-prefix checks and operators may believe `/design` is still active. Prose in 3.5 also ties the `[DESIGNED]` rename to `needs-design-clarification` still being present even though 3.4 removes that label, and it mixes rationale in ways that contradict Step 5b’s meaning of `[DESIGNED]`, so operators cannot tell when `[DESIGNED]` is authoritative vs “still in flight.” Finally, `[DESIGNING]` is touched in both 3.5 and Step 5.5, which is redundant and adds extra `gh` traffic unless intentionally documented.


### FINDING_3: Written “zero grep hits” acceptance vs allow-listed literals and harness
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Written acceptance still reads like a naive “`git grep` finds no `[IN PROGRESS]` / `[PLANNED]` outside CHANGELOG/`larch-logs`” rule, but the branch deliberately keeps literals in runtime files and gates behind an allow list exercised by `scripts/test-legacy-title-prefix-literals-scope.sh`. Checklists or reviewers running the literal naive grep therefore get non-zero hits despite a green harness. The harness’s allow list is also reported to omit some files that still contain those literals (e.g. `combinable-issues-title-filter.jq` comments and the harness itself), which can make `make test-legacy-title-prefix-literals-scope` / lint shard `test-harnesses-5` fail until paths are allow-listed or literals are removed from comments. Documentation (`docs/linting.md`) and tracking-plan acceptance bullets are not consistently pointed at the harness as the source of truth, so plan-vs-branch reviewers may mark work “incomplete” against stale acceptance language.


