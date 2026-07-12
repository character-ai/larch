### OOS_2: Plan says retain marker-only/rollback structural checks that are not in the harness
- **Description**: Plan says retain marker-only/rollback structural checks that are not in the harness. Scenario: Retain checks for marker-only staging, root-relative rollback overstates current coverage; only O/P ordering checks exist today
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/tests/skills/_structure_learn_from_bugs_specialized.py:plan testing section
- **Phase**: design

### OOS_5: Publication fragment is prose-only not one shared fenced block
- **Description**: Publication fragment is prose-only not one shared fenced block. Scenario: Three call sites risk drift without a single literal Bash fence the structural harness can pin once
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/learn-from-bugs/SKILL.md
- **Phase**: design

### OOS_7: Document new marker durability semantics
- **Description**: Document new marker durability semantics. Scenario: Operator-facing behavior is already carried in `skills/learn-from-bugs/SKILL.md`; catalog docs can follow separately
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: docs/skills.md
- **Phase**: design

### OOS_8: Restore the operator's pre-run branch after publication
- **Description**: Restore the operator's pre-run branch after publication. Scenario: Success or manual handoff does not require checking out the original branch to satisfy the bug fix
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/learn-from-bugs/SKILL.md
- **Phase**: design

