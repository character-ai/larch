# Review Round 1

- Mode: `diff`
- Accepted findings: 5
- Rejected findings: 1
- Exonerated findings: 2
- Neutral findings: 1

## Accepted Findings

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


