## Review Phase Detail

| Round | Suggestions | Accepted | OOS proposed | OOS fileable | Time | Cost | Reviewers |
|--:|--:|--:|--:|--:|:--|--:|--:|
| 1 | 4 | 3 | 1 | 0 | 2h 44m 43s | $7.33 | 8 |
| **Total (round-sum)** | **4** | **3** | **1** | **0** | **2h 44m 43s** | **$7.33** | **8** |

_The Total (round-sum) row adds up the per-round Suggestions and Accepted: when the review loop re-raises the same finding across rounds, that finding is counted once per round, so the round-sum can exceed the number of distinct findings. Top reviewers counts per-round accepted-point scores the same way._

_Finding decomposition (canonical, scope-aware): round 1: 8 finding(s) = 4 in-scope (voted; matches the headline X/Y accepted) + 4 out-of-scope (1 OOS proposed, 0 OOS fileable). The Suggestions and OOS columns above count findings by finding id (raw per-finding) and can disagree with this scope-aware split when findings are reclassified out-of-scope after voting; round-meta.json records both raw (`tally`) and canonical (`tally_canonical`) counts so downstream joins do not contradict._

### Round 1 reviewer timing

```
Round 1 reviewer timing  ·  window 0:00-164:43 (9883s)
                                          0:00                               164:43
                                         ┌─────────────────────────────────────────┐
codex/dyn-dyn-tmpdir-lint-baseline-codex │█                                        │   67s
codex/testing                            │█                                        │   79s
codex/correctness                        │█                                        │   90s
cursor/testing                           │█                                        │  137s
cursor/edge-cases                        │█                                        │  150s
codex/edge-cases                         │█                                        │   95s
reviewer-collect                         │          █                              │    1s
aggregator                               │          ████████████████████           │ 4861s
aggregator (via fallback)                │                              █          │  338s
aggregator (via fallback)                │                               █████████ │ 2133s
voter-dispatch-prep                      │                                        █│  124s
codex/plan-fidelity-vote                 │                                        █│   38s
codex/pragmatism-vote                    │                                        █│   61s
codex/validity-vote                      │                                        █│   81s
                                         └─────────────────────────────────────────┘
```

**Top reviewers** (by per-round accepted-point score, whole run):
1. codex/correctness: 3
2. codex/edge-cases: 2
3. cursor/testing: 1

**Reviewer slot failures**: 1
- cursor/dyn-dyn-tmpdir-lint-baseline: 1

## Exec Issues and Warnings
Exec Issues (2):
  1. Step review Step 2: codex-review failed (exit 1, unknown)
  2. Step review Step 2: cursor-review failed (exit 1, unknown)
Warnings (1):
  1. code-review panel (round 1): dynamic reviewer slot drop/failure detected (failed=1, dropped=1, stragglers=2); review continued with the remaining panel output.

## Architectural invariants

The changed code does not touch any invariant-governed surface. The new lint module (`lint_tmpdir_arg_env_fallback.py`), the `bgjob/cli.py` env-fallback addition, the `dispatch_step2.py` env-var constant fix, the mechanical refactors in `scope_disposition.py`, `file_oos.py`, `admission.py`, and `_corpus.py`, and the associated tests and docs updates are all confined to lint enforcement, a runtime env-fallback improvement, and code-quality cleanup. None of these changes touch gate disarmament inputs, pause snapshot contents or resume guards, step-result staleness validation, run-log flush or commit paths, outcome label writes, panel slot accounting, machine-parsed agent verdict machinery, or ship recovery routing. All invariants hold.

## Architectural guidelines

The changed code conforms to the applicable architectural guidelines. No G-* identifier is triggered.

The diff implements a class-level fix across six production sites (`bgjob/cli.py`, `dispatch_step2.py`, `scope_disposition.py`, `file_oos.py`, `state/_corpus.py`, `state/admission.py`) and mechanizes enforcement via a new `lint_tmpdir_arg_env_fallback` lint module, which is consistent with the fix-the-class and prefer-mechanical-enforcement directions. The new module is registered in `cli.py` via a `main(argv)->int` entry, satisfying the uniform CLI surface contract. The bare `"IMPLEMENT_TMPDIR"` string literal in `dispatch_step2.py` is replaced with `config.ENV_IMPLEMENT_TMPDIR`, and the corresponding grandfathered baseline entries in `env-via-config-constant-baseline.json` are pruned. The new module manifest entry carries `host_decision: "new-module-justified"`, names the two nearest candidate hosts (`lint_tempfile_dir`, `lint_env_via_config_constant`), explains why each is insufficient in shape and baseline schema, and references the commissioning issue. The sole grandfathered site in `python/tmpdir-arg-env-fallback-baseline.json` carries an explicit documented reason. New tests in `test_bgjob_cli.py` and the comprehensive `test_lint_tmpdir_arg_env_fallback.py` cover the changed recovery-path behavior and lint engine contract. The docs/linting.md prose and Makefile `.PHONY` and regen targets are updated in the same change as the new lint surface.

## /implement run DDC05324-43BD-41AC-A311-48D0074C7A4C: shipping

- **Outcome**: shipping
- **Duration**: 03:14:25
- **Cost**: 💰 TOTAL ~$17.49: Claude $3.35, Codex-5.6 $4.90, Codex-mini $0.00, Cursor $4.97 (Composer $1.98, Grok $2.99), Claude (subprocess) $4.27  |  Tokens: 20254k
- **Issue**: #7297: https://github.com/character-ai/larch/issues/7297
- **Plan review**: N/A
- **Plan coverage**: 14/14 firm headings; band: advisory; disposition: none; todos_left: 0
- **Difficulty**: predicted MODERATE; applied MODERATE
- **Dynamic archetypes**: ok (1)
- **Code review**: 3/4 accepted
- **Lines (PR diff)**: N/A
- **OOS filed**: 0
- **Exec issues**: 2
- **Warnings**: 1
- **Run logs**: `larch-logs/implement/DDC05324-43BD-41AC-A311-48D0074C7A4C/`
- **Main agent model**: claude-sonnet-4-6
- **Effort**: max
- **Larch version**: 53.1.14

<!-- larch:run-summary v=1 -->
