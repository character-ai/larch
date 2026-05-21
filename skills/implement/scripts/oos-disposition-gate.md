# oos-disposition-gate.sh

Mechanical gate invoked from `/implement` Step 8+ after the Step 9a.1 `/issue` pipeline finishes and **before** `OOS_PENDING` is cleared. Prevents silent loss of voted-in, non-security OOS items: each accepted `### OOS_` block must either produce at least one filed GitHub issue URL (possibly combined into one issue), be accounted for by `Inline-triage rule N:` lines in commit messages on the supplied `--commit-range`, or appear under an explicit `oos-issues` NDJSON Rejected sub-block with structured `### OOS_` / `- **OOS_<n>` markers (see Counting rules).

## Invocation

```text
oos-disposition-gate.sh [--fork-mode] [--repo-unavailable] \
  --accepted-files CSV --filed-urls-file PATH \
  [--oos-issues-ndjson PATH] --commit-range RANGE
```

- `--accepted-files` — Comma-separated list of markdown paths (typically `$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md`, `oos-accepted-design.md`, `oos-accepted-review.md`). Missing paths are ignored; empty aggregate is a pass.
- `--filed-urls-file` — Path to the Step 9a.1 sentinel or sidecar listing created issues (e.g. `$IMPLEMENT_TMPDIR/oos-issues-created.md`). De-duplicated `https://…/issues/<n>` tokens are counted and **unioned** with URL tokens from `--oos-issues-ndjson` when that path is supplied.
- `--oos-issues-ndjson` — Optional path to the staged `oos-issues.ndjson` batch for the run. When present, unique issue URLs from this file participate in the filed-URL count, and rejected-sub-block bodies contribute `rejected_oos_markers` (see below).
- `--commit-range` — Git revision range passed to `git log` (e.g. `$(git merge-base HEAD origin/main)..HEAD`, or `origin/main..HEAD` when merge-base is empty but `origin/main` resolves). Used only when the gate is not skipped.
- `--fork-mode` / `--repo-unavailable` — When either is set, the gate **exits 0 immediately** (no file reads, no `git log`).

## Exit codes

| Code | Meaning |
|------|--------|
| 0 | Skipped (fork / repo-unavailable), or nothing to check (`non_security_oos == 0`), or disposition satisfied (`filed > 0` or `inline_triage_lines >= non_security_oos` or `rejected_oos_markers >= non_security_oos`). |
| 1 | Disposition gap: `non_security_oos > 0` and `filed == 0` and `inline < non_security_oos` and `rejected_oos_markers < non_security_oos`. |
| 2 | Bad arguments, invalid `commit-range`, or not inside a git work tree when a scan is required. |

## Counting rules

- **non_security_oos** — Parsed by `oos-non-security-block-count.awk` across all accepted files: count of `### OOS_` blocks whose body does **not** contain a dedicated `- **focus-area**:` field line whose value begins with `security` (security-routed entries are excluded). Prose such as `focus-area = security` inside a `**Description**` line does **not** mark a block as security-routed.
- **filed_urls** — Count of unique `https://…/issues/<digits>` substrings in the union of `--filed-urls-file` and `--oos-issues-ndjson` (when provided).
- **inline** — Count of lines in `git log --format=%B RANGE` containing the literal substring `Inline-triage rule` (heuristic aggregate — any such line counts toward the total; there is no strict per-OOS index linkage).
- **rejected_oos_markers** — For each JSON line in `--oos-issues-ndjson` whose `body` contains a Rejected heading (`## Rejected` / `Rejected / Out-of-Scope`), count `### OOS_` and `- **OOS_<digit>` lines only under the rejected section (after the first `## Rejected` heading, until the next `##` heading that is not itself a Rejected heading). Summed across all matching records.

## Consumer

Orchestrator (`skills/implement/SKILL.md` Step 8+ OOS checkpoint): on exit **1**, log via `append-tool-failure.sh` with `--site step-8-oos-checkpoint` and **do not** clear `OOS_PENDING` or write the `run-statistics` batch until the disposition gap is resolved. On exit **2**, log with `--site step-8-oos-checkpoint-validation` — treat as invalid range / git context / arguments (not a disposition-count gap).

Harness: `skills/implement/scripts/test-oos-disposition-gate.sh`.
