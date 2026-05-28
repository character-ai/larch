# scripts/test-lint-gh-body-inline.sh - contract

Black-box regression harness for `scripts/lint-gh-body-inline.sh`. It invokes
`bash scripts/lint-gh-body-inline.sh --root "$TMPROOT"` against isolated
`mktemp -d` fixture roots and verifies clean file-backed callers pass, inline
`--body` and `--notes` fail, heredoc-substituted bodies fail, full-line comments
and same-line `# lint-gh-body-inline: ok <reason>` suppressions are ignored,
`--body-file` / `--notes-file` variants pass, Python argv-list calls are covered,
and tracked `larch-logs/` files are excluded from the git enumeration branch.

Bad fixtures are assembled at write time so the harness source itself contains
no command-like `gh` token on the same physical line as inline `--body` or
`--notes`. Keep that invariant when adding cases: store the option token in a
variable or otherwise split the generated fixture content across source
fragments. Do not add heredocs with literal forbidden command lines to this
harness.

Wiring expectations are Makefile target `test-lint-gh-body-inline` and one
`test-harnesses-N` shard entry. The primary contract is
`scripts/lint-gh-body-inline.md`; edit both files together when the linter
grammar or fixture policy changes.
