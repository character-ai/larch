### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:63-74
- **Concern**: The learn-from-bugs schema update contradicts itself on hook dedup. Step 4 requires mapping coverage from the coverage index, but the Python step explicitly leaves hooks unindexed while the SKILL schema still lists hooks in the dedup set.. Scenario: After rule deletion the report can tell operators to dedup against hooks with no hooks field in coverage-index.json or RULES_INDEXED successor stats, so hook coverage claims are unverifiable and the report schema diverges from the machine index.
- **Proposed resolution**: Pick one contract: either remove hooks from Step 4 dedup and cite hooks only from fixed docs (hooks/hooks.json, hook sibling .md), or add a minimal hooks index (matcher ids from hooks/hooks.json) and HOOKS_INDEXED stats alongside the removed rules field.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:63-89
- **Concern**: The SKILL.md edit list does not explicitly rewrite Step 3's COVERAGE_INDEX read tuple or Step 4 item 3's `.claude/rules/` wording.. Scenario: The three schema bullets are easy to apply partially while Step 3 still tells the orchestrator to read a rules field and Step 4 still asks for a `.claude/rules/` file in dedup prose, leaving stale rule-era instructions after deletion.
- **Proposed resolution**: Add explicit Step 3/4/5 edit lines: drop rules from the read tuple and indexed stats, replace `.claude/rules/` dedup text with guidelines/invariants/lints (and hooks only if indexed), and delete the Step 5 follow-up that drafts `.claude/rules/*.md`.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh
- **Concern**: Timing-kind structural pin drops reference-file coverage from the deleted rule. Scenario: The plan replaces `timing-task-kind-allowlist` with a test that scans only `skills/*/SKILL.md` and `agents/` launcher files, but the deleted rule also covered `skills/design/references/*.md`; after deletion, a literal `--timing-task-kind` added to a design reference can miss `TIMING_TASK_KINDS_ALLOWED` and CI stays green
- **Proposed resolution**: Expand the planned `scripts/test-design-structure.sh` scan to include the timing rule's current skill reference surfaces, at minimum `skills/*/references/*.md` alongside `skills/*/SKILL.md`, and align `scripts/test-design-structure.md` with that scope



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:63
- **Concern**: Step 3 still tells the orchestrator to read a rules field from coverage-index.json. Scenario: The plan removes rules from CoverageIndex and updates Step 4 schema, but Step 3 still lists guidelines, invariants, rules, python_lints, script_lints. After implementation the index has no rules key, so Step 3 contract and machine JSON diverge.
- **Proposed resolution**: Extend the SKILL.md update to Step 3: read guidelines, invariants, python_lints, script_lints only; if hooks stay prose-only dedup, say hooks are not indexed and must not be read from the JSON.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: ARCHITECTURAL_GUIDELINES.md:107
- **Concern**: G-Sec-3 deviate note still points at deleted gh-body-file rule. Scenario: The plan removes .claude/rules citations and adds BASH_AUTHORING.md plus lint gh-body-inline docs, but G-Sec-3 line 107 is the guideline operators read at egress. Deleting the rule cite without a replacement drops the only guideline-level pointer for new gh callers.
- **Proposed resolution**: Replace the deviate bullet with lint gh-body-inline as the mechanical backstop and BASH_AUTHORING.md for authoring guidance; do not leave G-Sec-3 silent on inline gh bodies.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh
- **Concern**: New timing allow-list pins will fail on literals already missing from TIMING_TASK_KINDS_ALLOWED. Scenario: The plan adds pins over skills/*/SKILL.md and agents/, but test-design-structure.sh currently has no timing pins. Existing literals such as rejected-analysis-verify in skills/rejected-analysis/SKILL.md are absent from python/larch/report/timing.py. make test-design-structure will fail as soon as pins land.
- **Proposed resolution**: Add a reconciliation step before or with the pins: enumerate existing --timing-task-kind literals in the scan scope, add missing kinds to TIMING_TASK_KINDS_ALLOWED or fix stale literals, then enable the structural pin.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/test-design-structure.sh
- **Concern**: Timing pin scan scope is narrower than the deleted timing rule paths. Scenario: The deleted .claude/rules/timing-task-kind-allowlist.md path-triggered skills/design/references/*.md as well as SKILL.md launch blocks. The plan pins only skills/*/SKILL.md and agents/, so a new literal kind added in skills/design/references would not fail CI after rule deletion.
- **Proposed resolution**: Expand the pin scan to skills/design/references/*.md (or all skills/**/*.md launch fences) to match the retired rule coverage, or document that Python launchers own literals and references must stay template-indirected only.



### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: docs/linting.md:11
- **Concern**: `markdown-no-space-in-code-span` is planned as delete-only even though the scope routes lint-backed rule prose to the mechanism doc. Scenario: The `.claude/rules` deletion removes the only controlled prose for MD038-specific author guidance; the migration no longer satisfies "route each rule's content" for this lint-backed rule
- **Proposed resolution**: Add a concise MD038/no-inner-whitespace note to the markdownlint row or nearby docs/linting.md text, without copying the whole old rule



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:63-74
- **Concern**: learn-from-bugs dedup contract still implies coverage-index backs hooks after rules removal. Scenario: The plan removes the rules field from coverage-index.json and leaves hooks unindexed, but the updated SKILL.md schema still lists hooks beside index-backed categories in the Step 4 dedup section without saying hooks are manual-only. Step 3 still tells the orchestrator to read rules from COVERAGE_INDEX_PATH. An implementer can keep mapping hook coverage from the index and emit false already-covered dedup after rules deletion.
- **Proposed resolution**: In skills/learn-from-bugs/SKILL.md, update Step 3 to read only guidelines, invariants, python_lints, and script_lints from coverage-index.json. In Step 4, state that hooks are checked by reading hooks/hooks.json and hook sibling docs directly, not from the index. Remove the rule best-home option from Step 5 follow-up gates. Match the python/larch/issue/learn_from_bugs.py plan by dropping RULES_INDEXED from prepare stdout.



### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh (plan.txt:143-148)
- **Concern**: Prior accepted timing allow-list fix remains incomplete; the planned structural pin scans only `skills/*/SKILL.md` and `agents/` launcher files, but current literal `--timing-task-kind` call sites live in `python/larch/agents/*.py`, `python/larch/design/*.py`, `python/larch/review/*.py`, `python/larch/git/pr_body.py`, and `skills/implement/scripts/generate-code-flow-diagram.sh`.. Scenario: After `.claude/rules/timing-task-kind-allowlist.md` is deleted, a new or renamed Python launcher task kind can miss `TIMING_TASK_KINDS_ALLOWED`; the runtime only warns on unknown kinds, so CI no longer preserves the allow-list contract that this migration is supposed to route into the harness.
- **Proposed resolution**: Extend the `scripts/test-design-structure.sh` pin to cover the current launcher/code surfaces that pass literal `--timing-task-kind` values, including Python launcher modules and the implement code-flow script, not just `skills/*/SKILL.md` and top-level `agents/`.



### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: scripts/test-design-structure.sh
- **Concern**: The proposed timing allow-list pins scan only skills/*/SKILL.md and agents/, but the deleted timing rule also covered skills/design/references/*.md and skill scripts; agents/ has no --timing-task-kind literals today.. Scenario: After deleting .claude/rules/timing-task-kind-allowlist.md, literals such as claude-plan-voter in skills/design/references/plan-review.md and implement-code-flow in skills/implement/scripts/generate-code-flow-diagram.sh lose the only structural pairing check; a new kind added there will not fail make test-design-structure even though the old rule paths included skills/design/references/*.md.
- **Proposed resolution**: Expand the pin scan globs to match the deleted rule’s literal-host surfaces at minimum skills/**/references/*.md and skills/**/scripts/*.sh (plus skills/*/SKILL.md); drop or replace the agents/ scope unless literals are added there; keep the allow-list cross-check against TIMING_TASK_KINDS_ALLOWED.



### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1
- **Concern**: Round-1 timing fix is incomplete because the planned structural pin names only skills/*/SKILL.md and agents/ launcher files.. Scenario: Current literal --timing-task-kind call sites also live in skills/design/references/brainstorm.md, skills/rejected-analysis/SKILL.md, and skills/implement/scripts/generate-code-flow-diagram.sh, so deleting the timing rule would still leave required literals outside the new allow-list check.
- **Proposed resolution**: Make the harness scan all tracked non-test launcher/prompt surfaces that can contain literal --timing-task-kind values, or at least the deleted rule's path set plus current skill reference and skill script call sites, and assert each literal appears in TIMING_TASK_KINDS_ALLOWED.



