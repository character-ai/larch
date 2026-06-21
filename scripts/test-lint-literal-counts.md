# scripts/test-lint-literal-counts.sh

Black-box regression harness for `python3 python/cli.py lint literal-counts`, invoked with `--root "$TMPROOT"` against a `mktemp -d` fixture root.

The harness covers clean prose, violations, fenced-code exemptions, same-line allow pragmas, plural noun coverage, multi-file aggregation, BOM/CRLF normalization, non-UTF-8 internal errors, exit-code priority, fence close behavior, empty roots, git and non-git enumeration, symlink non-following, positional-argument rejection, untracked markdown coverage, and `larch-logs/` exclusion.

Wiring expectations are Makefile target `test-lint-literal-counts`, one harness shard entry, and an `agent-lint.toml` exclude for the `.sh` only. The primary contract is `python/lint_literal_counts.md`.
