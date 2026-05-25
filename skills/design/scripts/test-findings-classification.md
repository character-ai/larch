# test-findings-classification.sh

Offline regression harness for `findings-classification.tsv`.

It exercises the shared parser (`scripts/parse-judge-vote-and-rating.sh`) and the `/design` tally emitter (`skills/design/scripts/tally-plan-review.sh`) with per-case temporary fixtures. Covered contracts include complete three-judge ratings, position-agnostic axis tokens, fixed `v1=Claude` / `v2=Codex` / `v3=Cursor` slot mapping, missing-slot empty cells, partial-axis uncertainty, zero-judge fallback rows, empty-ballot header-only output, rerun overwrite, OOS rows, trailing rating compatibility with `vote_for_id`, phase-style voter paths with explicit `--voter SLOT:PATH`, malformed vote tokens, lowercase-only axis values, duplicate id last-line-wins, reviewer cell sanitization, and deterministic numeric row order.

Makefile target: `make test-findings-classification`.
