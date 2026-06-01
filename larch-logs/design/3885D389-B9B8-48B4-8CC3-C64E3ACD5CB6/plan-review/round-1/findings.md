### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:12-14
- **Concern**: Protocol Execution Directive and Anti-halt still mandate `implement-bootstrap.sh --up-to-phase coder` while Step 0 will call `implement-bootstrap-invoke.sh`. Scenario: Agents can follow the preamble and bypass the new wrapper/parse contract, reintroducing duplicated argv assembly and drift from the extracted harness
- **Proposed resolution**: Retarget both directives to `scripts/implement-bootstrap-invoke.sh --mode initial` (and dirty-tree `--mode resume`) in the same Step 0 edit, or widen the planned SKILL.md scope beyond “Step 0 region only”

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:454-508
- **Concern**: Dirty-tree recovery still specifies a third direct `implement-bootstrap.sh --up-to-phase plan --resume-plan-tail` fence with duplicated argv assembly and `_ib_kv_scan`, but the plan only thins the Step 0 entry/resume call sites. Scenario: After `_ib_run_bootstrap` / `_ib_parse_bootstrap_out` removal, recovery either keeps a second copy of the logic the wrapper was meant to delete, or breaks if helpers are deleted without retargeting this fence
- **Proposed resolution**: In the same SKILL.md edit, route dirty-tree continuation through `implement-bootstrap-invoke.sh --mode resume`, reuse the shared envelope parse, and replace prose at ~458 that still names direct `implement-bootstrap.sh`

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:454-509
- **Concern**: Dirty-tree recovery still duplicates argv assembly and calls implement-bootstrap.sh directly. Scenario: Plan extracts two inline harness copies but leaves the Step 0 dirty-tree bash block (~470-508) and item-3 prose (~458) on the old direct bootstrap + _ib_kv_scan path, so argv/exit-2/redaction logic stays duplicated and can drift from the new wrapper
- **Proposed resolution**: Replace the dirty-tree bash example with implement-bootstrap-invoke.sh --mode resume plus the shared routing-env parse; update item-3 prose and routing row 446 to match

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:12,14
- **Concern**: Protocol Execution Directive still mandates direct implement-bootstrap.sh --up-to-phase coder. Scenario: Step 0 bash may call implement-bootstrap-invoke.sh --mode initial while lines 12 and 14 still tell the orchestrator to run implement-bootstrap.sh --up-to-phase coder, inviting a bypass of the wrapper and envelope parse
- **Proposed resolution**: Retarget the directive and anti-halt boundary text to implement-bootstrap-invoke.sh --mode initial (and dirty-tree --mode resume) with envelope parsing as today

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-step2-routing.sh:35
- **Concern**: Harness still requires --up-to-phase coder in SKILL.md. Scenario: After Step 0 thins to implement-bootstrap-invoke.sh, assert_contains on --up-to-phase coder in skills/implement/SKILL.md fails in test-harnesses-16 (plan lists this file under verify-only, not UPDATED)
- **Proposed resolution**: Retarget the pin to implement-bootstrap-invoke.sh --mode initial or phase_coder_select in implement-bootstrap.sh per plan Approach edit-in-sync sweep

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:454-509
- **Concern**: Dirty-tree recovery still embeds a third argv assembly plus a direct `implement-bootstrap.sh --up-to-phase plan --resume-plan-tail` call and `_ib_kv_scan` re-parse; the plan only names routing-table prose at :446 and thin `--mode initial`/`--mode resume` sites above that block. Scenario: Goal #3298 is to collapse duplicated Step 0 harness; item 3 and the fenced bash block keep ~50 lines of duplicate logic, so extraction is incomplete and behavior can drift from the wrapper/redaction path
- **Proposed resolution**: In `### UPDATED: skills/implement/SKILL.md`, require dirty-tree step 3 and the recovery bash fence to call `implement-bootstrap-invoke.sh --mode resume` (with the same pre-call `export` list), drop reassembled `_ib_caller_env`/`_ib_issue`/… arrays and the direct bootstrap invocation, and reuse the single shared routing-env parse block (no second `_ib_kv_scan`)

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:12-14
- **Concern**: Protocol Execution Directive and Anti-halt still mandate `${CLAUDE_PLUGIN_ROOT}/scripts/implement-bootstrap.sh --up-to-phase coder`; the plan scopes edits to the Step 0 region only (:32-39). Scenario: Orchestrators that follow the top-of-file protocol before the numbered Step 0 section can still invoke bootstrap directly, bypassing the wrapper and reintroducing the duplication this PR removes
- **Proposed resolution**: Extend the SKILL.md update (or add an explicit plan bullet) to retarget items (3) and the Anti-halt Preflight→Step 0 boundary to `implement-bootstrap-invoke.sh --mode initial`, matching the new Step 0 call sites

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:550-575
- **Concern**: Plan says to retarget the Step 0 awk guard but does not state new expected counts after bootstrap moves out of `<!-- step:0` bash blocks. Scenario: Implementer may leave `bootstrap_calls==1` / `resume_mentions==1` on `implement-bootstrap.sh` literals and get a false CI pass or a confusing failure after SKILL.md correctly drops direct bootstrap calls
- **Proposed resolution**: Spell out the post-refactor awk expectations (e.g. zero direct `implement-bootstrap.sh` calls in Step 0 bash, exactly one `implement-bootstrap-invoke.sh --mode initial`, exactly one `--mode resume`, `--up-to-phase coder` asserted only in `scripts/implement-bootstrap-invoke.sh`)

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-env-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:454-509
- **Concern**: Dirty-tree recovery fence still calls implement-bootstrap.sh directly with a second inline _ib_kv_scan/export block; UPDATED only names initial/resume wrapper call sites in the main Step 0 harness. Scenario: The extraction leaves a third argv-assembly + bootstrap + parse copy. Dirty-tree resume can diverge from --mode resume envelope filtering, and line 458 prose still mandates _ib_kv_scan while _ib_parse_bootstrap_out is deleted
- **Proposed resolution**: In UPDATED: require the dirty-tree gate bash fence to invoke implement-bootstrap-invoke.sh --mode resume (after IMPLEMENT_TMPDIR export and plugin-root rehydration) and the same shared routing-env parse as the initial path; drop the duplicate _ib_caller_env.._ib_emergency block and direct bootstrap call; align line 458 re-parse text with the shared parse block
