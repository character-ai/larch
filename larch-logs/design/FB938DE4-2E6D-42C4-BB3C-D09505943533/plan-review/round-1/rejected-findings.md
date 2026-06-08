### [Plan Review] FINDING_1

### FINDING_1: Route/resume merge can drop argv-only --skip-approve
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The plan threads `skip_approve_requested` into the jq OR-merge, but does not explicitly require updating the outer shell guard that decides whether the merge runs. If only `--skip-approve` is present on resume/already-planned routes, the merge may be skipped and later gates may still see `skip_approve_requested=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: State explicitly that the outer `if [[ ... ]]` must gain `|| "$skip_approve_requested" == true` (and the `SKIP_APPROVE_REQUESTED` analogue in `design-init-runparams.sh` / `test-step0b-router-flag-recovery.sh`) in every merge site, not only the jq filter; add a structural pin for the SKILL.md route-fence outer guard (today only the `$merge_a` arm is pinned in `test-step0b-router-flag-recovery.sh` case 12).


### [Plan Review] FINDING_2

### FINDING_2: Gate C prompt path remains reachable under --skip-approve
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-gate-wire
- **Severity**: important
- **Concern**: Gate C’s auto-approve behavior is not clearly made exclusive with the interactive Presentation→Prompt path. If the Prompt subtree, loop prose, and re-prompt options remain unconditional or only sibling-gated, an implementer can still fire `AskUserQuestion` or cap-aware re-prompts under `--skip-approve`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Gate the entire post-emit interactive block on skip_approve_requested=false: after the emit fence prints SKIP_APPROVE_REQUESTED= auto-approve with breadcrumb and jump to Step 5; wrap approval-gates.md Prompt plus SKILL.md cap-aware option text and loop-until-Approve sentence in the same guard; add a structural pin that skip=true paths omit AskUserQuestion under Step 4b
  - From Cursor-dyn-gate-wire: Insert `### Auto-approve (--skip-approve)` immediately after Presentation and before Prompt; change Presentation handoff to "continue to auto-approve branch or Prompt when `skip_approve_requested=false`"; prefix the entire `### Prompt` block (including all re-fire / Other / cap-aware text) with that guard; extend `### Loop exit` to cover programmatic auto-approve → Step 5.


### [Plan Review] FINDING_3

### FINDING_3: Final-plan auto-approve can bypass full-plan visibility in summary mode
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: When Gate C uses summary-mode preview for large plans, `--skip-approve` may auto-approve after showing only the title/outline, removing the manual “See full plan” or “Other” path that would otherwise expose the complete plan before publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Before auto-approve when skip_approve_requested=true and summary mode fired, cat plan.txt under ## Final Design Plan (or fail closed) and document the behavior in flags.md + SECURITY.md


### [Plan Review] FINDING_4

### FINDING_4: Gate C flag read can be spoofed if emitted with untrusted plan text
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Reading `skip_approve_requested` in the same fence that emits untrusted plan text allows a malicious or accidental plan body line such as `SKIP_APPROVE_REQUESTED=true` to be confused with trusted control output, potentially skipping the final approval without the flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep the preview unchanged, then run a separate read-only fence that emits only the trusted SKIP_APPROVE_REQUESTED=<bool> line and branch only on that value.


