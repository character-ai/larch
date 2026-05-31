### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-init-runparams.sh:97-108
- **Concern**: Post-rename-only env refresh after moving feature-description ahead of init. Scenario: Collapses today's 5.5-bis refresh that bound ISSUE_NUMBER before sub-step 6; new order writes feature-description.txt then calls init, so source-env.sh / current-design-env symlink may lack ISSUE_NUMBER until rename completes inside the driver — widening the pause-save window SKILL.md documents at skills/design/SKILL.md:282
- **Proposed resolution**: In design-init-runparams.sh run the single write-design-current-env.sh call before tracking-issue-write.sh rename (still once per init), or add an orchestrator Bash refresh immediately after design-route.sh on ROUTE=proceed

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:602-612
- **Concern**: Harness still pins Step 0b write-run-params / jq merge in SKILL.md after extraction. Scenario: Plan re-points FINDING_13/#3008/refusal greps but not the Check 21 (#2930) anchors at lines 602-612 that require --manual-gate-b and the canonical jq filter in $SKILL_MD; after Step 0b inline bash removal make lint structure tests fail despite green driver logic
- **Proposed resolution**: Extend scripts/test-design-structure.sh updates to re-point lines 602-612 (and any related 617-621 greps) at design-init-runparams.sh, or keep one SKILL.md forwarder fence that satisfies the pins

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:67-68
- **Concern**: already-planned verdict only says body contains a larch:plan block. Scenario: plan-block-read.sh treats partial/duplicate markers as malformed, not present; a naive grep for start marker can mis-route or diverge from implement Preflight semantics
- **Proposed resolution**: Pin detection in design-route.md to the plan-block-read.sh MARK_START/MARK_END count rules on --issue-body-file (present only when exactly one well-formed pair)

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:50-75
- **Concern**: ERROR from design-pause-load is dropped from the proposed result contract. Scenario: design-pause-load.sh emits LOAD_OK=false ERROR=<token> for expected restore failures, and current Step 0b says those ERROR lines are printed before falling through. The plan forwards ERROR in responsibilities but omits ERROR from the result-env allowlist, so malformed pause markers or missing snapshots can degrade to a fresh run without surfacing the reason.
- **Proposed resolution**: Add ERROR to the design-route result allowlist and require the orchestrator to re-emit ERROR lines as warnings on LOAD_OK=false fallthrough.

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-route.sh:1 and skills/design/scripts/design-init-runparams.sh:1
- **Concern**: New invoked driver scripts are not pinned executable. Scenario: The proposed SKILL.md will invoke both new scripts by path. If they land with the default non-executable mode, Step 0b fails with permission denied before routing or run-params setup. Existing adjacent driver coverage pins run-step3-review.sh as executable.
- **Proposed resolution**: Make both new .sh files executable and add test-design-structure.sh assertions that design-route.sh and design-init-runparams.sh are executable.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:282-305,plan.txt:21-24,97-108
- **Concern**: Removing 5.5-bis without a pre-init env refresh before the init bash prelude. Scenario: On ROUTE=proceed the init fence still prepends the canonical pause-check using $ISSUE_NUMBER from sourced source-env.sh, but the last refresh was Step 0a (no --issue-number); refresh moves inside design-init-runparams.sh after rename, so prelude runs before ISSUE_NUMBER exists and pause-save can hit set -u or a wrong issue
- **Proposed resolution**: Keep the minimum pre-init refresh: either restore a proceed-path write-design-current-env.sh call in its own Bash fence before design-init-runparams.sh (same contract as today's 5.5-bis), or reorder design-init-runparams.sh to refresh env first and add an orchestrator fence line that exports ISSUE_NUMBER before the prelude when feature-description stays out-of-band

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:220,279
- **Concern**: BRAINSTORM_PREFIX is only handled on the proceed route. Scenario: The proposed Step 0b route handling sends already-planned issues straight to the existing gate, so a Brainstorm-prefixed already-planned issue can miss the mental brainstorm_requested=true state needed for the ad-hoc Q&A plus Step 1d.5 path
- **Proposed resolution**: Set brainstorm_requested=true and print the existing banner immediately after reading BRAINSTORM_PREFIX=true, before branching on ROUTE; then proceed/already-planned both see the same state

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/design-pause-load.sh:25-31
- **Concern**: LOAD_OK=false is specified as ROUTE=proceed in the edge cases. Scenario: A failed pause load on an issue that also has needs-design-clarification or an existing larch:plan block can bypass the clarify/already-planned gates and continue as a fresh replacement flow
- **Proposed resolution**: Make LOAD_OK=false fall through to the normal title/reentry/final verdict logic instead of setting ROUTE=proceed early, and carry ERROR alongside WARN so the existing warning breadcrumb is preserved

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:214
- **Concern**: skills/design/SKILL.md:214. Scenario: Resume env refresh omits conditional --manual-requested
- **Proposed resolution**: After pause/resume, restored run-params.json can set manual_gate_b=true; today Step 0b adds --manual-requested true on refresh when required. The plan moves refresh to orchestrator on resume@ but does not carry that rule. Gate B and source-env can drop manual mode mid-resume. In the SKILL.md resume@ branch, keep the existing rule: after re-exporting pause KVs, refresh source-env with --manual-requested true when restored $DESIGN_TMPDIR/run-params.json has manual_gate_b=true (or equivalent), matching current sub-step 2.5-bis prose.

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-phase-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:71-77
- **Concern**: `ERROR` is not on the result-env allowlist while the plan requires forwarding pause-load `ERROR=` on `LOAD_OK=false`. Scenario: Failure mode #1 says orchestrators should parse via `phase_driver_read_result_env`; `ERROR=` from `design-pause-load.sh` (`scripts/design-pause-load.sh:29-31`) is dropped from `.design-route-result.env`, so resume-failure breadcrumbs are lost unless stdout is re-parsed ad hoc
- **Proposed resolution**: Add `ERROR` to the allowlist and `design-route.md`, and write it through `phase_driver_write_result_env` when surfacing pause-load failures
