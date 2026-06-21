### OOS_1: [OUT_OF_SCOPE] resolve-upstream-larch-repo.sh is non-thin residual Bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/resolve-upstream-larch-repo.sh:9-61` is listed in `scripts/residual-bash-paths.txt` as kept residual Bash, but it is a non-thin inline-Python heredoc utility, not a `python/cli.py` delegation wrapper like `read-result-env.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Either port to an existing CLI verb for inventory consistency, or document this script explicitly as a deliberate exception in `docs/python-migration.md`.


