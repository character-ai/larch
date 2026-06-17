### FINDING_1: Reconcile "No shims" with forward-looking thin-wrapper policy
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan only adds a new decision-log bullet and does not explicitly amend the existing **No shims** line ("no intermediate .sh wrapper files, ever"). Readers and implementers can see contradictory guidance: migration playbook forbids wrappers absolutely while AGENTS.md and the new path-triggered rule permit thin delegation wrappers for glue/hooks/CI. That can misclassify existing launcher wrappers (e.g. `skills/implement/scripts/step-7a.sh`) as migration violations, or encourage cutover shims where only forward-looking glue is intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make ### UPDATED: docs/python-migration.md explicitly amend the **No shims** bullet to migration cutover only (retire forwarding stubs after consumer repoint), and add the forward-looking Python-first bullet that cross-links AGENTS.md and `.claude/rules/python-first-scripts.md`
  - From Cursor-Innovation: Require an explicit ### UPDATED edit to the existing **No shims** bullet scoping it to migration cutover (retire a domain: repoint consumers to cli.py and delete the old .sh) and state that forward-looking glue wrappers are governed by the new Python-first bullet; mirror the same scoped wording in AGENTS.md and `.claude/rules/python-first-scripts.md`
  - From Cursor-Requirements: In `### UPDATED: docs/python-migration.md`, require the new decision-log entry to explicitly scope **No shims** to migration/voluntary-port cutovers (or add a cross-linked parenthetical there) and state that forward-looking glue/hook/CI wrappers are governed by the new policy, not the shim prohibition


### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: .claude/rules/python-first-scripts.md:1-4
- **Concern**: [SCOPE-REDUCTION] Rule paths include .github/workflows/**/* even though the scope asks for a point-of-edit reminder when .sh files are edited. Scenario: This broadens the new rule to workflow YAML and requirements files, adding non-.sh trigger surface beyond the approved doc-only minimum-change plan
- **Proposed resolution**: Remove .github/workflows/**/* from the frontmatter paths. Keep the CI/pre-commit exception in the rule text only.


### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: .claude/rules/python-first-scripts.md:1-3 (planned)
- **Concern**: [SCOPE-REDUCTION] Planned rule paths include `.github/workflows/**/*` outside the `.sh` edit surface. Scenario: The issue asks for an always-loaded rule plus a point-of-edit reminder when `.sh` files are edited. This path also loads the script policy for workflow YAML and requirements files, adding noise and scope beyond the request.
- **Proposed resolution**: Drop `.github/workflows/**/*` and keep the shell-strict-mode `.sh` path set.


### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/python-migration.md:9-42
- **Concern**: [SCOPE-REDUCTION] New decision-log bullet alone leaves the standing No shims ever line and recipe step 4 cut consumers to direct cli.py unreconciled with permitted new thin wrappers. Scenario: Contributors porting bash may add new .sh delegation stubs believing the forward policy allows wrappers, or avoid legitimate new skill glue wrappers because No shims still reads as absolute
- **Proposed resolution**: In the UPDATED docs/python-migration.md task, require amending the No shims bullet to scope it to migration consumer cutover (no cutover stubs) and add the new Python-first bullet that permits only new orchestration or CI or hook glue wrappers; cross-link recipe step 4 explicitly


### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:30-36,62
- **Concern**: [SCOPE-REDUCTION] Rule paths include .github/workflows/**/* even though scope asks for .sh edit-point visibility. Scenario: The new rule would fire on workflow YAML and requirements text changes that are not larch script edits; the CI glue exception can be documented in rule text without broadening the trigger surface
- **Proposed resolution**: Drop .github/workflows/**/* and the matching edge-case bullet; keep the CI/pre-commit glue exception in AGENTS.md, the rule body, and docs/python-migration.md



### FINDING_1: No shims permits orchestration launchers that AGENTS and the rule do not define
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The amended "No shims" wording names orchestration launchers as permitted forward-looking glue, while AGENTS.md and the path-triggered rule content only allow thin env-plus-delegate wrappers and hooks or CI glue. Three surfaces can ship with conflicting guidance: the decision log permits orchestration launchers but AGENTS and the rule do not define or allow that category; step-8-ship-style scripts may be misclassified and future authors get contradictory answers on how much Bash is allowed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Drop orchestration launchers from the No shims parenthetical or define the term identically on all three surfaces; minimum-change is to keep only thin delegation wrappers hooks and pre-commit or CI glue per the issue anchor


### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:21-23,40-41; docs/python-migration.md:14
- **Concern**: [SCOPE-REDUCTION] Planned policy allows thin Bash wrappers to delegate to another Python module, even though the plan and existing migration contract keep new logic behind python3 python/cli.py. Scenario: A future wrapper can bypass the canonical CLI registry by calling python/foo.py directly; the new rule would bless a second entrypoint beyond the issue's thin-wrapper exception
- **Proposed resolution**: Drop "or another Python module" from AGENTS.md and .claude/rules/python-first-scripts.md; require thin wrappers to delegate through python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ...


