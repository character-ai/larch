# oos-disposition-gate.sh

Mechanical gate invoked from `/implement` Step 8+ after the Step 9a.1 `/issue` pipeline finishes and **before** `OOS_PENDING` is cleared. Prevents silent loss of voted-in, non-security OOS items: each accepted `### OOS_` block must either produce at least one filed GitHub issue URL (possibly combined into one issue) or be accounted for by `Inline-triage rule N:` lines in commit messages on the supplied `--commit-range`.

## Invocation

```text
oos-disposition-gate.sh [--fork-mode] [--repo-unavailable] \
  --accepted-files CSV --filed-urls-file PATH --commit-range RANGE
```

- `--accepted-files` — Comma-separated list of markdown paths (typically `$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md`, `oos-accepted-design.md`, `oos-accepted-review.md`). Missing paths are ignored; empty aggregate is a pass.
- `--filed-urls-file` — Path to the Step 9a.1 sentinel or sidecar listing created issues (e.g. `$IMPLEMENT_TMPDIR/oos-issues-created.md`). De-duplicated `https://…/issues/<n>` tokens are counted.
- `--commit-range` — Git revision range passed to `git log` (e.g. `$(git merge-base HEAD origin/main)..HEAD`). Used only when the gate is not skipped.
- `--fork-mode` / `--repo-unavailable` — When either is set, the gate **exits 0 immediately** (no file reads, no `git log`).

## Exit codes

| Code | Meaning |
|------|--------|
| 0 | Skipped (fork / repo-unavailable), or nothing to check (`non_security_oos == 0`), or disposition satisfied (`filed > 0` or `inline_triage_lines >= non_security_oos`). |
| 1 | Disposition gap: `non_security_oos > 0` and `filed == 0` and `inline < non_security_oos`. |
| 2 | Bad arguments, invalid `commit-range`, or not inside a git work tree when a scan is required. |

## Counting rules

- **non_security_oos** — Number of `### OOS_` blocks across all accepted files whose body (from header through the next `###` heading or EOF) does **not** match `focus-area[[:space:]]*=[[:space:]]*security` on any line (security-routed entries are excluded from the obligation set).
- **filed_urls** — Count of unique `https://…/issues/<digits>` substrings in `--filed-urls-file`.
- **inline** — Count of lines in `git log --format=%B RANGE` containing the literal substring `Inline-triage rule` (per-entry breadcrumbs from implementer commit messages).

## Consumer

Orchestrator (`skills/implement/SKILL.md` Step 8+ OOS checkpoint): on exit 1, log via `append-tool-failure.sh` and **do not** clear `OOS_PENDING` or write the `run-statistics` batch until the gap is resolved.

Harness: `skills/implement/scripts/test-oos-disposition-gate.sh`.
