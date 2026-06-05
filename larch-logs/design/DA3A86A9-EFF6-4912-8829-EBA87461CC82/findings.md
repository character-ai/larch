### FINDING_1:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:654-678
- **Concern**: Proposed SIMPLE entry-fence writes completion sentinels after multiple artifact writes without requiring fail-fast behavior. Scenario: A partial write failure such as approach-synthesis.txt being unwritable can still leave the last .completed touch successful, causing resume to skip Step 2a/2a.5 with missing or corrupt SIMPLE artifacts
- **Proposed resolution**: Wrap the guarded SIMPLE write block in set -e or an explicit if ! { ...; } failure block, and write .completed/step-2a plus .completed/step-2a.5 only after all three artifact writes succeed

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1343-1351
- **Concern**: Step 4 entry compatibility FINALIZE lacks the explicit set +e / capture / warn / exit pattern spelled out for the Step 3b completion fence. Scenario: Under set -e the driver can exit before the repair warning is printed; FM6 and the new exit pins treat warning-only as a failure
- **Proposed resolution**: Mirror item 3 in item 4: wrap compatibility FINALIZE in set +e, capture _finalize_rc, print the repair warning on non-zero, then exit "$_finalize_rc"

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/references/flags.md:48; docs/configuration-and-permissions.md:274
- **Concern**: Plan retargets Step 3b-to-Step 4 routing in SKILL.md, approval-gates.md, and run-step3-review.sh, but leaves the round-cap/env-var contract prose with the old Step 3b / Step 4 / Gate C shortcut.. Scenario: The invalid LARCH_DESIGN_ROUND_CAP panel-failed path remains documented as a direct Step 3b-to-Step 4 chain, so future prompt or doc edits can reintroduce a path that skips the Step 3b FINALIZE boundary and leaves rejected-findings.md missing at Step 4.
- **Proposed resolution**: Add the same boundary-qualified wording to flags.md and the env-var docs, or explicitly include them in the routing guard’s checked surfaces.

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-routing-surface-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh (planned routing guard per plan.txt:68)
- **Concern**: Harness shorthand list omits the comma-without-then form Step 3b, Step 4. Scenario: Cap breadcrumb in skills/design/scripts/run-step3-review.sh:167 and skills/design/references/approval-gates.md:17 uses continuing to Step 3b, Step 4; plan lists only Step 3b, then Step 4 and continuing may not match a strict continue word boundary — bare regressions could pass CI
- **Proposed resolution**: Extend the line-scoped guard to also fail Step 3b, Step 4 (comma, optional then) and Step 3b / Step 4 (space-padded slash); keep positive pins aligned with boundary-qualified cap strings

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-routing-surface-audit
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1299
- **Concern**: Descriptive executes before Step 4 line sits in the Step 3b slice without naming the completion boundary. Scenario: A naive line guard that flags any Step 4 mention in the Step 3b region could false-fail descriptive ordering prose after retargets
- **Proposed resolution**: Scope the guard to routing verbs plus listed shorthands, or exempt non-imperative ordering sentences like executes before Step 4

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-routing-surface-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:29; scripts/test-design-structure.sh:921
- **Concern**: Retarget inventory omits the global anti-halt sequence that still names the bare 3b→4 transition, and the existing structure test pins that stale sequence.. Scenario: After Step 3b visible output, the top-level anti-halt prose can still be read as direct next-step routing to Step 4, bypassing the proposed completion boundary wording.
- **Proposed resolution**: Add this anti-halt line and its test pin to the retarget inventory; route the 3b transition through the Step 3b completion boundary before 4, and extend the guard to catch bare 3b→4 arrows.

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-routing-surface-audit
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/references/flags.md:48; docs/configuration-and-permissions.md:274
- **Concern**: The plan misses additional Step 3b / Step 4 / Gate C routing prose, and the described slash guard only names the unspaced Step 3b/4 form.. Scenario: Env-var docs can keep teaching the panel-failed path as Step 3b / Step 4 / Gate C without the FINALIZE boundary, while the planned guard will not scan these files or catch the spaced-slash form.
- **Proposed resolution**: Retarget these two lines to insert the Step 3b completion boundary before Step 4, and include the spaced-slash Step 3b / Step 4 form in the routing guard if these docs stay in scope.

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-guard-logic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:704-716; plan.txt:17-19
- **Concern**: Step 2a.2 still gates the SIMPLE fast-path on orchestrator-mental `design_classification == SIMPLE`, while the new sentinel writes move into the Step 2a entry bash fence guarded only by `read-design-classification.sh` (default HARD on read/parse failure per plan.txt:17). Scenario: If the script stderr-warns and emits HARD but the orchestrator still treats the run as SIMPLE at line 704, the entry fence writes no sentinels yet control flow still skips sketches/2a.5 and jumps to Step 2b — missing `approach-synthesis.txt` / `contested-decisions.md` and a broken Step 2b read
- **Proposed resolution**: Retarget the 2a.2 SIMPLE branch (and the deleted `### SIMPLE branch` redirect) to follow the entry-fence classification outcome only, e.g. proceed to Step 2b when the entry bash block already wrote SIMPLE sentinels, or re-read `read-design-classification.sh` once and use that value for both the guard and the skip prose

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-guard-logic
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:17-19,32,134-136; skills/design/SKILL.md:666-678,789-802
- **Concern**: The SIMPLE marker plan does not cover pre-PR paused SIMPLE sessions with .completed/step-2a present and .completed/step-2a.5 absent. Scenario: For state step-2a=present step-2a.5=absent, regardless of step-3b/finalize, pause/resume routes to Step 2a.5. The proposed Step 2a entry SIMPLE guard no longer runs, and the proposed Step 2a.5 prose only says the marker was already written, so .completed/step-2a.5 remains missing and later pauses can route back to Step 2a.5.
- **Proposed resolution**: Add a minimal SIMPLE-guarded compatibility write on the Step 2a.5 skip path, or normalize that resume state back to Step 2a. Keep artifact sentinel file writes entry-fence-only and HARD paths untouched.

### OOS_1:
- **Description**: Panel-failed / invalid round-cap docs still say proceeds to Step 3b / Step 4 / Gate C with no completion boundary. Scenario: Operators reading env-var docs may believe Step 4 follows Step 3b without FINALIZE; does not affect SKILL.md orchestration
- **Reviewer**: Cursor-dyn-routing-surface-audit
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/flags.md:48; docs/configuration-and-permissions.md:274
- **Phase**: design
