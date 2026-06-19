### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/release_finish.py:42-50
- **Concern**: `release_finish._origin_repo` still shells out to `scripts/github-remote-repo.sh` but the plan only says to preserve the env override. Scenario: After G13 deletes `github-remote-repo.sh`, `cli.py release finish` loses origin resolution whenever `LARCH_RELEASE_FINISH_ORIGIN_REPO` is unset; release tagging/promotion can fail or target the wrong repo
- **Proposed resolution**: Add a `release_finish.py` step mirroring `release_prepare.py`: resolve origin via `gh remote-repo` (module helper or `python/cli.py gh remote-repo`), keep the override, and drop the bash helper existence check



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/step_7a.py:290-300
- **Concern**: The `step_7a.py` cutover bullet omits preserving checkpoint-probe argv derived from `forked_target`. Scenario: An implementer may call `push checkpoint-probe` with only `7a.r`/`diagrams`, dropping `--base-remote upstream --base-ref main`; fork-mode 7a.r rebases against `origin/main` instead of `upstream/main` and breaks the contract pinned by `skills/implement/scripts/test-step-7a.sh`
- **Proposed resolution**: Extend the `step_7a.py` plan step: when replacing the probe call, keep the existing fork mapping (`forked_target` -> `base_remote=upstream`, `base_ref=main`) and pass those flags through `_run_cli("push", "checkpoint-probe", ...)`



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/release_finish.py:42-50
- **Concern**: `_origin_repo` still shells out to `scripts/github-remote-repo.sh` but the plan only says preserve the env override. Scenario: The `### UPDATED: python/release_finish.py` entry omits replacing the bash helper; after deletion `/release finish` returns `None` for origin when `LARCH_RELEASE_FINISH_ORIGIN_REPO` is unset, breaking origin/main tag verification
- **Proposed resolution**: Add the same cutover as `release_prepare.py`: call `gh remote-repo` (module helper or `cli.py gh remote-repo`) and drop the `github-remote-repo.sh` subprocess; update `python/test_release.py` if the real `_origin_repo` path is exercised



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/release_finish.py:42-50
- **Concern**: Plan omits repointing `_origin_repo` off deleted `scripts/github-remote-repo.sh`. Scenario: After the helper is deleted, `_origin_repo` returns `None` when `LARCH_RELEASE_FINISH_ORIGIN_REPO` is unset (`helper.is_file()` fails at line 47), so `/release finish` can lose origin resolution and fail or mis-validate repo context
- **Proposed resolution**: Expand the `python/release_finish.py` plan bullet to match `release_prepare.py`: call `gh remote-repo` (CLI helper or `python/cli.py gh remote-repo`) instead of `bash scripts/github-remote-repo.sh`, preserving override and return-code semantics



### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/release_finish.py:42-50
- **Concern**: python/release_finish.py keeps only the override preservation in the plan and does not repoint the github-remote-repo.sh fallback. Scenario: After scripts/github-remote-repo.sh is deleted, release finish without LARCH_RELEASE_FINISH_ORIGIN_REPO returns origin_repo=None and fails origin-repo-mismatch before tagging or promoting
- **Proposed resolution**: Replace the helper branch with a module-local python/cli.py gh remote-repo origin call while preserving LARCH_RELEASE_FINISH_ORIGIN_REPO override behavior



