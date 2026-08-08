# Recon and Design Phase

Read `phase-common.md` in this directory in full before acting.

The spawn prompt supplies `REPOSITORY`, `UMBRELLA`, `LEAF`, `REPO_ROOT`, and `HANDOFF_ROOT`. Require positive numeric issue IDs, exact `OWNER/REPO` syntax, the current working directory as `REPO_ROOT`, and `HANDOFF_ROOT=$SESSION_TMPDIR`.

Run the standalone driver in prepare mode before any repository or issue read:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" complete-umbrella ship-leaf \
  --mode prepare \
  --repository "<REPOSITORY>" \
  --repo-root "$PWD" \
  --handoff-root "$SESSION_TMPDIR" \
  --umbrella "<UMBRELLA>" \
  --leaf "<LEAF>"
```

Require `SHIP_STATUS=prepared`. This verified mutation adds `[IMPLEMENTING]` to the leaf title and changes no other title bytes.

Then:

1. Read `AGENTS.md`, `ARCHITECTURAL_INVARIANTS.md`, and `ARCHITECTURAL_GUIDELINES.md` when present. Follow their repository rules.
2. Fetch the full leaf and umbrella issue bodies into `leaf-issue.md` and `umbrella-issue.md` below `$SESSION_TMPDIR`. Redirect the `gh issue view` output to those files. Do not return issue text in tool output.
3. Read both issue files in full. Inspect relevant precedent pull requests and the target source. Use no more than five precedent PRs.
4. Inspect only enough repository context to identify the implementation. Batch independent `Read`, `Grep`, and `Glob` calls.
5. Write `$SESSION_TMPDIR/design-brief.md`. Include requirements, relevant architectural rules, file-and-line anchors, exact code and test surfaces, generated or projected companions, stale callers to sweep, local checks, and a parity plan. If a differential harness is needed, require an assertion that proves a success path executed.

Keep the brief concrete. Do not copy issue bodies into it. The next phase must be able to implement from the brief and `leaf-issue.md` without broad exploration.

End with:

```text
PHASE_STATUS=complete
HANDOFF_FILE=<absolute path to design-brief.md>
```
