# skills/design/scripts/check-plan-size.sh

Mechanical plan-size detector for `/design` **Step 2b.5** (issue #2670). Threshold semantics are normatively documented in [`skills/design/references/flags.md`](../references/flags.md).

## argv

- `--design-tmpdir DIR` (required): design session root; default plan path is `$DIR/plan.txt`.
- `--plan-file PATH` (optional): override plan path (must still satisfy the trailer contract).

## Input contract

- Plan file MUST exist (otherwise exit **2**, `PLAN_SIZE_STATUS=missing-plan` on the contract stream — see **Exit codes**).
- The **final non-empty line** MUST match `emit-plan.sh` grammar: the literal prefix `diff_lines:` followed by **exactly one ASCII space** and then ASCII digits only to end-of-line — same rule as `skills/design/scripts/emit-plan.sh` (`case "$last_line" in diff_lines:\ *)` + digit validation). Tabs, multiple spaces after the colon, or other whitespace variants are rejected so the helper never accepts a trailer `emit-plan.sh` would refuse.
- **Plan body line count (`PLAN_LINES`)** is the number of physical lines **before** that final non-empty trailer line (blank lines count; the trailer line itself is excluded).

## Output contract (`emit_kv` on FD 3)

After `larch_quiet_init` from [`scripts/lib-quiet.sh`](../../../scripts/lib-quiet.md), machine-readable lines use `emit_kv` on **FD 3** (quiet session) or **stdout** when `LARCH_QUIET_DISABLE=1` — same capture pattern as `emit-plan.sh` / `test-emit-plan.sh`.

Emitted keys (exit **0** only):

| Key | Meaning |
|-----|---------|
| `PLAN_LINES` | Body lines excluding the trailer line |
| `DIFF_LINES` | Integer from the trailer |
| `HARD_TRIGGER_FIRED` | `true` or `false` |
| `TRIGGER_REASONS` | Comma-separated tokens in **fixed priority order** `plan-body-lines`, `diff-lines` (matches hard-threshold evaluation order in this helper — **not** lexicographic). Empty string when no hard threshold crossing. |

**Strict `>` boundary semantics** (800/1500 hard): equality does **not** trip — see `flags.md`.

## Exit codes

| rc | Meaning |
|----|---------|
| 0 | Valid plan; KV lines emitted as above |
| 2 | Missing plan file → `PLAN_SIZE_STATUS=missing-plan`; or missing/malformed trailer → `PLAN_SIZE_STATUS=missing-diff-lines` |
| 3 | Invocation / argv error (e.g. missing `--design-tmpdir`, unknown flag) — stderr only; **no** `PLAN_SIZE_STATUS` on the contract stream |

## Edit in sync

Update [`test-check-plan-size.sh`](test-check-plan-size.sh), [`test-check-plan-size.md`](test-check-plan-size.md), `Makefile` (`test-check-plan-size`), `skills/design/references/flags.md`, and `skills/design/SKILL.md` Step 2b.5 when changing thresholds or contracts.
