Here is the normalized aggregator output (plain structured text; no `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line because there are in-scope findings).

### FINDING_1: Step 3 drops explicit `run-params.json` read; harness and `review_budget` prose merged
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-portability-output.txt, dyn-skill-md-continuity-output.txt
- **Severity**: important
- **Concern**: Step 3 text merges the hermetic harness pointer with the `review_budget` / valid-values / `quick_mode` fallback paragraph and no longer leads with an explicit instruction to read `review_budget` from `$DESIGN_TMPDIR/run-params.json` before the **If review_budget=quick** / **If review_budget=full** branches. That weakens the mechanical contract (and can contradict deferral text elsewhere): orchestrators may infer `review_budget` from context or misread the harness sentence as the source of truth, mis-routing quick vs full. Relatedly, harness guidance and normative `run-params.json` rules appear in one paragraph, increasing the risk of future edits dropping normative sentences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-portability-output.txt, dyn-skill-md-continuity-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Split into two paragraphs: harness pointer vs run-params review_budget rules

### FINDING_2: Issue acceptance vs documented chat order (breadcrumb, timing ledger, plan preview)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-portability-output.txt
- **Severity**: important
- **Concern**: Acceptance / issue-level text still treats the plan preview as immediately after the Step 3 breadcrumb, while SKILL and `docs/configuration-and-permissions.md` describe timing-ledger output before the preview. Manual QA, log audits, or merge checklists keyed only on breadcrumb adjacency can false-fail even when behavior matches the documented ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_3: Harness uses `echo` instead of `printf` for PASS/FAIL messages
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-emit-design-plan-preview.sh` uses `echo` for FAIL/PASS while related feature scripts prefer `printf`; minor style inconsistency, low operational risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Shared script vs duplicated SKILL fences and strict plan-fidelity audits
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Logic lives in a shared `emit-design-plan-preview.sh` instead of duplicated inline Bash from an earlier plan; functionally centralized and testable, but strict literal plan-fidelity or character-for-character SKILL fence audits could still flag divergence unless the script-as-canonical choice is recorded in the issue / plan / acceptance language.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_5: Written plan vs branch surface (topology, new script, tests, Makefile, file-count claims)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan / documentation impact claims (e.g., topology unchanged, bounded file set, no new scripts) diverge from the branch, which adds `emit-design-plan-preview.sh`, test and Makefile wiring, `skills/shared/topology.tsv` (and related rules). That weakens plan-to-implementation traceability and can mislead release notes or review gates that assumed a smaller declared file set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: `plan.txt` reads without rejecting symlinks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `plan.txt` is read without requiring a regular non-symlink file; in a compromised or hand-crafted `DESIGN_TMPDIR`, a symlink could cause unintended file content to be printed as if it were the plan. Mitigations: enforce regular-file checks or document a trusted-tmpdir invariant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_7: `touch` on `.step3-entry-plan-printed` under `set -e` can abort the script
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `touch` on `.step3-entry-plan-printed` runs under `set -e` and can fail the fenced block on read-only tmpdir or full disk after emitting the preview; empty-plan paths may re-spam warnings if the marker never succeeds. Prefer best-effort `touch` or failure handling that does not fail the whole script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Regression harness under-covers Gate C and threshold normalization paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `test-emit-design-plan-preview.sh` focuses on Step 3 paths but does not adequately cover Gate C (e.g., large-plan summary, 4b-style warnings, invalid-threshold / `abc` / `0` threshold silent fallback). Regressions in the Gate C branch or threshold normalization could ship without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Leading-zero / `10#` coercion vs original plan snippet
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `emit-design-plan-preview.sh` extends numeric coercion (leading zeros, `10#`) beyond the single-case pattern in the original issue bash snippet; slight spec drift vs the written plan though behavior may be documented elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### OOS_1: [OUT_OF_SCOPE] Large committed implement run-log delta
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Large `larch-logs/implement/1155499A-6F9F-48EE-9D1B-E423B3D294DB/*` diff from implement flush / fixtures is noise for this feature’s functional review and is governed by run-log policy rather than a regression signal for design preview behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Factored script vs duplicated SKILL fences (architectural deviation from early plan text)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: Branch factors shared logic into `emit-design-plan-preview.sh` (plus tests/docs cross-links) instead of large duplicated `SKILL.md` bash blocks; acceptable implementation choice and consistent with a mechanical-contract doc narrative unless strict plan document parity is required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-bash-portability-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Bash 3.2 / `lint-bash32` / `pipefail` note for `emit-design-plan-preview.sh`
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: Constructs used (`set -euo pipefail`, `[[ … ]]`, arithmetic, `printf '%s' "$((10#${_t}))"`, `grep … | head … || true`) are valid on macOS Bash 3.2 per `BASH_AUTHORING.md` / `lint-bash32` policy; `|| true` on the outline pipeline is a reasonable guard under `pipefail` (e.g., `SIGPIPE`) and does not mirror the Step 3 `run-params.json` contract regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Step 4b continuity (delegation to `approval-gates.md` / Gate C fence)
- **Reviewer(s)**: dyn-skill-md-continuity-output.txt
- **Severity**: nit
- **Concern**: Step 4b replaces older one-line prose with references to `approval-gates.md`, the `emit-design-plan-preview.sh --variant gatec` fence, and existing AskUserQuestion behavior; no comparable routing regression to Step 3 was identified for Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-md-continuity-output.txt: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Topology row vs plan text saying topology unchanged
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `skills/shared/topology.tsv` row added for the new script authority while some plan prose implied topology unchanged; repo convention favors updating the TSV when adding scripts—template/plan wording alignment only, not a functional defect for preview logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

**Merge notes (for traceability, not machine validation):**  
- FINDING_1 subsumes input FINDING_1, 5, 9, 13 (and the paragraph-structure aspect of 14, 16, 25, 29).  
- FINDING_2 subsumes input FINDING_2, 6, 22, 26.  
- FINDING_5 subsumes input FINDING_8, 21, 23 (in-scope plan/traceability only); OOS_5 keeps the explicitly tagged out-of-scope topology-template angle separate per scope tagging.  
- FINDING_8 subsumes input FINDING_10, 18.  
- OOS blocks subsume input FINDING_11, 12, 19, 20, 27, 28, 30 as scoped.
