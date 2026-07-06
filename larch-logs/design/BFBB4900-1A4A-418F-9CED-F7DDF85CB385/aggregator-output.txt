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

### FINDING_4: G-Sec-3 still points at the deleted gh-body-file rule
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The G-Sec-3 deviate note still names the deleted `gh-body-file` rule, so the guideline-level pointer for inline `gh --body` usage disappears when the rule is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: "Replace the deviate bullet with lint gh-body-inline as the mechanical backstop and BASH_AUTHORING.md for authoring guidance; do not leave G-Sec-3 silent on inline gh bodies."

### FINDING_5: markdownlint MD038 guidance is dropped without a replacement note
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The `markdown-no-space-in-code-span` migration is planned as delete-only, but the retired rule's content is supposed to be rerouted to the mechanism doc. Without a replacement note, MD038-specific author guidance goes missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: "Add a concise MD038/no-inner-whitespace note to the markdownlint row or nearby docs/linting.md text, without copying the whole old rule"
