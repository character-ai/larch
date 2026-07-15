## Review Phase Detail

| Round | Suggestions | Accepted | OOS proposed | OOS fileable | Time | Cost | Reviewers |
|--:|--:|--:|--:|--:|:--|--:|--:|
| 1 | 2 | 1 | 0 | 0 | 9m 35s | $9.19 | 8 |
| **Total (round-sum)** | **2** | **1** | **0** | **0** | **9m 35s** | **$9.19** | **8** |

_The Total (round-sum) row adds up the per-round Suggestions and Accepted: when the review loop re-raises the same finding across rounds, that finding is counted once per round, so the round-sum can exceed the number of distinct findings. Top reviewers counts per-round accepted-point scores the same way._

_Finding decomposition (canonical, scope-aware): round 1: 2 finding(s) = 2 in-scope (voted; matches the headline X/Y accepted) + 0 out-of-scope. The Suggestions and OOS columns above count findings by finding id (raw per-finding) and can disagree with this scope-aware split when findings are reclassified out-of-scope after voting; round-meta.json records both raw (`tally`) and canonical (`tally_canonical`) counts so downstream joins do not contradict._

### Round 1 reviewer timing

```
Round 1 reviewer timing  ·  window 0:00-9:35 (575s)
                                       0:00                                     9:35
                                      ┌─────────────────────────────────────────────┐
codex/edge-cases                      │█████                                        │  63s
codex/dyn-dyn-registry-dispatch-codex │██████                                       │  76s
codex/correctness                     │██████                                       │  77s
codex/testing                         │████████                                     │ 105s
cursor/testing                        │█████████████                                │ 167s
cursor/dyn-dyn-registry-dispatch      │██████████████                               │ 174s
cursor/correctness                    │█████████████████                            │ 221s
reviewer-collect                      │                        █                    │   4s
aggregator                            │                        █                    │   4s
voter-dispatch-prep                   │                        █████████████████    │ 205s
codex/validity-vote                   │                                         █   │  20s
codex/plan-fidelity-vote              │                                         ██  │  32s
codex/pragmatism-vote                 │                                         ███ │  46s
                                      └─────────────────────────────────────────────┘
```

**Top reviewers** (by per-round accepted-point score, whole run):
1. codex/testing: 2
2. cursor/correctness: 2
3. cursor/testing: 2

**Reviewer slot failures**: 0

## Exec Issues and Warnings
Exec Issues (0):
Warnings (41):
  1. The diff refactors `python/larch/cli.py` to add a third boolean field `machine_stdout` to each registry value (changing the type from `dict[tuple[str, str], tuple[str, str]]` to `dict[tuple[str, st...
  2. ## G-Md-2 deviation — prose consumers of renamed module paths not swept
  3. `G-Md-2` requires that a rename not be considered done until its prose consumers in `docs/`, `skills/**/SKILL.md`, `README.md`, `SECURITY.md`, and `.github/workflows/` are swept in the same change.
  4. The diff moves `design route` and `design init-runparams` from `larch.design.design_lifecycle` to `larch.design.design_router`. `skills/design/SKILL.md:681` is not updated in the diff. That line st...
  5. > `design route`, `design init-runparams`, and `design parse-flags`: Step 0 route/init/argv drivers; implementations `${CLAUDE_PLUGIN_ROOT}/python/larch/design/design_lifecycle.py` and `${CLAUDE_PL...
  6. After this diff, `route` and `init-runparams` are registered in `larch.design.design_router`, not `design_lifecycle`. The SKILL.md implementation pointer for those two verbs is now stale.
  7. Reviewer can confirm: in the new registry (diff lines 716-717), `("design", "route")` maps to `("larch.design.design_router", "route_main", True)` and `("design", "init-runparams")` maps to `("larc...
  8. ## Remaining changes are clean
  9. The `machine_stdout` consolidation (eliminating the separately maintained `_MACHINE_STDOUT_KEYS` and `_DESIGN_LIFECYCLE_STDOUT_KEYS` frozensets in favor of a flag co-located in each registry row, t...
  10. ## Deviation: G-Md-2 — one prose implementation pointer for `design step5c` not swept
  11. ### What the diff does
  12. `python/larch/cli.py` changes the registry entry for `("design", "step5c")` from
  13. `("larch.design.design_lifecycle", "step5c_main")` to `("larch.design.design_step5c", "step5c_main", True)`.
  14. It also sweeps many other `design_lifecycle` entries, and updates `skills/design/SKILL.md:681`
  15. to replace `design_lifecycle.py` with `design_router.py` for the `route` and `init-runparams` verbs.
  16. ### The stale reference
  17. `skills/design/SKILL.md:682` (unchanged in the diff — a context line in the only hunk that touches the file)
  18. still reads:
  19. > "`${CLAUDE_PLUGIN_ROOT}/python/cli.py design step5c`: Step 5c orchestration;
  20. > implementation `${CLAUDE_PLUGIN_ROOT}/python/design_lifecycle.py`; …"
  21. After the diff the verb `design step5c` is registered in `larch.design.design_step5c`, not
  22. `larch.design.design_lifecycle`. The prose pointer is now false.
  23. G-Md-2 requires sweeping prose consumers of a renamed module in the same change.
  24. The diff swept the `route`/`init-runparams` pointer (line 681) but left the adjacent
  25. `step5c` pointer (line 682) unchanged.
  26. ### Scope
  27. This is the only new G-Md-2 deviation introduced by the diff. All other swept-module pointer
  28. changes (`step0-*` verbs to `design_step0`/`design_step0_env`, `step1*`/`driver` to `design_step1`,
  29. `step2b*` to `design_step2b`, `step5b*` to `design_step5b`, `step6*` to `design_step6`,
  30. `read-result-env`/`stage-terminal-state`/`failure-report`/`step-final-summary` to `design_terminal`,
  31. `settle-next-action` to `design_session`) have no corresponding prose pointer in the swept
  32. `skills/`, `docs/`, `README.md`, `SECURITY.md`, or `.github/workflows/` files.
  33. `skills/review/SKILL.md:24` references `python/review_pipeline.py` for the prune-decision helper,
  34. and the diff removes several `review_pipeline` CLI registrations (`core`, `reviewer-prune`,
  35. `gather-context`, `dispatch-panel`, `collect-findings`, `check-reviewer-failure-threshold`).
  36. That path was already stale before this diff (old pre-migration form without `larch/`) and
  37. `python/larch/review/review_pipeline.py` still exists as a file, so that pre-existing staleness
  38. is not a new deviation introduced here.
  39. ### Correction needed
  40. Update `skills/design/SKILL.md:682` to name `design_step5c.py` instead of `design_lifecycle.py`
  41. for the `design step5c` verb.

## Architectural invariants

The changed lines are confined to the CLI dispatch registry, its derived compatibility view, associated test files, a skill-closure baseline JSON, and two prose lines in `skills/design/SKILL.md`. None of the changed code touches gate disarmament conditions, pause snapshot allowlists, stale-result identity validation or fingerprint checks, run-log flush artifact completeness guards, committed artifact content, pre-terminal outcome labels, panel slot accounting, agent evidence backing, or ship recovery routing. All invariants remain unaffected by this change.

## Architectural guidelines

The registry value type widens from a 2-tuple to a 3-tuple by adding an inline `machine_stdout` boolean, which consolidates the three previously hand-maintained constants (`_DESIGN_LIFECYCLE_STDOUT_KEYS`, `_MACHINE_STDOUT_KEYS`, and the registry itself) into a single source of truth. The compatibility `_MACHINE_STDOUT_KEYS` view is now derived from the registry with a one-line comprehension and is explicitly documented as not to be hand-maintained, consistent with the principle of defining a convention once and having all selectors derive from it.

Design lifecycle verbs are repointed from the monolithic `design_lifecycle` module to focused submodules (`design_step0`, `design_step0_env`, `design_step1`, `design_router`, `design_session`, `design_terminal`, `design_step2b`, `design_step5b`, `design_step5c`, `design_step6`). Review pipeline verbs are similarly repointed from `review_pipeline` to `review_gather`, `review_dispatch_panel`, `review_collect`, `review_threshold`, `review_core_body`, and `review_prune`. Run-log verbs are repointed from `run_logs` to `run_log_commit` and `run_log_flush`. All consumers of the registry (the main dispatcher, the test suite, skill-structure pins, and the `skills/design/SKILL.md` prose lines that named module paths) are swept in the same change. The test mock for `review core` is updated from `review_pipeline` to `review_core_body`. A new structural assertion verifies that no registry entry still references `larch.design.design_lifecycle`, providing a mechanical fence against reintroduction. The `LEGACY_ASSERTION_LABEL_COUNT` ratchet is decremented by one to account for the removed now-obsolete `_DESIGN_LIFECYCLE_STDOUT_KEYS` extraction check. No guideline deviation is introduced by the changed lines.

## /implement run 503DCB7A-6FDF-49C0-B53B-B8C2CFA52E2B: pr-created

- **Outcome**: ✅ DONE
- **Duration**: 00:35:08
- **Cost**: 💰 TOTAL ~$27.68: Claude $14.35, Codex-5.6 $4.48, Codex-mini $0.01, Cursor $8.18 (Composer $4.70, Grok $3.48), Claude (subprocess) $0.66  |  Tokens: 41771k
- **Issue**: #7387: https://github.com/character-ai/larch/issues/7387
- **PR**: #7441: https://github.com/character-ai/larch/pull/7441
- **Plan review**: N/A
- **Plan coverage**: 7/7 firm headings; band: advisory; disposition: none; todos_left: 0
- **Difficulty**: predicted MODERATE; applied MODERATE
- **Dynamic archetypes**: ok (1)
- **Code review**: 1/2 accepted
- **Lines (PR diff)**: code +883/-961, larch-logs +617/-0
- **OOS filed**: 0
- **Exec issues**: 0
- **Warnings**: 41
- **Run logs**: `larch-logs/implement/503DCB7A-6FDF-49C0-B53B-B8C2CFA52E2B/`
- **Main agent model**: claude-sonnet-4-6
- **Effort**: max
- **Larch version**: 53.1.11

<!-- larch:run-summary v=1 -->
