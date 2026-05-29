# skills/design/scripts/check-plan-size.sh

Mechanical plan-size detector for `/design` **Step 2b.5** (issue #2670). Threshold semantics are normatively documented in [`skills/design/references/flags.md`](../references/flags.md).

## argv

- `--design-tmpdir DIR` (required): design session root; default plan path is `$DIR/plan.txt`.
- `--plan-file PATH` (optional): override plan path (must still satisfy the trailer contract).

## Input contract

Validates `$DESIGN_TMPDIR` via `larch_design_tmpdir_validate` after the required-arg check, before reading `$DESIGN_TMPDIR/plan.txt`; failure maps to argv exit 3 (rc 2 remains reserved for `PLAN_SIZE_STATUS=missing-*`).

- Plan file MUST exist (otherwise exit **2**, `PLAN_SIZE_STATUS=missing-plan` on the contract stream — see **Exit codes**).
- The **final non-empty line** MUST match `emit-plan.sh` grammar: the literal prefix `diff_lines:` followed by **exactly one ASCII space** and then ASCII digits only to end-of-line — same rule as `skills/design/scripts/emit-plan.sh` (`case "$last_line" in diff_lines:\ *)` + digit validation). Tabs, multiple spaces after the colon, or other whitespace variants are rejected so the helper never accepts a trailer `emit-plan.sh` would refuse.
- **Plan body line count (`PLAN_LINES`)** is the number of physical lines **before** that final non-empty trailer line (blank lines count; the trailer line itself is excluded), **minus** any recognized optional metadata trailer lines in the final contiguous metadata block immediately above `diff_lines:` (see below). Legacy plans without optional trailers keep the same `PLAN_LINES` as before.

### Optional metadata trailers (final block only)

Designers MAY append these lines in the **final contiguous metadata block** immediately **above** the required final `diff_lines: <N>` line (same strict grammar as `diff_lines:` — literal token, exactly one ASCII space, value to end-of-line):

| Trailer | Accepted full-line regex |
|---------|--------------------------|
| `diff_added: <N>` | `^diff_added: [0-9]+$` |
| `diff_deleted: <N>` | `^diff_deleted: [0-9]+$` |
| `mechanical_churn: true\|false` | `^mechanical_churn: (true\|false)$` |

Parsing rules:

- Scan upward from the line above `diff_lines:`; the block contains only strict trailer lines matching the regexes above.
- Stop at the first line above `diff_lines:` that is **not** one of those regexes (including blank lines).
- Malformed trailer-looking lines are treated as absent and stop the block.
- Duplicate keys inside the block: **last match in file order** wins (closest to `diff_lines:`).
- `mechanical_churn: false` is explicit no-downgrade; absent or malformed mechanical values normalize to `false`.

## Output contract (`emit_kv` on FD 3)

After `larch_quiet_init` from [`scripts/lib-quiet.sh`](../../../scripts/lib-quiet.md), machine-readable lines use `emit_kv` on **FD 3** (quiet session) or **stdout** when `LARCH_QUIET_DISABLE=1` — same capture pattern as `emit-plan.sh` / `test-emit-plan.sh`.

Emitted keys (exit **0** only):

| Key | Meaning |
|-----|---------|
| `PLAN_LINES` | Body lines excluding the final `diff_lines:` trailer and recognized optional metadata trailers above it |
| `DIFF_LINES` | Integer from the required final `diff_lines:` trailer |
| `DIFF_ADDED` | Integer from `diff_added:` when present in the final metadata block; empty string when absent |
| `DIFF_DELETED` | Integer from `diff_deleted:` when present; empty when absent (informational only — never a trigger) |
| `MECHANICAL_CHURN` | `true` or `false` from the final metadata block |
| `SOFT_ADVISORY` | `true` when `mechanical_churn: true` downgraded a diff-side hard trigger; `false` otherwise |
| `HARD_TRIGGER_FIRED` | `true` or `false` |
| `TRIGGER_REASONS` | Comma-separated tokens in **fixed priority order** `plan-body-lines`, then `diff-added` (new-style) or `diff-lines` (legacy). Empty string when no hard threshold crossing. When mechanical churn downgraded the diff trigger, no diff reason is added. |

**Threshold semantics** (strict `>` — equality does not trip):

- Plan body: `PLAN_LINES > 800`.
- Diff (new-style): `diff_added > 2000` when the `diff_added:` trailer is present in the final metadata block.
- Diff (legacy fallback): `diff_lines > 1500` when `diff_added` is absent.
- Deletions never trip; `diff_deleted` is informational only.
- `mechanical_churn: true` suppresses the diff hard trigger and sets `SOFT_ADVISORY=true` when a diff trigger would have fired; plan-body hard triggers are unaffected.

## Exit codes

| rc | Meaning |
|----|---------|
| 0 | Valid plan; KV lines emitted as above |
| 2 | Missing plan file → `PLAN_SIZE_STATUS=missing-plan`; or missing/malformed trailer → `PLAN_SIZE_STATUS=missing-diff-lines` |
| 3 | Invocation / argv error (e.g. missing `--design-tmpdir`, unknown flag) — stderr only; **no** `PLAN_SIZE_STATUS` on the contract stream |

## Edit in sync

Update [`test-check-plan-size.sh`](test-check-plan-size.sh), [`test-check-plan-size.md`](test-check-plan-size.md), `Makefile` (`test-check-plan-size`), `skills/design/references/flags.md`, and `skills/design/SKILL.md` Step 2b.5 when changing thresholds or contracts.
