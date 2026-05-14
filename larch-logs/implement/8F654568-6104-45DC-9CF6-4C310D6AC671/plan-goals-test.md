## Goal
Add Step 0 loud-fail warning for transcript snapshot + Step 18 fallback discovery

## Implementation Plan

Goal: Make session-transcript capture resilient when Step 0's source-file snapshot fails.

### Part 1 — skills/implement/SKILL.md Step 0: loud-fail warning

Change the `token-claude-source.sh` invocation block from silent best-effort to warn-on-failure:

Current (lines ~214-215):
  "${CLAUDE_PLUGIN_ROOT}/scripts/token-claude-source.sh" > "$IMPLEMENT_TMPDIR/claude-source.env" 2>/dev/null && \
      export LARCH_CLAUDE_SOURCE_FILE="$IMPLEMENT_TMPDIR/claude-source.env" || true

New (replace with):
  if "${CLAUDE_PLUGIN_ROOT}/scripts/token-claude-source.sh" \
          > "$IMPLEMENT_TMPDIR/claude-source.env" \
          2>"$IMPLEMENT_TMPDIR/claude-source-error.log"; then
      export LARCH_CLAUDE_SOURCE_FILE="$IMPLEMENT_TMPDIR/claude-source.env"
  else
      "${CLAUDE_PLUGIN_ROOT}/scripts/append-tool-failure.sh" \
          --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
          --site "Step 0" \
          --tool "token-claude-source.sh" \
          --exit-code "1" \
          --category Warnings \
          --output-file "$IMPLEMENT_TMPDIR/claude-source-error.log" \
          --redact || true
  fi

Also update the comment above (lines ~206-213) from "Best-effort: a snapshot failure leaves
the env unset and the resolver falls back to mtime." to reflect that the failure now emits
a Warnings entry.

### Part 2 — scripts/capture-session-transcript.sh: fallback discovery

After the existing source-file-missing check (line 77-78), add a fallback that probes
$HOME/.claude/projects for a transcript newer than $IMPLEMENT_TMPDIR before emitting
source-file-missing.

The fallback reads IMPLEMENT_TMPDIR from the environment (best-effort; if unset, skip).
Uses find with -newer "$IMPLEMENT_TMPDIR" on $HOME/.claude/projects/**/*.jsonl, picks
the most recently modified file, validates it's a regular file, and uses it as SOURCE_FILE.
Emits source-file-recovered-via-discovery on success.

New code (replace line 77-79 block with):
  if [ -z "$SOURCE_FILE" ] || [ ! -f "$SOURCE_FILE" ]; then
      # Fallback: probe standard Claude Code project locations for a recent transcript
      _recovered=""
      if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -d "$IMPLEMENT_TMPDIR" ] && [ -d "${HOME:-}/.claude/projects" ]; then
          _recovered=$(
              find "$HOME/.claude/projects" -name '*.jsonl' -newer "$IMPLEMENT_TMPDIR" 2>/dev/null \
                  | while IFS= read -r f; do
                      stat_mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || printf '0')
                      printf '%s\t%s\n' "$stat_mtime" "$f"
                  done \
                  | sort -rn \
                  | awk -F'\t' 'NR==1 { print $2 }'
          ) || true
      fi
      if [ -n "$_recovered" ] && [ -f "$_recovered" ]; then
          SOURCE_FILE="$_recovered"
          append_warning "source-file-recovered-via-discovery" \
              "Original snapshot was missing; recovered transcript via \$HOME/.claude/projects probe: $_recovered"
      else
          emit_status "source-file-missing" "Claude source file was empty or not a regular file; transcript capture skipped."
      fi
  fi

### Part 3 — scripts/test-capture-session-transcript.sh: extend with fallback cases

Add three new test cases after the existing cases:
1. "fallback-discovery" — SOURCE_FILE empty, but a .jsonl file exists newer than IMPLEMENT_TMPDIR → STATUS=captured (via fallback)
2. "fallback-discovery-recovered-status" — same setup, verify execution-issues log contains source-file-recovered-via-discovery
3. "fallback-no-match" — SOURCE_FILE empty, no .jsonl file newer than IMPLEMENT_TMPDIR → STATUS=source-file-missing

The test helper needs to accept an optional IMPLEMENT_TMPDIR env var to simulate the
fallback environment.

### Part 4 — scripts/capture-session-transcript.md: document new fallback status

Add source-file-recovered-via-discovery to the Statuses section.

### Files to change
1. skills/implement/SKILL.md — Step 0 token-claude-source.sh block (~lines 214-215 + comment)
2. scripts/capture-session-transcript.sh — replace lines 77-79 with fallback block
3. scripts/test-capture-session-transcript.sh — add 3 new test cases
4. scripts/capture-session-transcript.md — add new status to Statuses section


## Test plan
Run make test-capture-session-transcript and /relevant-checks after implementation.
