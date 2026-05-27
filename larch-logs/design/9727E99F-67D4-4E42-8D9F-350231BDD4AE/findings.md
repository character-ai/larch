### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:50-57
- **Concern**: Proposed `phase_coder_select` re-declares `local codex_available=false` / `local cursor_available=false` and gates on nonexistent `codex_available_from_infra` / `cursor_available_from_infra` while the comment says to reuse `phase_infra` globals. Scenario: Function-local names shadow module globals from `phase_infra`; the bogus `*_from_infra` test never passes, so implicit/explicit routing always sees unavailable externals and falls through to Claude or mis-bails
- **Proposed resolution**: Remove the local availability block (plan lines 50–53); use only `codex_available` / `cursor_available` set in `phase_infra` (scripts/implement-bootstrap.sh:479-487) for routing; keep the four-key re-read solely for tri-state `*_BINARY_FOUND` classification

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap.sh:911-914
- **Concern**: Proposed phase_coder_select shadows availability globals and reads nonexistent *_from_infra variables. Scenario: Even when session setup reports Cursor or Codex healthy, implicit selection treats both externals as unavailable; explicit cursor/codex also bail incorrectly because the helper-local variables hide the phase_infra globals
- **Proposed resolution**: Remove the local codex_available/cursor_available declarations or derive them directly from the four re-read probe keys; add happy-path tests where each external is available

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/implement-bootstrap.sh:1077-1086
- **Concern**: Repo-unavailable and deferred paths can reach coder selection without plan artifacts. Scenario: phase_plan_materialize skips on REPO_UNAVAILABLE, but the widened post-tracking guard can still populate coder; Step 2 then fails in run-step2-dispatch.sh because feature-description.txt or plan.txt is missing
- **Proposed resolution**: Add an explicit artifact/repo gate before phase_coder_select or route these paths to Step 18 before Step 2; add a repo-unavailable --up-to-phase coder/all test

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:971-975
- **Concern**: Plan deletes the prompt-side waterfall but leaves downstream prose depending on coder_explicit and coder_fallback_target. Scenario: After the PR, only coder and coder_fallback are planned bootstrap KVs, so the Claude-fallback messaging branch has stale variables and cannot reliably distinguish explicit claude from implicit both-down fallback
- **Proposed resolution**: Either emit and parse the needed metadata from implement-bootstrap.sh or rewrite these Step 2.4 conditions around CODER_OPT/coder_fallback and remove coder_fallback_target references

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/test-implement-structure.sh:390-407
- **Concern**: New Step 0 fenced-bash count pin is scoped too broadly. Scenario: Implementation keeps Execution Issues Tracking before the Step 2 marker, including a retained bash example at skills/implement/SKILL.md:595-608, so the proposed awk from step:0 to step:2 will count non-Step-0 reference fences and fail after the intended collapse
- **Proposed resolution**: Narrow the structural pin to the Session Setup subsection only, or exclude retained reference/example sections before counting bootstrap invocation fences

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/append-tool-failure.sh:91-99
- **Concern**: Proposed _phase_coder_append_warning uses /dev/stdin against an API that requires a regular output file. Scenario: append-tool-failure.sh rejects missing/non-regular output files; the proposed call suppresses failures, so implicit fallback warnings may never land in execution-issues.md while sandbox stubs still pass
- **Proposed resolution**: Write the warning to a mktemp file before calling append-tool-failure.sh, or use append-execution-issue.sh for synthetic warning text and test with the real helper behavior

### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step2-implement.sh:15-18,128-131
- **Concern**: Step 2 dispatcher remains an independent coder-default authority. Scenario: The plan says phase_coder_select becomes the sole authority and reverses omitted --coder to Cursor-first, but step2-implement.sh still defaults omitted --coder to Codex; direct tests/docs preserve an inconsistent policy surface
- **Proposed resolution**: Make --coder required in step2-implement.sh, since run-step2-dispatch.sh already requires it, or explicitly align and document the fallback-only legacy behavior with tests

### FINDING_8:
- **Reviewer(s)**: Codex-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/test-implement-bootstrap.sh:965-1275
- **Concern**: New B6-B10 test names collide with existing B6-B9 labels. Scenario: The plan says to continue B1-B5 naming, but the harness already has B6/B7/B8/B9 sections; duplicate labels make failures harder to triage and weaken grep-based harness navigation
- **Proposed resolution**: Rename the new coder-selection cases to the next unused range or a distinct C-family prefix, and update the sibling .md accordingly

### FINDING_9:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap.sh:phase_coder_select
- **Concern**: Explicit `--coder` happy paths return before `emit_coder_breadcrumb_if_enabled`. Scenario: Plan places breadcrumb emission at the tail of `phase_coder_select`, but the proposed body returns immediately after `_phase_coder_explicit`; B6-explicit-claude and structural pin `→ step0: coder=` will fail and operators lose the coder breadcrumb on pinned runs
- **Proposed resolution**: Call `emit_coder_breadcrumb_if_enabled` from a single shared tail after both branches, or invoke it inside each successful `_phase_coder_explicit` / `_phase_coder_implicit` path before return

### FINDING_10:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap.sh:911-914
- **Concern**: Proposed phase_coder_select shadows codex_available and cursor_available with locals and then checks nonexistent codex_available_from_infra cursor_available_from_infra. Scenario: Every implicit run falls through to Claude and every explicit external coder is treated unavailable even when phase_infra proved the tool healthy
- **Proposed resolution**: Do not redeclare local availability names; either use the existing globals directly or derive from the reread *_PRESENT and *_BINARY_FOUND values

### FINDING_11:
- **Reviewer(s)**: Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/append-tool-failure.sh:100-104
- **Concern**: Proposed _phase_coder_append_warning passes --output-file /dev/stdin but append-tool-failure.sh requires a regular file. Scenario: The implicit fallback warnings are silently dropped from execution-issues.md because the helper fails and the plan masks it with >/dev/null 2>&1 || true
- **Proposed resolution**: Write the synthetic warning to a mktemp file first, or call append-execution-issue.sh --category Warnings --entry for this non-tool-output case

### FINDING_12:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap.sh:1077-1087
- **Concern**: Repo-unavailable coder path is allowed to continue without plan.txt or feature-description.txt. Scenario: With REPO_UNAVAILABLE=true, phase_plan_materialize is skipped, phase_coder_select now runs, Step 0 has no bail, and Step 2 later fails at run-step2-dispatch.sh because plan.txt is absent
- **Proposed resolution**: Either materialize the local plan and feature files before coder selection even when repo discovery fails, or add an explicit post-Step-0 route that skips Step 2 when plan artifacts are missing

### FINDING_13:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:90-106
- **Concern**: Plan updates only the L106 paragraph but SECURITY.md also embeds the old Codex-first order and deleted SKILL heading in the large external-delegation paragraph. Scenario: The shipped security/trust model would simultaneously claim Cursor-first and Codex-first routing, and reference a removed ### Implementer waterfall section
- **Proposed resolution**: Update every SECURITY.md occurrence in the Step 2 implementation trust discussion, not just the short L106 paragraph; add a grep/assertion for both old order strings and the deleted heading

### FINDING_14:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/implement-bootstrap.sh:911-914
- **Concern**: Breadcrumb placement instruction conflicts with helper early returns. Scenario: Placing emit_coder_breadcrumb_if_enabled before only the second return omits breadcrumbs for explicit happy paths; placing it after helper returns without a bail guard emits an empty coder breadcrumb on explicit-unavailable bails
- **Proposed resolution**: Refactor phase_coder_select to call the explicit/implicit helper, then emit only when coder is nonempty and IMPLEMENT_BAIL_REASON is empty, then return once

### FINDING_15:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/implement/SKILL.md:576-608
- **Concern**: Step 0 structural pin conflicts with retained Step 0 content and counts prose mentions as invocations. Scenario: The new at-most-one bash fence pin will fail unless retained Execution Issues examples are moved or converted; the grep-cE implement-bootstrap.sh count will also count prose references, not just the actual command
- **Proposed resolution**: Move retained reference sections outside the step:0 range or use non-bash fences for examples, and change the test to count implement-bootstrap.sh only inside the operational bash fence

### FINDING_16:
- **Reviewer(s)**: Codex-Edge
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap.sh:158-182
- **Concern**: Proposed emit_coder_breadcrumb_if_enabled uses nonempty LARCH_QUIET_BREADCRUMBS instead of the repo's truthy helper. Scenario: Setting LARCH_QUIET_BREADCRUMBS=0 or false would still emit the coder breadcrumb while other Step 0 breadcrumbs stay disabled
- **Proposed resolution**: Use larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}" for parity with existing breadcrumb helpers

### FINDING_17:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap.sh:911-914
- **Concern**: Proposed phase_coder_select shadows availability globals and checks undefined codex_available_from_infra cursor_available_from_infra. Scenario: Even with Cursor or Codex healthy, local availability stays false, explicit external coders hard-bail, and implicit routing falls through to Claude with false fallback warnings
- **Proposed resolution**: Do not redeclare codex_available cursor_available locally; reuse the phase_infra globals or assign from the four re-read keys directly, and add tests where each external is healthy

### FINDING_18:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap.sh:911-914
- **Concern**: The proposed breadcrumb placement conflicts with early returns in phase_coder_select. Scenario: Explicit happy paths such as --coder=claude or available --coder=cursor return before emit_coder_breadcrumb_if_enabled, contradicting the planned tests expecting a coder breadcrumb
- **Proposed resolution**: Centralize the return path: run explicit or implicit selection, then if IMPLEMENT_BAIL_REASON is empty and coder is non-empty emit the breadcrumb once

### FINDING_19:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/implement-bootstrap.sh:1077-1087, skills/implement/scripts/run-step2-dispatch.sh:89-93, skills/implement/SKILL.md:744
- **Concern**: Repo-unavailable and missing-plan routing is internally contradictory. Scenario: The widened coder phase can populate coder when REPO_UNAVAILABLE=true even though plan materialization skipped plan.txt and run-step2-dispatch fails closed on missing plan file
- **Proposed resolution**: Pick one contract: either skip coder selection unless plan.txt and feature-description.txt exist, or explicitly route repo-unavailable before Step 2; pin it with a bootstrap and Step 2 routing test

### FINDING_20:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:286-295
- **Concern**: The Step 0 single-fence collapse does not account for the fork pre-setup helper block. Scenario: Keeping the block violates the new at-most-one-fence pin; deleting it breaks fork recovery when forked_target=true and UPSTREAM_REPO is unset
- **Proposed resolution**: Fold implement-fork-env.sh into the single Step 0 fence before implement-bootstrap, or absorb it into implement-bootstrap phase_infra and add a structure pin for the chosen path

### FINDING_21:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/external-tool-registry.sh:1-9, scripts/implement-bootstrap.sh:969-1029
- **Concern**: The new --coder validation hardcodes the coder enum instead of using the existing canonical registry. Scenario: Future coder taxonomy changes can update step2-implement via external-tool-registry.sh while bootstrap rejects the same value
- **Proposed resolution**: Source scripts/external-tool-registry.sh in implement-bootstrap.sh and validate with larch_is_implementer_coder / larch_implementer_coders_braced; extend test-external-tool-registry.sh coverage to include bootstrap

### FINDING_22:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/test-implement-step2-routing.sh:41
- **Concern**: The plan retargets waterfall pins but misses the diff_lines non-routing assertion that currently lives in the deleted section. Scenario: After deleting the prompt-side waterfall, make test-implement-step2-routing can still fail on the stale SKILL.md assertion
- **Proposed resolution**: Move the diff_lines informational assertion to the new implement-bootstrap.md contract or preserve a short non-routing sentence outside the deleted waterfall section

### FINDING_23:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/implement/SKILL.md:478-510; scripts/test-implement-structure.sh:378-419
- **Concern**: Structural pin says Step 0 must have exactly one implement-bootstrap.sh invocation while the plan also keeps the dirty-tree --resume-plan-tail invocation. Scenario: Implementation either fails the new structure test or removes required dirty-tree recovery re-entry
- **Proposed resolution**: Revise the pin to allow one initial invocation plus one resume-tail invocation, or move resume-tail into a helper and pin both call paths explicitly

### FINDING_24:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:742-745; scripts/implement-bootstrap.sh:1077-1087
- **Concern**: Deleting the prompt-side waterfall removes the REPO_UNAVAILABLE/plan-artifact guard while the widened phase gate can still select coder with PLAN_FILE empty. Scenario: Repo-unavailable or missing-plan paths continue toward Step 2 and fail inside run-step2-dispatch instead of taking a controlled route
- **Proposed resolution**: Preserve the guard in bootstrap/orchestrator: require PLAN_FILE, plan.txt, and feature-description.txt before coder dispatch, or define and test an explicit repo-unavailable route

### FINDING_25:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap.sh:911-914
- **Concern**: Plan says to emit the coder breadcrumb before the second return only. Scenario: Explicit --coder happy paths return before the breadcrumb, contradicting the proposed tests and telemetry contract
- **Proposed resolution**: Restructure phase_coder_select to call emit_coder_breadcrumb_if_enabled once after either branch when coder is nonempty and no bail reason is set

### FINDING_26:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:971-975
- **Concern**: Plan deletes the only definitions of coder_explicit and coder_fallback_target but leaves Step 2 messaging keyed on them. Scenario: Claude fallback messages become wrong or unreachable after the Step 0 collapse
- **Proposed resolution**: Replace those conditions with parsed coder_fallback plus a preserved original --coder flag indicator, or have bootstrap emit coder_explicit

### FINDING_27:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:318-394; skills/implement/SKILL.md:480-510
- **Concern**: Plan removes all CLAUDE_PLUGIN_ROOT rehydration while still invoking bootstrap through ${CLAUDE_PLUGIN_ROOT}/.... Scenario: If the env var is absent during resume or degraded context, the shell cannot exec implement-bootstrap.sh, so the script's internal fallback never runs
- **Proposed resolution**: Make one top-of-fence root recovery block a required edit before both initial and resume-tail invocations

### FINDING_28:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: latent
- **Focus area**: security
- **Location**: skills/implement/scripts/step2-implement.sh:128-131; skills/implement/scripts/step2-implement.md:5-9
- **Concern**: Plan makes phase_coder_select the sole authority but leaves direct step2-implement.sh omitted---coder defaulting to Codex. Scenario: Direct dispatcher calls remain a second routing authority inconsistent with the new Cursor-first trust/security documentation
- **Proposed resolution**: Either make --coder required in step2-implement.sh too, or explicitly document/test the direct default as legacy non-/implement behavior

### FINDING_29:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements, Codex-dyn-deletion-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap.sh:911-914
- **Concern**: Planned coder breadcrumb placement misses explicit-coder success paths. Scenario: The plan says explicit --coder=claude should emit the coder breadcrumb, but placing the call only before the second return means the early explicit return skips it
- **Proposed resolution**: Restructure phase_coder_select to select first, then emit the breadcrumb once when coder is non-empty and IMPLEMENT_BAIL_REASON is empty

### FINDING_30:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/append-tool-failure.sh:100-103
- **Concern**: Planned _phase_coder_append_warning passes /dev/stdin to a helper that requires a regular file. Scenario: Implicit fallback warnings are silently not appended to execution-issues.md because append-tool-failure rejects non-file stdin and the plan hides the failure with >/dev/null 2>&1 || true
- **Proposed resolution**: Write the warning to a temp file under IMPLEMENT_TMPDIR and pass that path, or use append-execution-issue.sh for synthetic one-line warnings; make the harness assert the real entry body

### FINDING_31:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:478-510
- **Concern**: Structural pin conflicts with dirty-tree recovery and the kept Step 0-adjacent sections. Scenario: The plan requires at most one fenced bash block and exactly one implement-bootstrap.sh invocation between step:0 and step:2, but dirty-tree recovery still needs a resume-tail invocation and the kept Phantom/Execution Issues/Rebase 1.r content includes fenced bash blocks
- **Proposed resolution**: Narrow the structural awk range to only the collapsed setup subsection or add a new end anchor; separately pin the primary bootstrap call and the dirty-tree resume call

### FINDING_32:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap.sh:1077-1086
- **Concern**: Repo-unavailable and missing-plan paths are not guarded before coder selection. Scenario: The plan widens should_run_post_tracking_phase so repo-unavailable paths can emit coder even though plan materialization is skipped; Step 2 later assumes IMPLEMENT_TMPDIR/plan.txt and feature-description.txt exist
- **Proposed resolution**: Gate coder selection on PLAN_FILE and required artifacts, or add explicit orchestrator routing that prevents Step 1.r/Step 2 dispatch when repo_unavailable=true or plan artifacts are absent; add a repo-unavailable coder-phase test

### FINDING_33:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:971-975
- **Concern**: Step 2.4 still depends on prompt-side coder_explicit and coder_fallback_target state. Scenario: The plan only exports coder and coder_fallback from bootstrap, so implicit Claude fallback and explicit --coder=claude messaging may no longer match any branch
- **Proposed resolution**: Update Step 2.4 to use the parsed coder_fallback=true key and a preserved explicit-coder flag, or have bootstrap emit coder_explicit/coder_fallback_target equivalents

### FINDING_34:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: .claude/rules/script-md-siblings.md:1-13
- **Concern**: Plan omits required sibling-doc updates for edited harness scripts. Scenario: scripts/test-implement-step2-routing.md still documents the deleted SKILL.md waterfall and Codex-first order, and skills/implement/scripts/test-implement-bootstrap.md will not list the new coder-selection cases
- **Proposed resolution**: Add updates for scripts/test-implement-step2-routing.md and skills/implement/scripts/test-implement-bootstrap.md alongside the .sh edits

### FINDING_35:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step2-implement.sh:16,skills/implement/scripts/step2-implement.sh:128-130
- **Concern**: Step 2 dispatcher still documents and implements omitted---coder as Codex-first. Scenario: The plan makes phase_coder_select the sole authority and changes implicit default to Cursor-first, but direct or legacy Step 2 invocations still silently choose Codex when --coder is omitted
- **Proposed resolution**: Either make --coder required for Step 2 after bootstrap owns selection, or update the fallback/default docs and tests to match the intended compatibility contract

### FINDING_36:
- **Reviewer(s)**: Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:50-57, scripts/implement-bootstrap.sh:61-62, scripts/implement-bootstrap.sh:479-487
- **Concern**: FINDING 1 The proposed phase_coder_select shadows the existing codex_available and cursor_available globals and checks nonexistent codex_available_from_infra and cursor_available_from_infra variables. Scenario: With both external tools healthy, the local variables stay false, so implicit routing falls through to Claude and explicit --coder=codex or --coder=cursor falsely stalls as unavailable
- **Proposed resolution**: Remove the local codex_available/cursor_available declarations and use the existing globals set by phase_infra, or introduce correctly named saved globals before any local shadowing and add a test where both tools are available

### FINDING_37:
- **Reviewer(s)**: Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:3-11, skills/design/references/approval-gates.md:151-161, skills/implement/SKILL.md:220-279
- **Concern**: FINDING 2 The Gate C callout is advisory prose inside the plan, not a machine-enforced blocking gate. Scenario: /design Gate C only asks Approve/Discuss/Re-run; if the operator approves or an automated runner consumes the resulting larch:plan, /implement Preflight has no special check that the #2756 reversal was consciously approved and can silently implement Cursor-first
- **Proposed resolution**: Resolve the conflict before finalizing: replace the Open questions section with an explicit recorded decision outcome, or add a concrete Preflight refusal criterion/clarify marker that blocks implementation while unresolved wording remains

### FINDING_38:
- **Reviewer(s)**: Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:25, <TMPDIR>/plan.txt:193-195, <TMPDIR>/plan.txt:228-240, SECURITY.md:90, docs/linting.md:263, docs/run-logs.md:200, scripts/test-implement-step2-routing.md:3-8
- **Concern**: FINDING 3 The plan enumerates only SECURITY.md L106 and the shell harness, but other normative/docs surfaces still encode Codex-first Step 0 routing or the deleted SKILL heading. Scenario: After implementation, SECURITY.md would contain both Cursor-first at L106 and Codex-first plus the old SKILL heading at L90; docs/linting.md and test-implement-step2-routing.md would describe the old harness contract; docs/run-logs.md would say coder_fallback means routing fell past Codex
- **Proposed resolution**: Extend the plan to update SECURITY.md L90, docs/linting.md, docs/run-logs.md, and scripts/test-implement-step2-routing.md alongside the .sh harness, and retarget wording away from the deleted SKILL heading

### FINDING_39:
- **Reviewer(s)**: Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:9, <TMPDIR>/plan.txt:232, CHANGELOG.md:24, CHANGELOG.md:366-367, skills/review-and-fix/scripts/review-and-fix.sh:252-298, scripts/lint-fix-loop.sh:221-239, scripts/lint-fix-loop.sh:355-362
- **Concern**: FINDING 4 The proposed SECURITY adjacency overstates #2738 as reversing #2756 without distinguishing Step 2 default from fixer dispatch. Scenario: #2756 landed both omitted---coder Codex-first and fixer Codex-before-Cursor; the plan changes only the implementer waterfall while review-and-fix.sh and lint-fix-loop.sh remain Codex-first, so "reverses the Codex-first default landed by #2756" can be read as contradicting still-live fixer behavior
- **Proposed resolution**: Revise the SECURITY sentence to say Phase 4 reverses only the omitted---coder /implement Step 0 default, while fixer dispatch remains Codex-first; or explicitly add review-and-fix.sh and lint-fix-loop.sh changes plus tests if full #2756 reversal is intended

### FINDING_40:
- **Reviewer(s)**: Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:35, <TMPDIR>/plan.txt:331-333, scripts/implement-bootstrap.sh:184-193, scripts/implement-bootstrap.sh:1077-1087
- **Concern**: FINDING 5 The plan contradicts itself on REPO_UNAVAILABLE coder selection. Scenario: Approach says REPO_UNAVAILABLE still skips both plan and coder, but Edge case 4 says phase_coder_select still runs and that this is desirable; the current main flow would call phase_coder_select after dropping the DEFERRED guard because should_run_post_tracking_phase has no REPO_UNAVAILABLE or PLAN_FILE check
- **Proposed resolution**: Choose one contract: if repo-unavailable must skip coder, add REPO_UNAVAILABLE/PLAN_FILE guards and tests; if coder should be populated anyway, remove the earlier skip-both claim and update implement-bootstrap.md phase-skip semantics and tests accordingly

### FINDING_41:
- **Reviewer(s)**: Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:248-266
- **Concern**: FINDING 6 The new bootstrap test cases are described as B6-B10 but every listed case uses a B6 prefix. Scenario: Reviewers and future maintainers lose a stable mapping from failure output to the intended scenario, and duplicate case names can hide missing coverage in grep-based harness assertions
- **Proposed resolution**: Rename the listed cases to unique sequential identifiers or drop the B6-B10 claim and state the exact final case names the harness must expose

### FINDING_42:
- **Reviewer(s)**: Cursor-dyn-deletion-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:129-130
- **Concern**: `### Larch-log Batches and Summary Comments` positive pin not listed among drops. Scenario: Deleting the section without dropping L129 makes `make test-implement-structure` fail after SKILL collapse
- **Proposed resolution**: Add L129-130 to the harness drop list (or repoint batch semantics to `scripts/implement-bootstrap.md` if the heading moves)

### FINDING_43:
- **Reviewer(s)**: Codex-dyn-deletion-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap.sh:61-62; scripts/implement-bootstrap.sh:479-487; scripts/implement-bootstrap.sh:911-914
- **Concern**: FINDING_1: proposed phase_coder_select shadows the existing availability globals and references nonexistent codex_available_from_infra/cursor_available_from_infra. Scenario: The current script stores probe-derived globals as codex_available/cursor_available. The plan's local codex_available=false cursor_available=false declarations dynamically shadow those globals for helper calls, so implicit routing falls through to Claude and explicit cursor/codex can bail even when probes passed.
- **Proposed resolution**: Do not declare local variables with the global names. Either use the existing globals directly, or rederive availability from the reread CODEX_PRESENT/CODEX_BINARY_FOUND and CURSOR_PRESENT/CURSOR_BINARY_FOUND values. Add tests where cursor/codex are available and must be selected.

### FINDING_44:
- **Reviewer(s)**: Codex-dyn-deletion-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:286-295; skills/implement/SKILL.md:576-608; skills/implement/SKILL.md:780-798; scripts/test-implement-structure.sh:390-419
- **Concern**: FINDING_2: the proposed Step 0 <=1 bash-fence structural pin conflicts with retained Step 0 content. Scenario: The plan says to keep fork-target recovery, Execution Issues Tracking, and Rebase 1.r, but the proposed awk range /<!-- step:0/,/<!-- step:2/ counts their bash fences too. Keeping the sections fails the new pin; deleting them breaks existing recovery/docs/rebase contracts.
- **Proposed resolution**: Narrow the structural assertion to the bootstrap subsection only, or explicitly exempt/move retained non-bootstrap fences before adding the <=1 fence pin. Also specify how the forked_target recovery helper is merged into the single bootstrap fence if it is still required.

### FINDING_45:
- **Reviewer(s)**: Codex-dyn-deletion-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-foreground-markers.sh:15-19; scripts/lint-foreground-markers.sh:29-39; scripts/lint-foreground-markers.sh:693-720; BASH_AUTHORING.md:64-72; BASH_AUTHORING.md:120
- **Concern**: FINDING_3: the planned foreground comment is not a valid §4 background-pair marker for Family B anchors. Scenario: implement-bootstrap.sh is explicitly outside the Family B fence rule, so lint-foreground-markers.sh will ignore the proposed Step 0 foreground comment rather than validate it. If the collapsed fence ever contains a real Family B anchor with run_in_background and breadcrumb-monitor, # Foreground required: see BASH_AUTHORING.md §4 is treated as stale foreground wording and the fence still needs the exact background-pair comment.
- **Proposed resolution**: Do not present the Step 0 foreground comment as satisfying BASH_AUTHORING.md §4. Keep it as a local style pin only, or remove the pin. For any denylisted Family B invocation, require the exact background banner and # Background pair required: see BASH_AUTHORING.md §4 comment.

### FINDING_46:
- **Reviewer(s)**: Codex-dyn-deletion-completeness
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:90; SECURITY.md:106
- **Concern**: FINDING_4: SECURITY.md has two old implementer-routing references, but the plan only updates the L106 paragraph. Scenario: Line 90 still links the deleted SKILL.md ### Implementer waterfall section and states Codex → Cursor → Claude. The plan's testing note says only L106 should change, leaving the main external-delegation threat-model paragraph stale after Cursor-first lands.
- **Proposed resolution**: Update both SECURITY.md routing references: replace the deleted section link with script-side phase_coder_select/implement-bootstrap wording, and align both order descriptions and fallback examples with the final approved order.

### FINDING_47:
- **Reviewer(s)**: Codex-dyn-deletion-completeness
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: docs/linting.md:263; skills/shared/subskill-invocation.md:77; skills/shared/subskill-invocation.md:199
- **Concern**: FINDING_5: exact deleted heading references are missed outside the plan's file list. Scenario: Repo search finds ### Implementer waterfall in docs/linting.md and Plan materialization from issue body references in skills/shared/subskill-invocation.md. After deleting those SKILL.md headings, these docs point at nonexistent anchors or stale ownership boundaries.
- **Proposed resolution**: Add UPDATED entries for these files. Retarget docs/linting.md to scripts/implement-bootstrap.md or phase_coder_select, and retarget skills/shared/subskill-invocation.md to Preflight plus Step 0 bootstrap plan materialization without naming the deleted heading.

### FINDING_48:
- **Reviewer(s)**: Codex-dyn-deletion-completeness
- **Severity**: important
- **Focus area**: code-quality
- **Location**: .claude/rules/script-md-siblings.md:7-12; scripts/test-implement-step2-routing.sh:31-40; scripts/test-implement-step2-routing.md:3-10
- **Concern**: FINDING_6: the plan retargets test-implement-step2-routing.sh but omits its sibling markdown. Scenario: The repository rule requires sibling .md docs to update with script behavior changes. The .md currently pins ### Implementer waterfall and Codex → Cursor → Claude, so it will be stale after the .sh retarget.
- **Proposed resolution**: Add scripts/test-implement-step2-routing.md to the UPDATED list and align its contract text with the script-side coder selection/order pins.

### FINDING_49:
- **Reviewer(s)**: Codex-dyn-deletion-completeness
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-implement-timing-rehydration.sh:78-103; scripts/test-implement-timing-rehydration.sh:129-132; scripts/test-implement-timing-rehydration.md:10-14; skills/implement/SKILL.md:478-510
- **Concern**: FINDING_8: the CLAUDE_PLUGIN_ROOT recovery change is not paired with the existing same-fence rehydration contract. Scenario: The plan alternates between removing Step 0 rehydration boilerplate and keeping one recovery line, but the lint harness still requires every SKILL.md bash fence using ${CLAUDE_PLUGIN_ROOT} to contain the awk LARCH_CLAUDE_PLUGIN_ROOT guard. Any retained recovery/dirty-tree fence without that guard will fail make lint, and removing the guard entirely weakens dirty-tree resume recovery.
- **Proposed resolution**: Make the plan explicit: every retained Step 0 fence using ${CLAUDE_PLUGIN_ROOT} keeps a same-fence awk guard, or the harness and its .md are intentionally updated to the new single-fence contract. Also state that dirty-tree resume uses the same preserved recovery line before the resumed bootstrap invocation.
