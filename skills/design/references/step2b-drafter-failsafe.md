# Step 2b drafter missing-row fail-safe

**Consumer**: `/design` Step 2b drafter subprocess routing when the drafter reports success but authoritative postplan rows are missing.

**Contract**: missing-row and sidecar recovery for drafter success without wrapper-owned `POSTPLAN_RC=` / `POSTPLAN_STATUS=` rows, including authoritative result-env checks, `_postplan_rc` / `_postplan_status` binding, retained terminal postplan fence limits, and fail-closed diagnostics.

**When to load**: mandatory immediately before the zero-exit missing-row fail-safe branch when `DRAFTER_STATUS=succeeded` is present but wrapper-owned `POSTPLAN_RC=` or `POSTPLAN_STATUS=` rows are absent, or when the drafter fence exited zero with missing wrapper rows. Do not load this file for the non-zero or fatal-postplan abort branch, which remains inline in `SKILL.md`.

---

## Missing-row and sidecar recovery

If the drafter fence exited zero with missing postplan rows, inspect `$DESIGN_TMPDIR/.design-postplan-emit-result.env` (never `source` it) and `$DESIGN_TMPDIR/.completed/step-2b.5` before the retained terminal postplan fence runs. When `.completed/step-2b.5` exists and the sidecar shows `POSTPLAN_EMIT_STATUS=ok`, bind `_postplan_rc` and `_postplan_status` from the sidecar (`VALIDATE_STATUS=defects-found` → `_postplan_rc=10` / `validate-failed`; `PLAN_SIZE_STATUS=plan-size-trigger` → `_postplan_rc=12` / `plan-size-trigger`; `PLAN_SIZE_STATUS=partition-requested` → `_postplan_rc=13` / `partition-requested`; otherwise `_postplan_rc=0` / `ok`), do not run a second prompt-side postplan fence, and continue with the existing rc routing above. `python/cli.py design step2b-postplan --write-completion-only` writes `.completed/step-2b.5` without running `design-postplan-emit.sh`; treat that sentinel alone as non-authoritative for this branch. Fail closed with diagnostics when the sidecar is absent, unreadable, or conflicts with `.completed/step-2b.5` (for example step-2b.5 present without `POSTPLAN_EMIT_STATUS=ok`). The missing-row fail-safe may run the retained terminal postplan fence at most once when the drafter fence exited zero. The retained terminal postplan fail-safe may run only when the drafter fence exited zero, wrapper-owned postplan rows are missing, and no authoritative sidecar plus `step-2b.5` pair exists. `.completed/step-2b` can be written by `--write-step2b-completion-only` mode without successful postplan rows. Route from that fail-safe postplan result.
