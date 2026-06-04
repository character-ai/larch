### FINDING_1: Step 2b thin-fence pin lacks REPO passthrough
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned Step 2b `assert_thin_fence` pin may fail because Step 2b’s prelude does not pass through `${REPO:+--repo "$REPO"}`, while the scoped helper expects the same repo threading used elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify Step 2b/Gate B/discussion/Gate A thin-fence preludes and rc 11 exec arms thread REPO like Step 3.6, or document a Step-2b-specific assert variant before landing the pin


### FINDING_2: Legacy Step 2b / Step 2b.5 sentinel path not explicitly retired
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The merged `--with-plan-size` rc 0 path may write both Step 2b and Step 2b.5 sentinels while legacy prose still preserves the old Step 2b sentinel write and standalone “Run Step 2b.5 now” path, causing duplicate or repeated plan-size execution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit FILES bullet to delete the standalone step-2b-only sentinel and Run Step 2b.5 now prose once the rc 0 arm owns both sentinels and plan-size


### FINDING_3: Retained standalone Step 2b.5 hard prompt lacks Override path
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Some retained standalone Step 2b.5 callers still appear to use a Split/Cancel-only hard prompt, while Gate B plan-size flows require a site-aware Split/Override/Cancel prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Gate B Override-after-defects and plan-size-trigger paths that still call standalone Step 2b.5 lose the Override escape hatch approval-gates.md already documents Add explicit FILES work: branch Step 2b.5 hard AskUserQuestion by caller (or document caller-owned arms) and update approval-gates.md Gate B plan-size subsection to match merged rc12 vs retained standalone


### FINDING_4: Split-path dispatch can skip Step 2b.5 Refine return sentinel
- **Reviewer(s)**: Cursor-dyn-sentinel-lifecycle
- **Severity**: important
- **Concern**: The merged thin-fence rc12/rc13 hard/partition paths may dispatch directly to Split-path instead of entering the Step 2b.5 procedure, so Refine returns can skip the `.completed/step-2b.5` sentinel write owned by the legacy procedure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-sentinel-lifecycle: Either enter Split-path through the retained Step 2b.5 procedure (same as legacy steps 4–5) or add an explicit `: > "$DESIGN_TMPDIR/.completed/step-2b.5"` on every Refine return from rc12/rc13 Split-path arms


### FINDING_5: Existing ordering pins still require literal Step 2b.5 text
- **Reviewer(s)**: Cursor-dyn-sentinel-lifecycle
- **Severity**: latent
- **Concern**: Existing `scripts/test-design-structure.sh` ordering checks still grep for literal `Step 2b.5` text after `design-postplan-emit.sh`, which can fail after clean paths move to merged `--with-plan-size` sentinel behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-sentinel-lifecycle: Extend the planned `scripts/test-design-structure.sh` update to retire or repoint `(14c14e)` and `(14c14h)` to merged-fence / sentinel pins (or keep a literal `Step 2b.5` mention only on Override/retained-caller branches)


### FINDING_6: Nested plan-size capture omits LARCH_QUIET_DISABLE
- **Reviewer(s)**: Cursor-dyn-operator-diagnostics
- **Severity**: important
- **Concern**: The `--with-plan-size` path may invoke `check-plan-size.sh` from an already quiet-init parent without `LARCH_QUIET_DISABLE=1`, causing emitted verdict fields and warnings to go to the quiet log instead of stdout capture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-operator-diagnostics: Match skills/design/SKILL.md:980: pin the subprocess call to LARCH_QUIET_DISABLE=1 stdout-only capture (same as standalone Step 2b.5) before mapping verdicts

