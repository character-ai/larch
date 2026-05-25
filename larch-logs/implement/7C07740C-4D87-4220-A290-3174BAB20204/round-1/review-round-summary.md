# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (1 exonerated)

## Accepted Findings

### FINDING_1: Mermaid/npm changes in `relevant-checks.sh` absent from ship-pr plan (scope, bisect, traceability)

- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch adds Mermaid CLI / `npm ci` bootstrap behavior in `scripts/relevant-checks.sh` that was not listed in the narrow ship-pr implementation plan, which widens review and revert scope, bundles unrelated local-check behavior with ship-pr state work, and weakens strict plan-to-diff traceability for a PR framed around ship-pr state validation (reviewers and `git bisect` must reason about two concerns in one change set; reverting ship-pr validation could drop unrelated relevant-checks behavior unless called out explicitly).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


### FINDING_2: Auto `npm ci` when Markdown is in scope (Node/network/offline, lifecycle scripts, workflow blocking)

- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Conditional automatic `npm ci` when Markdown appears in the changed-file set couples `relevant-checks` to Node, npm, the network/registry, and install lifecycle scripts (including postinstall), adding time cost and hard failure modes on machines without Node, offline, or without registry access; doc-only or minimal environments can hit `ERROR` before other checks (e.g. pre-commit) where workflows previously could pass without a local npm install, and the automatic install is a non-obvious security/ops side effect for doc edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

---


### FINDING_4: `scripts/ship-pr.md` backward-compatibility prose vs Schema for hand-composed / minimal state

- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Backward-compatibility prose still emphasizes argv flags rather than the full state key schema; external tools or readers who hand-write minimal state may rely on that paragraph alone and miss that pre-composed state must satisfy `require_key` (or use `--force-init-state true`) and that the Schema note applies before/during composition, not only to mid-session binary upgrades—risking confusion when older/minimal state files lack newly required keys after upgrade.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

---


