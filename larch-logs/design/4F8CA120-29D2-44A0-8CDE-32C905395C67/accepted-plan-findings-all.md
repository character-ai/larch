### FINDING_1: Session tool-availability wiring is missing
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Waterfall Contract Auditor
- **Severity**: major
- **Concern**: The coordinator does not source Codex, Cursor, and Claude availability from `session-env.sh` before lane selection. This can skip available fallback lanes or attempt unavailable binaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `architectural_assessment.py`, resolve lane availability with the same `_binary_flag`/`CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND` contract used by `checks_lint_fix.py`, pass those flags into `next_untried_tier`, and add tests for present/absent binaries independent of `shutil.which` drift
  - From Cursor-Innovation: In `architectural_assessment.py` (or the child argv in `step-8-assessment.sh`), resolve `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` (and Claude presence) from `$IMPLEMENT_TMPDIR/session-env.sh` using the same `_binary_flag` pattern as `checks_lint_fix.py`, pass them into `next_untried_tier`, and add tests that prove unavailable externals are skipped while present ones are attempted.
  - From Cursor-Pragmatic: Read CODEX_BINARY_FOUND, CURSOR_BINARY_FOUND, and CLAUDE_BINARY_FOUND from $IMPLEMENT_TMPDIR/session-env.sh (same helper pattern as checks_lint_fix.py) before lane selection, and pass those booleans into next_untried_tier.
  - From Cursor-Requirements: In architectural_assessment.py (or a small shared helper), read CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND/CLAUDE_BINARY_FOUND from $IMPLEMENT_TMPDIR/session-env.sh with the same fallback semantics as checks_lint_fix._binary_flag, pass those flags into next_untried_tier, and add a unit test that external lanes are skipped only when the corresponding flag is false
  - From Cursor-dyn-Waterfall Contract Auditor: Resolve availability from $IMPLEMENT_TMPDIR/session-env.sh the same way checks_lint_fix._binary_flag does for CODEX_BINARY_FOUND and CURSOR_BINARY_FOUND; pass those flags into next_untried_tier and skip absent lanes before launch


### FINDING_4: Cursor evidence access is unspecified
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: major
- **Concern**: Cursor may not be able to read assessment evidence stored under `IMPLEMENT_TMPDIR` when its workspace is only the repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Grant Cursor read-only access to the evidence directory or stage evidence inside its workspace, and test that the assessment contract can read the staged files and return the exact JSON result.
  - From Codex-Pragmatic: Inline validated evidence for Cursor or launch it with a workspace that contains the evidence


### FINDING_6: Claude read-only invocation contract may regress
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Replacing `ClaudeLauncher` may silently drop the established `claude --print`, `--add-dir`, `--allowedTools Read`, and `--permission-mode plan` contract needed for assessment evidence access and permissions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In the architectural_assessment.py plan bullets, require the Claude adapter to preserve the current argv/read-only shape (or document an equivalent launch-review path) and extend test_architectural_assessment.py to assert those flags on the Claude lane adapter


### FINDING_8: Assessment mode must bypass review-only Cursor postprocessing
- **Reviewer(s)**: Cursor-Pragmatic, Codex-dyn-Waterfall Contract Auditor
- **Severity**: major
- **Concern**: Review-specific degraded-response heuristics can rewrite valid, compact assessment JSON as degraded or empty, incorrectly advancing to fallback or operator-bail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an assessment contract flag that skips review degraded postprocess, extracts the envelope result verbatim, and hands normalized assessment JSON to the coordinator parser; cover this in test_launch_review.py.
  - From Codex-dyn-Waterfall Contract Auditor: Add an assessment mode that preserves the raw result payload and bypasses review-only degradation normalization; test valid Cursor assessment acceptance and no later-lane launch


### FINDING_9: Cursor results require a clean dirty-tree sidecar
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: A Cursor assessment could modify the repository while leaving `HEAD` unchanged; accepting its verdict without dirty-tree validation risks persisting output from a mutating run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Accept Cursor output only when its dirty-tree sidecar reports STATUS=clean; fail closed on dirty or unknown and test this path


### FINDING_1: Codex assessment lane lacks access to validated evidence
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: In assessment mode, Codex is not granted read access to the validated evidence directory containing `diff_path` and `knowledge_path`. The backup lane may therefore produce empty or malformed output instead of a real assessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In assessment mode, pass the validated evidence directory as Codex --add-dir (keep repository -C for dirty-tree baseline), and add a launcher test that the prompt paths are inside the granted add-dir roots.
  - From Cursor-Requirements: In assessment mode, pass the validated evidence directory to Codex (extra --add-dir, or colocate launcher output under that directory), and add `test_launch_review.py` coverage that Codex `--add-dir` includes the evidence tree.


