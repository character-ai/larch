## Decision 1: /implement behavior
- **Question**: Does the user want to remove the <USER_PREFIX>/* bypass for /implement, or keep current behavior?
- **Resolution**: Keep current /implement behavior. stash-clear check only; branch-check stays as-is.
- **Source**: user

## Decision 2: /design branch check
- **Resolution**: Remove --skip-branch-check from design_step0.py. /design must now be on main.
- **Source**: issue body

## Decision 3: stash-check placement
- **Resolution**: Add stash check inside clean_tree() in python/larch/git/git.py. Both /design and /implement inherit it automatically.
- **Source**: issue body (shared helper path)

## Decision 4: error message granularity
- **Resolution**: Emit stash-specific PREFLIGHT_ERROR hint (git stash pop/drop) distinct from dirty-tree hint. Update _clean_tree() in admission.py to return dirty_out so preflight can discriminate.
- **Source**: issue body

1 decision resolved in Step 1c, 3 decisions resolved from codebase inspection.
