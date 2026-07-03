# test-cache-key-discipline.sh

**Purpose**: Structural regression guard for prompt cache-key discipline. It catches obvious non-stable shell content in prompt-bearing files and requires legitimate dynamic prompt inputs to be annotated with `# intentionally non-stable:`.

**Patterns checked**:
- `$(date`
- `$(uuidgen`
- `$(openssl rand`
- bare `$$`
- `$RANDOM`
- per-session prompt path variables in implementer launcher `PROMPT` blocks
- per-session diff/scope paths rendered by `python/cli.py render specialist`
- review prompt construction delegated through `python/larch/review/review_pipeline.py` and launcher/render helpers
- unstable shell-style tokens in Python prompt construction surfaces:
  - `python/larch/implement/checks_lint_fix.py`
  - `python/larch/review/coder_runner.py`
  - `python/larch/review/review_dispatch_panel.py`
  - `python/larch/review/round_runner.py`

**Scope**: External-tool prompt construction surfaces only. Runtime timing, logging, temp-file, and process-management shell code is intentionally out of scope unless it is inside a launcher `PROMPT` block, an audited prompt-bearing Markdown file, or one of the explicitly listed Python prompt construction files.

**Primary callers**: `make test-cache-key-discipline`, plus `make test-harnesses-3`.

**Invariants**:
- Test scripts are not scanned as prompt sources.
- The guard is intentionally structural and conservative; it is not a full parser for every heredoc in the repository.
- New prompt-construction files that interpolate per-session paths must be added to this harness and this document together.

**Edit-in-sync**: When adding a new prompt-rendering script, launcher prompt block, or inline external-tool prompt in a skill, update this harness and this sibling document in the same PR.
