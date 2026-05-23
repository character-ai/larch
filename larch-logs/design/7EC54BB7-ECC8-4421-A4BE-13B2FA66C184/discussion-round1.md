## Decision 1: Which of the suggested fixes (A/B/C/D) are in scope
- **Question**: Which of the four suggested fixes from the issue (A SKILL.md tightening, B dispatcher paths-file output, C collect-agent-results.sh --paths-file flag, D CI/lint coverage) should this design cover?
- **Resolution**: A + B + C. D (lint coverage) is out of scope.
- **Source**: user

## Decision 2: Fix A contract — bundle vs persistence pattern
- **Question**: For SKILL.md tightening (fix A), should we (i) bundle dispatch+collect into a single Bash block, (ii) document an explicit cross-subshell persistence pattern (paths-one-per-line file), or (iii) both?
- **Resolution**: Document persistence (paths-file pattern). Dispatcher writes paths one-per-line to a deterministic file under `$DESIGN_TMPDIR`; subsequent collect block reads it via Bash 3.2-compatible `while read`.
- **Source**: user

## Decision 3: Backward compatibility for dispatcher stdout
- **Question**: Must the change preserve the existing dispatcher stdout contract (the `ALL_OUTPUT_FILES=<space-separated paths>` emit_kv line)?
- **Resolution**: Yes — strictly additive. The paths-file is an additional output. Existing callers continue to work unchanged.
- **Source**: user

## Decision 4: Dispatcher scope — which dispatchers get the paths-file output
- **Question**: Should fix B extend to `dispatch-code-voters.sh` and `dispatch-plan-voters.sh` in addition to `dispatch-with-waterfall.sh`?
- **Resolution**: All three dispatchers. Apply the paths-file additive contract uniformly to avoid leaving latent hazards.
- **Source**: user

## Decision 5: SKILL.md audit scope — which skills get tightened
- **Question**: Should fix A apply only to `skills/design/SKILL.md` Step 3, or also to other skills that use the same dispatch+collect Bash split pattern?
- **Resolution**: Audit and fix all skills with the same pattern. After codebase audit: only `skills/design/SKILL.md` Step 3 + `skills/design/references/plan-review.md` exhibit the orchestrator-side inline `ALL_OUTPUT_FILES` cross-subshell hazard. `skills/review/SKILL.md` and its references wrap `dispatch-with-waterfall.sh` / `dispatch-code-voters.sh` inside script wrappers (`dispatch-panel.sh`, `aggregate-findings.sh`, `review-core.sh`), keeping the variable persistence inside one process. Hard scope boundary: only the two design-skill files need prompt-side tightening.
- **Source**: user + codebase audit

## Hard constraints (implicit, must not break)
- Bash 3.2 portability (BASH_AUTHORING.md §3) — no `mapfile` / `readarray`; use `while IFS= read -r ...` loops.
- Existing `dispatch-with-waterfall.sh` stdout/FD-3 emit_kv contract preserved (no removal/rename of `ALL_OUTPUT_FILES` or `ALL_OUTPUT_TOOLS` lines).
- `collect-agent-results.sh` anti-pattern rule #4 ("NEVER call with zero positional arguments") preserved — the new `--paths-file` flag must either be mutually exclusive with positional args or fail closed when the paths-file is empty.
- Existing test harnesses (`test-dispatch-with-waterfall.sh`, `test-dispatch-plan-voters.sh`, `test-dispatch-code-voters.sh`, plan-review and design-structure CI greps) must continue to pass.
- `lib-quiet.md` emit_kv FD 3 contract preserved on existing keys.
