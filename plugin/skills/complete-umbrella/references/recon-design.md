# Recon and Design Phase

**Consumer**: The first fresh general-purpose Agent spawned by the `/complete-umbrella` leaf orchestrator.

**Contract**: Adopt the leaf lifecycle, gather bounded requirements and repository evidence, and write the implementation-ready design brief without returning large content.

**When to load**: **MANDATORY: READ ENTIRE FILE** only for the primary recon-design phase.

Read `phase-common.md` in this directory in full before acting.

The spawn prompt supplies `REPOSITORY`, `UMBRELLA`, `LEAF`, `REPO_ROOT`, and `HANDOFF_ROOT`. Require positive numeric issue IDs, exact `OWNER/REPO` syntax, the current working directory as `REPO_ROOT`, and `HANDOFF_ROOT=$SESSION_TMPDIR`.

The prepare driver is the managed-chief admission gate, so do not run it until
this phase has written a valid durable plan. Then:

1. Read `AGENTS.md`, `ARCHITECTURAL_INVARIANTS.md`, and `ARCHITECTURAL_GUIDELINES.md` when present. Follow their repository rules.
2. Fetch the full leaf and umbrella issue bodies into `leaf-issue.md` and `umbrella-issue.md` below `$SESSION_TMPDIR`. Redirect the `gh issue view` output to those files. Do not return issue text in tool output.
3. Read both issue files in full. Inspect relevant precedent pull requests and the target source. Use no more than five precedent PRs.
4. Inspect only enough repository context to identify the implementation. Batch independent `Read`, `Grep`, and `Glob` calls.
5. Write `$SESSION_TMPDIR/design-brief.md`. Include requirements, relevant architectural rules, file-and-line anchors, exact code and test surfaces, generated or projected companions, stale callers to sweep, local checks, and a parity plan. If a differential harness is needed, require an assertion that proves a success path executed.
6. Write `$SESSION_TMPDIR/plan.md` as a concrete executable plan. It must satisfy the issue-anchored M1/M2 contract: firm file headings, ordered steps, closed ownership decisions, acceptance, breaking-change/migration treatment, and a terminal `diff_lines:` line. It is a new plan, not evidence of an approval that did not occur.
7. Publish exactly that file through the canonical wire owner:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" named-block write \
  --marker plan \
  --issue "<LEAF>" \
  --content-file "$SESSION_TMPDIR/plan.md" \
  --repo "<REPOSITORY>"
```

8. Run the standalone driver in prepare mode:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" complete-umbrella ship-leaf \
  --mode prepare \
  --repository "<REPOSITORY>" \
  --repo-root "$PWD" \
  --handoff-root "$SESSION_TMPDIR" \
  --umbrella "<UMBRELLA>" \
  --leaf "<LEAF>"
```

Require `SHIP_STATUS=prepared`. For an umbrella that declares a Chief umbrella,
this verifies the live plan before it adds `[IMPLEMENTING]`; it changes no other
title bytes. Do not echo `SHIP_STATUS` or any prepare-driver output in your final
response.

Keep the brief concrete. Do not copy issue bodies into it. The next phase must be able to implement from the brief and `leaf-issue.md` without broad exploration.

End with only:

```text
PHASE_STATUS=complete
HANDOFF_FILE=design-brief.md
```
