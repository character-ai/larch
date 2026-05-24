### OOS_1: [OUT_OF_SCOPE] Large committed implement run-log delta
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Large `larch-logs/implement/1155499A-6F9F-48EE-9D1B-E423B3D294DB/*` diff from implement flush / fixtures is noise for this feature’s functional review and is governed by run-log policy rather than a regression signal for design preview behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Factored script vs duplicated SKILL fences (architectural deviation from early plan text)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: Branch factors shared logic into `emit-design-plan-preview.sh` (plus tests/docs cross-links) instead of large duplicated `SKILL.md` bash blocks; acceptable implementation choice and consistent with a mechanical-contract doc narrative unless strict plan document parity is required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-bash-portability-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Bash 3.2 / `lint-bash32` / `pipefail` note for `emit-design-plan-preview.sh`
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: Constructs used (`set -euo pipefail`, `[[ … ]]`, arithmetic, `printf '%s' "$((10#${_t}))"`, `grep … | head … || true`) are valid on macOS Bash 3.2 per `BASH_AUTHORING.md` / `lint-bash32` policy; `|| true` on the outline pipeline is a reasonable guard under `pipefail` (e.g., `SIGPIPE`) and does not mirror the Step 3 `run-params.json` contract regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] Step 4b continuity (delegation to `approval-gates.md` / Gate C fence)
- **Reviewer(s)**: dyn-skill-md-continuity-output.txt
- **Severity**: nit
- **Concern**: Step 4b replaces older one-line prose with references to `approval-gates.md`, the `emit-design-plan-preview.sh --variant gatec` fence, and existing AskUserQuestion behavior; no comparable routing regression to Step 3 was identified for Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-md-continuity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

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

Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

