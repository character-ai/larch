# test-prune-nit-findings.sh

Regression harness for `prune-nit-findings.sh`.

## Primary contract

See `prune-nit-findings.md`.

## Coverage

| Test | What it checks |
|---|---|
| T1 | Code mode: nit blocks get `[OUT_OF_SCOPE]` prefix added to title; blocks stay in `findings.md`; important/latent untouched |
| T2 | Code mode: `FINDING_N` ids unchanged (no renumbering — stable for voter reference) |
| T3 | `LARCH_PRUNE_NITS_DISABLED=1` is a no-op; files unchanged, `STATUS=disabled` |
| T4 | Input with no `FINDING_N` blocks handled gracefully; `STATUS=ok`, `PRUNED_COUNT=0` |
| T5 | No nits → `PRUNED_COUNT=0`; no `[OUT_OF_SCOPE]` added; explicit negative for important/latent |
| T6 | Plan mode (`--input-mode plan`): nit `FINDING_N` removed, converted to `OOS_N` in `findings-oos.md`; pre-existing OOS blocks preserved |
| T7 | Code mode: `[OUT_OF_SCOPE]` prefix appears at title position after `FINDING_N:` heading |

## Makefile

Target: `test-prune-nit-findings` in shard `test-harnesses-10`.
