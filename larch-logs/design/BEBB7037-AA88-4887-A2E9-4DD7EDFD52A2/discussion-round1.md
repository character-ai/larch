## Decision 1: Call-site cutover scope
- **Question**: Should the implementation cut over ALL callers of the retired scripts (comprehensive sweep), or just the listed "at least" callers?
- **Resolution**: Comprehensive. The DoD says "direct call-site cutover (no shims)" and `make lint-retired-scripts` is the enforcement gate. The "at least" in the plan is a non-exhaustive starter list; every runtime caller must be ported.
- **Source**: codebase (definition of done in issue body)

## Decision 2: scripts/flush-vendor-failure-diagnostics.sh
- **Question**: Is `flush-vendor-failure-diagnostics.sh` being kept (not deleted)?
- **Resolution**: Yes — it is in the explicit "do not delete" list. Its body will be updated to call the new Python CLI verbs instead of the old bash helpers.
- **Source**: codebase (issue body "do not delete" section)

## Decision 3: python/verify_skill.py location
- **Question**: Is `python/verify_skill.py` a new file (does not yet exist)?
- **Resolution**: Yes, it does not yet exist. It is "### NEW" in the plan.
- **Source**: codebase (file absent at <OPERATOR_REPO_PATH>/python/verify_skill.py)

0 open scope questions — all resolved from the codebase.
