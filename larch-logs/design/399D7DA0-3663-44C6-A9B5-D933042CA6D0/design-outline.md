## Proposed Design Outline

### Goals
- Fix /combine-issues --oos: closed blockers (satisfied deps) no longer permanently prevent source closure.
- Add `close-stale` verb for source issues that are fully stale and have no combined host.
- Emit `SOURCE_TO_COMBINED_JSON_FRAGMENT` from `apply` (item D) and fix oos-6c SKILL.md prose (item C).

### Non-goals
- Do not change how genuinely-unknown blockers (failed reads) are handled — fail-closed preserved.
- Do not change `fetch_deps_main` wire format (blocker state annotation stays in plan_inherited enrichment).
- Do not change the exception gate or `oos-6b` behavior.

### Approach sketch
- Add `--repo` (optional) to `plan_inherited_main`; for each blocker absent from meta, call `gh issue view` to get state.
- In `_classify_edge`: when blocker_meta.state == "closed", return `("satisfied", "...")` instead of `unknown`.
- Emit `satisfied_edges` from `plan_inherited_main`; `close_eligible_main` reads it but adds no reasons (no write needed).
- Add `close_stale_main` (--issues, --repo, --reason, --comment-file, --dry-run) mirroring close_sources_main; register in cli.py.
- Update SKILL.md: oos-2 all-stale branch, oos-6 satisfied bucket doc, oos-6c refresh scope clarification, oos-5 apply mapping output.

### Surfaces in scope
- python/combine_issues.py — _classify_edge, plan_inherited_main, close_eligible_main, apply_main, new close_stale_main
- python/cli.py — add close-stale registration
- python/test_combine_issues.py — new test cases
- .claude/skills/combine-issues/SKILL.md — oos-2, oos-5, oos-6, oos-6c, oos-7 prose

### Open questions
- None.
