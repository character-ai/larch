### [Plan Review] FINDING_2

### FINDING_2: Validator-failure split lacks explicit special-case-before-auto-repair execution order
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan pins MANDATORY READ before Step 5c special-case evaluation while moving auto-repair and `_autofix_status` into `validator-failure.md`. Live `SKILL.md:884` orders special-case checks before auto-repair; that inline ordering is not retained in UPDATED bullets. An orchestrator can run reference auto-repair or the inline `design-step-validator-autofix.sh` fence before inline Step 5c special cases (or before `_validator_target_file` binding), breaking review-provenance and missing-composition short-circuits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the SKILL.md UPDATED validator-failure bullets add an explicit execution-order pin: after shared entry and MANDATORY READ, evaluate inline Step 5c special-case blocks before the inline autofix fence and before any reference auto-repair or _autofix_status body. Align validator-failure.md When to load to load-after-entry but execute reference auto-repair only after inline special cases pass.
  - From Cursor-Innovation: In the `skills/design/SKILL.md` UPDATED validator-failure bullets, add an explicit execution-order pin: after the mandatory READ, evaluate inline Step 5c special-case blocks first and short-circuit when they apply; only then bind `_validator_target_file` per `validator-failure.md` and invoke the inline autofix fence; then branch on `_autofix_status` per the reference. Keep a one-line inline reminder mirroring current `SKILL.md:884` special-cases-first ordering.
  - From Cursor-Requirements: Add an inline SKILL.md pin after the Step 5c special-case blocks: when no special case applies, execute validator-failure.md auto-repair coordinator before the inline design-step-validator-autofix.sh fence; keep _autofix_status branching in the reference after the fence The plan is largely aligned with the issue after prior rounds, but three gaps remain: the `validator-failure.md` subsection still lacks an explicit header triplet, **Override-after-defects** is wrongly treated as a direct-entry path, and the validator shared section needs an explicit bridge between inline special cases and the autofix fence.


### [Plan Review] FINDING_3

### FINDING_3: Step 2b.5 self-log paragraph omitted from verbatim move inventory
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The `step2b5-rc-handling.md` Include list covers rc 0/2/other bullets and branches 4-7 but omits the standalone paragraph at `skills/design/SKILL.md:522` between Step 2b.5 item 3 and branch 4 (`Launcher-routed Python design verbs should self-log when they own the failed capture. Prompt-side orchestration should only print the warning breadcrumb and continue.`). That text governs rc=2/other retained paths where the Python verb already logged to `execution-issues.md`. A partial move following only the Include list can drop the breadcrumb-only rule and cause duplicate logging or missing operator warnings on retained paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit move line for the self-log paragraph between item 3 and branch 4 in the step2b5-rc-handling.md NEW subsection, or state that the verbatim move must include that paragraph even though it is outside the numbered branch list.
  - From Cursor-Innovation: Add `skills/design/SKILL.md:522` (`Launcher-routed Python design verbs should self-log…`) to the `step2b5-rc-handling.md` verbatim move inventory, placed after the rc=2/other bullets and before branch 4 hard trigger.
  - From Cursor-Pragmatic: Explicitly include the `SKILL.md:522` paragraph in the `step2b5-rc-handling.md` verbatim move inventory (between rc=2/other-rc handling and branch 4) or add a Contract bullet requiring it verbatim in the reference.


