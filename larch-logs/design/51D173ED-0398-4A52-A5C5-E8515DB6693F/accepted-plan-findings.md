### FINDING_1: Parent-unset lint misses new nested review and CI children
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: Parent-unset lint only scans scripts containing `dispatch-with-waterfall.sh` and only treats that child as requiring parent-environment sanitization, so proposed `review-and-fix.sh` and `ci-wait.sh` nested calls in Step 5 and ship paths would not be enforced and could regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add review-and-fix.sh and ci-wait.sh to PARENT_UNSET_REQUIRED_CHILDREN; gate scan on any listed child (not only dispatch-with-waterfall); extend unset_before_anchor_idx to require all four unsets; add harness cases for review-and-fix and ci-wait anchors
  - From Cursor-Innovation: Extend PARENT_UNSET_REQUIRED_CHILDREN to include review-and-fix.sh and ci-wait.sh; run scan_shell_file_for_unset_before_nested_child on any script that invokes those children (not only dispatch-with-waterfall); teach unset_before_anchor_idx to require unset of all four env vars; mirror in test-lint-foreground-markers.sh.


### FINDING_2: Broadened parent-unset plan omits existing nested Family-B callsites
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-linter-coverage-completeness, Codex-dyn-linter-coverage-completeness
- **Severity**: important
- **Concern**: The plan broadens the parent-unset rule but updates only a subset of existing nested Family-B callsites. Existing review, design, dispatch-with-waterfall, and Step 2 implement paths would either fail the broadened lint or continue inheriting parent completion/status/surfaced env vars into nested writers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Extend Item 1A to every existing nested Family-B callsite scanned by the linter, including review/design dispatchers and run-step2-dispatch.sh, or narrow the lint rule to the exact intended scope
  - From Codex-Innovation: Update every existing nested Family-B call site to unset the full variable set, or narrow the lint rule to only the call sites the PR actually changes
  - From Cursor-Pragmatic: Add these existing nested call sites to Item 1A, or explicitly narrow the lint/root-cause claim if they are intentionally exempt; use the same four-variable unset before each nested writer invocation
  - From Cursor-Requirements: Include `skills/implement/scripts/run-step2-dispatch.sh` in Item 1A, unset `LARCH_DONE_SENTINEL`, `LARCH_STATUS_FILE`, and `LARCH_BREADCRUMBS_SURFACED_FILE` before `step2-implement.sh`, and extend the lint/test child list to cover `step2-implement.sh` too.
  - From Cursor-dyn-linter-coverage-completeness: Add these five call sites to Item 1A and broaden each local unset block to include LARCH_DONE_SENTINEL, LARCH_STATUS_FILE, LARCH_BREADCRUMBS_SURFACED_FILE, and LARCH_PAIRED_PID_FILE, or add a justified line-level exemption where inheritance is intentional.


### FINDING_3: Symlink rescan language overclaims TOCTOU closure
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Edge, Codex-Edge
- **Severity**: important
- **Concern**: The proposed post-enumeration or final tree-wide symlink rescan is framed as fully closing parent-directory or leaf replacement races, but a concurrent same-UID writer can swap a parent or leaf after the rescan, affect the copy, and restore it before the final check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep the change framed as defense in depth and retain residual-risk wording, or add a stronger per-file physical-path validation/copy contract before claiming the race is fully closed
  - From Cursor-Edge: Keep the residual-risk wording unless the implementation uses an open-time no-follow or locked snapshot strategy; at minimum revise the plan and SECURITY.md text to say the rescan narrows but does not fully close concurrent replacement races


### FINDING_4: Step 7a skip-reason item targets a nonexistent publication contract
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-dyn-line-ref-fidelity, Codex-dyn-line-ref-fidelity
- **Severity**: important
- **Concern**: Item 3.3 targets `CODE_FLOW_SKIP_REASON` or a skip-reason relay in Step 7a, but the current Step 7a contract does not publish that symbol and omitted/failed diagram generation does not upsert a skipped section. Implementing the plan literally risks adding new public behavior or sanitizing the wrong block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Drop Item 3.3 unless a real publication path is identified; if the concern is generator stdout, constrain the change to the existing SKIP_REASON extraction/contract instead of the diagrams upsert
  - From Codex-Innovation: For SIMPLE scope, drop Item 3.3 unless this PR intentionally changes skipped or failed diagram publication; if it does, explicitly add the contract, tests, and docs for that behavior change
  - From Cursor-dyn-line-ref-fidelity: Revise Item 3.3 to name the actual upsert range at skills/implement/scripts/step-7a.sh:389-406 and specify the exact CODE_FLOW_SKIP_REASON introduction or section-composition site to sanitize before upsert


### FINDING_5: Plain parent-shell unsets can break the parent completion trap
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Concern**: The plan unsets parent done/status variables in the current shell before nested children. Because the parent EXIT trap reads those variables at process exit, plain unsets can prevent the top-level process from writing its own completion sentinel and leave the foreground monitor waiting or misreporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Do not plain-unset those variables in the parent shell; invoke the nested child through a sanitized child environment using a subshell or env -u, or save and restore the variables before parent exit, and make the lint/test wording enforce child-environment sanitization rather than parent-state deletion


### FINDING_6: Ship failure-log relay line reference points at the wrong helper
- **Reviewer(s)**: Cursor-dyn-line-ref-fidelity, Codex-dyn-line-ref-fidelity
- **Severity**: important
- **Concern**: Item 3.2 cites a stale range in `scripts/ship-pr.sh` that now covers `capture_command_output`, not the operator-visible failure-log relay. An implementer could sanitize the wrong helper and leave the actual fallback relay unsanitized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-line-ref-fidelity: Retarget Item 3.2 to append_tool_failure_local fallback relay at scripts/ship-pr.sh:872-875, preserving per-line LF handling through sanitize_diagnostic_line


### FINDING_7: Review-and-fix unset placement is outside the linter look-back window
- **Reviewer(s)**: Cursor-dyn-linter-coverage-completeness, Codex-dyn-linter-coverage-completeness
- **Severity**: important
- **Concern**: The planned unset block in `scripts/run-step5-review.sh` is far above the actual `review-and-fix.sh` invocation. With the linter’s five-line look-back window, the broadened lint would not recognize the unsets if left near the existing early block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-linter-coverage-completeness: Move or repeat the four-variable unset block immediately before the "$REVIEW_AND_FIX_SH" invocation, after REVIEW_AND_FIX_ARGS is finalized, keeping it within five nonblank noncomment lines of the call.


