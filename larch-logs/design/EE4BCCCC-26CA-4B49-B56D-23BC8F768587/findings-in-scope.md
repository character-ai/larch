### FINDING_1: `release_finish._origin_repo` still depends on deleted `github-remote-repo.sh`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Generic
- **Severity**: blocking
- **Concern**: The plan only preserves the `LARCH_RELEASE_FINISH_ORIGIN_REPO` override but does not repoint `_origin_repo` off `scripts/github-remote-repo.sh`. After G13 deletes that helper, `/release finish` loses origin resolution when the env override is unset (`helper.is_file()` fails or the subprocess is gone), so origin/main tag verification and promotion can fail or target the wrong repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a `release_finish.py` step mirroring `release_prepare.py`: resolve origin via `gh remote-repo` (module helper or `python/cli.py gh remote-repo`), keep the override, and drop the bash helper existence check
  - From Cursor-Innovation: Add the same cutover as `release_prepare.py`: call `gh remote-repo` (module helper or `cli.py gh remote-repo`) and drop the `github-remote-repo.sh` subprocess; update `python/test_release.py` if the real `_origin_repo` path is exercised
  - From Cursor-Pragmatic: Expand the `python/release_finish.py` plan bullet to match `release_prepare.py`: call `gh remote-repo` (CLI helper or `python/cli.py gh remote-repo`) instead of `bash scripts/github-remote-repo.sh`, preserving override and return-code semantics
  - From Codex-Generic: Replace the helper branch with a module-local python/cli.py gh remote-repo origin call while preserving LARCH_RELEASE_FINISH_ORIGIN_REPO override behavior

### FINDING_2: `step_7a.py` cutover omits fork-mode `checkpoint-probe` argv
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The `step_7a.py` cutover bullet omits preserving checkpoint-probe argv derived from `forked_target`. An implementer may call `push checkpoint-probe` with only `7a.r`/`diagrams`, dropping `--base-remote upstream --base-ref main`; fork-mode `7a.r` then rebases against `origin/main` instead of `upstream/main` and breaks the contract pinned by `skills/implement/scripts/test-step-7a.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the `step_7a.py` plan step: when replacing the probe call, keep the existing fork mapping (`forked_target` -> `base_remote=upstream`, `base_ref=main`) and pass those flags through `_run_cli("push", "checkpoint-probe", ...)`
