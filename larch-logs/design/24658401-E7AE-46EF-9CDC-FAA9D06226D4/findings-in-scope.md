### FINDING_1: brainstorm.md Entry guard revives dual skip/run control after 1d.5 fold
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: The plan moves Step 1d.5 skip/run ownership into `step1d5 --mode entry` and a wrapper-emitted `STEP1D5_ACTION`, but `skills/design/references/brainstorm.md` is not in the planned file surface. On `STEP1D5_ACTION=run`, SKILL still loads `brainstorm.md`, whose Entry guard (lines 25–30) independently re-reads `run-params.json` and decides skip vs run. That guard checks `brainstorm_requested` before `.brainstorm-done`, unlike the wrapper precedence, so the wrapper can emit **run** while the loaded panel file skips to Step 1d.7, replays incorrectly on resume, or prints the wrong skip breadcrumb. This reintroduces a second source of truth the fold is meant to remove.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/design/references/brainstorm.md`: replace the Entry guard with a short note that skip/run was decided by `STEP1D5_ACTION` in the entry fence; on the run path start at the brainstorm banner / prompts read without re-reading `run-params.json` or re-skipping.
  - From Cursor-Requirements: Add ### UPDATED: skills/design/references/brainstorm.md: replace Entry guard steps 1-3 with wrapper-trust prose (only load on STEP1D5_ACTION=run; no independent skip/run; print the Step 1d.5 banner and continue to prompts). Update the Consumer line to reference STEP1D5_ACTION instead of direct run-params reads.

### FINDING_2: Step 1d.5 entry fold must pin strict `brainstorm_requested is True` predicate
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan says brainstorm is off when `brainstorm_requested is not true` but does not require the `step1d5_main --mode entry` implementation to use the same strict predicate as `step2a_main` (`data.get("brainstorm_requested") is True`, missing/malformed JSON defaulting to `False`). A loose truthiness read can disagree with Step 2a repair and emit `STEP1D5_ACTION=run` when Step 2a still treats brainstorm as off. Precedence for skip breadcrumbs (`.brainstorm-done` vs `brainstorm_requested`) should also match the wrapper contract explicitly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the `step1d5_main --mode entry` implementation bullet, require `brainstorm_requested = (json.loads(...) or {}).get("brainstorm_requested") is True` and branch skip only when that is false; mirror the missing-file default (`False`) explicitly.
  - From Cursor-Requirements: In the step1d5 --mode entry fold, load run-params with the same strict contract as step2a_main: missing or malformed JSON defaults false; enabled only when value is True; disabled when is not True; .brainstorm-done checked before brainstorm_requested.
