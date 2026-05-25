Here is the normalized aggregator output. In-scope merges first (by first-seen source id), then out-of-scope blocks. No raw transcripts. Because there is at least one `### FINDING_N:` block, the empty-merge attestation line must **not** appear.

---

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

### FINDING_3: `is_bool` key list formatting vs `require_key` style in `ship-pr.sh`

- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The `is_bool` for-loop key list is one long line while `require_key` uses wrapped line continuations, making future diffs and readability inconsistent when editing boolean keys beside the wrapped `require_key` block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---

### FINDING_4: `scripts/ship-pr.md` backward-compatibility prose vs Schema for hand-composed / minimal state

- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Backward-compatibility prose still emphasizes argv flags rather than the full state key schema; external tools or readers who hand-write minimal state may rely on that paragraph alone and miss that pre-composed state must satisfy `require_key` (or use `--force-init-state true`) and that the Schema note applies before/during composition, not only to mid-session binary upgrades—risking confusion when older/minimal state files lack newly required keys after upgrade.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

---

### OOS_1: [OUT_OF_SCOPE] Duplicate manual key lists without drift automation (`#2753`)

- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `write_initial_state` vs `require_key` (and related) remain as separate manual key lists without drift automation per `#2753`; future keys added only on one side could slip past review until runtime or tests fail—optional small follow-up only if this PR is intended to close that gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---

### OOS_2: [OUT_OF_SCOPE] `DESIGN_ONLY_DONE` state transition in `ship-pr.sh`

- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `DESIGN_ONLY_DONE` never transitions in `ship-pr.sh` today; not judged to produce wrong output from this diff unless product intent is to drive this key from `ship-pr` later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

---

### OOS_3: [OUT_OF_SCOPE] Large `larch-logs/**` diffs alongside functional changes (review noise)

- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Large committed run-log trees/commits accompany the branch but sit outside enumerated ship-pr code edits, increasing review paging noise and time on unrelated log diffs; acceptable per repo policy, but splitting or separating log commits from functional review helps when hygiene matters; no plan-fidelity gap for the validator plan’s code requirements.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### OOS_4: [OUT_OF_SCOPE] State file trust model (`ship-pr.sh`)

- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The state file remains a high-trust writable input for the implement session; `require_key` / `is_bool` extensions do not authenticate the writer or sanitize path-like values—pre-existing trust boundary, largely unchanged beyond stricter key presence and extra boolean checks; hardening belongs to a dedicated state-integrity or path-canonicalization effort, not required for this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

---

**Merge notes (for voters, not separate findings):**

- **FINDING_1** subsumed source ids **1, 5, 14** (plan/listing/traceability and “not in three-file plan” overlap; max severity important).
- **FINDING_2** subsumed **2, 7, 10, 12** (same behavioral risk: automatic `npm ci` / Mermaid bootstrap side effects and prerequisites; max severity important).
- **FINDING_3** kept **3** alone (formatting-only).
- **FINDING_4** merged **8, 13** (same doc path and reader confusion class; max severity nit).
- **OOS_3** merged **9, 15** (both `larch-logs` volume vs functional review noise; max severity nit).

Every merged block includes exactly one `- **Severity**:` line. No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).
