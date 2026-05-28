### FINDING_1: Env-var docs promise fallback/clamping not implemented
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-script-ground-truth, Codex-dyn-script-ground-truth, Cursor-dyn-cross-doc-integrity, Codex-dyn-cross-doc-integrity
- **Severity**: important
- **Concern**: Planned documentation for `LARCH_DESIGN_ROUND_CAP` and `LARCH_DESIGN_CONVERGENCE_THRESHOLD` describes fallback, clamping, or positivity semantics that do not match the current launcher and `plan-review-loop.sh` validation behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge: For this docs-only PR, revise the proposed docs to match current behavior: default 5/3, invalid argv/env values fail the plan-review-loop validation, convergence threshold is non-negative, and the Gate C review-run cap is separate from the loop-internal round cap. Only document fallback/clamping if the plan also adds the code change.
  - From Cursor-Innovation, Codex-Innovation: Keep the docs-only scope by documenting the actual argv validation semantics, or expand the plan to add script fallback/clamping plus tests
  - From Cursor-Pragmatic, Codex-Pragmatic: Document the actual current behavior, or explicitly add a code change if fallback/clamping is intended; minimum-change path is to say empty uses defaults, invalid values hard-error, convergence threshold is non-negative, and Step 3 tier entry caps are distinct from --round-cap
  - From Cursor-Requirements, Codex-Requirements: Keep the PR docs-only by documenting actual behavior: empty shell expansion defaults, invalid round cap/threshold rejected by the driver, convergence threshold is non-negative, and Step 3 re-entry cap is separate from inner LARCH_DESIGN_ROUND_CAP; add code and tests only if clamping/fallback is intended
  - From Cursor-dyn-script-ground-truth, Codex-dyn-script-ground-truth: Document the current script contract: round cap argv must be positive, convergence threshold argv must be non-negative, invalid explicit values exit 2, and no max-5 clamp exists unless this docs-only plan is expanded to change code
  - From Cursor-dyn-cross-doc-integrity: Document exit-2 behavior to match plan-review-loop.sh, or add the same normalization pattern as LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD in emit-design-plan-preview.sh before argv is built
  - From Codex-dyn-cross-doc-integrity: Keep the PR docs-only: document the current behavior exactly, including empty unset defaulting, invalid non-numeric values failing, positive ROUND_CAP, and non-negative CONVERGENCE_THRESHOLD

### FINDING_2: Run-log artifact enumeration omits allowlisted files
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Requirements, Codex-Requirements, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-script-ground-truth, Codex-dyn-script-ground-truth, Codex-dyn-cross-doc-integrity
- **Severity**: important
- **Concern**: The planned `docs/run-logs.md` per-round artifact section claims or implies it enumerates allowlisted artifacts, but omits several basenames and patterns allowed by `scripts/lib-design-round-artifacts.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch, Cursor-Requirements, Codex-Requirements: Add those top-level basenames and patterns to the planned docs/run-logs.md section, or narrow the prose so it explicitly says the list is representative and points to scripts/lib-design-round-artifacts.md for the complete allowlist.
  - From Cursor-Edge, Codex-Edge: Add the omitted allowlisted basenames/patterns, or narrow the prose to say it lists selected artifacts and point to scripts/lib-design-round-artifacts.sh as the mechanical authority.
  - From Cursor-Innovation, Codex-Innovation: Either include every allowlisted artifact/pattern in the new docs/run-logs.md section or narrow the wording to say the section lists common artifacts and points to the allowlist for the full set
  - From Cursor-Pragmatic, Codex-Pragmatic: Add a small "Manifests and voter diagnostics" group with those allowlisted names, or narrow the prose so it does not claim complete enumeration
  - From Cursor-dyn-script-ground-truth, Codex-dyn-script-ground-truth: Either add the missing allowlisted names to docs/run-logs.md or narrow the prose from exhaustive enumeration to selected common artifacts
  - From Codex-dyn-cross-doc-integrity: Add the omitted allowlisted names or explicitly state the section is a summary and that scripts/lib-design-round-artifacts.md is exhaustive

### FINDING_3: Mixed-severity fallback rule is inconsistent
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements, Codex-dyn-cross-doc-integrity
- **Severity**: important
- **Concern**: The planned Gate B structured-severity fallback behavior conflicts with itself by saying structured counts are used only when every accepted finding has `Severity`, while also describing mixed per-finding fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Use the all-or-nothing rule from the acceptance criterion, or explicitly define a hybrid question text including Critical; for this SIMPLE lane, remove the per-finding hybrid edge case and fall back to Concern-text when any accepted finding lacks Severity
  - From Codex-dyn-cross-doc-integrity: Choose one rule; the least invasive fix is to document per-finding fallback consistently and specify that mixed counts keep the Critical column if any Concern-text fallback can produce Critical

### FINDING_4: SECURITY.md confinement prose misses rollback snapshot
- **Reviewer(s)**: Cursor-dyn-script-ground-truth, Codex-dyn-script-ground-truth
- **Severity**: latent
- **Concern**: The planned `SECURITY.md` wording says outputs are confined to the revise directory, but the script also creates `plan.txt.before-revise` as a sibling snapshot outside that subtree on certain failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-script-ground-truth, Codex-dyn-script-ground-truth: Narrow the sentence to say launcher outputs, prompts, and candidate patches are confined to plan-review/round-<N>/revise/, and explicitly note that the rollback snapshot is intentionally plan.txt.before-revise outside that subtree on failure

### FINDING_5: FINDING_N template test omits required fields
- **Reviewer(s)**: Cursor-dyn-test-pin-adequacy, Codex-dyn-test-pin-adequacy
- **Severity**: important
- **Concern**: The planned structure-test pin for accepted `FINDING_N` blocks omits required `Concern` and `Proposed resolution` field labels, so changes that remove or rename fields used by Gate B could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-pin-adequacy, Codex-dyn-test-pin-adequacy: Extend the planned Accepted FINDING_N template-block assertion to check all required field labels exactly: - **Reviewer(s)**:, - **Severity**:, - **Focus area**:, - **Location**:, - **Concern**:, and - **Proposed resolution**:
