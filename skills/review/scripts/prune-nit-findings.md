# prune-nit-findings.sh

## Purpose

Moves in-scope `nit`-severity findings from the ballot track to the OOS track
before the voting round. Nit findings are not dropped — they become
`[OUT_OF_SCOPE]` proposals (code path) or `OOS_N` proposals (plan path) that
voters can still accept for filing. Judges never spend a vote deciding a nit.

Severity match reuses the exact pattern from `aggregate-findings.sh:321`:
`^- \*\*Severity\*\*:\s*(important|latent|nit)\s*$` (case-insensitive).

## CLI

```
prune-nit-findings.sh --findings-file PATH --oos-file PATH [--input-mode code|plan]
```

| Flag | Default | Description |
|---|---|---|
| `--findings-file PATH` | required | In-scope findings file to prune in place |
| `--oos-file PATH` | required | OOS file to append pruned findings to |
| `--input-mode code\|plan` | `code` | `code`: `oos.md` uses `FINDING_N: [OUT_OF_SCOPE] …`; `plan`: `findings-oos.md` uses `OOS_N:` format |

## Stdout (KV)

| Key | Values | Meaning |
|---|---|---|
| `PRUNED_COUNT` | `<n>` | Number of nit findings moved to OOS |
| `INSCOPE_REMAINING` | `<n>` | Number of in-scope findings after pruning |
| `STATUS` | `ok` / `skipped` / `disabled` | Outcome |

## Behavior

- **`STATUS=ok`**: `PRUNED_COUNT` nit blocks removed from `--findings-file`;
  appended to `--oos-file`. Remaining in-scope `FINDING_N` ids renumbered from 1
  (matching `aggregate-findings.sh` id-rewriting behavior). Writes to
  `--findings-file` are atomic (tempfile + rename).
- **`STATUS=skipped`**: parse or I/O error — both files left unchanged, exit 0.
  Never blocks the round.
- **`STATUS=disabled`**: `LARCH_PRUNE_NITS_DISABLED=1` is set — no-op
  pass-through, mirroring `LARCH_AGGREGATOR_DISABLED`.

## Callers

- `skills/review/scripts/review-core.sh` — after `collect-findings.sh`, before
  `aggregate-findings.sh` (code path, `--input-mode code`).
  Override via `REVIEW_CORE_PRUNE_NITS_SH`.
- `skills/design/scripts/plan-review-loop.sh` — after in-scope/OOS split, before
  `aggregate-findings.sh` (plan path, `--input-mode plan`).
  Override via `LARCH_PLAN_REVIEW_PRUNE_NITS_SH`.

## Invariants

- Never exits non-zero (fail open contract).
- Never modifies files when `STATUS=skipped` or `STATUS=disabled`.
- `latent` and `important` findings are untouched.
- Pruned blocks in `--oos-file` retain all original fields including
  `- **Severity**: nit`.

## Harness

`skills/review/scripts/test-prune-nit-findings.sh` — Makefile target
`test-prune-nit-findings`.

## Edit-in-sync

Changes to block-splitting, severity parsing, or output KV format must be
reflected in the test harness and in this sibling `.md`.
