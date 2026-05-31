### OOS_1: [OUT_OF_SCOPE] StubRunner duplicates pattern in `test_git.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: StubRunner duplicates the pattern in test_git.py with call recording. Minor DRY violation across test files; pre-existing convention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared test helper module if test duplication becomes painful repo-wide.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_2: [OUT_OF_SCOPE] Bash `compose_prompt` does not re-redact log tails (Python is stricter)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Bash compose_prompt does not re-redact log tails; Python `_compose_prompt` does. No breakage; Python is stricter. Optional documentation only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Submodule paths inlined into prompts without newline sanitization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Submodule paths from repo metadata are inlined into prompts without newline sanitization. Malicious `.gitmodules` path values could attempt prompt-structure injection; same broad trust model as consumer-repo fixer runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Strip or reject control characters in submodule path lists if hardening consumer-repo threat model.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_4: [OUT_OF_SCOPE] Unplanned harness/version changes on branch
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-parity-drift-output.txt
- **Severity**: latent
- **Concern**: Changes outside Phase 4 plan file list (`scripts/test-lint-literal-counts.sh`, `skills/design/scripts/test-plan-review-loop.sh`, `.claude-plugin/plugin.json`, commit `abfbc565c` lint-literal-counts / plan-review-loop poll / version bump) are unrelated review surface; no action required for Phase 4 fidelity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: No action required for Phase 4 fidelity
  - From dyn-parity-drift-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] Implement self-fix / run-log commits outside planned deliverables
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-parity-drift-output.txt
- **Severity**: latent
- **Concern**: Commits `cee777a21` / `f44395376` (run logs / implement commit) and similar implement self-fix work are not part of checks.py Phase 4 scope unless they touch checks.py.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Ignore for Phase 4 plan fidelity unless it touches checks.py
  - From dyn-parity-drift-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_6: [OUT_OF_SCOPE] `_scripts_dir` ignoring `repo_root` matches bash plugin-script resolution
- **Reviewer(s)**: dyn-parity-drift-output.txt
- **Severity**: nit
- **Concern**: Ignoring `repo_root` and resolving `Path(__file__).parents[1] / "scripts"` matches bash `lint-fix-loop.sh` (`SCRIPT_DIR` / plugin scripts), not `repo_root/scripts`. Consumer `relevant-checks.sh` is correctly resolved under `repo_root` in `run_relevant_checks`. Not a production parity defect; tests that monkeypatch `_scripts_dir` to the consumer tree exercise a different layout.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] `_post_dispatch_forbidden_revert` unused baselines match bash
- **Reviewer(s)**: dyn-parity-drift-output.txt
- **Severity**: nit
- **Concern**: Bash `post_dispatch_forbidden_revert` also ignores pre-dispatch baselines and reverts any current tracked/untracked path matching the forbidden list (`scripts/lint-fix-loop.sh:170-199`). Python’s discard of `baseline_tracked` / `baseline_untracked` matches that behavior.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] `run_checks_phase` single-site wiring relevant only at full ship-pr cutover
- **Reviewer(s)**: dyn-parity-drift-output.txt
- **Severity**: latent
- **Concern**: Python uses one `site` for both checks and fix (default `step6`). Bash uses step6 checks and `ship-pr-ci-initial` fix. Relevant only when this API replaces ship-pr’s custom checks loop at cutover; plan positions `run_checks_phase` as `run_captured_cmd_then_fix_loop` wiring, not a full port of bash `run_checks_phase`.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

