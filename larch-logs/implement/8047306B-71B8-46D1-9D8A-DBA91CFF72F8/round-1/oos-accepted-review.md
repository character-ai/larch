### OOS_1: [OUT_OF_SCOPE] Five Makefile harness targets run identical full pytest file
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Five harness targets run identical full pytest file on different CI shards. Full `make lint` runs the same ~17 tests five times; CI time waste as suite grows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Consolidate to one shard target or split pytest by marker (-k) per Makefile target


### OOS_2: [OUT_OF_SCOPE] `launcher-argv-test-coverage.md` has stale path globs
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-reference-sweep-output.txt
- **Severity**: important
- **Concern**: Path-triggered rule frontmatter still globs deleted `skills/implement/scripts/test-step2-*.sh` and triple-lists `python/test_implement_dispatch.py`. Edits to Step 2 Python CLIs or the pytest harness will not inject the launcher-argv coverage reminder the rule is meant to provide.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Remove stale glob and dedupe python/test_implement_dispatch.py entry
  - From dyn-reference-sweep-output.txt: Drop the deleted `test-step2-*.sh` glob, dedupe the pytest path once, and add explicit globs for `python/implement_dispatch.py` and `python/cli.py implement {run-dispatch,step2-dispatch,commit}` so the rule fires on the surfaces it now describes.


