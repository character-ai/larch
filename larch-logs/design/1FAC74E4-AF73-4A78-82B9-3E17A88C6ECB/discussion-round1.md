## Decision 1: Agentic ship-pr CI fixer architecture (Change #2)
- **Question**: How should the agentic CI fixer integrate with the existing Python `monitor()` loop in `ci_monitor.py`?
- **Resolution**: Spawn a dedicated minimal-context **Opus 4.8** agentic subprocess that owns the full `fix → local-test → push → passive-CI-wait` loop internally (≤20 cycles). `ci_monitor` delegates to it for the CI-fix path instead of driving its own fix/push/poll cycle. Passive CI monitoring must use a **blocking shell CI-watch** so the LLM spends no tokens polling.
- **Source**: user

## Decision 2: CI-fix loop exhaustion behavior (Change #2)
- **Question**: After the agentic Opus loop exhausts its 20 cycles without green CI, what happens?
- **Resolution**: **Bail to the operator** (NEEDS_USER `ci-fix-exhausted`). The 20-cycle Opus loop is the entire CI-fix budget. Codex/Cursor are **no longer used for CI fixes** (role=fix); they serve conflict-resolution only after this change.
- **Source**: user

## Decision 3: resolve-conflict role stays single-shot (Change #1 only)
- **Question**: Does the Change #2 agentic loop also apply to rebase/merge-conflict resolution (role=resolve-conflict)?
- **Resolution**: No. The conflict-resolution waterfall (`rebase.py`) stays a **single-shot** Claude→Codex→Cursor waterfall (reordered + Opus model per Change #1). The agentic loop's "push → monitor CI" steps are inapplicable to local conflict resolution. Only the order/model change touches this path.
- **Source**: codebase (CI monitoring is not meaningful for local conflict resolution)

## Decision 4: Version-bump removal scope (Change #3)
- **Question**: How much of the version-bump machinery is removed from ship-pr?
- **Resolution**: Full removal of `_deterministic_prepass`, `_is_bump_path`, `_conflicts_are_non_bump_only` (and now-orphaned helpers like `_is_plugin_json_path` / `_larch_bump_files` if unused elsewhere) from `python/rebase.py`. `_resolve_conflicts` sends all unmerged paths straight to the waterfall; the pre-push handoff gate becomes unconditional on `enable_pre_push_handoff`. Remove related prose/docs. Premise: regular PRs no longer bump versions, so version-file conflicts should not arise; `/release` owns version bumping exclusively.
- **Source**: issue + codebase

## Decision 5: Pre-ship lint-fix loop is order/model only (Change #4)
- **Question**: Does Change #4 (`python/checks.py` `run_lint_fix`) get the agentic loop too?
- **Resolution**: No. Order/model only — add a **Claude/Opus 4.8** tier as the first dispatch, demote Codex/Cursor one slot each, keep their models (`gpt-5.5`, `composer-2.5`), and keep `main-agent-required` as the final fallback. The agentic local-test+push+CI-monitor loop does NOT apply here (this loop is pre-push and never touches CI). Spawning Opus on routine pre-ship lint failures is intended for policy consistency.
- **Source**: issue

## Hard constraints (binding for plan drafting)
- Passive CI monitoring MUST NOT generate extra LLM turns or burn tokens on the monitoring process itself (use a blocking shell-level CI watch, not LLM polling).
- Keep Codex `gpt-5.5` (effort `high`) and Cursor `composer-2.5` models unchanged; only the Claude tier moves to `claude-opus-4-8`.
- Update affected tests (`python/test_agents.py`, `python/test_checks.py`, `python/test_ci_monitor.py`, `python/test_rebase.py`, `python/test_config.py`, launcher/review harnesses) and `.md` sibling contracts and any docs enumerating waterfall order or tier models.
- ship-pr has no local checks/lint gate (the upfront pre-PR checks phase was removed by design); do not reintroduce it.
