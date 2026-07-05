# scripts/test-research-structure.sh — contract

`scripts/test-research-structure.sh` is the structural regression guard for
the `/research` skill under the simplified fixed-shape topology
(4 Codex-first research lanes + 3-reviewer validation panel,
`--no-issue` as the only flag).

## What it pins

1. `skills/research/SKILL.md` exists.
2. The 4 reference files exist: `references/research-phase.md`,
   `references/validation-phase.md`, `references/citation-validation-phase.md`,
   `references/critique-loop-phase.md`.
3. `references/adjudication-phase.md` does NOT exist (removed under the
   simplified shape).
4. Each reference is named on a `MANDATORY: READ ENTIRE FILE` line in
   `SKILL.md`, and that same line carries reciprocal `Do NOT load <other>`
   guards naming the OTHER three references on the same line (line-scoped,
   presence-not-order).
5. Each `references/*.md` opens with the `**Consumer**:` /
   `**Contract**:` / `**When to load**:` triplet in the first 20 lines.
6. The four named angle-prompt identifiers
   (`RESEARCH_PROMPT_ARCH` / `_EDGE` / `_EXT` / `_SEC`) appear in
   `research-phase.md`.
7. Reviewer XML wrapper tags (`<reviewer_research_question>`,
   `<reviewer_research_findings>`) appear in `validation-phase.md`.
8. `SKILL.md` carries the fail-closed unknown-flag guard heading and the
   `unsupported flag` abort message.
9. `SKILL.md`'s recovery hint enumerates each removed-flag CATEGORY:
   `scale`, `plan`, `interactive`, `adjudicate`, `token-budget`,
   `keep-sidecar`, `verbosity`. (Categories rather than literal `--foo`
   tokens to avoid tripping the unknown-flag guard the prose is documenting.)
10. `SKILL.md` surfaces `--no-issue` (the only supported flag).
11. `research-phase.md` pins `python/cli.py research run-planner` in §1.1.b and the §1.1.c edit loop.
12. `citation-validation-phase.md` and `SKILL.md` pin `python/cli.py research validate-citations`.
13. `research-phase.md` pins `python/cli.py research banner` at Step 1.5 and `SKILL.md` pins `python/cli.py research render-findings-batch` at Step 3.
14. `research-phase.md` pins terminal `STATUS=NOT_SUBSTANTIVE` handling:
    no Claude replacement, no narrative synthesis input, and no
    non-substantive retry artifacts.
15. `research-phase.md` pins synthesis-header ownership and the
    `[lane dropped: collector NOT_SUBSTANTIVE]` exclusion marker.
16. `SKILL.md` frontmatter passes the `research` token to
    `scripts/deny-edit-write.sh`.
17. `SKILL.md` creates `research-$PPID` only after the degraded-tools gate and
    before the first `Write` need.
18. `SKILL.md` aborts loudly when activation fails.
19. `SKILL.md` and `research-phase.md` remove
    `"$RESEARCH_DENY_ACTIVE_SENTINEL"` on cleanup and controlled abort paths.
20. `SKILL.md` distinguishes inactive fail-open activation from active
    fail-closed path enforcement.

## Wiring

- `make test-research-structure` is assigned to exactly one `test-harnesses-N`
  shard via the Makefile target.
- `agent-lint.toml` exempts this harness's literal pins from agent-lint scans.

## Edit-in-sync rules

When editing `skills/research/SKILL.md` (MANDATORY directives, flag surface,
unknown-flag-guard recovery hint, or activation sentinel lifecycle) or any of
the four reference files (header triplet, angle prompts, reviewer wrappers, or
abort cleanup), update this harness if a pinned literal moves.
