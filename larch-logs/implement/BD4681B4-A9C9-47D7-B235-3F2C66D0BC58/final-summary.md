## Review Phase Detail

| Round | Suggestions | Accepted | OOS proposed | OOS fileable | Time | Cost | Reviewers |
|--:|--:|--:|--:|--:|:--|--:|--:|
| 1 | 4 | 3 | 0 | 0 | 8m 48s | $10.07 | 8 |
| **Total (round-sum)** | **4** | **3** | **0** | **0** | **8m 48s** | **$10.07** | **8** |

_The Total (round-sum) row adds up the per-round Suggestions and Accepted: when the review loop re-raises the same finding across rounds, that finding is counted once per round, so the round-sum can exceed the number of distinct findings. Top reviewers counts per-round accepted-point scores the same way._

_Finding decomposition (canonical, scope-aware): round 1: 9 finding(s) = 4 in-scope (voted; matches the headline X/Y accepted) + 5 out-of-scope. The Suggestions and OOS columns above count findings by finding id (raw per-finding) and can disagree with this scope-aware split when findings are reclassified out-of-scope after voting; round-meta.json records both raw (`tally`) and canonical (`tally_canonical`) counts so downstream joins do not contradict._

### Round 1 reviewer timing

```
Round 1 reviewer timing  ·  window 0:00-8:48 (528s)
                                           0:00                                 8:48
                                          ┌─────────────────────────────────────────┐
codex/edge-cases                          │█████                                    │  59s
codex/testing                             │█████                                    │  66s
codex/dyn-dyn-wire-fixture-boundary-codex │██████                                   │  69s
codex/correctness                         │█████████                                │ 117s
cursor/edge-cases                         │███████████                              │ 138s
cursor/testing                            │█████████████                            │ 160s
cursor/correctness                        │████████████████                         │ 207s
cursor/dyn-dyn-wire-fixture-boundary      │███████████████████                      │ 245s
reviewer-collect                          │                   █                     │   2s
aggregator                                │                   ██                    │  13s
voter-dispatch-prep                       │                     ████████            │ 107s
codex/pragmatism-vote                     │                             ████        │  56s
codex/plan-fidelity-vote                  │                             █████       │  64s
codex/validity-vote                       │                             ██████      │  84s
codex/apply                               │                                    ████ │  59s
                                          └─────────────────────────────────────────┘
```

**Top reviewers** (by per-round accepted-point score, whole run):
1. codex/correctness: 2
2. cursor/testing: 1

**Reviewer slot failures**: 0

## Exec Issues and Warnings
Exec Issues (0):
Warnings (37):
  1. Step 7a.1 — 1 explicit plan-listed path(s) untouched by the working-tree delta before dispatcher commit. First 10: python/tests/design/test_design_log_publish_flow.py
  2. ## Summary
  3. The diff centralises design and plan wire-format test fixtures into a new `python/tests/support/design_wire.py` support module, updates multiple test files to use the new builders, and extracts `ru...
  4. ## Deviations
  5. ### G-Py-9 — two unannotated locals whose types are not obvious from the RHS
  6. `lines` in `diff_lines_trailer`: (`python/tests/support/design_wire.py`):
  7. ```python
  8. lines = compose_trailer_lines(values)
  9. return "\n".join(lines) + "\n"
  10. ```
  11. `compose_trailer_lines` returns `tuple[str, ...]` (confirmed from `python/larch/design/plan_grammar.py:258`). The return type is not derivable from the call expression alone; a reader must look up...
  12. `payload` in `run_params_text`: (`python/tests/support/session.py`):
  13. payload = dict(_RUN_PARAMS_SCHEMA_V3)
  14. if overrides:
  15. payload.update(overrides)
  16. `_RUN_PARAMS_SCHEMA_V3` is declared as `dict[str, object]`, so `payload` should carry the same annotation. `dict(mapping)` copies the mapping's type, but the specific type here (`dict[str, object]`...
  17. Both deviations are in test-support code and are minor in practice, but neither qualifies for the G-Py-9 deviate clause ("the type is obvious from the RHS") because both require following a callee...
  18. The diff introduces a new test-support module (`python/tests/support/design_wire.py`) that centralises design and plan wire-format fixture builders, extracts `run_params_text` from `session.py`, an...
  19. ## Deviation
  20. ### G-Cfg-1 — plan heading kind wire literals re-listed rather than built from the canonical prior set
  21. `plan_grammar.py` already defines the canonical heading-kind set as:
  22. HeadingKind = Literal["NEW", "UPDATED", "REWRITTEN", "MAY_UPDATE"] # line 14
  23. FIRM_HEADING_KINDS: Final[frozenset[HeadingKind]] = frozenset({"NEW", "UPDATED", "REWRITTEN"}) # line 27
  24. `design_wire.py` introduces a standalone type alias and a runtime guard that re-list the same literals independently:
  25. `PlanHeadingKind = Literal["NEW", "UPDATED"]` at diff line 20 — a new `Literal` type built from inline string literals rather than derived from `HeadingKind` or `FIRM_HEADING_KINDS` via import.
  26. `if kind not in ("NEW", "UPDATED"):` at diff line 970 — the runtime guard in `plan_body` also re-lists the two values inline rather than using a frozenset constant drawn from the canonical source.
  27. G-Cfg-1 guidance: "build token sets from prior sets rather than re-listing." The `PlanHeadingKind` type alias and the `plan_body` guard should import `HeadingKind` (or the firm-heading frozenset) f...
  28. The G-Cfg-1 deviate clause ("a module-private constant used at one call site with no cross-module contract") does not apply: `PlanHeadingKind` is exported, used in the public `PlanSection` type ali...
  29. The diff introduces `python/tests/support/design_wire.py`, a test-support module centralising design and plan wire-format fixture builders, and migrates all test call sites. The broad picture is he...
  30. `python/larch/design/plan_grammar.py` is the authoritative owner of the heading-kind vocabulary:
  31. `HeadingKind = Literal["NEW", "UPDATED", "REWRITTEN", "MAY_UPDATE"]` (line 14)
  32. `FIRM_HEADING_KINDS: Final[frozenset[HeadingKind]] = frozenset({"NEW", "UPDATED", "REWRITTEN"})` (line 27)
  33. The new `design_wire.py` introduces a standalone type alias and a derived runtime guard that re-list the same literals independently:
  34. `PlanHeadingKind = Literal["NEW", "UPDATED"]` — a new `Literal` type spelled from inline string literals rather than derived from `HeadingKind` or narrowed from `FIRM_HEADING_KINDS` via import.
  35. `_PLAN_HEADING_KINDS: frozenset[HeadingKind] = frozenset(get_args(PlanHeadingKind))` — the runtime guard frozenset is built from the re-listed type, not from `FIRM_HEADING_KINDS`.
  36. G-Cfg-1 guidance: "build token sets from prior sets rather than re-listing." A future grammar addition to `plan_grammar.py` would require a matching update to `design_wire.py`; a mismatch would be...
  37. Exception: Python's type system does not support narrowing a `Literal` type from another without re-listing the values. `PlanHeadingKind = Literal["NEW", "UPDATED"]` is the single canonical definit...

## Architectural guidelines

## Summary

The diff introduces `python/tests/support/design_wire.py`, a test-support module centralising design and plan wire-format fixture builders, and migrates all test call sites. The broad picture is healthy: `write_result_env` routes through `atomic_write` from `larch.io` (aligned with G-IO-1), validates env values for embedded newlines, CR, and NUL before writing (G-IO-2), rejects symlink targets at write time (G-Sec-4), every `# noqa` suppression carries an inline reason (G-Py-11), and function signatures are fully typed.

## Deviation

### G-Cfg-1 — plan heading kind wire literals re-listed rather than built from the canonical prior set

`python/larch/design/plan_grammar.py` is the authoritative owner of the heading-kind vocabulary:

- `HeadingKind = Literal["NEW", "UPDATED", "REWRITTEN", "MAY_UPDATE"]` (line 14)
- `FIRM_HEADING_KINDS: Final[frozenset[HeadingKind]] = frozenset({"NEW", "UPDATED", "REWRITTEN"})` (line 27)

The new `design_wire.py` introduces a standalone type alias and a derived runtime guard that re-list the same literals independently:

- `PlanHeadingKind = Literal["NEW", "UPDATED"]` — a new `Literal` type spelled from inline string literals rather than derived from `HeadingKind` or narrowed from `FIRM_HEADING_KINDS` via import.
- `_PLAN_HEADING_KINDS: frozenset[HeadingKind] = frozenset(get_args(PlanHeadingKind))` — the runtime guard frozenset is built from the re-listed type, not from `FIRM_HEADING_KINDS`.

G-Cfg-1 guidance: "build token sets from prior sets rather than re-listing." A future grammar addition to `plan_grammar.py` would require a matching update to `design_wire.py`; a mismatch would be silent. The G-Cfg-1 deviate clause ("a module-private constant used at one call site with no cross-module contract") does not apply: `PlanHeadingKind` is exported, used in the public `PlanSection` type alias, and consumed by multiple test files that import `plan_body`.

Exception: Python's type system does not support narrowing a `Literal` type from another without re-listing the values. `PlanHeadingKind = Literal["NEW", "UPDATED"]` is the single canonical definition within this module; the runtime set `_PLAN_HEADING_KINDS` is derived from it via `get_args()` (not re-listed). The builder intentionally supports a strict subset (NEW, UPDATED) smaller than `FIRM_HEADING_KINDS` (NEW, UPDATED, REWRITTEN), so no intersection expression avoids listing the two values. This deviation is in test-support code only; the production grammar remains the canonical owner. (author: main-agent, date: 2026-07-14)

## /implement run BD4681B4-A9C9-47D7-B235-3F2C66D0BC58: shipping

- **Outcome**: shipping
- **Duration**: 00:28:31
- **Cost**: 💰 TOTAL ~$18.53: Claude $4.61, Codex-5.6 $5.24, Codex-mini $0.02, Cursor $8.46 (Composer $4.81, Grok $3.65), Claude (subprocess) $0.20  |  Tokens: 26705k
- **Issue**: #7026: https://github.com/character-ai/larch/issues/7026
- **Plan review**: N/A
- **Plan coverage**: 7/8 firm headings; band: advisory; disposition: none; todos_left: 0
- **Difficulty**: predicted MODERATE; applied MODERATE
- **Dynamic archetypes**: ok (1)
- **Code review**: 3/4 accepted
- **Lines (PR diff)**: N/A
- **OOS filed**: 0
- **Exec issues**: 0
- **Warnings**: 37
- **Run logs**: `larch-logs/implement/BD4681B4-A9C9-47D7-B235-3F2C66D0BC58/`
- **Main agent model**: claude-sonnet-4-6
- **Effort**: max
- **Larch version**: 53.1.2

<!-- larch:run-summary v=1 -->
