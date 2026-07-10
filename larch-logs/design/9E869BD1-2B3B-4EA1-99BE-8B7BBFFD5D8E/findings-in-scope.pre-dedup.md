### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:173-189
- **Concern**: The finalize split moves `/design auto error reporting` out of green `finalize-step5.md`, but SKILL still anchors failure teardown to the green file and never mandates `finalize-step5-failures.md` on pre-Step-5 exit paths.. Scenario: After the split, clarify (`failed-clarify` / `failed-plan-write`), Split-path (`failed-judge-panel`), Step 3 terminal routes (`failed-postplan`, `failed-judge-panel`), and the shared Final summary block still run without the failures slice. Staging, sentinel precedence, operator-action handling, and failure-report classification live only in the moved section, so early exits can mis-stage terminal state or run Final summary without the normative teardown contract while the green file stays resident from Step 5 entry.
- **Proposed resolution**: Extend the SKILL.md update list beyond Step 5 entry: retarget line 189 to `finalize-step5-failures.md`; add a conditional MANDATORY READ of `finalize-step5-failures.md` immediately before any `failed-*` staging and before the Final summary block (clarify, Split-path, Step 3 `final-summary:*`, Step 5c non-zero abort routing); keep green `finalize-step5.md` limited to Step 5 happy-path 5b/5b.5/5c/5d. Pin those load triggers and moved auto-error-reporting needles in `scripts/test-design-structure.sh`.



### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:173-189
- **Concern**: Failure-slice load contract omits Final summary and other pre-Step-5 terminal exits. Scenario: The plan splits auto error reporting into finalize-step5-failures.md and limits green-path finalize-step5.md to Step 5 entry, but it never retargets the Final summary block anchor at line 189 or enumerate MANDATORY READ sites for cancel/clarify-fail/decompose-fail/Step 3 final-summary:* / validator-failure exits. Those paths can run terminal staging without the moved sentinel-precedence and failure-report rules, or still treat green finalize-step5.md as the failure authority.
- **Proposed resolution**: Add explicit SKILL bullets: retarget line 189 to finalize-step5-failures.md; MANDATORY READ the failures slice immediately before any failed-* SUMMARY_OUTCOME Final summary launch and before Step 5c _publish_rc abort/staging; extend finalize-step5-failures.md When to load with that exit list; pin anchor retarget and at least one pre-Step-5 failure-path read in scripts/test-design-structure.sh.



### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh
- **Concern**: Gate A default-path exclusion lacks a structure harness pin. Scenario: Acceptance requires Gate A slice content never load on the default auto-apply path. The plan pins unconditional Gate B/C reads and migrates monolith negatives, but it does not add a negative check that approval-gates-gate-a.md MANDATORY READ appears only at Step 1e Gate A re-entry. A regression could reintroduce Gate A on Steps 3/3.5/4b while closure baseline still passes.
- **Proposed resolution**: Add not_contains checks that SKILL.md lacks approval-gates-gate-a.md outside Step 1e Gate A re-entry; keep Gate A render-gate contains probes on APPROVAL_GATES_GATE_A_MD only. **1. Failure-slice wiring is incomplete (correctness).** Round 1 FINDING_1 remains open. The plan moves auto error reporting into `finalize-step5-failures.md` and restricts green-path `finalize-step5.md` to Step 5 entry, but it does not retarget the Final summary block at `skills/design/SKILL.md:189` or list the pre-Step-5 exits that must load the failures slice (`cancelled-*`, `failed-*`, Step 3 `final-summary:*`, validator-failure Cancel, decompose `failed-judge-panel`, Step 5c `_publish_rc` abort/staging). Without that wiring, early terminal paths can miss moved rules or keep pulling the green file. **2. Gate A default-path guard is untested in structure harness (risk-integration).** The plan migrates Gate A prose and closure baseline expectations, but `scripts/test-design-structure.sh` updates do not add a negative pin that `approval-gates-gate-a.md` is absent from the common path. That leaves acceptance criterion “Gate A never loads on default runs” dependent on closure regeneration alone. Prior accepted items on Step 3 preview ownership, gate-slice unconditional reads, and promoted pytest/heatmap validation look addressed in the current plan text. No additional in-scope gaps found beyond the two above.



### FINDING_4:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-entry.sh:42-108
- **Concern**: Step 3 runtime read is ordered after a wrapper that already emits the Step 3 preview. Scenario: The plan requires `plan-review-runtime.md` to be read after `design-step3-entry.sh` but before the pre-voting preview, yet `design-step3-entry.sh` calls `design-step3-entry-preview.sh` internally, which runs `python/cli.py plan-review preview --variant step3` and prints the preview before control returns to `SKILL.md`. Implementing only the listed SKILL/reference/test changes leaves the preview path executing before the new runtime slice can be loaded, so the accepted Step 3 preview ownership fix remains incomplete.
- **Proposed resolution**: Either read `plan-review-runtime.md` before launching `design-step3-entry.sh`, or add firm updates to split/move `design-step3-entry-preview.sh` so `SKILL.md` reads the runtime slice before invoking the preview wrapper, with matching script-doc and structure-test pins.



