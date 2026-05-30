### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Sparse cone equality may never match, blocking steady-state marketplace update
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `marketplace_sparse_cone_matches` compares raw or normalized `git sparse-checkout list` output to `LARCH_SPARSE_DIRS` tokens; cone-mode CLI/git output may include meta-patterns, `/*` / `!/*/`, or other formatting that does not equal bare sorted directory names. If the check is almost always false, steady-state `claude plugin marketplace update` is skipped and every upgrade (or repair) does remove + sparse re-add instead of in-place update, defeating Part 2 speed goals and adding operator churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Normalize both sides before compare or use plan probe: .git present and larch-logs absent for update path; keep strict cone compare only if normalized
  - From cursor-specialist-correctness-output.txt: Normalize paths before compare or use a dedicated sparse marker instead of raw list output.
  - From cursor-specialist-testing-output.txt: Operator-verify sparse-checkout list after add; adjust normalize/compare to match real CLI output or relax check beyond string equality.
  - From cursor-specialist-edge-cases-output.txt: Operator-verify list format after sparse add; normalize comparison or match documented CLI/git output
  - From cursor-specialist-plan-fidelity-output.txt: Operator-verify sparse-checkout list format matches normalization on real install; adjust comparison if needed.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: mmdc resolved only under mermaid-lint after toolchain move
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `lint-mermaid-fences` resolves `mmdc` only under `mermaid-lint/node_modules`. Developers with legacy root `node_modules` still fail fenced-md lint until `(cd mermaid-lint && npm ci)`; migration note may be needed beyond docs already updated in installation-and-setup.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Sparse include list duplicated without drift guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The sparse include list is duplicated across `upgrade-larch.sh`, install docs, `SKILL.md`, and `docs/skills.md` with no automated drift test after harness removal. A new top-level runtime dir added to the script but omitted from prose copies can ship incomplete consumer installs while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Centralize list in upgrade-larch.sh; docs reference LARCH_SPARSE_DIRS or one shared snippet
  - From cursor-specialist-testing-output.txt: Treat LARCH_SPARSE_DIRS as sole executable source; cross-link docs; or accept plan comment-only maintenance.
  - From cursor-specialist-security-output.txt: Document invariant in SECURITY.md/upgrade-larch.md or add separate dir-list drift check
  - From cursor-specialist-edge-cases-output.txt: Add lightweight ls-tree vs sparse-list lint or release checklist (not full upgrade harness)
  - From cursor-specialist-plan-fidelity-output.txt: Extend MAINTENANCE comment to list all sync sites or consolidate to one canonical reference.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Upgrade-larch offline harnesses removed with no CI substitute
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: All offline upgrade-larch and prune harnesses were removed per plan Part 4 with no CI substitute. Regressions in prune cap, gh redaction, sparse refresh, or already-latest repair can ship without automated signal (plan-accepted; needs explicit manual verification in PR/acceptance).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: upgrade-larch.md step 2 wording misstates idempotent marketplace behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Idempotency step 2 says a valid sparse clone is left alone, but code can still refresh/repair the marketplace on the already-latest path. Operators miss that stale-cone repair can run marketplace update without matching steady-state vs repair branches in step 4.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Install docs --sparse enumeration beyond closed plan scope
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `docs/installation-and-setup.md` Install section documents `--sparse` though closed plan Part 5 only authorized the Upgrade paragraph change. Strict plan-traceability reviewers may treat this as undeclared scope expansion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Document intentional scope expansion in PR notes, or revert Install section if strict adherence required.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

