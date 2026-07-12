### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:108-156,236-238
- **Concern**: [1] Marker writes use ANALYSIS_ROOT, but the preserved commit and rollback commands still operate from PWD. Scenario: With an explicit --root pointing to another checkout, write-state updates that checkout while git commit --only and rollback inspect PWD. The scan boundary may remain uncommitted, or the wrong repository may be modified.
- **Proposed resolution**: Run the marker commit and rollback against ANALYSIS_ROOT, such as with git -C "$ANALYSIS_ROOT", and derive the marker path relative to that checkout.



### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py:planned canonical target validation and filing reconciliation
- **Concern**: [2] Filing reconciliation can make a fix proposal invalid under its own target grammar. Scenario: The plan requires fix targets to use fix:<stable-descriptive-token> without filed_issue and issue:<number> when filed_issue is present, but filing only says to attach filed_issue to the proposal. If the target is not rewritten, write-state rejects the successfully filed fix record or persists a record that violates the schema.
- **Proposed resolution**: When attaching an issue number to a fix proposal, rewrite its target to issue:<number>, or define and validate one consistent target form that preserves the fix target while carrying filed_issue.



### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py:planned stable-ID helper; skills/learn-from-bugs/SKILL.md:planned residual proposal requirements
- **Concern**: [3] Stable-ID construction remains underspecified despite the dedup fix. Scenario: The plan requires a stable kebab-case ID derived from durable meaning but does not define canonical normalization, field ordering, or collision handling. Independent runs can produce different IDs for the same residual, or identical IDs for distinct proposals, defeating still-pending deduplication.
- **Proposed resolution**: Specify one deterministic ID algorithm over normalized immutable proposal fields, including normalization and collision behavior, and use it in both proposal generation and reconciliation.



### FINDING_4:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py:43-49
- **Concern**: Fix target grammar conflicts with filing reconciliation. Scenario: A new fix starts with target `fix:<stable-descriptive-token>` and `filed_issue: null`. Filing attaches an issue number, but the proposed loader then requires target `issue:<number>`. The reconciled record becomes invalid and blocks marker advancement. Rewriting the target would also violate the plan's immutable-content comparison.
- **Proposed resolution**: Keep `fix:<stable-descriptive-token>` valid after `filed_issue` is populated. Use the separate `filed_issue` field for GitHub adoption checks.



