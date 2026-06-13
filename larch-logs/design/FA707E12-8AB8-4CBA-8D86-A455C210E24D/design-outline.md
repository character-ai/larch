## Proposed Design Outline

### Goals
- Port all plan-quality bash scripts (parse, validate, check-size, revise, auto-fix, optional-trailers) to a new `python/plan_quality.py` module and register CLI verbs in `cli.py`.
- Delete all absorbed bash/awk scripts, their harnesses, and fixture files; replace harness coverage with pytest.
- Cut over every direct caller to `python3 cli.py <domain> <verb>` with no shims.

### Non-goals
- Porting `lib-drift-baseline.sh` (still used by `design-postplan-emit.sh`, deferred).
- Porting `gate-b-dedup-plan.sh` itself (update only the `lib-plan-optional-trailers.sh` usage inside it).
- Adding new validation behavior beyond what the bash scripts implement.
- Porting `design-driver.sh`, `design-postplan-emit.sh`, or `review-design-step3-loop.sh` (only update their call sites).

### Approach sketch
- Create `python/plan_quality.py` with parse-commands, check-size, validate-commands, validate, revise, auto-fix, and optional-trailer functions (awk logic ported to pure Python).
- Register verbs under the existing `plan` domain in `cli.py` (extends `plan scope-paths`), or under a new `plan-quality` domain if the domain structure is clearer.
- Port `fixtures/parse-plan-commands/` and `fixtures/validate-plan-commands/` to pytest parametrize fixtures in `python/test_plan_quality.py`.
- Update consumer call sites: `design-postplan-emit.sh`, `design-driver.sh`, `gate-b-dedup-plan.sh`, `design-step-validator-autofix.sh`, `design-step2b5.sh`, `run-step1-plan-log.sh`.
- Append all retired paths to `python/migrated-scripts.tsv` and run stale-reference sweep.

### Surfaces in scope
- `python/plan_quality.py` (new)
- `python/test_plan_quality.py` (new)
- `python/cli.py` (new verbs)
- `python/migrated-scripts.tsv` (extended)
- `skills/design/scripts/` — delete ~12 absorbed scripts + awk files; update consumer scripts
- `scripts/` — delete `compose-plan-goals-test.sh` + harness; update `run-step1-plan-log.sh`
- `docs/python-migration.md`, `skills/design/SKILL.md`, `AGENTS.md`, reference docs (stale-reference sweep)

### Open questions
- CLI domain: extend existing `plan` domain, or use a new `plan-quality` domain?
