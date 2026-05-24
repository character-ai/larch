# Review Round 2

- Mode: `diff`
- 8 accepted, 8 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: `emit-design-plan-preview.sh` outline capture under `set -e` / `pipefail` can exit before empty-outline or `head -n 30` fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Under `set -euo pipefail`, capturing `_outline` via `grep '^#{2,3} ' … | head` yields non-zero when there are no `^#{2,3} ` matches (`grep` exit 1) and/or SIGPIPE when `head` closes the pipe; the script can abort before the documented first-30-lines fallback and before sentinel/touch paths, so large headerless plans break Step 3 / Gate C preview and acceptance/docs that assume the fallback runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Append `|| true` to the pipeline or disable pipefail for that capture; keep empty-outline fallback.
  - From cursor-specialist-edge-cases-output.txt: Wrap grep in `(... || true)` or disable pipefail for that capture.


### FINDING_10: Plan / topology narrative vs new `skills/design/scripts/emit-design-plan-preview.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan-style bullets claimed no new scripts / unchanged topology or omitted the script from “files to modify”; the branch adds `emit-design-plan-preview.sh`, so traceability and regeneration expectations can disagree until plan/topology/wording is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: List the script in the plan surface or remove it per original plan.


### FINDING_12: Bash 3.2: `$((10#_t))` does not expand `_t`; breaks `normalize_summary_threshold` under `set -e`
- **Reviewer(s)**: dyn-bash-script-output.txt, dyn-bash-script-output.txt
- **Severity**: important
- **Concern**: `printf '%s' "$((10#_t))"` is invalid on bash 3.2: `10#_t` is parsed as a base-10 literal with digit characters `_t`, causing arithmetic evaluation error (“value too great for base”) and, with `set -e`, aborting the script whenever `normalize_summary_threshold` runs in `emit_plan_body`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-script-output.txt: Use base-10 coercion on the variable value, e.g. `printf '%s' "$((10#${_t}))"` (verified on bash 3.2), or assign to a safe numeric path without the broken token.
  - From dyn-bash-script-output.txt: Coerce the *value* of `_t`, e.g. `printf '%s' "$((10#${_t}))"` (or an equivalent safe integer path), after the `case` has restricted `_t` to digits-only.


### FINDING_13: `--design-tmpdir` parsing: `${2:?…}` aborts on empty second token before warning/`exit 0` paths
- **Reviewer(s)**: dyn-bash-script-output.txt, dyn-bash-script-output.txt
- **Severity**: important
- **Concern**: `design_tmpdir="${2:?--design-tmpdir requires a value}"` treats an empty value after the flag as fatal during expansion, so calls like `--design-tmpdir "$DESIGN_TMPDIR"` when `DESIGN_TMPDIR` is unset exit before branches that print `**⚠ 3:**` / `**⚠ 4b:**` and `exit 0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-script-output.txt: Accept empty after `--design-tmpdir` (e.g. `design_tmpdir=${2-}` then `shift 2`) and rely on the existing `[[ -z "$design_tmpdir" || ! -d ... ]]` checks to emit the same warnings and exit 0 as the inlined SKILL behavior.
  - From dyn-bash-script-output.txt: Avoid `:?` on `$2` for this flag (e.g. assign `design_tmpdir=${2-}` and `shift 2`, then let the existing `[[ -z "$design_tmpdir" || ! -d "$design_tmpdir" ]]` branches print the warning and exit 0).


### FINDING_15: `approval-gates.md` “Presentation” MUST vs missing/empty `plan.txt` warning-only path
- **Reviewer(s)**: dyn-skill-invocation-output.txt
- **Severity**: important
- **Concern**: `### Presentation` states the executor MUST emit `plan.txt` under `## Final Design Plan`, while the same material documents a path that prints only `**⚠ 4b: plan.txt missing or empty...**` and continues—a literal MUST read contradicts the exception path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-invocation-output.txt: Reword so the obligation is on running the preview block and emitting the header **when** `plan.txt` is present and non-empty, with the warning-only path explicitly labeled as the defined exception.


### FINDING_2: Step 3 chat order: timing-ledger vs acceptance “immediately after the Step 3 breadcrumb”
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: SKILL documents plan preview after the timing-ledger, while acceptance/checklist language treats the plan header as immediately after the Step 3 breadcrumb; literal QA or acceptance audits can fail despite SKILL’s ordering note unless acceptance or step order is aligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Reorder steps or rewrite acceptance to name the timing-ledger boundary as the anchor before the preview.


### FINDING_3: Plan / acceptance expect inlined fenced Bash; implementation centralizes behavior in `emit-design-plan-preview.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Issue/plan/AC text and “files to modify” narratives describe duplicated inline fenced blocks and a fixed file list; shipped behavior invokes a shared script, so mechanical/audit expectations (grep for fenced bodies, topology/script inventory, “no new scripts”) can false-negative or drift unless plan, acceptance, topology, or SKILL fences are reconciled with the script-backed path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Update issue acceptance or add one clarifying sentence that the mechanical contract is the script invocation.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Amend plan/acceptance to script-backed emit, or replace the thin fences with the plan’s inline Bash bodies.


### FINDING_6: No harness coverage for `emit-design-plan-preview.sh` threshold / sentinel / summary vs full paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New preview logic (threshold, sentinel, outline vs summary, edge cases) is not covered by a registered hermetic test next to peer design script tests; regressions may only show up in manual `/design` or field use.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


