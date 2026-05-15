# test-cache-key-discipline.sh

**Purpose**: Structural regression guard for prompt cache-key discipline. It catches obvious non-stable shell content in prompt-bearing files and requires legitimate dynamic prompt inputs to be annotated with `# intentionally non-stable:`.

**Patterns checked**:
- `$(date`
- `$(uuidgen`
- `$(openssl rand`
- bare `$$`
- `$RANDOM`
- per-session prompt path variables in implementer launcher `PROMPT` blocks
- per-session diff/scope paths rendered by `render-specialist-prompt.sh`
- review prompt construction delegated through `skills/review/scripts/dispatch-panel.sh` and launcher/render helpers

**Scope**: External-tool prompt construction surfaces only. Runtime timing, logging, temp-file, and process-management shell code is intentionally out of scope unless it is inside a launcher `PROMPT` block or an audited prompt-bearing Markdown file.

**Annotation rule**: Legitimate dynamic content must have `# intentionally non-stable:` within the three preceding lines. Use this only when the content is per-session by design and is passed to Codex, Cursor, or Gemini rather than the Claude API system prompt.

**Primary callers**: `make test-cache-key-discipline`, plus `make test-harnesses-7`.

**Invariants**:
- Test scripts are not scanned as prompt sources.
- The guard is intentionally structural and conservative; it is not a full parser for every heredoc in the repository.
- New prompt-construction files that interpolate per-session paths must be added to this harness.

**Edit-in-sync**: When adding a new prompt-rendering script, launcher prompt block, or inline external-tool prompt in a skill, update this harness and this sibling document in the same PR.
