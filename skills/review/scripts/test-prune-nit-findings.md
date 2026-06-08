# test-prune-nit-findings.sh

Regression harness for `prune-nit-findings.sh`.

## Primary contract

See `prune-nit-findings.md`.

## Coverage

| Test | What it checks |
|---|---|
| T1 | Nit blocks moved to `oos.md` with `[OUT_OF_SCOPE]` prefix; important/latent untouched |
| T2 | Remaining in-scope `FINDING_N` ids renumbered from 1 |
| T3 | `LARCH_PRUNE_NITS_DISABLED=1` is a no-op; files unchanged, `STATUS=disabled` |
| T4 | Input with no `FINDING_N` blocks handled gracefully; `STATUS=ok`, `PRUNED_COUNT=0` |
| T5 | No nits → `PRUNED_COUNT=0`; OOS file left empty; explicit negative for important/latent |
| T6 | Plan mode (`--input-mode plan`): moved nit block appended as `OOS_N` format in `findings-oos.md`; pre-existing OOS blocks preserved |

## Makefile

Target: `test-prune-nit-findings` in shard `test-harnesses-10`.
