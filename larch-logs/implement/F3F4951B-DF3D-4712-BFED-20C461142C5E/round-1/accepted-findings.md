### FINDING_1: Fenced collect-agent-results example conflicts with conditional path rules
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The fenced collector example always passes two paths while surrounding prose requires omitting non-external slots, forbidding zero-path calls, and matching Step 2a-style dynamic argv. An orchestrator that copies the fence can invoke the collector on paths that were never launched as externals, hit wrong or empty files, or fail to reconcile the example with Step 2a.3-style guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Replace static fence with one-path/two-path examples and explicit copy-paste warning tied to actual launches.


### FINDING_12: `.brainstorm-done` short-circuit skips without the same visibility as `brainstorm_requested=false`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The sentinel-hit path can short-circuit without the visible skip breadcrumb used when brainstorm is disabled, making re-entry logs look like silent no-ops and incident triage harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Emit a distinct skip breadcrumb for sentinel-hit path.


### FINDING_2: Scope vs framing output paths ambiguous under waterfall and lane swaps
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Under waterfall fallback and non-deterministic lane or tool order, slot-to-output filename mapping is unclear: operators may write synthesis inputs to the wrong deterministic path, parent writes may target the wrong canonical file, the same vendor output path may be reused twice, or framing and scope roles may be mixed in synthesis. Non-deterministic “adjust” language for output filenames exacerbates ambiguity when lanes swap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Pin canonical per-slot filenames independent of which vendor executed, or use distinct staging files per slot.


### FINDING_3: Step 1d.5 breadcrumb UX: duplicates and premature banner on skip paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Step 1d.5 start messaging is duplicated when both the SKILL and brainstorm.md entry guard print a start line; operators following both files literally can print the same step-start twice. Separately, the orange step banner can print before brainstorm.md decides to skip (e.g. off-path `/design --simple`), so acceptance wording that only names the skip line may not match visible logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Gate timing/print on brainstorm_requested or reorder so skip is the only user-visible 1d.5 line when skipped.
  - From cursor-specialist-plan-fidelity-output.txt: Remove one of the duplicate Print directives (prefer deleting brainstorm.md entry-guard step 4 or not printing in SKILL before the reference runs)


### FINDING_4: Released [42.4.16] changelog understates shipped /design --brainstorm surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Release notes for [42.4.16] call out other changes (e.g. ship-pr key drift harness) but omit the public `--brainstorm` / `brainstorm_requested` / Step 1d.5 behavior shipped on the branch, so operators relying on the changelog may miss user-visible behavior for that version tag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Add a concise Changed bullet for --brainstorm / Step 1d.5 aligned with the version bump.
  - From cursor-specialist-edge-cases-output.txt: Add bullet or adjust versioning per changelog policy.


### FINDING_8: `plan-review-loop.sh` merges `brainstorm.md` into plan-review context without tests guarding the contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The script merges `brainstorm.md` into `plan-review-feature-context.txt` before scout/panel, but tests never create `brainstorm.md`, assert merged output, or validate `--feature-file` wiring. A refactor could drop the merge, reorder it after validation, or pass the wrong path while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a stubbed tmpdir scenario with non-empty brainstorm.md plus assertions on the merged artifact and/or a dispatch stub that logs the resolved --feature-file path.


