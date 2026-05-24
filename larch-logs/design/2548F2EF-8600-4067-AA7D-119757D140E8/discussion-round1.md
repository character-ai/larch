## Decision 1: Trivial tier validator scope
- **Question**: Should the validator run for the `--trivial` design tier?
- **Resolution**: Skip on `--trivial`. Validator runs only for `--simple` and `--hard`. Trivial tier already opts out of the reviewer panel; keep the lightweight path lightweight.
- **Source**: user (Step 1c Q1)

## Decision 2: `### UPDATED:` heading + new-flag listing
- **Question**: How should the validator handle plans that introduce a NEW flag on an EXISTING script?
- **Resolution**: Parser recognizes `### UPDATED: <script>` headings AND requires a `- Adds flag: --newflag` bullet (or similar declarative line) under the heading. The validator then silently allows that flag on that script only. More precise than operator-override-only; lower false-negative risk than blanket UPDATED-skip.
- **Source**: user (Step 1c Q2)

## Decision 3: Out of scope for /implement Preflight
- **Question**: Should the validator also gate `/implement`'s Preflight check?
- **Resolution**: Out of scope for this issue. Keep #2674 focused on `/design`. /implement Preflight has its own plan-adequacy check. A separate validator-in-Preflight follow-up can be filed if reviewers raise it.
- **Source**: user (Step 1c Q3)

## Decision 4: Missing `--help` fallback (graceful-skip)
- **Question**: What should Tier 2 do when a script has no `--help` arm? Codebase audit: 394 of 501 .sh scripts (79%) lack `--help`.
- **Resolution**: Graceful skip with logged note. Existence is still verified, but the flag-check is skipped per command and a `SKIPPED_FLAG_CHECK: <script> reason=no-help` note is written to `validate-plan-commands.log` (or equivalent) for forensics. Won't catch invented flags on those 394 scripts.
- **Companion action**: A separate issue (#2679) was filed via `/larch:issue --no-dedup` to overhaul all 394 `.sh` scripts to add `--help` arms. Independent of #2674; not a hard blocker.
- **Source**: user (Step 1d Q1) + companion filed issue #2679

## Decision 5: Validator scope (repo scripts only)
- **Question**: Which command paths does the validator process?
- **Resolution**: Repo scripts only — paths matching `scripts/`, `skills/*/scripts/`, or `.claude/skills/*/scripts/`. Skip system commands (gh, jq, awk, sed, grep, find, printf, sort, etc.) silently. System-command stability is out of /design's purview.
- **Source**: user (Step 1d Q2)

## Decision 6: Tier 2 → Tier 3 ordering (both run)
- **Question**: When a script is opted into Tier 3 (`dry-runnable-scripts.tsv`), how should Tier 2 and Tier 3 relate?
- **Resolution**: Tier 2 first, then Tier 3 (both must pass). Tier 2 is cheap and catches typos with a specific "flag-X unknown" error; Tier 3 catches semantic defects like path-containment. Defects from either layer surface to the AskUserQuestion fail handler.
- **Source**: user (Step 1d Q3)

## Decision 7: Parser scope (pipes + chains; skip heredoc bodies)
- **Question**: What command-composition scope should the v1 parser handle?
- **Resolution**: Split each fenced bash line on `|`, `&&`, `||`, `;` and validate each repo-script component independently (skipping system-command components per Decision 5). Treat heredoc bodies (`<<EOF ... EOF` and `<<'EOF' ... EOF`) as data — do not parse commands inside them. Subshells `$(...)` and process substitution `<(...)` are out of v1 scope.
- **Source**: user (Step 1d Q4)
