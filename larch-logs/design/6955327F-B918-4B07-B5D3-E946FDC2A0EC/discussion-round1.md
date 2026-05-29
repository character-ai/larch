## Decision 1: Claude tier must be tool-capable (not embed-only)
- **Question**: When the Codex→Cursor→Claude waterfall reaches the Claude tier, should it stay embed-only (`claude --print` with the diff pasted into the prompt) or read the diff from disk?
- **Resolution**: Make the Claude tier tool-capable too — even a Claude-only host reads the diff from disk via the Read tool. Embed-only is not acceptable as the final design.
- **Source**: user

## Decision 2: Also trim the review diff (exclude run-log artifacts)
- **Question**: Stay strictly scoped to the 3 scout changes, or also fix the root cause (huge diff from committed `larch-logs/**`)?
- **Resolution**: Also change how the review diff is constructed so the underlying diff stays small — exclude run-log artifacts (`larch-logs/**`). This is in scope for this design.
- **Source**: user

## Decision 3: Diff-trim point is gather-branch-context.sh
- **Question**: Where is the review diff built, and what is the blast radius of trimming it?
- **Resolution**: `scripts/gather-branch-context.sh` is the single review-diff builder (`git diff -U20 MERGE_BASE...HEAD > diff.txt`, plus `--name-only > file-list.txt`). Its only caller is `skills/review/scripts/gather-context.sh`, used by diff-mode code review (`/implement` Step 5, `/review --diff`). `/design` plan review is description-mode and does NOT use it. Trimming `larch-logs/**` there affects diff-mode reviewers AND the scout (both consume diff.txt), which is the intended fix.
- **Source**: codebase

## Decision 4: `claude --print` is tool-capable (issue premise corrected)
- **Question**: Is the issue's claim that "`--print` mode has no tools" correct? (Issue Note asked to re-verify.)
- **Resolution**: Incorrect. `claude --help` confirms `--print` supports `--allowedTools` / `--disallowedTools` / `--permission-mode`. A tool-capable Claude tier is achievable by passing a read-only tool allowlist (`Read`/`Grep`/`Glob`) plus a read-only permission mode and instructing the prompt to Read the diff path — not a rewrite. The current scout's prompt-embedding is a launcher choice (`launch-claude-subprocess.sh` runs `claude --print < prompt` with no tool flags), not a CLI limitation.
- **Source**: codebase

## Decision 5: Tool-capable Claude must stay read-only (hard constraint)
- **Question**: What must not break when Claude gains tool access?
- **Resolution**: The Claude tier must remain read-only — allowlist read tools only (`Read`/`Grep`/`Glob`) and/or disallow `Edit`/`Write`/mutating `Bash`. Codex/Cursor already enforce read-only via `--sandbox read-only`. Verify the exact `claude --print` invocation per `.claude/rules/verify-external-tool-invocations.md`.
- **Source**: codebase / constraint

## Decision 6: Fail-open invariant preserved (hard constraint)
- **Question**: What behavior must be preserved regardless of tier/availability?
- **Resolution**: The scout stays non-fatal. Any tier failure (timeout, parse error, tool unavailable, oversized) → write `{"archetypes":[]}` and a non-`ok` `SCOUT_STATUS`; static reviewer dispatch and round count must be unchanged. This is the acceptance "no regression" clause.
- **Source**: issue acceptance / codebase

## Decision 7: Change applies to both modes via the shared scout script
- **Question**: Does this affect `/design` as well as `/implement`/`/review`?
- **Resolution**: Yes. `scout-dynamic-archetypes.sh` is shared. The waterfall + tool-capable read + 256 KB-gate removal land in that one script and flow to both callers: diff mode (`skills/review/scripts/dispatch-panel.sh`, code review) and description mode (`skills/design/scripts/scout-plan-archetypes-wrapper.sh`, plan review). The 256 KB gate only bites in diff mode (large diffs); description-mode inputs are small. The `--prompt-override-file` mechanism (used by /design plan scout) must keep working.
- **Source**: codebase

Decisions resolved: 7 (2 from user, 5 from codebase).
