## Goal
Add skill name to step headers across all larch skills

## Implementation Plan
## Implementation Plan

### Goal
Add the skill name between the 🔶 icon and the step number in every skill's step header. Change `> **🔶 N: step-name**` to `> **🔶 /skill-name N: step-name**`. For nested calls, propagate parent skill path through --step-prefix third :: field.

### Files to modify

**1. skills/shared/progress-reporting.md**
- Update breadcrumb format spec from `{icon} {step_number}: {breadcrumb_path}` to `{icon} /{skill_path} {step_number}: {breadcrumb_path}`
- Add {skill_path} definition (standalone = skill name; nested = PARENT_SKILL_PATH:/skill_name from --step-prefix third :: field)
- Extend --step-prefix encoding to add optional third :: field PARENT_SKILL_PATH
- Update all examples

**2. skills/fix-issue/SKILL.md**
- Add /fix-issue to all Print 🔶 directives: Steps 0, 3, 4, 5, 6
- Update anti-halt Step 6 reference

**3. skills/implement/SKILL.md**
- Add /implement to Print 🔶 directives: Steps 2, 5, 7a
- Update --step-prefix calls: "1.::design plan" -> "1.::design plan::/implement"; "5.::code review" -> "5.::code review::/implement"

**4. skills/design/SKILL.md**
- Add /design to all standalone Print: directives
- Update line 38 override rule to add skill path handling
- Update line 36 example format

**5. skills/design/references/flags.md**
- Update --step-prefix description for third :: field

**6. skills/research/SKILL.md**
- Add /research to all Print 🔶 directives

**7. skills/research/references/research-phase.md**
- Add /research to all Print 🔶 directives

**8. skills/review/SKILL.md**
- Update Progress section to mention skill path in breadcrumbs

### Estimated diff_lines
~90 lines changed across 8 files

## Test plan
(no test plan section in plan-file)
