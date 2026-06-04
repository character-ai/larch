### [Plan Review] FINDING_3

### FINDING_3: Plan defers the stated Step 3 turn-reduction goal
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The feature description requires removing the separate preview turn and claims a one-turn reduction per Step 3 entry, but the plan still keeps a separate live preview-only Bash fence before the captured review call. That would land without satisfying a core acceptance rationale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Reconcile the scope before implementation: either change the plan to a single driver-owned invocation shape that preserves live preview before review, or explicitly revise the feature acceptance for this PR to driver-owned sentinel/direct-renderer removal only and track turn reduction as a separate follow-up.


### [Plan Review] FINDING_5

### FINDING_5: Markdown script contract omits full sentinel touch rules
- **Reviewer(s)**: Codex-dyn-sentinel-touch-contract
- **Severity**: latent
- **Concern**: The planned `run-step3-review.md` update does not restate the full sentinel contract from the shell spec. It omits exact positive strings, negative no-touch cases, and valid-tmpdir re-entry suppression, allowing docs/script behavior to drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sentinel-touch-contract: In the run-step3-review.md update bullet, spell out the same contract as run-step3-review.sh: valid tmpdir plus header or exact missing-plan warning only; no touch for non-header output, allowlist-invalid tmpdir, nonzero non-header renderer output, or bare missing plan.txt; suppress only when sentinel exists and tmpdir validates.


### [Plan Review] FINDING_7

### FINDING_7: Documentation sweep is underspecified for operator-contract updates
- **Reviewer(s)**: Cursor-dyn-doc-reference-sweep, Codex-dyn-doc-reference-sweep
- **Severity**: important
- **Concern**: The plan’s documentation/reference sweep is too generic and does not explicitly require all named operator-contract files and linting rows to be updated. An implementer could leave stale direct `emit-design-plan-preview.sh --variant step3` prose or miss the new `test-run-step3-review` harness documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-doc-reference-sweep: In step 6, explicitly require a pass over skills/design/SKILL.md, skills/design/scripts/run-step3-review.md, skills/design/scripts/emit-design-plan-preview.md, docs/configuration-and-permissions.md (Chat-order + Mechanical contract), docs/issue-anchored-plan.md:189-194, docs/linting.md harness row, and SECURITY.md allowlist paragraph, confirming no remaining Step 3 direct emit-design-plan-preview.sh --variant step3 orchestration fence
  - From Codex-dyn-doc-reference-sweep: Add a docs/linting.md table row for make test-run-step3-review near test-step3-review-cap, and separately update the existing test-emit-design-plan-preview row to say step3 is a pure renderer with no sentinel idempotency

