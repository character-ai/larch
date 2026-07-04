### FINDING_2: bg-wait writer parity lint is too line-local for live writers
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The lint anchor only recognizes literal same-line `.bg-wait-active` plus write tokens, but live design writers emit `CLONE_PATH=` through temp-file / variable-backed write flows, so the repo-root acceptance test can false-fail or the rule can miss the actual write context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the plan rule to anchor on the writer function/block: treat a .bg-wait-active path assignment within the window as the anchor, or scan the enclosing function for CLONE_PATH= near write_text/printf/replace/mv marker promotion; keep the repo-root acceptance test as the gate
  - From Codex-Arch: Extend the plan rule to anchor on the writer function/block: treat a .bg-wait-active path assignment within the window as the anchor, or scan the enclosing function for CLONE_PATH= near write_text/printf/replace/mv marker promotion; keep the repo-root acceptance test as the gate
  - From Cursor-Innovation: Extend write-context detection: treat a ±15-line window around any of `write_text(`, `printf`, `>`, `.replace(`, or `mv` as an anchor when the same window also references `.bg-wait-active` (literal or via a marker variable assigned from it); require `CLONE_PATH=` inside that window. Add fixtures mirroring `design_core.py` and `design-step3-review.sh`.
  - From Codex-Innovation: Revise _has_clone_path_emission to treat marker variable assignment plus temp-to-marker mv/replace/write_text in the same function or nearby block as the write context, then require CLONE_PATH= within that block/window; add a fixture for this indirect temp-writer shape.
  - From Cursor-Pragmatic: Define anchors as a ±15 window around either (a) a write-indicator line or (b) an assignment to a `*.bg-wait-active` path, and require `CLONE_PATH=` in that window; treat `mv`/`replace` promotion from a temp file as write context. Add fixture regressions mirroring `design_core.py` and `design-step3-review.sh` shapes.
  - From Codex-Requirements: Define `_has_clone_path_emission` around writer blocks or functions: treat marker variable assignment plus temp write or mv, and Python marker Path plus write_text or replace, as qualifying writer blocks; require at least one qualifying writer block; make cleanup-only pass fixtures include a real writer elsewhere and add a no-write-anchor fixture that fails


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_5: Extracted `bg_wait.py` needs pyright-safe handling
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Moving the helper body into a new module can introduce pyright failures for ignored `write_text` / `unlink` results, and the imported underscored helper can also trip private-usage reporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add either exact pyright ignores or local unused-result assignments in bg_wait.py, and add an exact reportPrivateUsage ignore for the step_7a private-helper import or call


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Pre-commit `lint-bg-wait-writer-parity` `files:` glob skips Python-only writer edits
- **Description**: [OUT_OF_SCOPE] Pre-commit `lint-bg-wait-writer-parity` `files:` glob skips Python-only writer edits. Scenario: The hook triggers only on `^skills/(design|implement|review|review-and-fix)/`. This plan’s main writer move is `python/larch/implement/bg_wait.py` plus lint-module edits; those paths can merge without running the parity lint unless pytest/CI executes the new repo-root acceptance test every time.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:674-679
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: Live Step 3 composite still skips FINDING_5 pre-arm cleanup
- **Description**: Live Step 3 composite still skips FINDING_5 pre-arm cleanup. Scenario: `checks_commit_route_main` arms `implement-step3-checks` on the production `/implement` Step 3 path but never deletes stale `.completed/step-3-terminal` or `bg-poll-guard-probe-denials.step-3-terminal.count` before writing `.bg-wait-active`. `run-step-checks.sh` and `design_core._bg_wait_marker_context` both clear these; a leftover sentinel makes `marker_step_completed` treat the new wait as already finished and hook denial can stay off on resume.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:896-898
- **Phase**: design

Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted

