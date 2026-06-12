### FINDING_1: Python targets fail under bare launcher exec
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Codex-Arch, Codex-Pragmatic, Cursor-Innovation, Codex-Innovation, Codex-dyn-fence-boundary-audit, Cursor-dyn-fence-boundary-audit, Codex-dyn-session-key-format-contract
- **Severity**: important
- **Concern**: The proposed `larch-run.sh` launcher accepts `.py` targets but execs them directly. Post-Step-0 conversions include `python/cli.py`, which has no shebang and is not executable, so converted run-log append paths can fail with permission, exec-format, or equivalent execution errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Requirements: In emit_larch_run_sh() branch on *.py and use exec python3 "$CLAUDE_PLUGIN_ROOT/$script" "$@" (or equivalent) while keeping .sh on bare exec
  - From Codex-Arch, Codex-Pragmatic: Dispatch *.py targets with python3 inside larch-run.sh, or remove .py from the new launcher shape and keep Python CLI calls in a supported one-line form
  - From Cursor-Innovation: In larch-run.sh branch on *.py and exec python3 "$CLAUDE_PLUGIN_ROOT/$script" "$@" (or keep that one fence on the pre-bootstrap guard shape)
  - From Codex-Innovation, Codex-dyn-fence-boundary-audit: Make larch-run.sh dispatch *.py with python3 "$CLAUDE_PLUGIN_ROOT/$script" "$@" and update the fence-shape test to require that behavior, or do not allow .py launcher targets and keep this call on a valid python3 path
  - From Cursor-dyn-fence-boundary-audit: In emit_larch_run_sh generated body branch on *.py (or always for python/cli.py) to exec python3 "$CLAUDE_PLUGIN_ROOT/$script" "$@" instead of bare exec
  - From Codex-dyn-session-key-format-contract: Handle .py targets in larch-run with python3, or keep launcher targets to executable .sh files and route this call through a shell wrapper


### FINDING_2: Structure and anti-halt harnesses remain pinned to old fence shape
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan updates the SKILL.md fence shape but omits required lint-gated harness updates. Existing structure and anti-halt checks still look for old `${CLAUDE_PLUGIN_ROOT}` wrapper anchors, inline guards, background markers, and site-count patterns, so `make lint` may fail or stop verifying the intended launcher conversion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update these harnesses and sibling docs to recognize the larch-run one-line shape for the same wrapper sites while preserving the existing anti-halt, timeout, and site-count assertions
  - From Cursor-Pragmatic: Add `### UPDATED: scripts/test-implement-structure.sh` (and sibling `.md` if needed): retarget anchors to `larch-run.sh` launcher lines or script basename substrings; relax the Step 5 background regex to allow the one-line launcher form; list this harness in required testing (not only "if time allows")
  - From Cursor-Requirements: Add scripts/test-implement-structure.sh (and sibling .md if present) to Files to modify/create; retarget anchors to larch-run.sh invocations and step-5-resume background regex; list make test-implement-structure in required tests not optional




### FINDING_1: Resume-tail launcher emission must be unconditional
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `--resume-plan-tail` must create `larch-run.sh` even when `plugin-root.env` already exists. If emission is placed inside the `plugin-root.env` sync branch, upgraded or partially bootstrapped tmpdirs can keep `plugin-root.env` but lack the launcher, causing every converted post-Step-0 fence to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: State explicitly that `emit_larch_run_sh` runs once at the end of the resume-plan-tail branch regardless of whether sync ran; add a bootstrap harness case: plugin-root.env present, larch-run.sh absent, resume-tail creates launcher
  - From Cursor-Innovation: Call emit_larch_run_sh once at the common tail of phase_infra for both fresh and resume-plan-tail paths; add a bootstrap harness case: session-env.sh plus plugin-root.env present, larch-run.sh absent, resume-tail creates executable launcher
  - From Cursor-Pragmatic: Call `emit_larch_run_sh()` unconditionally immediately after the sync `if`/`fi` on the resume-plan-tail branch (idempotent rewrite), and add a bootstrap harness case: tmpdir with `plugin-root.env` present but `larch-run.sh` absent before resume-tail


### FINDING_3: Physical one-line fence acceptance is not pinned
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: Acceptance requires each post-Step-0 Bash fence body to be one physical line, but the plan and fence-shape harness may only enforce one logical launcher command. Comment lines or backslash continuations could pass while violating the stated acceptance criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Align SKILL.md conversion and scripts/test-implement-fence-shape.sh: post-Step-0 fence bodies should be exactly one non-comment physical line (the launcher call); move # Foreground required / anti-halt duplicates to prose outside the fence; add a harness assert that new-shape fences have no non-blank lines besides the launcher invocation
  - From Codex-Requirements: Add a new-shape check that each post-Step-0 fence has exactly one nonblank noncomment physical line, no trailing backslash, and that line matches bash "$IMPLEMENT_TMPDIR/larch-run.sh" <relative .sh|.py> ....


### FINDING_4: Old-shape fence whitelist must account for both plan-block reads
- **Reviewer(s)**: Cursor-dyn-whitelist-gap
- **Severity**: important
- **Concern**: The old-shape whitelist describes four categories, but five Bash fences need to remain old shape because there are two plan-block read variants. A category-count-based harness can reject one valid Preflight fence or allow incorrect regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-whitelist-gap: In test-implement-fence-shape.sh pin five old-shape fences by target path: extract-closes-issue-from-pr.sh both plan-block read fences step-0-bootstrap.sh --mode initial step-0-bootstrap.sh --mode resume; document expected old=5 new=32 in PASS output


### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-whitelist-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:188-198 vs plan.txt:106
- **Concern**: [SCOPE-REDUCTION] Plan prelude contract says every pre-bootstrap fence keeps source guard plus awk fallback but the two Preflight plan-block read fences are guard-only today. Scenario: Implementer or harness author may add awk fallback to Preflight fences or require awk on all old-shape fences; that changes untouched Preflight behavior and can break runs where IMPLEMENT_TMPDIR is unset
- **Proposed resolution**: State explicitly that Preflight plan-block read fences (default and forked) keep their current guard-only shape; awk fallback is optional and only on structured-invocation pin Step 0 initial and dirty-tree resume



