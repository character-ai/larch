### FINDING_1: Emit-plan validates a different plan file than the revised file
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The proposed `--plan-file` argument can point at a different file than `ACTION=EMIT_PLAN` validates and uses for `diff-lines.txt`, so the revision waterfall can apply a candidate to one plan while accepting or rejecting another.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require `--plan-file` to resolve to `$design_tmpdir/plan.txt` in pre-flight (exit 2 on mismatch) and document the invariant in the sibling `.md`; Piece 5 should pass the same paths as `plan-review-loop.sh` (`SKILL.md` uses both as `$DESIGN_TMPDIR/plan.txt`)
  - From Codex-Arch: Add preflight requiring canonical --plan-file to equal "$design_tmpdir/plan.txt", or change the proposed validation path to use a helper that validates the same file being modified
  - From Cursor-Edge: For SIMPLE scope, canonicalize and require --plan-file to equal $DESIGN_TMPDIR/plan.txt, or explicitly copy/symlink the candidate into that path before running ACTION=EMIT_PLAN and restore afterward
  - From Codex-Edge: For SIMPLE scope, canonicalize and require --plan-file to equal $DESIGN_TMPDIR/plan.txt, or explicitly copy/symlink the candidate into that path before running ACTION=EMIT_PLAN and restore afterward
  - From Codex-Innovation: Minimum-change fix: preflight canonicalize and require --plan-file to equal "$design_tmpdir/plan.txt", then document that invariant. If arbitrary plan paths are required later, add a separate candidate-validation path instead of using design-driver unchanged.
  - From Codex-Pragmatic: Preflight-require canonical --plan-file equals "$design_tmpdir/plan.txt", or narrow the argv contract to that exact path before shipping
  - From Cursor-Requirements: Preflight that canonical --plan-file equals "$design_tmpdir/plan.txt", or drop the independent plan path and derive it from --design-tmpdir
  - From Codex-Requirements: Preflight that canonical --plan-file equals "$design_tmpdir/plan.txt", or drop the independent plan path and derive it from --design-tmpdir

### FINDING_2: Launcher calls omit required prompt source flags
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Edge, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-launcher-argv-completeness, Codex-dyn-launcher-argv-completeness
- **Severity**: important
- **Concern**: The plan routes review tiers with `--mode description` and `--description-text` but no required prompt source, so real Codex, Cursor, and Claude launchers can exit 2 before producing patches while permissive stubs still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Pass the composed prompt via --prompt-file "$prompt_path" or --prompt "$prompt_text"; keep --description-text only if using an agent-file render path
  - From Cursor-Innovation: Pass the composed prompt via --prompt-file "$prompt_path" or --prompt "$prompt_text"; keep --description-text only if using an agent-file render path
  - From Cursor-Edge: Pass the composed prompt as --prompt-file prompt.txt or --prompt to all three launchers; keep --description-text only as auxiliary context if needed
  - From Codex-Edge: Pass the composed prompt as --prompt-file prompt.txt or --prompt to all three launchers; keep --description-text only as auxiliary context if needed
  - From Codex-Innovation: Pass --prompt-file "$prompt_file" to all three launchers and keep --mode description; use --description-text only with an agent-file render path or drop it. Add a harness assertion that stubs receive --prompt-file.
  - From Codex-Pragmatic: Invoke each launcher with --prompt-file "$prompt_file" or --prompt "$(cat "$prompt_file")"; keep --plan-file --feature-file --scope-files only as context flags
  - From Cursor-Requirements: Revise the launch step to pass the composed prompt via --prompt-file "$prompt_file" or --prompt "$prompt_content", and make launcher stubs assert exactly one prompt source is present
  - From Codex-Requirements: Revise the launch step to pass the composed prompt via --prompt-file "$prompt_file" or --prompt "$prompt_content", and make launcher stubs assert exactly one prompt source is present
  - From Cursor-dyn-launcher-argv-completeness: Change the tier call sketch to pass the composed prompt as --prompt-file "$prompt_file" or --prompt "$prompt"; do not rely on --description-text as the prompt source
  - From Codex-dyn-launcher-argv-completeness: Change the tier call sketch to pass the composed prompt as --prompt-file "$prompt_file" or --prompt "$prompt"; do not rely on --description-text as the prompt source

### FINDING_3: Patch application lacks a real single-plan-file allowlist
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements, Codex-Requirements, Cursor-Edge, Codex-Edge, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The planned unified-diff application treats `git apply --unsafe-paths` as if it restricted edits to the plan file, but it can allow patches touching unrelated files or paths outside the intended work area before later validation notices.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Remove --unsafe-paths and explicitly reject any diff whose touched path is not the canonical plan-file path before git apply --check/apply
  - From Cursor-Requirements: Remove --unsafe-paths and explicitly reject any diff whose touched path is not the canonical plan-file path before git apply --check/apply
  - From Codex-Requirements: Remove --unsafe-paths and explicitly reject any diff whose touched path is not the canonical plan-file path before git apply --check/apply
  - From Cursor-Edge: Validate diff headers before apply so every old/new path is exactly the canonical plan file path or apply in an isolated temp dir containing only plan.txt, then move the validated candidate over --plan-file
  - From Codex-Edge: Validate diff headers before apply so every old/new path is exactly the canonical plan file path or apply in an isolated temp dir containing only plan.txt, then move the validated candidate over --plan-file
  - From Codex-Innovation: Remove --unsafe-paths. Run git apply from dirname "$plan_file", require the diff to touch exactly basename "$plan_file", and use --include "$base" --exclude "*" or an explicit header check before apply. Add a regression where a patch targeting another file is rejected and leaves that file unchanged.
  - From Codex-Pragmatic: Add explicit diff header validation that every old/new path resolves to the single plan file before git apply; avoid --unsafe-paths unless the validated temp-application strategy requires it

### FINDING_4: File-replacement patch mode is premature scope
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements, Codex-Requirements
- **Severity**: latent
- **Concern**: The plan adds `--patch-format file-replacement` as a second patch protocol even though current acceptance needs appear to require only unified diffs, increasing validation, docs, and test surface in a SIMPLE lane.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Drop --patch-format file-replacement and its test/docs branches for this PR; keep unified diff only unless the current caller requires replacement mode
  - From Cursor-Requirements: Keep only unified-diff for this piece unless the feature explicitly requires replacement mode; defer file-replacement to a follow-up if unified diffs prove brittle
  - From Codex-Requirements: Keep only unified-diff for this piece unless the feature explicitly requires replacement mode; defer file-replacement to a follow-up if unified diffs prove brittle

### FINDING_5: Candidate validation does not preserve file-scope headings
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Concern**: The validator may accept a revised plan that preserves only the `diff_lines` trailer while dropping parseable `### NEW`, `### UPDATED`, or `### REWRITTEN` file-scope headings, which can break downstream scope parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add a minimal post-candidate check that parseable file-scope headings still exist when the original plan had them, reusing the existing heading grammar rather than adding new semantic validation
  - From Codex-Edge: Add a minimal post-candidate check that parseable file-scope headings still exist when the original plan had them, reusing the existing heading grammar rather than adding new semantic validation

### FINDING_6: Unified-diff application is underspecified for non-repo tempdirs
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-git-apply-portability, Codex-dyn-git-apply-portability
- **Severity**: important
- **Concern**: The plan does not define a reliable patch application strategy and header path convention for session tmpdirs that are not git worktrees, so unified-diff tiers can fail or depend on exact mocked path forms.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Apply patches with patch(1) from the plan file directory (check + apply), or run git init in $design_tmpdir before the first git apply; document the choice in revise-plan-with-waterfall.md
  - From Cursor-dyn-git-apply-portability: Revise the plan to require one canonical form: either cd to dirname "$plan_file" and accept only a/plan.txt b/plan.txt, or rewrite single-file patch headers to a//$abs_plan_file and b//$abs_plan_file before both --check and apply; make the harness fixtures use the same form
  - From Codex-dyn-git-apply-portability: Revise the plan to require one canonical form: either cd to dirname "$plan_file" and accept only a/plan.txt b/plan.txt, or rewrite single-file patch headers to a//$abs_plan_file and b//$abs_plan_file before both --check and apply; make the harness fixtures use the same form

### FINDING_7: Codex and Cursor launcher sketches omit required timeout
- **Reviewer(s)**: Cursor-dyn-launcher-argv-completeness, Codex-dyn-launcher-argv-completeness
- **Severity**: important
- **Concern**: The Codex and Cursor launcher call sketch omits required `--timeout`, so `launch-review.sh` can reject those tiers with exit 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-launcher-argv-completeness: Include --timeout "$timeout" on both launch-review.sh --tool codex and launch-review.sh --tool cursor calls; Claude may also receive it to honor the plan's per-tier timeout option
  - From Codex-dyn-launcher-argv-completeness: Include --timeout "$timeout" on both launch-review.sh --tool codex and launch-review.sh --tool cursor calls; Claude may also receive it to honor the plan's per-tier timeout option

### FINDING_8: Failure finalization does not actually emit unconditional empty KV records
- **Reviewer(s)**: Cursor-dyn-kv-unconditional-drift, Codex-dyn-kv-unconditional-drift
- **Severity**: important
- **Concern**: The failure finalize path promises unconditional KV output but does not explicitly emit empty `REVISE_TIER` and `REVISE_PATCH_PATH` records, so presence-aware callers can observe missing keys rather than `KEY=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-unconditional-drift: Make the failure finalize branch explicitly emit emit_kv REVISE_TIER "" and emit_kv REVISE_PATCH_PATH "", and update the all-fail harness assertion to require REVISE_TIER= and REVISE_PATCH_PATH=.
  - From Codex-dyn-kv-unconditional-drift: Make the failure finalize branch explicitly emit emit_kv REVISE_TIER "" and emit_kv REVISE_PATCH_PATH "", and update the all-fail harness assertion to require REVISE_TIER= and REVISE_PATCH_PATH=.

### FINDING_9: Tier status ordinal mapping is not contractual
- **Reviewer(s)**: Cursor-dyn-kv-unconditional-drift, Codex-dyn-kv-unconditional-drift
- **Severity**: latent
- **Concern**: `REVISE_TIER_<N>_STATUS` uses ordinal status fields without explicitly documenting that the mapping is one-based and tied to codex, cursor, then claude, which can cause callers to misread the KV contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-unconditional-drift: Add one KV-contract sentence: REVISE_TIER_1_STATUS is codex, REVISE_TIER_2_STATUS is cursor, and REVISE_TIER_3_STATUS is claude.
  - From Codex-dyn-kv-unconditional-drift: Add one KV-contract sentence: REVISE_TIER_1_STATUS is codex, REVISE_TIER_2_STATUS is cursor, and REVISE_TIER_3_STATUS is claude.
