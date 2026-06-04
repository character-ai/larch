### FINDING_1: Step 3 rc=2 handling does not fail closed
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The Step 3 thin fence treats `run-step3-review.sh` exit 2 as a banner-only configuration error instead of aborting the fence before downstream branching. Because the fence may still load a stale/safe `.step3-review-result.env`, `LOOP_STATUS=complete` or similar state can drive the post-loop branch matrix despite argv/config failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After the exit-2 banner add `exit 1` (or equivalent fence abort) matching Step 0b/3.6; keep normalization guarded with `_plan_review_rc!=2` only as defense in depth
  - From Cursor-Edge: After the exit-2 banner add exit 1 (match Step 2b/3.6); pin in test-design-structure.sh; add harness case that safe-env+rc=2 does not leave LOOP_STATUS=complete for downstream use
  - From Cursor-Pragmatic: Mirror Step 2b: after capture, handle `_plan_review_rc==2` first with the banner plus `exit 1`; defer safe-env read/parse until rc is not 2; add explicit prose to skip the post-loop branch matrix on configuration error (and add a harness case that rc=2 with a stale env does not leave a branchable `LOOP_STATUS`)

### FINDING_2: Display-pass contract can hide non-KV driver breadcrumbs
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-kv-wire-contract
- **Severity**: important
- **Concern**: The display-pass plan is inconsistent about whether captured Step 3 output should replay non-KV driver lines or only non-allowlisted `KEY=value` lines. This can hide user-facing warnings/breadcrumbs such as cap-reached or non-numeric review-round-count messages, or cause tests and SKILL prose to assert different behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Make the display pass print non-KV lines verbatim, while suppressing only the twelve allowlisted KVs and WARN=, and add one harness case for a non-KV warning line
  - From Codex-dyn-kv-wire-contract: Choose one rule and state it identically; minimum-change is to replace the non-KV echo wording with non-allowlisted KEY=value echo unless non-KV warning display is required, in which case add that branch to both SKILL.md and test-step3-orchestrator-fence.sh specs

### FINDING_3: Plan defers the stated Step 3 turn-reduction goal
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The feature description requires removing the separate preview turn and claims a one-turn reduction per Step 3 entry, but the plan still keeps a separate live preview-only Bash fence before the captured review call. That would land without satisfying a core acceptance rationale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Reconcile the scope before implementation: either change the plan to a single driver-owned invocation shape that preserves live preview before review, or explicitly revise the feature acceptance for this PR to driver-owned sentinel/direct-renderer removal only and track turn reduction as a separate follow-up.

### FINDING_4: KV precedence conflicts with post-loop branch-matrix prose
- **Reviewer(s)**: Cursor-dyn-kv-wire-contract
- **Severity**: important
- **Concern**: The plan’s Key mechanics define safe-env authority plus stdout fallback/precedence rules, but the unchanged post-loop branch matrix still says to read the result env first and treat driver stdout KVs only as fallback. This can mis-handle symlink/missing-file paths or diverge from the qualified rc override behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-wire-contract: Operators or implementers following the matrix can mis-handle symlink/missing-file paths or treat stdout as fallback when a safe file was loaded; diverges from qualified rc!=0 override rule Revise the post-loop matrix intro (one sentence) to match Key mechanics: safe non-symlink env authoritative; stdout fills missing only when safe env loaded; stdout-primary with later-wins only when no safe env

### FINDING_5: Markdown script contract omits full sentinel touch rules
- **Reviewer(s)**: Codex-dyn-sentinel-touch-contract
- **Severity**: latent
- **Concern**: The planned `run-step3-review.md` update does not restate the full sentinel contract from the shell spec. It omits exact positive strings, negative no-touch cases, and valid-tmpdir re-entry suppression, allowing docs/script behavior to drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sentinel-touch-contract: In the run-step3-review.md update bullet, spell out the same contract as run-step3-review.sh: valid tmpdir plus header or exact missing-plan warning only; no touch for non-header output, allowlist-invalid tmpdir, nonzero non-header renderer output, or bare missing plan.txt; suppress only when sentinel exists and tmpdir validates.

### FINDING_6: Sentinel harness omits two no-touch cases
- **Reviewer(s)**: Codex-dyn-sentinel-touch-contract
- **Severity**: latent
- **Concern**: The proposed `test-run-step3-review.sh` coverage does not include renderer nonzero exit with non-header body or bare missing `plan.txt` without the exact renderer warning. The implementation could still touch the sentinel in those invalid cases and pass tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sentinel-touch-contract: Add minimal stub-seam assertions for those two cases: nonzero non-header renderer output leaves `.step3-entry-plan-printed` absent and does not abort; missing `plan.txt` without the exact missing-plan warning also leaves the sentinel absent.

### FINDING_7: Documentation sweep is underspecified for operator-contract updates
- **Reviewer(s)**: Cursor-dyn-doc-reference-sweep, Codex-dyn-doc-reference-sweep
- **Severity**: important
- **Concern**: The plan’s documentation/reference sweep is too generic and does not explicitly require all named operator-contract files and linting rows to be updated. An implementer could leave stale direct `emit-design-plan-preview.sh --variant step3` prose or miss the new `test-run-step3-review` harness documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-doc-reference-sweep: In step 6, explicitly require a pass over skills/design/SKILL.md, skills/design/scripts/run-step3-review.md, skills/design/scripts/emit-design-plan-preview.md, docs/configuration-and-permissions.md (Chat-order + Mechanical contract), docs/issue-anchored-plan.md:189-194, docs/linting.md harness row, and SECURITY.md allowlist paragraph, confirming no remaining Step 3 direct emit-design-plan-preview.sh --variant step3 orchestration fence
  - From Codex-dyn-doc-reference-sweep: Add a docs/linting.md table row for make test-run-step3-review near test-step3-review-cap, and separately update the existing test-emit-design-plan-preview row to say step3 is a pure renderer with no sentinel idempotency
