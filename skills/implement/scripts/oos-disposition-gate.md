# oos-disposition-gate.sh

Mechanical gate invoked from `/implement` Step 8+ after the Step 9a.1 `/issue` pipeline finishes and **before** `OOS_PENDING` is cleared. Prevents silent loss of voted-in, non-security OOS items: each accepted `### OOS_` block must either produce at least one filed GitHub issue URL (possibly combined into one issue), be accounted for by `Inline-triage rule N:` lines in commit messages on the supplied `--commit-range`, or appear under an explicit `oos-issues` NDJSON Rejected sub-block with structured `### OOS_` / `- **OOS_<n>` markers (see Counting rules).

## Invocation

```text
oos-disposition-gate.sh [--fork-mode] [--repo-unavailable] \
  --accepted-files CSV (--filed-urls-file PATH)* (--filed-urls-strict-file PATH)* \
  [--oos-issues-ndjson PATH] --commit-range RANGE
```

- `--accepted-files` — Comma-separated list of markdown paths (typically `$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md`, `oos-accepted-design.md`, `oos-accepted-review.md`). Missing paths are ignored; empty aggregate is a pass.
- `--filed-urls-file` — Repeatable **loose** counter. Each path is a Step 9a.1 sentinel, `/design` `oos-issues-created.md`, or any sidecar where issue URLs appear as plain tokens (grep scans the whole file). De-duplicated `https://…/issues/<n>` tokens are counted across the **union** of all `--filed-urls-file` arguments and **unioned** with URL tokens from `--oos-issues-ndjson` when that path is supplied.
- `--filed-urls-strict-file` — Repeatable **strict** counter. Counts only lines matching a dedicated `- **Filed URL**` markdown list item with optional whitespace before the colon whose value is a GitHub issue URL (same host rules as the loose counter). Incidental issue URLs elsewhere in the file (for example inside a reviewer `**Description**`) are ignored. Unique strict URLs are de-duplicated across all strict-file arguments. The gate’s `filed_urls` total is **`count_filed_urls_union_files(loose…, ndjson)` + `count_filed_url_field_lines(strict…)`** (double-counting a URL that appears in both a loose and a strict input is allowed — the pass criterion is disjunctive; see Exit codes, not `filed_urls >= non_security_oos`).
- `--oos-issues-ndjson` — Optional path to the staged `oos-issues.ndjson` batch for the run. When present, unique issue URLs from this file participate in the filed-URL count, and rejected-sub-block bodies contribute `rejected_oos_markers` (see below).
- `--commit-range` — Git revision range passed to `git log` (e.g. `$(git merge-base HEAD origin/main)..HEAD`, or `origin/main..HEAD` when merge-base is empty but `origin/main` resolves). Used only when the gate is not skipped.
- `--fork-mode` / `--repo-unavailable` — When either is set, the gate **exits 0 immediately** (no file reads, no `git log`).

## Exit codes

| Code | Meaning |
|------|--------|
| 0 | Skipped (fork / repo-unavailable), or nothing to check (`non_security_oos == 0`), or disposition satisfied: **`filed_urls > 0`** *or* **`inline_triage_lines >= non_security_oos`** *or* **`rejected_oos_markers >= non_security_oos`** (implemented in `oos-disposition-gate.sh`; the first branch is *not* `filed_urls >= non_security_oos`). |
| 1 | Disposition gap: `non_security_oos > 0` and **`filed_urls == 0`** (aggregate `filed` in `oos-disposition-gate.sh`: loose + strict URL counts) and `inline < non_security_oos` and `rejected_oos_markers < non_security_oos`. |
| 2 | Bad arguments, invalid `commit-range`, not inside a git work tree when a scan is required, `--accepted-files` path exists but is not a readable regular file, or `oos-issues.ndjson` lists filed issue URLs while no CSV path resolves to a regular file (misconfiguration). |

## Counting rules

- **non_security_oos**: parsed by `${CLAUDE_PLUGIN_ROOT}/python/larch/issue/file_oos.py` (`_count_non_security_markdown` / `count_non_security`) across all accepted files. It counts `### OOS_` blocks, plus legacy tagged `### FINDING_N: [OUT_OF_SCOPE]` headers where the `[OUT_OF_SCOPE]` literal is required for `FINDING` headers. Bare `### FINDING_N:` stays uncounted. Coder-skipped OOS is normalized to canonical `### OOS_` at append time in `review-and-fix CLI`, so the legacy match is defense-in-depth; #3550. Counted blocks must not contain a dedicated `- **focus-area**:` field line whose value begins with `security`. Security-routed entries are excluded. Prose such as `focus-area = security` inside a `**Description**` line does **not** mark a block as security-routed.
- **filed_urls** — Sum of (a) unique `https://…/issues/<digits>` substrings from the loose union of every `--filed-urls-file` path plus `--oos-issues-ndjson` (when provided), and (b) unique URLs read only from `- **Filed URL**` field lines (optional whitespace before `:`) in every `--filed-urls-strict-file` path (Python OOS disposition authority).
- **inline** — Count of lines in `git log --format=%B RANGE` containing the literal substring `Inline-triage rule` (heuristic aggregate — any such line counts toward the total; there is no strict per-OOS index linkage).
- **rejected_oos_markers** — For each JSON line in `--oos-issues-ndjson` whose `body` contains a Rejected heading (`## Rejected` / `Rejected / Out-of-Scope`), count `### OOS_` and `- **OOS_<digit>` lines only under the rejected section (after the first `## Rejected` heading, until the next `##` heading that is not itself a Rejected heading). Summed across all matching records.

## Consumer

`oos-disposition-checkpoint.sh` invokes this gate from `skills/implement/SKILL.md` Step 8+ and owns exit-code mapping plus `run-log append-failure` logging. Orchestrator readers should use `oos-disposition-checkpoint.md` for the checkpoint exit contract and logging sites. After checkpoint exit **0**, `run-statistics`, `OOS_PENDING=false`, and re-invoke `step-8-ship.sh` without resume-phase (Python reads scoped state internally) remain orchestrator-owned per `skills/implement/SKILL.md`; on checkpoint non-zero, the orchestrator must not perform those post-pass steps.

Harness: `skills/implement/scripts/test-oos-disposition-gate.sh`.
