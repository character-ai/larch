# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_2: design GC retention drops accepted-plan-findings-audit.md
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-gatec-audit
- **Severity**: major
- **Concern**: The design GC keep set and `docs/run-logs.md` consumer-core prose omit `accepted-plan-findings-audit.md`, so `gc_run_logs.py` slimming deletes the durable Gate C audit artifact from older design runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add to SKILL_KEEP design set, update docs/run-logs.md consumer-core list, and test_gc_run_logs.py.
  - From codex-specialist-correctness: Add accepted-plan-findings-audit.md to SKILL_KEEP["design"], update the Retention keep-set prose, and add the planned GC test assertion.
  - From cursor-specialist-edge-cases: Add accepted-plan-findings-audit.md to SKILL_KEEP design in gc_run_logs.py update consumer-core prose in docs/run-logs.md and add test_gc_run_logs keep assertion
  - From codex-specialist-edge-cases: Add accepted-plan-findings-audit.md to SKILL_KEEP["design"], update docs/run-logs.md, and add the planned report test.
  - From cursor-specialist-testing: Add accepted-plan-findings-audit.md to SKILL_KEEP design and extend test_gc_run_logs.py with a keep/slim assertion.
  - From cursor-specialist-testing: Add accepted-plan-findings-audit.md to the /design consumer-core keep-set bullet.
  - From codex-specialist-testing: Add accepted-plan-findings-audit.md to SKILL_KEEP["design"], update docs/run-logs.md retention prose, and add the planned gc_run_logs keep-set test.
  - From dyn-dyn-gatec-audit: Add accepted-plan-findings-audit.md to `SKILL_KEEP["design"]`, update the consumer-core bullet in `docs/run-logs.md`, and extend `python/tests/report/test_gc_run_logs.py` as planned.


### FINDING_3: fidelity traces against `accepted-plan-findings-all.md` even when selection falls back
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-gatec-audit
- **Severity**: major
- **Concern**: Step 7 checks fidelity against `accepted-plan-findings-all.md` even when classification fell back to `accepted-plan-findings.md`, so valid findings can be treated as untraced and force dissent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Align fidelity authority with filtered _accepted_corpus from step 2.
  - From codex-specialist-edge-cases: Make fidelity use the filtered selected corpus, and mirror the wording in skills/design/references/plan-review.md.
  - From dyn-dyn-gatec-audit: Align fidelity with the same `_accepted_corpus` used for classification/filtering (after skip-filter when required), and document that explicitly in both files; only treat `-all` as the authority when it is the selected corpus.


### FINDING_11: strong-audit state is bound under the wrong variable name
- **Reviewer(s)**: dyn-dyn-gatec-audit
- **Severity**: major
- **Concern**: The step-10 binding uses `strong_audit_dissent`, but the render path reads `STRONG_AUDIT_DISSENT`, so re-prompts can lose the strong-audit flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-gatec-audit: Use one name everywhere (e.g. bind `STRONG_AUDIT_DISSENT` in step 10 and in post-audit routing), or add an explicit mapping step (`STRONG_AUDIT_DISSENT="${strong_audit_dissent:-false}"`) immediately before any `render-gate` call; pin the chosen name in `scripts/test-design-structure.sh`.


