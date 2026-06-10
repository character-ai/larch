## Proposed Design Outline

### Goals
- Port 18 bash scripts across 6 skills (/issue, /block-issue, /alias, /cleanup, /upgrade-larch, /set-up-forked-open-source-repo) to stdlib-only Python modules.
- Replace all associated bash test harnesses with colocated pytest; retire bash scripts and harness files.
- Preserve byte-exact stdout KV grammars (ISSUES_*, ITEM_<i>_*) consumed by /implement and /research.

### Non-goals
- No changes to SKILL.md orchestration logic beyond call-site cutover (scripts → cli.py verbs).
- No changes to hooks, linters, or non-absorbed scripts.
- No redesign of the public APIs; port the existing contracts exactly.

### Approach sketch
- Create python/issue_create.py (absorbs parse-input, create-one, allocate-candidates, add-blocked-by, fetch-issue-details, list-issues, write-sentinel, cleanup-failed-issue) with one function per former script.
- Create python/alias_skill.py (generate-alias, resolve-target), python/cleanup_skill.py (cleanup.sh), python/upgrade_larch.py (upgrade-larch, release-step7-root, lib-larch-dev-clone, lib-sparse-dirs), python/forked_repo.py (setup-forked-open-source-repo, lib-remotes).
- Register CLI verbs in _REGISTRY for each function; cut all SKILL.md call-sites to python3 cli.py <domain> <verb>.
- Port all Makefile-wired bash harnesses to colocated pytest files; delete absorbed bash + md files; append retired paths to python/migrated-scripts.tsv.

### Surfaces in scope
- python/issue_create.py (new), python/alias_skill.py (new), python/cleanup_skill.py (new), python/upgrade_larch.py (new), python/forked_repo.py (new)
- python/cli.py (add ~20 registry entries)
- python/test_issue_create.py, python/test_alias_skill.py, python/test_cleanup_skill.py, python/test_upgrade_larch.py, python/test_forked_repo.py (new)
- skills/issue/SKILL.md, skills/block-issue/SKILL.md, skills/alias/SKILL.md, skills/cleanup/SKILL.md, skills/upgrade-larch/SKILL.md, skills/set-up-forked-open-source-repo/SKILL.md (call-site cutover)
- scripts/test-redact-secrets.sh (update create-one.sh reference)
- python/migrated-scripts.tsv (append retired paths)
- Makefile (swap bash harness targets for pytest)
- All absorbed .sh, .md sibling, and test harness files (deleted)

### Open questions
- None.
