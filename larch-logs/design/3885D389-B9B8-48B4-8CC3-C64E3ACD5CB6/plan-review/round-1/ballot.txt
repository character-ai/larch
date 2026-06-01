Normalized aggregator output from the nine reviewer slots. Four distinct behavioral risks after merge (preamble bypass, dirty-tree third copy, routing harness pin, structure-test expectations).

### FINDING_1: Preamble still mandates direct `implement-bootstrap.sh --up-to-phase coder`
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The Protocol Execution Directive (item 3) and Anti-halt Preflight→Step 0 boundary still require `${CLAUDE_PLUGIN_ROOT}/scripts/implement-bootstrap.sh --up-to-phase coder` while Step 0 is being thinned to `implement-bootstrap-invoke.sh`. Orchestrators that follow the top-of-file protocol before the numbered Step 0 section can bypass the new wrapper, envelope parse, and argv assembly the extraction is meant to centralize—reintroducing duplication and drift from the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Retarget both directives to `scripts/implement-bootstrap-invoke.sh --mode initial` (and dirty-tree `--mode resume`) in the same Step 0 edit, or widen the planned SKILL.md scope beyond “Step 0 region only”
  - From Cursor-Pragmatic: Retarget the directive and anti-halt boundary text to implement-bootstrap-invoke.sh --mode initial (and dirty-tree --mode resume) with envelope parsing as today
  - From Cursor-Requirements: Extend the SKILL.md update (or add an explicit plan bullet) to retarget items (3) and the Anti-halt Preflight→Step 0 boundary to `implement-bootstrap-invoke.sh --mode initial`, matching the new Step 0 call sites

### FINDING_2: Dirty-tree recovery keeps a third direct bootstrap + argv/`_ib_kv_scan` copy
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-env-boundary
- **Severity**: important
- **Concern**: Dirty-tree recovery (`skills/implement/SKILL.md` ~454–509) still documents a fenced bash path with reassembled `_ib_caller_env` / issue / fork / emergency argv, a direct `implement-bootstrap.sh --up-to-phase plan --resume-plan-tail` call, and a second `_ib_kv_scan` re-parse; item-3 prose (~458) and routing row ~446 still name the old path. The plan thins main Step 0 initial/resume sites but leaves this third harness copy, so #3298’s collapse is incomplete and dirty-tree resume can diverge from `--mode resume` envelope filtering (especially once `_ib_parse_bootstrap_out` is removed from the skill).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the same SKILL.md edit, route dirty-tree continuation through `implement-bootstrap-invoke.sh --mode resume`, reuse the shared envelope parse, and replace prose at ~458 that still names direct `implement-bootstrap.sh`
  - From Cursor-Pragmatic: Replace the dirty-tree bash example with implement-bootstrap-invoke.sh --mode resume plus the shared routing-env parse; update item-3 prose and routing row 446 to match
  - From Cursor-Requirements: In `### UPDATED: skills/implement/SKILL.md`, require dirty-tree step 3 and the recovery bash fence to call `implement-bootstrap-invoke.sh --mode resume` (with the same pre-call `export` list), drop reassembled `_ib_caller_env`/`_ib_issue`/… arrays and the direct bootstrap invocation, and reuse the single shared routing-env parse block (no second `_ib_kv_scan`)
  - From Cursor-dyn-env-boundary: In UPDATED: require the dirty-tree gate bash fence to invoke implement-bootstrap-invoke.sh --mode resume (after IMPLEMENT_TMPDIR export and plugin-root rehydration) and the same shared routing-env parse as the initial path; drop the duplicate _ib_caller_env.._ib_emergency block and direct bootstrap call; align line 458 re-parse text with the shared parse block

### FINDING_3: `test-implement-step2-routing.sh` still pins `--up-to-phase coder` in SKILL.md
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `scripts/test-implement-step2-routing.sh:35` still asserts `--up-to-phase coder` in `skills/implement/SKILL.md`. After Step 0 moves to `implement-bootstrap-invoke.sh --mode initial`, that `assert_contains` will fail in test-harnesses-16 while the plan lists this file under verify-only, not UPDATED.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Retarget the pin to implement-bootstrap-invoke.sh --mode initial or phase_coder_select in implement-bootstrap.sh per plan Approach edit-in-sync sweep

### FINDING_4: Plan omits post-refactor awk expectations in `test-implement-structure.sh`
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Concern**: The plan says to retarget the Step 0 awk guard in `scripts/test-implement-structure.sh` (~550–575) but does not specify new expected counts after bootstrap moves out of `<!-- step:0` bash blocks. An implementer may leave `bootstrap_calls==1` / `resume_mentions==1` on `implement-bootstrap.sh` literals and get a false pass or a confusing failure after SKILL.md correctly drops direct bootstrap calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Spell out the post-refactor awk expectations (e.g. zero direct `implement-bootstrap.sh` calls in Step 0 bash, exactly one `implement-bootstrap-invoke.sh --mode initial`, exactly one `--mode resume`, `--up-to-phase coder` asserted only in `scripts/implement-bootstrap-invoke.sh`)

**Merge notes (for voters, not machine output):** Input FINDING_2–3, 6, and 9 → aggregator FINDING_2; input FINDING_1, 4, and 7 → aggregator FINDING_1. No `[OUT_OF_SCOPE]` tags in the supplied input.
