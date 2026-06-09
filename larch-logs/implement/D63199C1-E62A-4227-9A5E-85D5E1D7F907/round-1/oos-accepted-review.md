### OOS_1: [OUT_OF_SCOPE] `pr checks` accepts `--repo` without slug validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `python/pr.py:1494-1504` accepts `--repo` without `validate_repo_slug`, unlike other PR CLI verbs; the reviewer marked this behavior unchanged from deleted `pr_cli.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: reuse `_validate_repo_arg` before `gh.pr_checks_text_read` for consistent slug validation across PR CLI verbs.


### OOS_2: [OUT_OF_SCOPE] `create_branch_main` emits empty KVs on some exits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `python/pr.py:353-354` emits `BRANCH_NAME`/`ACTION` from empty variables on `exists`/`invalid`/`fetch_failed` paths, while bash emitted no KVs; the reviewer marked this unchanged from `pr_cli.py`.
- **Suggested revisions (informational for voters; coder decides)**:


