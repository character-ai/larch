# skills/design/scripts/check-plan-size.sh

Mechanical plan-size detector for `/design` **Step 2b.5** (issue #2670). Threshold semantics are normatively documented in [`skills/design/references/flags.md`](../references/flags.md).

## argv

- `--design-tmpdir DIR` (required): design session root; default plan path is `$DIR/plan.txt`.
- `--plan-file PATH` (optional): override plan path (must still satisfy the trailer contract).

## Input contract

- Plan file MUST exist (otherwise exit **2**, `PLAN_SIZE_STATUS=missing-plan` on the contract stream — see **Exit codes**).
- The **final non-empty line** MUST match `emit-plan.sh` grammar: `diff_lines:` + whitespace + digits only — same rule as `skills/design/scripts/emit-plan.sh` (awk `NF` trailer selection). This keeps the helper aligned with `ACTION=EMIT_PLAN` validation so the two never disagree on trailer presence.
- **Plan body line count (`PLAN_LINES`)** is the number of physical lines **before** that final non-empty trailer line (blank lines count; the trailer line itself is excluded).
- **Files count (`FILES_COUNT`)** counts lines matching the scout-tolerant heading regex (at least one whitespace after `###` before the keyword):

  `^###[[:space:]]+(NEW|UPDATED|REWRITTEN)[[:space:]]*:`

## Output contract (`emit_kv` on FD 3)

After `larch_quiet_init` from [`scripts/lib-quiet.sh`](../../../scripts/lib-quiet.md), machine-readable lines use `emit_kv` on **FD 3** (quiet session) or **stdout** when `LARCH_QUIET_DISABLE=1` — same capture pattern as `emit-plan.sh` / `test-emit-plan.sh`.

Emitted keys (exit **0** only):

| Key | Meaning |
|-----|---------|
| `PLAN_LINES` | Body lines excluding the trailer line |
| `DIFF_LINES` | Integer from the trailer |
| `FILES_COUNT` | Heading count per regex above |
| `SOFT_TRIGGER_FIRED` | `true` or `false` |
| `HARD_TRIGGER_FIRED` | `true` or `false` |
| `TRIGGER_REASONS` | Comma-separated tokens in **fixed priority order** `plan-body-lines`, `diff-lines`, `files-count` (matches threshold evaluation order in this helper — **not** lexicographic). Empty string when no threshold crossing. The orchestrator may append display-only context such as `trigger=partition-flag` for `--partition`; this helper does **not** emit that token. |

**Strict `>` boundary semantics** (250/600/8 soft; 800/1500 hard): equality does **not** trip — see `flags.md`.

**Hard precedence**: when any hard threshold trips, `HARD_TRIGGER_FIRED=true` and `SOFT_TRIGGER_FIRED=false` even if soft thresholds would also have fired. `TRIGGER_REASONS` still lists every crossed dimension in fixed-priority order.

## Exit codes

| rc | Meaning |
|----|---------|
| 0 | Valid plan; KV lines emitted as above |
| 2 | Missing plan file → `PLAN_SIZE_STATUS=missing-plan`; or missing/malformed trailer → `PLAN_SIZE_STATUS=missing-diff-lines` |
| 3 | Invocation / argv error (e.g. missing `--design-tmpdir`, unknown flag) — stderr only; **no** `PLAN_SIZE_STATUS` on the contract stream |

## Edit in sync

Update [`test-check-plan-size.sh`](test-check-plan-size.sh), [`test-check-plan-size.md`](test-check-plan-size.md), `Makefile` (`test-check-plan-size`), `skills/design/references/flags.md`, and `skills/design/SKILL.md` Step 2b.5 when changing thresholds or contracts.
