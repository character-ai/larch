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


### FINDING_4: KV precedence conflicts with post-loop branch-matrix prose
- **Reviewer(s)**: Cursor-dyn-kv-wire-contract
- **Severity**: important
- **Concern**: The plan’s Key mechanics define safe-env authority plus stdout fallback/precedence rules, but the unchanged post-loop branch matrix still says to read the result env first and treat driver stdout KVs only as fallback. This can mis-handle symlink/missing-file paths or diverge from the qualified rc override behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-wire-contract: Operators or implementers following the matrix can mis-handle symlink/missing-file paths or treat stdout as fallback when a safe file was loaded; diverges from qualified rc!=0 override rule Revise the post-loop matrix intro (one sentence) to match Key mechanics: safe non-symlink env authoritative; stdout fills missing only when safe env loaded; stdout-primary with later-wins only when no safe env


### FINDING_6: Sentinel harness omits two no-touch cases
- **Reviewer(s)**: Codex-dyn-sentinel-touch-contract
- **Severity**: latent
- **Concern**: The proposed `test-run-step3-review.sh` coverage does not include renderer nonzero exit with non-header body or bare missing `plan.txt` without the exact renderer warning. The implementation could still touch the sentinel in those invalid cases and pass tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sentinel-touch-contract: Add minimal stub-seam assertions for those two cases: nonzero non-header renderer output leaves `.step3-entry-plan-printed` absent and does not abort; missing `plan.txt` without the exact missing-plan warning also leaves the sentinel absent.


