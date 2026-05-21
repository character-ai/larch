---
name: audit-runs
description: "Use when auditing recently-merged /implement run logs for anomalies, filing the chain-of-history audit-report issue, and proposing bug-issue follow-ups that require explicit user direction before any filing or augmentation. Mechanizes the ad-hoc post-merge audit workflow."
allowed-tools: Bash, Read
---

# audit-runs

Audit recently-merged `/implement` run logs for anomalies (EXON regression, OOS mangling, missing files, NS-retry sidecars, self-deploying gap, etc.); always file a chain-of-history audit-report issue; record bug-issue candidates as proposals at scan time and act on them only after explicit user direction in chat.

This is a **dev-only** operator skill (`.claude/skills/`). It is NOT shipped with the plugin.

## Usage

```
/larch:audit-runs [<verbal-description>] [--repo owner/name] [--allow-concurrent]
```

(Plugin slash-alias: `/audit-runs …` may also resolve to this skill depending on marketplace wiring; prefer `/larch:audit-runs` when unsure.)

### Args

- `<verbal-description>` (optional positional): when present, describes which PRs to audit. When omitted or empty, treat as `since last audit` (same error paths as that form). Supported forms:
  - `last N PRs` — N most-recently-merged PRs targeting `main`
  - `since last audit` — PRs merged after the prior audit report's `audited_pr_range.last`; error if no prior report exists or no new PRs have merged (do NOT file an empty report)
  - `since <ISO8601-instant>` — PRs merged after that instant (same interpretable forms as GitHub `mergedAt`: `…Z` or explicit `±HH:MM` offset). This filter is **not** tied to the Pacific wall-clock convention used for audit report titles and `audit_timestamp`.
  - `#N` or `PR #N` — exactly one PR
  - Default when empty: treat as `since last audit` (requires a prior audit-report issue; continues to error if no prior report or malformed frontmatter — same as the explicit `since last audit` form)
- `--repo <owner/name>`: target repo. Default: `character-ai/larch`
- `--allow-concurrent`: override the 5-minute concurrency guard
- **Removed flag**: `--no-fix-issues` is not supported. If any token in the skill argv is exactly `--no-fix-issues`, refuse immediately with a clear usage error (flag removed); do not proceed or silently ignore it.

## Pre-flight

```bash
PREFLIGHT_OUT=$(bash "$PWD/.claude/skills/audit-runs/scripts/audit-preflight.sh" \
  --repo "<owner/name>" [--allow-concurrent])
```

Read `PREFLIGHT_OK` and `REASON` from stdout. Fail-fast when `PREFLIGHT_OK=false`; print `REASON` to the user. Contract: `.claude/skills/audit-runs/scripts/audit-preflight.md`.

## Verbal-Description Resolution

```bash
RESOLVE_OUT=$(bash "$PWD/.claude/skills/audit-runs/scripts/audit-resolve-prs.sh" \
  --repo "<owner/name>" [--verbal-description "<verbal-description>"])
```

Read `PR_LIST`, `PR_COUNT`, `IMPLICIT_SINCE_LAST_AUDIT`, `PRIOR_REPORT_NUMBER`, `RESOLVED_ECHO`, and `ERROR` from stdout. Fail-fast when `ERROR` is non-empty; print it to the user. Print `RESOLVED_ECHO` before scanning. Contract: `.claude/skills/audit-runs/scripts/audit-resolve-prs.md`.

## Scan Registry

The scan list is externalized in `.claude/skills/audit-runs/scans.tsv` (one row per scan: `name`, `type`, `pattern`, `expected_outcome`, `severity`). JSON string escaping for NDJSON payloads is implemented in `.claude/skills/audit-runs/scripts/audit-scan-run-jstr.inc.bash` (sourced by `audit-scan-run.sh` and `test-audit-runs.sh`). **Adding a scan** requires coordinated updates: (1) a new `scans.tsv` row, (2) a matching `case` branch (and scan function) in `audit-scan-run.sh`, (3) any counter wiring in `audit-compute-counters.sh` / `audit-compute-counters.md` when the scan feeds cumulative totals, (4) `audit-scan-run.md` / `SKILL.md` scan tables if the operator-facing baseline changes, and (5) hermetic coverage in `test-audit-runs.sh` for the new NDJSON shape and counter path. **Plan fidelity**: substantive changes to that surface (new counters, new cumulative YAML keys, or registry-wide behavior) should be tracked in their own issue/PR when they go beyond a routine scan-row + test update — routine `changelog-rebase-conflicts` / `changelog_rebase_conflicts` / `ns_retries_cursor_specialist` wiring is part of this skill’s maintained baseline, not an ad-hoc add-on.

Read the registry at runtime:
```bash
SCANS_TSV="$PWD/.claude/skills/audit-runs/scans.tsv"
```

### Scans (baseline — see scans.tsv for the machine-readable registry)

| Scan | What | Where |
|---|---|---|
| Required-file presence | Compare against `docs/run-logs-required-files.tsv` (NDJSON `result` is `pass` / `fail` / `skip` / `error`) | run-log root |
| EXON misclassification | `\| FINDING_.* \| 0 \| 0 \| [1-9]+ \|.*\| rejected \|` | `round-*/voting-tally.md` |
| OOS category mangle | `category` field not in `{code-quality, risk-integration, correctness, architecture, security}` | `review-findings-full.jsonl` |
| NS-retry sidecars | files matching `*-ns-retry*` (see `scans.tsv`; first-pass trailing-content checks are the separate `trailing-content-no-issues-found` scan) | `round-*/` |
| Codex round-1 adherence | round 2+ panel-manifest should not contain `tool=codex` | `round-N/panel-manifest.ndjson` |
| Codex generalist waste | `codex-generalist-output.txt` is `NO_ISSUES_FOUND` only AND timing > 120s | `round-1/` + `timing-report.json` |
| Execution-issues categories | non-Warnings entries in `execution-issues.ndjson` | `execution-issues.ndjson` |
| Cache freshness | `manifest.json::larch_version` vs latest plugin version (`result: informational` when the run lags current; empty `larch_version` remains `fail`; other rows may emit `skip`/`error`) | `manifest.json` |
| Changelog rebase/conflicts (heuristic) | `execution-issues.ndjson` bodies mentioning changelog + rebase/conflict | `execution-issues.ndjson` |
| Coder tool | `CODER_TOOL` field | `round-*/coder.env` |
| Trailing-content NO_ISSUES_FOUND | first-pass content matches `^NO_ISSUES_FOUND\n` plus extra | `*-first-pass.txt` |

## Scanning

```bash
# Map each PR to its run-log directory
RUN_MAP_TSV=$(bash "$PWD/.claude/skills/audit-runs/scripts/audit-map-runs.sh" \
  --pr-list "$PR_LIST" --repo "<owner/name>")
# TSV: pr_number<TAB>run_id<TAB>started_at<TAB>larch_version<TAB>closes_issue
```

Then for each PR row in the TSV:

```bash
bash "$PWD/.claude/skills/audit-runs/scripts/audit-scan-run.sh" \
  --run-dir "larch-logs/implement/<RUN_ID>" \
  --pr <PR_NUM> \
  --scans-tsv "$PWD/.claude/skills/audit-runs/scans.tsv" \
  --required-files-tsv "$PWD/docs/run-logs-required-files.tsv" \
  --current-version "<latest-plugin-version>" \
  > "$TMPDIR/scan-results-<PR_NUM>.ndjson"
```

Read `scan-results-*.ndjson` files as NDJSON (one JSON object per scan per line). Each line’s `result` is not limited to pass/fail: treat **`informational`**, **`skip`**, and **`error`** as first-class outcomes when writing the report (for example `cache-freshness` behind current vs missing inputs vs manifest/registry drift). Contract: `.claude/skills/audit-runs/scripts/audit-scan-run.md`.

**Cross-cutting checks (NDJSON + operator judgment):** the synthetic `cross-cutting` object (and `cache-freshness` / manifest fields) flags **manifest integrity** — empty `ended_at` / `pr_number`, and `manifest_pr_number_mismatch_with_audited_pr` / legacy `self_deploying_gap` when `manifest.json`’s `pr_number` disagrees with the audited PR (run-log vs merge skew / self-deploying version gaps). When `run_version < current_version`, `cache-freshness` emits **`result: informational`** (not `fail`): treat it as a self-deploying lens on the batch, not a defect signal versus the fix stream. **`proposed_new_issues` / `proposed_augmentations`** must be reconciled against **actually filed or closed** bug issues after the report (per **Post-report user prompt**); do not assume a proposal row implies an open issue without `gh` verification.

## Proposed bug-issue actions

At scan time, **only** record findings as proposals. **Never** auto-file a bug issue and **never** auto-post augmentation comments during the scan.

- **`proposed_new_issues`**: findings with no matching open issue (excluding titles matching `^\[Run Logs Audit Report` or `^\[IN PROGRESS\]` when searching). Always present in the audit-report frontmatter (possibly empty).
- **`proposed_augmentations`**: findings that match an existing open issue (same title search as today). Always present in the audit-report frontmatter (possibly empty).

For each finding, classify it into one of these two lists (search open issues with `gh issue list --state open --repo <repo> --search "<finding keywords>" --json number,title`); do not file or comment until after the post-report user prompt below.

### Post-report user prompt

After the audit report issue is filed and prior reports are handled per **Close Prior Reports**:

1. Print the **full audit-report body** verbatim to chat (the same markdown submitted as the issue body), then print the **audit-report URL**.
2. **Zero-findings short-circuit**: if `proposed_new_issues` and `proposed_augmentations` are both empty, state `No findings — no bug issues to file.` and exit — do **not** ask the 3-way question.
3. **Otherwise**, ask the operator a 3-way question: (1) file/augment all, (2) discuss specific findings first, or (3) skip filing. Act on the response:
   - **File/augment all**: file new issues via `/larch:issue` (dedup ON); post augmentation comments with `gh issue comment <N> --repo "<repo>" --body-file "$TMPDIR/audit-augment-<N>.md"` (write the **Augmentation comment shape** markdown to that file first — same `--body-file` pattern as `create-one.sh`; do not pass multi-line tables through an inline `--body` string).
   - **Discuss first**: wait for operator direction; file or augment per finding only as approved.
   - **Skip filing**: exit cleanly; the audit report already captures proposed findings for the historical record.

The audit report issue is **never** edited after creation (chain-of-history).

### Augmentation comment shape

```markdown
**Additional data from <PR list>:**

| PR | Count |
|---|---|
| #N | M occurrences |

Previous cumulative: X → Now: X+M
```

## Audit Report

Always file an audit report after the scan, EXCEPT when the scope is `since last audit` (including an empty/omitted positional normalized to that form per **Verbal-Description Resolution**) and the query yields zero new PRs (exit cleanly without filing).

### Title Format

```bash
PACIFIC_OUT=$(bash "$PWD/.claude/skills/audit-runs/scripts/audit-pacific-timestamp.sh")
PACIFIC_TIMESTAMP=$(printf '%s\n' "$PACIFIC_OUT" | sed -n 's/^PACIFIC_TIMESTAMP=//p')
# → PACIFIC_TIMESTAMP=2026-05-20T21:59-07:00

TITLE_OUT=$(bash "$PWD/.claude/skills/audit-runs/scripts/audit-title.sh" \
  --pr-list "$PR_LIST" --timestamp "$PACIFIC_TIMESTAMP")
# stdout is KV-shaped: each line is `KEY=value`. The title script prints `TITLE=...` (not a bare title string).
TITLE=$(printf '%s\n' "$TITLE_OUT" | sed -n 's/^TITLE=//p')
```

Contracts: `audit-pacific-timestamp.md`, `audit-title.md`.

### Label

`audit-report` (must exist in the repo; verify via `gh label list --search 'audit-report'` before filing)

### Filing Method

Use `create-one.sh` directly (bypasses the batch parser's `###` heading-trap):
```bash
"$PWD/skills/issue/scripts/create-one.sh" \
  --title "<title>" \
  --body-file "$TMPDIR/audit-report-body.md" \
  --label "audit-report" \
  --repo "<repo>"
```

### Counter Computation

Before composing the report body, run `audit-compute-counters.sh` to get cumulative totals:

```bash
COUNTERS_OUT=$(bash "$PWD/.claude/skills/audit-runs/scripts/audit-compute-counters.sh" \
  --scan-results-dir "$TMPDIR" \
  [--prior-frontmatter "$TMPDIR/prior-report-body.md"])
```

Read `SCAN_FILES_FOUND`, `EXON_MISCLASSIFICATIONS`, `EXON_DELTA`, `OOS_CATEGORIES_MANGLED`, `OOS_MANGLED_DELTA`, `OOS_CATEGORIES_CLEAN`, `OOS_CLEAN_DELTA`, `OOS_CATEGORIES_BLANK`, `OOS_BLANK_DELTA`, `NS_RETRIES_CURSOR_SPECIALIST`, `NS_RETRIES_DELTA`, `CHANGELOG_REBASE_CONFLICTS`, `CHANGELOG_DELTA`, and `CATEGORY_STATS_PARTIAL` (`true` when any PR scan lacked `review-findings-full.jsonl`, so `OOS_*_DELTA` for clean/blank skipped those rows). Contract: `audit-compute-counters.md`.

### Frontmatter (YAML block between `---` markers at top of body)

`audit_timestamp` matches **Title Format** `<Pacific-ISO-timestamp>`: Pacific wall time with explicit `-07:00` or `-08:00` and minute precision when `audit-pacific-timestamp.sh` resolves `America/Los_Angeles` (`PACIFIC_TIMESTAMP_SOURCE=tz_america_los_angeles`). It is **not** the `since <ISO8601-instant>` filter convention. **UTC `Z` is allowed only** as the script’s last-resort fallback when Pacific resolution fails (`PACIFIC_TIMESTAMP_SOURCE=utc_fallback`; same shape as `audit-pacific-timestamp.sh` may emit). Populate `cumulative_counters` from `audit-compute-counters.sh` output keys below.

```yaml
audit_schema_version: 1
audit_timestamp: <Pacific-ISO-timestamp>
audited_repo: <owner/name>
audited_pr_range:
  first: N
  last: M
  count: K
audited_prs: [N, ..., M]   # explicit list when range has gaps
prior_report_issue: <N | null>
proposed_new_issues: [...]        # always present; findings with no matching open issue
proposed_augmentations: [...]     # always present; findings matched to an existing issue
cumulative_counters:
  exon_misclassifications: N
  oos_categories_mangled: N
  oos_categories_clean: N
  oos_categories_blank: N
  ns_retries_cursor_specialist: N
  changelog_rebase_conflicts: N
```

### Report Sections (in this order, exact `##` headers with a trailing space before the title; use `####` for internal subheadings)

- `## Summary` (when any audited run’s `cache-freshness` line shows `run_version` strictly less than `--current-version`, prepend a bold one-line banner immediately under the heading: **Self-deploying lens:** runs in this batch were on `<run_version(s)>`; current `main` is `<current-version>`. Use the scan NDJSON values; do not invent versions.)
- `## Delta from prior audit` (omit when `prior_report_issue` is null)
- `## Per-PR findings` (one `####` subsection per PR)
- `## Open issues snapshot` (list every open audit-eligible issue: number, title, last-seen-symptom-count)
- `## Scan results` (table: scan-name → pass/fail/finding count, plus issue cross-references)

## Close Prior Reports

After the new audit report is filed:

```bash
bash "$PWD/.claude/skills/audit-runs/scripts/audit-close-priors.sh" \
  --new-issue-number "<ISSUE_NUMBER>" --repo "<repo>"
```

Stdout is KV-shaped. Successful closes emit `CLOSED_NUMBER=<N>` (one line per issue). Failures can still exit `0` while emitting `CLOSE_FAILED=<N>` then a **TAB**-separated `REASON=...` continuation on the same line (see `audit-close-priors.md`). If `gh issue list` fails up front, the script prints `ISSUE_LIST_FAILED=true` plus `REASON=...` and exits non-zero. After any `audit-close-priors.sh` invocation, scan stdout for `CLOSE_FAILED=` / `ISSUE_LIST_FAILED=` even when the exit code is `0` — do not treat “some `CLOSED_NUMBER=` lines” as unconditional full success.

Contract: `audit-close-priors.md`.

## Output to chat

Only after the new audit report issue is filed and prior reports are handled per **Close Prior Reports** (same sequencing precondition as `### Post-report user prompt` above), the orchestrator MUST surface to chat (in order):

1. The **full audit-report body**, verbatim (same content as the filed issue body).
2. The **audit-report URL**.
3. Either the **zero-findings short-circuit** message (`No findings — no bug issues to file.`) when both proposal lists are empty, **or** the **3-way question** about filing/augmenting when there is at least one proposed item.

Bug-issue filing and augmentation happen only after operator response to that question (unless skipped); they are not part of this mandatory chat tail when the short-circuit applies.

## Output

Optional stdout-style summary after the chat contract (for example per-scan PASS/FAIL counts). Lists of bug issues filed or augmented belong here only **after** the operator has directed those actions — not at scan time.

## Preconditions

- Working tree must be a clone of `--repo`
- `audit-report` label must exist in the target repo (created by the bootstrap audit report — treat its existence as a precondition assertion, not something to create on each invocation)
- `docs/run-logs-required-files.tsv` must exist in the repo root (for the Required-file presence scan)
- `larch-logs/implement/` directory must exist in the repo root (for all scans)

## Revised Orchestrator Flow

```
audit-preflight.sh           → PREFLIGHT_OK / fail-fast
audit-resolve-prs.sh         → full stdout KV contract (see `audit-resolve-prs.md`: IMPLICIT_SINCE_LAST_AUDIT, PRIOR_REPORT_NUMBER, PR_LIST, PR_COUNT, RESOLVED_ECHO, ERROR)
audit-map-runs.sh            → run-map.tsv
for each PR:
  audit-scan-run.sh          → scan-results-NNNN.ndjson
audit-compute-counters.sh    → COUNTERS_OUT (KV lines on stdout; treat as counters input)
[LLM: classify proposed_new_issues / proposed_augmentations via gh search + reasoning]
audit-pacific-timestamp.sh   → PACIFIC_TIMESTAMP (extract from stdout KV)
audit-title.sh               → TITLE
[LLM: write report prose — Summary, Delta, Per-PR findings, Open issues, Scan results table
       reading from COUNTERS_OUT + scan-results-*.ndjson as structured input]
create-one.sh                → file audit report
audit-close-priors.sh        → close prior audit-report issues
[LLM: post-report 3-way question if proposed issues exist]
```

## Scripts

- `.claude/skills/audit-runs/scripts/audit-preflight.sh` (contract: `audit-preflight.md`) — git fetch/pull, repo-identity, concurrency guard
- `.claude/skills/audit-runs/scripts/audit-resolve-prs.sh` (contract: `audit-resolve-prs.md`) — verbal-description → PR_LIST
- `.claude/skills/audit-runs/scripts/audit-map-runs.sh` (contract: `audit-map-runs.md`) — PR → run-log directory mapping (TSV)
- `.claude/skills/audit-runs/scripts/audit-scan-run.sh` (contract: `audit-scan-run.md`) — all scans against one run-log dir; NDJSON output
- `.claude/skills/audit-runs/scripts/audit-compute-counters.sh` (contract: `audit-compute-counters.md`) — sum scan deltas + prior totals; KV output
- `.claude/skills/audit-runs/scripts/audit-pacific-timestamp.sh` (contract: `audit-pacific-timestamp.md`) — portable Pacific timestamp
- `.claude/skills/audit-runs/scripts/audit-title.sh` (contract: `audit-title.md`) — generate report title string
- `.claude/skills/audit-runs/scripts/audit-close-priors.sh` (contract: `audit-close-priors.md`) — close prior audit-report issues
- `.claude/skills/audit-runs/scripts/test-audit-runs.sh` (contract: `.claude/skills/audit-runs/scripts/test-audit-runs.md`) — offline unit test harness

## Anti-patterns

- Do NOT file an empty audit report (zero PRs audited)
- Do NOT recurse: the skill must not audit its own audit-report issues
- Do NOT close prior reports before the new one is confirmed filed (ISSUE_NUMBER from create-one.sh is non-empty)
- Do NOT `gh issue create` directly — use `create-one.sh` for audit reports and `/larch:issue` for bug issues
- Do NOT auto-file or auto-augment bug issues — only file the audit report itself at scan/report time. Bug-issue actions require explicit user direction in chat.
- Do NOT ask the 3-way question when there are zero findings — state `No findings — no bug issues to file.` and exit.
