# prune-nit-findings.sh

## Purpose

Moves in-scope `nit`-severity findings to the OOS track before voting.
Nit findings are not dropped — they become `[OUT_OF_SCOPE]` proposals that
voters can still accept for filing. Judges never spend a vote deciding a nit.

Severity match reuses the exact pattern from `aggregate-findings.sh:321`:
`^- \*\*Severity\*\*:\s*(important|latent|nit)\s*$` (case-insensitive).

**Code path** (called after `aggregate-findings.sh`, before voter dispatch):
adds `[OUT_OF_SCOPE]` to nit block titles in `findings.md`. Blocks stay in
the ballot; `tally-code-votes.sh` routes them to `oos.md` automatically.

**Plan path** (called after the in-scope/OOS split, before aggregation):
removes nit `FINDING_N` blocks from `findings-in-scope.md` and appends them
as `OOS_N` blocks to `findings-oos.md` for the design ballot.

## CLI

```
prune-nit-findings.sh --findings-file PATH [--oos-file PATH] [--input-mode code|plan]
```

| Flag | Default | Description |
|---|---|---|
| `--findings-file PATH` | required | Findings file to modify in place |
| `--oos-file PATH` | optional | OOS file; required for `--input-mode plan` |
| `--input-mode code\|plan` | `code` | `code`: modify title in `findings.md`; `plan`: remove from findings, add as `OOS_N` |

## Stdout (KV)

| Key | Values | Meaning |
|---|---|---|
| `PRUNED_COUNT` | `<n>` | Number of nit findings moved to OOS |
| `INSCOPE_REMAINING` | `<n>` | Number of in-scope findings after pruning |
| `STATUS` | `ok` / `skipped` / `disabled` | Outcome |

## Behavior

- **`STATUS=ok`**: `PRUNED_COUNT` nit blocks processed. For code mode: titles
  prefixed with `[OUT_OF_SCOPE]` in-place; `FINDING_N` ids unchanged (stable
  for voter reference); tally routes them to `oos.md`. For plan mode: removed
  from `--findings-file`, appended as `OOS_N` to `--oos-file`; remaining
  `FINDING_N` ids renumbered from 1. Writes are atomic (tempfile + rename).
- **`STATUS=skipped`**: parse or I/O error — both files left unchanged, exit 0.
  Never blocks the round.
- **`STATUS=disabled`**: `LARCH_PRUNE_NITS_DISABLED=1` is set — no-op
  pass-through, mirroring `LARCH_AGGREGATOR_DISABLED`.

## Callers

- `skills/review/scripts/review-core.sh` — after `aggregate-findings.sh`, before
  voter dispatch (code path, `--input-mode code`, `--oos-file` not passed).
  Override via `REVIEW_CORE_PRUNE_NITS_SH`.
- `skills/design/scripts/plan-review-loop.sh` — after in-scope/OOS split, before
  `aggregate-findings.sh` (plan path, `--input-mode plan`).
  Override via `LARCH_PLAN_REVIEW_PRUNE_NITS_SH`.

## Invariants

- Never exits non-zero (fail open contract).
- Never modifies files when `STATUS=skipped` or `STATUS=disabled`.
- `latent` and `important` findings are intentionally untouched by this script
  (option b: latent findings stay in-scope at vote time; `tally-code-votes.sh`
  and `tally-plan-review.sh` re-route non-accepted latent blocks to `oos.md`
  after voting, preserving the in-PR-fix path for genuine-correctness latent
  findings that do pass the in-scope gate).
- Pruned blocks in `--oos-file` retain all original fields including
  `- **Severity**: nit`.

## Harness

`skills/review/scripts/test-prune-nit-findings.sh` — Makefile target
`test-prune-nit-findings`.

## Edit-in-sync

Changes to block-splitting, severity parsing, or output KV format must be
reflected in the test harness and in this sibling `.md`.
