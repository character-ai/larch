### FINDING_1: Topology pre-commit hook still watches the deleted path
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The topology hook still keys off `python/check_topology_rule_paths.py`, so once the lint is repointed, edits to the real implementation will stop retriggering `check-topology-rule-paths` locally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Update the hook files: pattern to skills/shared/topology.tsv, python/larch/lint/check_topology_rule_paths.py, and python/check_topology_rule_paths.md; drop the stale python/check_topology_rule_paths.py and topology-generation.md entries.
  - From Cursor-Innovation: When removing .claude/rules/topology-generation.md from the trigger list, replace the stale path with python/larch/lint/check_topology_rule_paths.py (keep skills/shared/topology.tsv).
  - From Cursor-Pragmatic: When updating triggers, replace the stale path with python/larch/lint/check_topology_rule_paths.py and drop .claude/rules/topology-generation.md.


### FINDING_2: Topology lint and harness need a fixture contract for authority files
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The repointed topology lint will validate `runtime_authority`, but the `--root` harness still uses non-git temp trees and does not yet spell out how authority files, tracked-by-git checks, and row values should behave together.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Gate the tracked-by-git assertion on lint_common.git_rooted(repo_root) (skip under isolated --root fixtures); document that behavior in python/check_topology_rule_paths.md and keep the real-registry smoke without --root.
  - From Cursor-Innovation: Specify harness contract: each fixture runs git init, writes authority files containing the row value, and git add's them; or gate the git-tracked check to real-registry runs only and document that --root fixtures omit it.
  - From Cursor-Pragmatic: Specify contract in python/check_topology_rule_paths.md: either skip tracked-by-git when --root is set, or require fixtures to git init and git add authority files. Document the choice in the harness sibling.
  - From Cursor-Requirements: Specify behavior in python/check_topology_rule_paths.md and the harness rework: either skip git-tracked checks when --root is not the live checkout, or git init && git add authority files in each fixture; add a failure case for untracked authorities on the real-registry path


### FINDING_5: learn-from-bugs coverage index still tracks rules
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Rule Retirement Sweep
- **Severity**: major
- **Concern**: The Python coverage index still scans `.claude/rules`, emits `rules`/`RULES_INDEXED`, and lacks a hooks field, so the updated skill/report schema and machine index will diverge after rule deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add python/larch/issue/learn_from_bugs.py and python/tests/issue/test_learn_from_bugs.py to the plan. Replace the rules scan/stat with hook coverage, or otherwise align the JSON schema and stats with the planned skill report schema.
  - From Cursor-Innovation: Add ### UPDATED: python/larch/issue/learn_from_bugs.py and python/tests/issue/test_learn_from_bugs.py: drop the rules field from CoverageIndex, remove _scan_rules/RULES_INDEXED, and align Step 3 coverage-index reads with the new SKILL.md schema.
  - From Codex-Pragmatic: Add python/larch/issue/learn_from_bugs.py and python/tests/issue/test_learn_from_bugs.py to the plan: remove rules from CoverageIndex and stats, add the planned hook coverage field, and update tests.
  - From Cursor-Requirements: Add ### UPDATED: python/larch/issue/learn_from_bugs.py and python/tests/issue/test_learn_from_bugs.py: drop rules scanning and RULES_INDEXED (or replace with hooks if dedup should index hook contracts); align Step 3 coverage-index field list with the new JSON shape
  - From Cursor-dyn-Rule Retirement Sweep: Add ### UPDATED: python/larch/issue/learn_from_bugs.py: drop _scan_rules and CoverageIndex.rules; stop emitting rules and RULES_INDEXED; map already-covered dedup to guidelines invariants hooks python_lints script_lints only


### FINDING_8: Submodule workflow guidance needs a controlled home in the hook doc
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-Rule Retirement Sweep
- **Severity**: major
- **Concern**: Deleting `no-direct-submodule-edits` without expanding `scripts/block-submodule-edit.md` drops the routed submodule workflow and detection contract from the controlled docs surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add scripts/block-submodule-edit.md as an UPDATED file and move a concise version of the old rule's operator guidance and detection contract there before deleting the rule.
  - From Codex-Innovation: Add ### UPDATED: scripts/block-submodule-edit.md and move the small required content there: do not edit submodules directly, change them via their own PR and pin bump, and note the symlink / superproject detection contract.
  - From Codex-Pragmatic: Make scripts/block-submodule-edit.md the controlled destination for the retained guidance: how to update submodules via the submodule repo plus the symlink, cd, and superproject detection contract.
  - From Codex-Requirements: Add a firm update for `scripts/block-submodule-edit.md` or the hook contract that concisely carries the old rule's submodule-change workflow and detection invariants before deleting the rule.
  - From Codex-dyn-Rule Retirement Sweep: Add `### UPDATED: scripts/block-submodule-edit.md` with a small migration of the rule's unique hook and workflow details


### FINDING_11: Timing-task-kind allow-list still lacks structural enforcement
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Deleting the timing rule without adding pins to `scripts/test-design-structure.sh` drops the only documented enforcement for the `TIMING_TASK_KINDS_ALLOWED` allow-list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Change the test-design-structure item to require a minimal structural check (literals in skills/*/SKILL.md and agents launchers must appear in python/larch/report/timing.py TIMING_TASK_KINDS_ALLOWED) before deleting the rule.
  - From Cursor-Pragmatic: Add explicit harness pins in scripts/test-design-structure.sh (and sibling .md) that fail when a new --timing-task-kind literal is introduced without updating TIMING_TASK_KINDS_ALLOWED in python/larch/report/timing.py, or name another existing harness that will own this check.


### FINDING_1: learn-from-bugs still mixes rule-era and index-era contracts
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The learn-from-bugs migration leaves Step 3/4/5 inconsistent with the new coverage-index contract: Step 3 still reads a `rules` field, Step 4 treats hooks as if they are index-backed even though the Python path leaves them unindexed, and the follow-up/edit-list text still carries stale rule-era language after rules removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Pick one contract: either remove hooks from Step 4 dedup and cite hooks only from fixed docs (hooks/hooks.json, hook sibling .md), or add a minimal hooks index (matcher ids from hooks/hooks.json) and HOOKS_INDEXED stats alongside the removed rules field."
  - From Cursor-Arch: "Add explicit Step 3/4/5 edit lines: drop rules from the read tuple and indexed stats, replace `.claude/rules/` dedup text with guidelines/invariants/lints (and hooks only if indexed), and delete the Step 5 follow-up that drafts `.claude/rules/*.md`."
  - From Cursor-Innovation: "Extend the SKILL.md update to Step 3: read guidelines, invariants, python_lints, script_lints only; if hooks stay prose-only dedup, say hooks are not indexed and must not be read from the JSON."
  - From Cursor-Pragmatic: "In skills/learn-from-bugs/SKILL.md, update Step 3 to read only guidelines, invariants, python_lints, and script_lints from coverage-index.json. In Step 4, state that hooks are checked by reading hooks/hooks.json and hook sibling docs directly, not from the index. Remove the rule best-home option from Step 5 follow-up gates. Match the python/larch/issue/learn_from_bugs.py plan by dropping RULES_INDEXED from prepare stdout."


### FINDING_2: Timing pin scans too little of the repo
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The planned timing structural pin only scans `skills/*/SKILL.md` and `agents/`, but the retired timing rule covered `skills/design/references/*.md`, skill scripts, and current launcher/code surfaces that also carry literal `--timing-task-kind` values. As written, a new literal in those surfaces can bypass CI even though the old rule paths would have caught it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: "Expand the planned `scripts/test-design-structure.sh` scan to include the timing rule's current skill reference surfaces, at minimum `skills/*/references/*.md` alongside `skills/*/SKILL.md`, and align `scripts/test-design-structure.md` with that scope"
  - From Cursor-Innovation: "Expand the pin scan to skills/design/references/*.md (or all skills/**/*.md launch fences) to match the retired rule coverage, or document that Python launchers own literals and references must stay template-indirected only."
  - From Codex-Pragmatic: "Extend the `scripts/test-design-structure.sh` pin to cover the current launcher/code surfaces that pass literal `--timing-task-kind` values, including Python launcher modules and the implement code-flow script, not just `skills/*/SKILL.md` and top-level `agents/`."
  - From Cursor-Requirements: "Expand the pin scan globs to match the deleted rule’s literal-host surfaces at minimum skills/**/references/*.md and skills/**/scripts/*.sh (plus skills/*/SKILL.md); drop or replace the agents/ scope unless literals are added there; keep the allow-list cross-check against TIMING_TASK_KINDS_ALLOWED."
  - From Codex-Requirements: "Make the harness scan all tracked non-test launcher/prompt surfaces that can contain literal --timing-task-kind values, or at least the deleted rule's path set plus current skill reference and skill script call sites, and assert each literal appears in TIMING_TASK_KINDS_ALLOWED."


### FINDING_3: Timing pin needs allowlist reconciliation before it can be enforced
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Even if the scan scope is expanded, the new timing pin will fail immediately unless existing literal `--timing-task-kind` call sites are reconciled with `TIMING_TASK_KINDS_ALLOWED`; otherwise the structural check turns red on preexisting literals instead of catching only new drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: "Add a reconciliation step before or with the pins: enumerate existing --timing-task-kind literals in the scan scope, add missing kinds to TIMING_TASK_KINDS_ALLOWED or fix stale literals, then enable the structural pin."


