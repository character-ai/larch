## Proposed Design Outline

### Goals
- Port remaining bash bodies in `skills/implement/scripts/` to Python in `implement_dispatch.py`, `file_oos.py`, and `execution_issues.py`.
- Cut all consumers (primarily `SKILL.md`) to call `python3 cli.py` directly; delete retired bash scripts and add them to `migrated-scripts.tsv`.
- Retire `lib-execution-issues.sh` and `step-0-degraded-gate.sh`.

### Non-goals
- No changes to existing Python implementations in the target modules (they already exist for OOS, flush, refresh, slack, diagram).
- No new Python modules; all ports land in the three target files.
- No behavior changes; ports must be functionally equivalent to the bash originals.

### Approach sketch
- Add three new CLI verbs: `implement step2-post-dispatch` (in `implement_dispatch.py`), `implement python-guard` (in `implement_dispatch.py`), `implement post-tracking-issue` (in `execution_issues.py`).
- Thin delegation wrappers with non-trivial env setup (step-0-bootstrap, step-8-seed-initial, step-8-ship, step-5-resume, step-5-review, step-6-entry, step-2-entry, run-step-checks, step-8-oos-checkpoint) stay; their SKILL.md call sites remain unchanged.
- Bash-body scripts with existing Python ports (OOS five + flush + refresh + slack + diagram): update SKILL.md fences to call `python3 cli.py` directly and delete the bash scripts.
- Delete all listed scripts, their `.md` siblings, and legacy harnesses; add paths to `migrated-scripts.tsv`.

### Surfaces in scope
- `python/implement_dispatch.py` — new `step2_post_dispatch_main`, `python_guard_main`
- `python/execution_issues.py` — new `post_tracking_issue_main`
- `python/cli.py` — register three new verbs
- `python/test_implement_dispatch.py`, `python/test_execution_issues.py` — new test coverage
- `skills/implement/SKILL.md` — fence cutover for non-wrapper scripts
- `python/migrated-scripts.tsv` — add ~20 retired paths
- `scripts/lib-execution-issues.sh` — delete
- `skills/implement/scripts/` — delete ~20 scripts + `.md` siblings

### Open questions
- `step-5-resume.sh` and `step-5-review.sh` have minor bash logic (banner printing, dynamic_archetypes_cap). Do they warrant new Python verbs, or stay as thin wrappers?
- `step-2-post-dispatch.sh` sources `lib-phantom-probe.sh`. Does the Python port replicate phantom probe functionality?
