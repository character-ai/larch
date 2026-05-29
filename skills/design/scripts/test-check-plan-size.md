# skills/design/scripts/test-check-plan-size.sh

Offline regression harness for [`check-plan-size.sh`](check-plan-size.sh). Captures the `emit_kv` contract stream with `LARCH_QUIET_DISABLE=1` (same pattern as [`test-emit-plan.sh`](test-emit-plan.sh)).

## Cases exercised

1. No triggers — medium plan and moderate `diff_lines`; asserts the retired optional-prompt and file-count keys are not emitted.
2. Plan-body hard — 801 body lines.
3. Diff-lines hard — `diff_lines` past 1500.
4. Hard plan with former soft dimensions — only hard reasons are emitted.
5. Ten file headings — no retired file-count key emission and no trigger.
6. Missing plan file — exit 2, `PLAN_SIZE_STATUS=missing-plan`.
7. Unknown argv / missing `--design-tmpdir` — exit **3**, no `PLAN_SIZE_STATUS` lines.
8. Malformed trailer — exit 2, `PLAN_SIZE_STATUS=missing-diff-lines`.
9. Hard boundary equalities — 800 body lines and `diff_lines: 1500` do not trip.
10. Zero headings — valid plan with no `set -e` regression.
11. Multiple `diff_lines:` lines — rejects when final non-empty line is not the trailer; accepts when trailer is last non-empty line.
12. Strict `diff_lines:` trailer — tab or extra ASCII spaces after the colon fail closed (`missing-diff-lines`), matching `emit-plan.sh`.
13. `--plan-file` override — non-default path still parses and emits hard-only keys.
14. Optional metadata excluded from `PLAN_LINES` (800 body + three optional trailers).
15. `diff_added` boundary at 2000/2001.
16. Additions override legacy total churn when `diff_added` present.
17. Deletions exempt (`diff_deleted` informational only).
18. Mechanical advisory (new-style `diff_added` + `mechanical_churn: true`).
19. Mechanical advisory legacy (`diff_lines` + `mechanical_churn: true`, no `diff_added`).
20. Plan-body hard trigger unaffected by mechanical downgrade.
21. `mechanical_churn: false` explicit — no downgrade.
22. Malformed optional trailers (tab / double space) — legacy fallback; four new keys always emitted.
23. Spoof resistance — body prose ignored; final metadata block wins.
24. Blank line stops metadata scan.
25. Duplicate optional keys — last match closest to `diff_lines:` wins for values; every strict optional trailer line in the block is subtracted from `PLAN_LINES`.
26. Combined plan-body hard + downgraded diff (`SOFT_ADVISORY=true`).
27. 801 raw body lines minus optional metadata avoids plan-body hard trigger (`PLAN_LINES=798`).
28. `mechanical_churn` under already-soft `diff_added` does not set `SOFT_ADVISORY`.
29. `diff_deleted`-only legacy fallback (no `diff_added`).
30. 800 body + duplicate `diff_added` lines — no spurious `plan-body-lines` hard trigger.
31. 799 body + three `diff_added` lines — full metadata line subtraction (`PLAN_LINES=799`).
32. Leading-zero trailer digits — `10#` decimal coercion for threshold comparisons; invalid `diff_added: 08` / `09` rejected as metadata (legacy `diff_lines` path).
33. `diff_deleted`-only legacy hard trigger — high `diff_deleted` with `diff_lines > 1500` and no `diff_added` fires `HARD_TRIGGER_FIRED=true`, `TRIGGER_REASONS=diff-lines`.

Cases 14–32 call `assert_always_emitted_keys` on every `run_ok` exit 0 path.

## Run

```bash
bash skills/design/scripts/test-check-plan-size.sh
# or
make test-check-plan-size
```
