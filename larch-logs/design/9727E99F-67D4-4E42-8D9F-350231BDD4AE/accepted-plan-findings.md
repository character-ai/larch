### FINDING_1: Availability globals are shadowed in coder selection
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict, Codex-dyn-deletion-completeness
- **Severity**: important
- **Concern**: Proposed `phase_coder_select` shadows the `codex_available` / `cursor_available` globals populated by `phase_infra` and checks nonexistent `*_available_from_infra` variables, causing explicit external coders to bail and implicit routing to fall through incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Remove the local availability block (plan lines 50–53); use only `codex_available` / `cursor_available` set in `phase_infra` (scripts/implement-bootstrap.sh:479-487) for routing; keep the four-key re-read solely for tri-state `*_BINARY_FOUND` classification
  - From Codex-Arch: Remove the local codex_available/cursor_available declarations or derive them directly from the four re-read probe keys; add happy-path tests where each external is available
  - From Codex-Edge: Do not redeclare local availability names; either use the existing globals directly or derive from the reread *_PRESENT and *_BINARY_FOUND values
  - From Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements: Do not redeclare codex_available cursor_available locally; reuse the phase_infra globals or assign from the four re-read keys directly, and add tests where each external is healthy
  - From Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict: Remove the local codex_available/cursor_available declarations and use the existing globals set by phase_infra, or introduce correctly named saved globals before any local shadowing and add a test where both tools are available
  - From Codex-dyn-deletion-completeness: Do not declare local variables with the global names. Either use the existing globals directly, or rederive availability from the reread CODEX_PRESENT/CODEX_BINARY_FOUND and CURSOR_PRESENT/CURSOR_BINARY_FOUND values. Add tests where cursor/codex are available and must be selected.


### FINDING_2: Repo-unavailable or missing-plan paths can reach Step 2
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict
- **Severity**: important
- **Concern**: The proposed flow can select a coder when `REPO_UNAVAILABLE=true` or plan artifacts are absent, even though plan materialization is skipped and Step 2 requires `plan.txt` / `feature-description.txt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add an explicit artifact/repo gate before phase_coder_select or route these paths to Step 18 before Step 2; add a repo-unavailable --up-to-phase coder/all test
  - From Codex-Edge: Either materialize the local plan and feature files before coder selection even when repo discovery fails, or add an explicit post-Step-0 route that skips Step 2 when plan artifacts are missing
  - From Cursor-Innovation, Codex-Innovation: Pick one contract: either skip coder selection unless plan.txt and feature-description.txt exist, or explicitly route repo-unavailable before Step 2; pin it with a bootstrap and Step 2 routing test
  - From Cursor-Pragmatic, Codex-Pragmatic: Preserve the guard in bootstrap/orchestrator: require PLAN_FILE, plan.txt, and feature-description.txt before coder dispatch, or define and test an explicit repo-unavailable route
  - From Cursor-Requirements, Codex-Requirements: Gate coder selection on PLAN_FILE and required artifacts, or add explicit orchestrator routing that prevents Step 1.r/Step 2 dispatch when repo_unavailable=true or plan artifacts are absent; add a repo-unavailable coder-phase test
  - From Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict: Choose one contract: if repo-unavailable must skip coder, add REPO_UNAVAILABLE/PLAN_FILE guards and tests; if coder should be populated anyway, remove the earlier skip-both claim and update implement-bootstrap.md phase-skip semantics and tests accordingly


### FINDING_3: Step 2 messaging references deleted coder metadata
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan removes prompt-side definitions such as `coder_explicit` and `coder_fallback_target` but leaves Step 2.4 messaging branches that depend on them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Either emit and parse the needed metadata from implement-bootstrap.sh or rewrite these Step 2.4 conditions around CODER_OPT/coder_fallback and remove coder_fallback_target references
  - From Cursor-Pragmatic, Codex-Pragmatic: Replace those conditions with parsed coder_fallback plus a preserved original --coder flag indicator, or have bootstrap emit coder_explicit
  - From Cursor-Requirements, Codex-Requirements: Update Step 2.4 to use the parsed coder_fallback=true key and a preserved explicit-coder flag, or have bootstrap emit coder_explicit/coder_fallback_target equivalents


### FINDING_4: Step 0 structural pin counts retained non-bootstrap fences
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-deletion-completeness
- **Severity**: important
- **Concern**: The proposed at-most-one Step 0 bash fence / single bootstrap invocation assertion is scoped too broadly and conflicts with retained fork recovery, execution issue examples, rebase content, or dirty-tree resume-tail invocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Narrow the structural pin to the Session Setup subsection only, or exclude retained reference/example sections before counting bootstrap invocation fences
  - From Codex-Edge: Move retained reference sections outside the step:0 range or use non-bash fences for examples, and change the test to count implement-bootstrap.sh only inside the operational bash fence
  - From Cursor-Innovation, Codex-Innovation: Fold implement-fork-env.sh into the single Step 0 fence before implement-bootstrap, or absorb it into implement-bootstrap phase_infra and add a structure pin for the chosen path
  - From Cursor-Pragmatic, Codex-Pragmatic: Revise the pin to allow one initial invocation plus one resume-tail invocation, or move resume-tail into a helper and pin both call paths explicitly
  - From Cursor-Requirements, Codex-Requirements: Narrow the structural awk range to only the collapsed setup subsection or add a new end anchor; separately pin the primary bootstrap call and the dirty-tree resume call
  - From Codex-dyn-deletion-completeness: Narrow the structural assertion to the bootstrap subsection only, or explicitly exempt/move retained non-bootstrap fences before adding the <=1 fence pin. Also specify how the forked_target recovery helper is merged into the single bootstrap fence if it is still required.


### FINDING_5: Synthetic fallback warnings use append-tool-failure with stdin
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: `_phase_coder_append_warning` passes `/dev/stdin` to `append-tool-failure.sh`, but that helper requires a regular output file, so fallback warnings can be silently dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Write the warning to a mktemp file before calling append-tool-failure.sh, or use append-execution-issue.sh for synthetic warning text and test with the real helper behavior
  - From Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic: Write the synthetic warning to a mktemp file first, or call append-execution-issue.sh --category Warnings --entry for this non-tool-output case
  - From Cursor-Requirements, Codex-Requirements: Write the warning to a temp file under IMPLEMENT_TMPDIR and pass that path, or use append-execution-issue.sh for synthetic one-line warnings; make the harness assert the real entry body


### FINDING_6: Step 2 dispatcher remains a second coder-default authority
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: latent
- **Concern**: `step2-implement.sh` still documents and implements omitted `--coder` as Codex-first, conflicting with the plan’s claim that bootstrap is the sole Cursor-first coder selection authority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make --coder required in step2-implement.sh, since run-step2-dispatch.sh already requires it, or explicitly align and document the fallback-only legacy behavior with tests
  - From Cursor-Pragmatic, Codex-Pragmatic: Either make --coder required in step2-implement.sh too, or explicitly document/test the direct default as legacy non-/implement behavior
  - From Cursor-Requirements, Codex-Requirements: Either make --coder required for Step 2 after bootstrap owns selection, or update the fallback/default docs and tests to match the intended compatibility contract


### FINDING_7: New bootstrap test labels collide
- **Reviewer(s)**: Codex-Arch, Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict
- **Severity**: nit
- **Concern**: The proposed B6-B10 coder-selection tests duplicate or inconsistently reuse existing B6-B9 / B6 labels, weakening harness navigation and failure triage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Rename the new coder-selection cases to the next unused range or a distinct C-family prefix, and update the sibling .md accordingly
  - From Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict: Rename the listed cases to unique sequential identifiers or drop the B6-B10 claim and state the exact final case names the harness must expose


### FINDING_8: Coder breadcrumb emission misses explicit success paths
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-deletion-completeness
- **Severity**: important
- **Concern**: The planned breadcrumb placement conflicts with early returns from explicit coder selection, causing successful explicit paths to skip `emit_coder_breadcrumb_if_enabled` or risking empty breadcrumbs on bails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Call `emit_coder_breadcrumb_if_enabled` from a single shared tail after both branches, or invoke it inside each successful `_phase_coder_explicit` / `_phase_coder_implicit` path before return
  - From Codex-Edge: Refactor phase_coder_select to call the explicit/implicit helper, then emit only when coder is nonempty and IMPLEMENT_BAIL_REASON is empty, then return once
  - From Cursor-Innovation, Codex-Innovation: Centralize the return path: run explicit or implicit selection, then if IMPLEMENT_BAIL_REASON is empty and coder is non-empty emit the breadcrumb once
  - From Cursor-Pragmatic, Codex-Pragmatic: Restructure phase_coder_select to call emit_coder_breadcrumb_if_enabled once after either branch when coder is nonempty and no bail reason is set
  - From Cursor-Requirements, Codex-Requirements: Restructure phase_coder_select to select first, then emit the breadcrumb once when coder is non-empty and IMPLEMENT_BAIL_REASON is empty


### FINDING_9: SECURITY.md update misses stale routing references
- **Reviewer(s)**: Codex-Edge, Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict, Codex-dyn-deletion-completeness
- **Severity**: important
- **Concern**: The plan updates only one SECURITY.md paragraph while other SECURITY.md text still embeds Codex-first routing or links to the deleted `### Implementer waterfall` section.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Update every SECURITY.md occurrence in the Step 2 implementation trust discussion, not just the short L106 paragraph; add a grep/assertion for both old order strings and the deleted heading
  - From Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict: Extend the plan to update SECURITY.md L90, docs/linting.md, docs/run-logs.md, and scripts/test-implement-step2-routing.md alongside the .sh harness, and retarget wording away from the deleted SKILL heading
  - From Codex-dyn-deletion-completeness: Update both SECURITY.md routing references: replace the deleted section link with script-side phase_coder_select/implement-bootstrap wording, and align both order descriptions and fallback examples with the final approved order.


### FINDING_10: Breadcrumb truthiness differs from quiet helper behavior
- **Reviewer(s)**: Codex-Edge
- **Severity**: nit
- **Concern**: `emit_coder_breadcrumb_if_enabled` treats any nonempty `LARCH_QUIET_BREADCRUMBS` value as enabled, unlike existing breadcrumb helpers that use truthy parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Use larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}" for parity with existing breadcrumb helpers


### FINDING_12: Deleted waterfall section leaves stale diff_lines routing assertion
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: nit
- **Concern**: The plan retargets waterfall pins but misses an existing `diff_lines` non-routing assertion in the deleted SKILL.md section.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation, Codex-Innovation: Move the diff_lines informational assertion to the new implement-bootstrap.md contract or preserve a short non-routing sentence outside the deleted waterfall section


### FINDING_13: CLAUDE_PLUGIN_ROOT rehydration is removed before bootstrap invocations
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic, Codex-dyn-deletion-completeness
- **Severity**: important
- **Concern**: The plan removes or weakens same-fence `CLAUDE_PLUGIN_ROOT` recovery while retained Step 0 and resume-tail invocations still depend on `${CLAUDE_PLUGIN_ROOT}`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic, Codex-Pragmatic: Make one top-of-fence root recovery block a required edit before both initial and resume-tail invocations
  - From Codex-dyn-deletion-completeness: Make the plan explicit: every retained Step 0 fence using ${CLAUDE_PLUGIN_ROOT} keeps a same-fence awk guard, or the harness and its .md are intentionally updated to the new single-fence contract. Also state that dirty-tree resume uses the same preserved recovery line before the resumed bootstrap invocation.


### FINDING_14: Script sibling markdown updates are omitted
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements, Codex-dyn-deletion-completeness
- **Severity**: important
- **Concern**: The plan edits harness scripts but omits required sibling `.md` updates, leaving documentation stale under the repository’s script-md sibling rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Add updates for scripts/test-implement-step2-routing.md and skills/implement/scripts/test-implement-bootstrap.md alongside the .sh edits
  - From Codex-dyn-deletion-completeness: Add scripts/test-implement-step2-routing.md to the UPDATED list and align its contract text with the script-side coder selection/order pins.


### FINDING_16: SECURITY wording overstates reversal scope
- **Reviewer(s)**: Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict
- **Severity**: important
- **Concern**: The proposed SECURITY adjacency says the plan reverses #2756 without distinguishing `/implement` Step 0 default routing from still-live Codex-first fixer dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict: Revise the SECURITY sentence to say Phase 4 reverses only the omitted---coder /implement Step 0 default, while fixer dispatch remains Codex-first; or explicitly add review-and-fix.sh and lint-fix-loop.sh changes plus tests if full #2756 reversal is intended


### FINDING_17: Larch-log section pin is not dropped
- **Reviewer(s)**: Cursor-dyn-deletion-completeness
- **Severity**: important
- **Concern**: The plan does not account for a positive structural pin on `### Larch-log Batches and Summary Comments`, so deleting or moving that section can fail `test-implement-structure`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-deletion-completeness: Add L129-130 to the harness drop list (or repoint batch semantics to `scripts/implement-bootstrap.md` if the heading moves)


### FINDING_19: Deleted heading references remain outside the planned file list
- **Reviewer(s)**: Codex-dyn-deletion-completeness
- **Severity**: important
- **Concern**: Additional docs still reference deleted `### Implementer waterfall` / plan materialization anchors, so removing the headings would leave stale or broken references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-deletion-completeness: Add UPDATED entries for these files. Retarget docs/linting.md to scripts/implement-bootstrap.md or phase_coder_select, and retarget skills/shared/subskill-invocation.md to Preflight plus Step 0 bootstrap plan materialization without naming the deleted heading.

