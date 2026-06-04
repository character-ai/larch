### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:80-84
- **Concern**: Step 2b assert_thin_fence pin lacks REPO passthrough contract. Scenario: Plan adds assert_thin_fence for Step 2b but scoped assert_thin_fence requires ${REPO:+--repo "$REPO"} on the entry pause-save guard; current Step 2b prelude omits REPO while Step 3.6 includes it, so the new pin fails immediately or the harness must be weakened
- **Proposed resolution**: Specify Step 2b/Gate B/discussion/Gate A thin-fence preludes and rc 11 exec arms thread REPO like Step 3.6, or document a Step-2b-specific assert variant before landing the pin

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:973-973,1015-1015
- **Concern**: Legacy Step 2b sentinel and Run Step 2b.5 now not explicitly retired. Scenario: After --with-plan-size rc 0 writes step-2b and step-2b.5, leaving the pre-2b.5 step-2b write and Run Step 2b.5 now re-invokes standalone check-plan-size and can write step-2b.5 twice
- **Proposed resolution**: Add an explicit FILES bullet to delete the standalone step-2b-only sentinel and Run Step 2b.5 now prose once the rc 0 arm owns both sentinels and plan-size

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:994-996
- **Concern**: skills/design/references/approval-gates.md:161-163. Scenario: Approach requires site-aware hard prompts for retained standalone Step 2b.5 (Gate B / plan-review-loop: Split/Override/Cancel) but FILES only narrows merged-path prose; Step 2b.5 hard branch stays Split/Cancel-only
- **Proposed resolution**: Gate B Override-after-defects and plan-size-trigger paths that still call standalone Step 2b.5 lose the Override escape hatch approval-gates.md already documents Add explicit FILES work: branch Step 2b.5 hard AskUserQuestion by caller (or document caller-owned arms) and update approval-gates.md Gate B plan-size subsection to match merged rc12 vs retained standalone

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-sentinel-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:994-1013
- **Concern**: Thin-fence rc12/rc13 Split-path dispatch bypasses the Step 2b.5 named procedure that owns the Refine return sentinel write. Scenario: Merged `--with-plan-size` routes hard/partition to thin-fence rc arms that call Split-path directly; legacy Step 2b.5 writes `.completed/step-2b.5` only at procedure exit (line 1013). Refine-from-Split returns skip that write, leaving a stale or missing sentinel after a revised plan
- **Proposed resolution**: Either enter Split-path through the retained Step 2b.5 procedure (same as legacy steps 4–5) or add an explicit `: > "$DESIGN_TMPDIR/.completed/step-2b.5"` on every Refine return from rc12/rc13 Split-path arms

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-sentinel-lifecycle
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:556-565
- **Concern**: Existing ordering pins still require literal `Step 2b.5` after `design-postplan-emit.sh` in approval-gates and discussion-rounds. Scenario: Merged clean paths replace standalone Step 2b.5 calls with `--with-plan-size` plus `.completed/step-2b.5` sentinel prose; `(14c14e)` / `(14c14h)` grep `Step 2b.5`, not the sentinel path, so CI fails even when runtime behavior is correct
- **Proposed resolution**: Extend the planned `scripts/test-design-structure.sh` update to retire or repoint `(14c14e)` and `(14c14h)` to merged-fence / sentinel pins (or keep a literal `Step 2b.5` mention only on Override/retained-caller branches)

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-operator-diagnostics
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:13-16
- **Concern**: --with-plan-size omits LARCH_QUIET_DISABLE=1 when invoking check-plan-size.sh from an already quiet-init parent. Scenario: Under $() capture design-postplan-emit.sh runs larch_quiet_init; nested check-plan-size emit_kv lines go to the quiet log not the driver capture so HARD_TRIGGER_FIRED/SOFT_ADVISORY parsing rc12/rc13/0 and nonfatal rc2/3 WARN text silently fail
- **Proposed resolution**: Match skills/design/SKILL.md:980: pin the subprocess call to LARCH_QUIET_DISABLE=1 stdout-only capture (same as standalone Step 2b.5) before mapping verdicts
