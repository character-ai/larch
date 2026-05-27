## Decision 1: Granularity approach for per-step readability lint
- **Question**: How should the per-step granularity be enforced?
- **Resolution**: Per-file expected count — extend each orchestrator-inline manifest_rows entry with an expected count, mirroring the existing external-prompt variant pattern. SKILL.md→4, the six references→1 each. Use `grep -Ec` and compare to expected count.
- **Source**: user

## Decision 2: Scope boundary
- **Question**: Is this change limited to `scripts/lint-readability-preamble.sh` + its test harness, or does it also touch the SKILL.md/references directives themselves?
- **Resolution**: Lint + harness only. The 4 SKILL.md directives and 1-per-file references already exist on the implementing branch; the lint must enforce that they remain present, not move or rewrite them.
- **Source**: codebase (directive lines confirmed at SKILL.md:793, 1081, 1129, 1234 and 1 each in 6 references on the implementing branch)
