Here is the normalized aggregator output. Multiple inputs described the same risks; those are merged with combined reviewer attribution. Verbatim suggested revisions are preserved; identical wording across slots is collapsed into one bullet with combined `From` attribution.

---

### FINDING_1: Shard-coverage harness churn vs plan “do not touch”
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Broad mechanical renames/refactors in `scripts/test-harness-shards-coverage.sh` and `scripts/test-harness-shards-coverage.md` conflict with a plan that listed those paths as must-not-touch, increasing merge conflict and partition-guard regression risk without being necessary for skill deletion; plan traceability is weakened unless the plan is explicitly updated to authorize the edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### FINDING_2: `Tracking/umbrella` → `Tracking umbrella` category label drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The default or documented analyze-issues category string was changed from `Tracking/umbrella` to `Tracking umbrella` (in `.claude/skills/analyze-issues/scripts/analyze.py`, related harnesses/docs such as `test-analyze` and `docs/linting.md`), which can contradict a plan that called for keeping the legacy label and can break downstream filters, greps, cohorts, or human habits keyed on the exact historical token, even when behavior is otherwise equivalent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Document as intentional breaking rename in operator-facing notes or narrow the grep exclude list if preserving the legacy token is required.
  - From cursor-specialist-edge-cases-output.txt: Document the intentional rename in CHANGELOG or beside default_category for consumers comparing historical outputs.
  - From cursor-specialist-plan-fidelity-output.txt: Revert to Tracking/umbrella; adjust grep invariant if needed without touching forbidden files.
  - From cursor-specialist-plan-fidelity-output.txt: Restore Tracking/umbrella wording per plan.

---

### FINDING_3: Missing generic-mode `###` split hazard in `parse-input.md`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Removing the umbrella-era subsection also removed the only explicit warning that generic-mode `/issue --input-file` parsing can silently split batch markdown when bodies contain heading-shaped `###` lines, risking wrong items, titles, or `depends_on` metadata without a clear error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

---

### FINDING_4: Plan acceptance vs committed `larch-logs` / flushed plan snapshots
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: New or updated implement run artifacts under `larch-logs/implement/...` (including flushed plan text) can read as contradicting acceptance language that `larch-logs` stay unmodified or that certain paths are must-not-touch, creating reviewer/QA confusion about whether the tree violates the plan versus intentional run-log policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Clarify in run-log process that flushed plans are snapshots only, or avoid copying stale NOT-to-touch bullets into flushed artifacts.
  - From cursor-specialist-plan-fidelity-output.txt: Omit larch-logs commit or reconcile plan/acceptance with intentional log flush policy.

---

### FINDING_5: [OUT_OF_SCOPE] Historical `CHANGELOG.md` still names removed skills
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Pre-existing changelog history still references removed skills; reviewers treat this as preservation/no runtime impact for this branch unless changelog policy changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

---

### FINDING_6: Non-sequential structural test numbering in `test-review-structure.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: After deleting a former case (18), visible case labels jump (e.g. (17) then (20)), making failure messages and checklist navigation harder to map when debugging CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Renumber remaining structural tests sequentially.
  - From cursor-specialist-testing-output.txt: Renumber remaining cases sequentially.
  - From cursor-specialist-plan-fidelity-output.txt: Renumber structural test comments sequentially.

---

### FINDING_7: Shard-coverage sibling doc names wrong guard-owning shard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Contract prose still points maintainers at the wrong shard (e.g. `test-harnesses-13`) after Makefile resharding moved `test-harness-shards-coverage` to another shard’s first slot, risking inspection/rebalance on the wrong partition and missing real drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update the parenthetical to test-harnesses-5 or drop hardcoded shard ids in favor of discovery-first wording consistent with the same file line 12.

---

### FINDING_8: Weaker structural pin after `--pieces-json` anchor removal
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Removing a structural `--pieces-json` pin without replacement assertions for new `/review` Step 4 description-mode filing behavior reduces mechanical coverage; partial edits could regress filing semantics without failing `make test-review-structure` despite the harness being called out as mitigation in the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add grep-based pins for the new Step 4 stable phrases and optional negative grep for /umbrella in skills/review/SKILL.md.

---

### FINDING_9: OOS auto-filing prose may over-read to description-mode `/review`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Wording around out-of-scope filing can be read as universal auto-filing via `/implement` Step 9a.1 before accounting for the description-mode exception, misleading operators about whether description-mode `/review` still auto-files accepted OOS items.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reorder or qualify so auto-filing is explicitly scoped to /implement; state description-mode manual /issue follow-up as the parallel rule.

---

### FINDING_10: `script-md-siblings` rule example cross-reference scope
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Example harness cross-reference updates in `.claude/rules/script-md-siblings.md` may be minor scope creep relative to a strictly enumerated plan file matrix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Document intent in plan or revert if strict enumeration matters.

---

### FINDING_11: [OUT_OF_SCOPE] Makefile `.PHONY` cleanup without recipe hunks
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Removed `test-umbrella-handler` / `test-finalize-umbrella` from `.PHONY` without corresponding recipe changes in the surfaced diff; treated as possibly stale `.PHONY` entries on main, not plan-listed deletion work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### FINDING_12: [OUT_OF_SCOPE] Trade space after umbrella structural anchor removal
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Removing a structural `SKILL.md` anchor tied to umbrella removal yields less mechanical guard if umbrella wiring were ever reintroduced incompletely; reviewers frame this as accepting the trade or adding a different negative guard if umbrella stays permanently deleted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

**Merge note:** `FINDING_7` was kept separate from `FINDING_1` because it is a **targeted documentation/shard-ID correctness** issue, not the same fix path as **bulk harness rename churn**. `FINDING_8` and `FINDING_12` were **not** merged because `FINDING_12` is explicitly `[OUT_OF_SCOPE]` “accept trade / alternate guard” while `FINDING_8` is an in-scope call for **replacement pins**; merging would either drop the `[OUT_OF_SCOPE]` tag (disallowed) or blur distinct voter actions.

Because this output contains one or more `### FINDING_N:` blocks, **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** anywhere in this response.
