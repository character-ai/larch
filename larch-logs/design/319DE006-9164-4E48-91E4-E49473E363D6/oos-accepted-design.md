### OOS_1:
- **Description**: Prose names `LARCH_DESIGN_CONVERGENCE_THRESHOLD` alongside `LARCH_DESIGN_ROUND_CAP` in the Gate B apply contract note; this env var is fully removed by the plan but `approval-gates.md` is absent from the plan's update list. Scenario: After the PR lands `approval-gates.md:209` still references the removed env var; the drift-prone-prose-in-docs rule requires a grep sweep of docs/ for stale names, and the plan's own "Failure modes" section acknowledges a grep-sweep mitigation — but the file is not added to the explicit update list
- **Reviewer**: unknown-slot
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/design/references/approval-gates.md:209
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/3255
