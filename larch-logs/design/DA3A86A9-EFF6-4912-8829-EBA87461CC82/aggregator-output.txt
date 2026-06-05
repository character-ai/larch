### FINDING_1: SIMPLE entry fence can mark completion after partial artifact writes
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Concern**: Proposed SIMPLE entry-fence writes completion sentinels after multiple artifact writes without requiring fail-fast behavior. A partial artifact write failure could still leave completion markers behind, causing resume to skip Step 2a/2a.5 with missing or corrupt SIMPLE artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Wrap the guarded SIMPLE write block in set -e or an explicit if ! { ...; } failure block, and write .completed/step-2a plus .completed/step-2a.5 only after all three artifact writes succeed

### FINDING_2: Step 4 compatibility FINALIZE lacks explicit warning-preserving failure handling
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Step 4 entry compatibility FINALIZE lacks the explicit set +e / capture / warn / exit pattern spelled out for the Step 3b completion fence. Under set -e, the driver can exit before the repair warning is printed, conflicting with warning-only expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation, Cursor-Pragmatic: Mirror item 3 in item 4: wrap compatibility FINALIZE in set +e, capture _finalize_rc, print the repair warning on non-zero, then exit "$_finalize_rc"

### FINDING_3: Env-var and flags docs retain stale Step 3b-to-Step 4 routing prose
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-routing-surface-audit
- **Severity**: latent
- **Concern**: The plan retargets core Step 3b-to-Step 4 routing surfaces but leaves flags/env-var prose documenting the old Step 3b / Step 4 / Gate C shortcut. That can preserve or reintroduce a path that skips the Step 3b FINALIZE boundary and leaves Step 4 without rejected-findings.md.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the same boundary-qualified wording to flags.md and the env-var docs, or explicitly include them in the routing guard’s checked surfaces.
  - From Codex-dyn-routing-surface-audit: Retarget these two lines to insert the Step 3b completion boundary before Step 4, and include the spaced-slash Step 3b / Step 4 form in the routing guard if these docs stay in scope.

### FINDING_4: Routing guard misses comma/slash shorthand variants for Step 3b to Step 4
- **Reviewer(s)**: Cursor-dyn-routing-surface-audit
- **Severity**: important
- **Concern**: The planned routing guard shorthand list omits variants such as `Step 3b, Step 4` and spaced-slash forms. Existing breadcrumbs using those forms could remain or regress while passing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-routing-surface-audit: Extend the line-scoped guard to also fail Step 3b, Step 4 (comma, optional then) and Step 3b / Step 4 (space-padded slash); keep positive pins aligned with boundary-qualified cap strings

### FINDING_5: Naive routing guard could false-fail descriptive Step 4 ordering prose
- **Reviewer(s)**: Cursor-dyn-routing-surface-audit
- **Severity**: nit
- **Concern**: A descriptive “executes before Step 4” line sits in the Step 3b slice without naming the completion boundary. A broad guard that flags any Step 4 mention in that region could incorrectly fail non-routing prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-routing-surface-audit: Scope the guard to routing verbs plus listed shorthands, or exempt non-imperative ordering sentences like executes before Step 4

### FINDING_6: Global anti-halt sequence still pins bare 3b→4 transition
- **Reviewer(s)**: Codex-dyn-routing-surface-audit
- **Severity**: important
- **Concern**: The retarget inventory omits a global anti-halt sequence that still names the bare 3b→4 transition, and the structure test pins that stale sequence. This can still be read as direct routing to Step 4 after Step 3b visible output, bypassing completion-boundary wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-routing-surface-audit: Add this anti-halt line and its test pin to the retarget inventory; route the 3b transition through the Step 3b completion boundary before 4, and extend the guard to catch bare 3b→4 arrows.

### FINDING_7: SIMPLE branch can diverge from entry-fence classification outcome
- **Reviewer(s)**: Cursor-dyn-guard-logic
- **Severity**: important
- **Concern**: Step 2a.2 still gates the SIMPLE fast-path on orchestrator-side classification, while the new sentinel writes move into an entry bash fence guarded by `read-design-classification.sh`. If those disagree, the entry fence may write no sentinels while the prose still skips sketches/2a.5 and jumps to Step 2b, leaving required artifacts missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-guard-logic: Retarget the 2a.2 SIMPLE branch (and the deleted `### SIMPLE branch` redirect) to follow the entry-fence classification outcome only, e.g. proceed to Step 2b when the entry bash block already wrote SIMPLE sentinels, or re-read `read-design-classification.sh` once and use that value for both the guard and the skip prose

### FINDING_8: SIMPLE marker plan misses paused sessions with step-2a complete but step-2a.5 absent
- **Reviewer(s)**: Codex-dyn-guard-logic
- **Severity**: important
- **Concern**: The SIMPLE marker plan does not cover pre-PR paused SIMPLE sessions where `.completed/step-2a` exists but `.completed/step-2a.5` does not. Resume can route to Step 2a.5 after the Step 2a entry guard has already been skipped, leaving `.completed/step-2a.5` missing and causing later pauses to route back there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-guard-logic: Add a minimal SIMPLE-guarded compatibility write on the Step 2a.5 skip path, or normalize that resume state back to Step 2a. Keep artifact sentinel file writes entry-fence-only and HARD paths untouched.
