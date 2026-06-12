# test-render-review-phase-detail.sh

Regression harness for `scripts/render-review-phase-detail.sh` (issue #3774). See
`scripts/render-review-phase-detail.md` for the full contract.

Covers: per-round table counts (suggestions made/accepted, OOS proposed/accepted,
reviewers launched) and the Total row; round dirs without `round-meta.json` are
skipped; top-reviewers attribution by `vendor/archetype` (panel-manifest map plus
basename-derive fallback); failed-slot counting from `round-meta.json` `.collector`
`STATUS != OK` blocks; per-round Time from `timing-ledger.tsv` round rows and the
`—` em dash when no ledger is present; the single-source dollar-line invariant (no
`$` / `💰` in output, cost cells are `—`); the singular `reviewer` schema fallback;
the no-completed-rounds case (`No review rounds completed.`, exit 0), including
in-flight round directories without completed metadata; usage errors (exit 2);
stdout mode; Mermaid reviewer timing Gantt charts, `--no-gantt` suppression,
vendor rows selected by overlap regardless of skill column, sanitized labels,
deterministic ids, the 25-task cap, and malformed timing row tolerance;
per-round VENDOR cost from token-ledger timestamp windows (in-window priced,
out-of-window excluded, empty window = `$0.00`); skill-window contamination
regression (table Time/Cost ignore other-skill `type=round` rows); Gantt
preservation regression (vendor rows join by unfiltered round overlap); and a
regression assertion that a forced `python/report_tokens_cost.py` subprocess
failure surfaces a labeled `FAIL:` diagnostic rather than a bare non-zero abort
(#3781).

## Generated Mermaid validation

After Gantt-producing cases, `assert_mermaid_valid` runs
`python3 python/cli.py lint mermaid-fences` on the rendered output when a Mermaid
fence is present. The helper prechecks for an existing Mermaid CLI at
`mermaid-lint/node_modules/.bin/mmdc` or `mmdc` on `PATH` and does **not** run
`npm ci`, install Mermaid packages, or set up Chromium itself.

- **Local runs** may skip generated Mermaid validation when no existing CLI is
  available: the harness prints one visible
  `SKIP: Mermaid CLI unavailable; Mermaid parse validation skipped` line and
  continues. Set `LARCH_MERMAID_REQUIRED=1` to hard-fail locally instead.
- **GitHub Actions CI** (`GITHUB_ACTIONS` set) treats validation as required: the
  harness fails when the CLI is absent or when `lint mermaid-fences` exits `2`.
  CI installs the Mermaid toolchain on the `test-harnesses` shard that hosts this
  harness (`make test-harnesses-12`) before the harness runs; that install stays
  outside this script.
- Exit `2` from `lint mermaid-fences` means unavailable tooling in optional mode
  (same skip breadcrumb) and a real failure in required mode.

The separate `lint-mermaid` CI job validates **changed committed** Markdown fences
only; it does not cover generated harness output from this renderer fixture.

Makefile target `test-render-review-phase-detail`; shard `test-harnesses-12`.
