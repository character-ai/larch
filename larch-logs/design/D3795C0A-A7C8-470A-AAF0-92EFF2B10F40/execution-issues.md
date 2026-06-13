### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-stall-policy-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-dyn-stall-policy-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	testing	skills/implement/scripts/test-stall-recovery-report.sh:200-205	Item 1 tests omit stale-evidence regression mirroring protected-path case7k2	#4122 fallthrough is dispatch-output or transient matching on poisoned evidence; clean write_state fixtures today classify submodule bail as unrecoverable so tests can pass without proving the early bail arm beats grep classifiers	Add a state-file classify fixture with write_state ... submodule-edit-required-out-of-scope and extra NOTE=network timeout (or execution text containing step2 dispatch); assert FAILURE_CLASS=submodule-restricted and MATCHED_CLASSIFIER_PATTERN=submodule-restricted-bail-token
2	in_scope	latent	correctness	skills/implement/scripts/stall-recovery-report.sh:721-726	Plan step to remove submodule-edit from dispatch-bail-token list targets the wrong arm	submodule-edit-required-out-of-scope is not in the line 722 dispatch-bail-token case today; real misclassification is dispatch-output grep at 716-719 or transient-output at 728-731	Drop the removal step; document actual fallthrough paths and rely on the new early bail case before those greps
3	out_of_scope	latent	risk-integration	skills/implement/references/stall-recovery.md:42-43	stall-recovery.md documents protected-path inline resume but not submodule-restricted	Operators following Step 18a normative doc may not know submodule-restricted uses the same step2-impl handoff and warning pattern	Add a sentence parallel to the protected-path bullet when implementing Item 1

### FINDING_1: Missing stale-evidence regression for submodule classification
- **focus_area**: testing
- **location**: `skills/implement/scripts/test-stall-recovery-report.sh:200-205`
- **Concern**: Item 1 adds classification tests but does not require the stale-evidence fixture that protected-path uses. The motivating bug is fallthrough to `dispatch-failure` (via `dispatch-output` grep when evidence contains step2 dispatch text) or `transient-infra` (when evidence contains timeout/network phrases). Clean `write_state` evidence alone currently lands on `unrecoverable`, so tests can pass without proving the early bail arm wins over those greps.
- **Suggested fix**: Mirror case7k2: `write_state "$dir" 2 implementation submodule-edit-required-out-of-scope "NOTE=network timeout"` plus argv-only case; assert `FAILURE_CLASS=submodule-restricted`, `MATCHED_CLASSIFIER_PATTERN=submodule-restricted-bail-token`, and `RESUME_HINT=step2-impl`.

### FINDING_2: Plan misidentifies dispatch-bail-token as current fallthrough path
- **focus_area**: correctness
- **location**: `skills/implement/scripts/stall-recovery-report.sh:716-726`
- **Concern**: The plan says to remove `submodule-edit-required-out-of-scope` from the dispatch-bail-token list near line 722, but that token is not in that arm today. Actual pre-fix paths are the `dispatch-output` heuristic (line 716) and `transient-output` heuristic (line 728). The proposed early bail case before those greps is the right fix; the removal step is misleading.
- **Suggested fix**: Remove the inaccurate dispatch-bail-token removal instruction from the plan; keep only the early `submodule-edit-required-out-of-scope)` arm parallel to `protected-path-edit-required-out-of-scope`.

### [OUT_OF_SCOPE] FINDING_3: stall-recovery.md omits submodule-restricted resume semantics
- **focus_area**: risk-integration
- **location**: `skills/implement/references/stall-recovery.md:42-43`
- **Concern**: Normative Step 18a reference documents protected-path inline resume but not the new `submodule-restricted` class. SKILL.md escalation prose is updated; this reference is not.
- **Suggested fix**: Add submodule-restricted inline-resume wording parallel to the protected-path bullet.

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-stall-policy-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-dyn-stall-policy-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-dyn-stall-policy-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-dyn-stall-policy-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-dyn-stall-policy-output.txt.launch-stderr)

timing: WARNING: unknown task-kind: cursor-phase1-dyn-cursor-plan-stall-policy
  ```
### Warnings

- **Step design file-design-oos annotate — file-design-oos.sh empty stdout failed (exit 1)**:
  ```
file-design-oos annotate: issue-stdout-file empty or missing (<TMPDIR>/oos-issue.stdout.txt)
  ```
