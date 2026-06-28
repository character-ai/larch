# Force Mode

**Consumer**: `/implement` Preflight, loaded by the main agent only on the `--force` / `-f` path.

**Contract**: Define the downgraded Preflight gates, structured bypass log grammar, and carve-outs for force mode. The item 4 plan-adequacy audit skip remains inline in `skills/implement/SKILL.md` and is not a downgraded gate.

**When to load**: MANDATORY when `force_requested=true`, before applying force-specific Preflight behavior. Do not load when `force_requested=false`.

## Force-specific Preflight behavior

When `force_requested=true`, Preflight may downgrade exactly three gates from hard refusal to warn-and-proceed: missing issue-body `larch:plan` (including a title-as-plan fallback when the body is empty), malformed extracted-plan fallback, and the `missing-designed-prefix` admission check.

The item 4 audit skip is **not** a downgraded gate and writes **no** bypass-log entry; no `AUDIT=refuse` result exists on the force path, so there is nothing to downgrade.

Force mode does **not** bypass explicit zero-review provenance such as `review_status=panel-init-failed`, `review_status=panel-skipped`, or `rounds_completed=0`.

Each triggered bypass MUST print a loud bold warning and append **one line** to `$PREFLIGHT_TMPDIR/force-bypass.log` with the exact grammar `BYPASS kind=<lowercase-token> issue=<number>` (example: `BYPASS kind=missing-plan issue=<N>`).

The log is invalid when it is empty, blank-only, or names an `issue=` value other than the current target issue.

Canonical `kind=` tokens for current `/implement` force bypasses are:

- `missing-plan` for `BLOCK_PRESENT=false` (including the title-as-plan fallback when the body is empty).
- `malformed-plan` for malformed extracted-plan fallback.
- `missing-designed-prefix` for the `ADMISSION_RESULT=missing-designed-prefix` admission carve-out.

Step 0 bootstrap consumes that log into `$IMPLEMENT_TMPDIR/execution-issues.md` only once for the current force run, even after dirty-tree resume.

Force mode bypasses the `missing-designed-prefix` admission check (the `[DESIGNED]` title prefix requirement) but does **not** bypass other admission blocks (`managed-prefix` for active lifecycle prefixes such as `[IMPLEMENTING]`/`[DONE]`/`[STALLED]`, `has-blockers`, `audit-report-label`, `report-title`) or semantic materiality / stale-plan notice.
