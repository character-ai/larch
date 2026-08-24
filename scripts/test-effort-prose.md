# test-effort-prose.sh

**Purpose**: Guard prompt source files against reintroducing hardcoded max-effort prose. Reasoning effort for external reviewers is owned by launcher mechanisms (`--with-effort` for Codex and Cursor max-mode / suffix handling in the Cursor launcher), not embedded prompt bodies.

**Coverage**: Greps the reviewer, sketch, voter, judge, dialectic, and specialist-renderer prompt sources for both supported prose variants: `Work at your maximum reasoning effort level.` and `Work at maximum reasoning effort level.` Launcher-owned model and effort handling is intentionally outside this prompt-source file list.

**Makefile wiring**: `make test-effort-prose`; included in `make test-harnesses`.

**Edit-in-sync**: Update this harness when a new prompt-source file starts carrying reviewer, voter, judge, sketch, or dialectic prompt text.
