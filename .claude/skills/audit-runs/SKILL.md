---
name: audit-runs
description: "Use when auditing recently-merged /implement run logs for anomalies, filing or augmenting bug issues, and maintaining a chain-of-history audit-report issue trail. Mechanizes the ad-hoc post-merge audit workflow."
allowed-tools: Bash, Read
---

# audit-runs

Audit recently-merged `/implement` run logs for anomalies (EXON regression, OOS mangling, missing files, NS-retry sidecars, self-deploying gap, etc.); file or augment bug issues; always file a chain-of-history audit-report issue.

This is a **dev-only** operator skill (`.claude/skills/`). It is NOT shipped with the plugin.

## Usage

```
/larch:audit-runs <verbal-description> [--no-fix-issues] [--repo owner/name] [--allow-concurrent]
```

(Plugin slash-alias: `/audit-runs …` may also resolve to this skill depending on marketplace wiring; prefer `/larch:audit-runs` when unsure.)

### Args

- `<verbal-description>` (mandatory positional): describes which PRs to audit. Supported forms:
  - `last N PRs` — N most-recently-merged PRs targeting `main`
  - `since last audit` — PRs merged after the prior audit report's `audited_pr_range.last`; error if no prior report exists or no new PRs have merged (do NOT file an empty report)
  - `since <ISO-timestamp>` — PRs merged after the given timestamp
  - `#N` or `PR #N` — exactly one PR
  - Default when empty: fail with usage error
- `--no-fix-issues`: suppress filing new bug issues and augmentation comments; audit report is still filed (records what would have been filed in `proposed_issues_no_filing` field)
- `--repo <owner/name>`: target repo. Default: `character-ai/larch`
- `--allow-concurrent`: override the 5-minute concurrency guard

## Pre-flight

Run these checks before doing any work:

1. `git fetch origin main && git pull --ff-only`. Refuse if working tree is dirty.
2. Verify `pwd` is a clone of `--repo`. Compare `gh repo view -R <owner/name> --json url` (substitute the same `owner/name` you passed to `--repo`) with `git config --get remote.origin.url`. Fail-fast if they don't match.
3. Concurrency guard: GitHub issue search `created:` filters expect **absolute** dates, not rolling windows like `5m`, so do **not** rely on `gh issue list --search 'created:>5m'`. Instead list `audit-report` issues with `--json number,createdAt` and filter in `jq` against a UTC cutoff for **now − 5 minutes** (unless `--allow-concurrent`).

   Compute `CUTOFF` portably, for example:

   - GNU `date`: `CUTOFF="$(date -u -d '5 minutes ago' +'%Y-%m-%dT%H:%M:%SZ')"`
   - macOS `date`: `CUTOFF="$(date -u -v-5M +'%Y-%m-%dT%H:%M:%SZ')"`

   Then refuse when any row is newer than `CUTOFF`:

   ```bash
   gh issue list --state all --label audit-report --repo "<owner/name>" --json number,createdAt --limit 50 \
     | jq -e --arg c "$CUTOFF" 'any(.[]; .createdAt > $c)' >/dev/null \
     && { echo "Refuse: audit-report filed within the 5-minute concurrency window"; exit 1; }
   ```

## Verbal-Description Resolution

1. Parse the description and resolve to a concrete PR list using `gh pr list --repo <repo> --state merged --base main` with appropriate filters.
2. Echo the resolved PR list BEFORE running the audit: `Resolved <description> to: [#X, #Y, #Z]. Proceeding.`
3. For "since last audit":
   - Read the most-recent issue matching label `audit-report` (sorted `createdAt DESC`, both states): `gh issue list --state all --label audit-report --json number,title,body,createdAt --jq 'sort_by(.createdAt) | reverse | .[0]'`
   - Parse its YAML frontmatter for `audited_pr_range.last`
   - Query for PRs merged after that PR's `mergedAt` timestamp
   - Error if no prior report exists OR its frontmatter is malformed/unparseable
   - Error if the query yields zero new PRs (do NOT file an empty report; exit cleanly with a message)

## Scan Registry

The scan list is externalized in `.claude/skills/audit-runs/scans.tsv` (one row per scan: `name`, `type`, `pattern`, `expected_outcome`, `severity`). Adding a scan = adding a TSV row, no SKILL.md edit needed.

Read the registry at runtime:
```bash
SCANS_TSV="$PWD/.claude/skills/audit-runs/scans.tsv"
```

### Scans (baseline — see scans.tsv for the machine-readable registry)

| Scan | What | Where |
|---|---|---|
| Required-file presence | Compare against `docs/run-logs-required-files.tsv` | run-log root |
| EXON misclassification | `\| FINDING_.* \| 0 \| 0 \| [1-9]+ \|.*\| rejected \|` | `round-*/voting-tally.md` |
| OOS category mangle | `category` field not in `{code-quality, risk-integration, correctness, architecture, security}` | `review-findings-full.jsonl` |
| NS-retry sidecars | files matching `*-ns-retry*` (see `scans.tsv`; first-pass trailing-content checks are the separate `trailing-content-no-issues-found` scan) | `round-*/` |
| Codex round-1 adherence | round 2+ panel-manifest should not contain `tool=codex` | `round-N/panel-manifest.ndjson` |
| Codex generalist waste | `codex-generalist-output.txt` is `NO_ISSUES_FOUND` only AND timing > 120s | `round-1/` + `timing-report.json` |
| Execution-issues categories | non-Warnings entries in `execution-issues.ndjson` | `execution-issues.ndjson` |
| Cache freshness | `manifest.json::larch_version` vs latest plugin version | `manifest.json` |
| Coder tool | `CODER_TOOL` field | `round-*/coder.env` |
| Trailing-content NO_ISSUES_FOUND | first-pass content matches `^NO_ISSUES_FOUND\n` plus extra | `*-first-pass.txt` |

## Scanning

For each audited PR:

1. Look up the PR's run-log directory: find the most recent `larch-logs/implement/<RUN_ID>/` directory whose `manifest.json` has a `pr_number` matching the PR.
2. Run each scan from `scans.tsv` against the appropriate files in that run-log root.
3. Collect findings per PR, per scan.

### Cross-cutting Checks

Run for each audited PR:

- **Self-deploying gap detection**: cross-reference `manifest.json::larch_version` with the version that contains the PR's `Closes #N` fix. Warn loudly if the run used a version BEFORE the fix landed (the bug-being-fixed exhibits in the very run that fixes it).
- **Closed-issue cross-reference**: parse `Closes #N` from the PR body. Check if the run still exhibits the bug that `#N` claims to fix.

## Bug Issue Handling

For each finding from the scans:

1. Search open issues (excluding titles matching `^\[Run Logs Audit Report` or `^\[IN PROGRESS\]`): `gh issue list --state open --repo <repo> --search "<finding keywords>" --json number,title`
2. If a match is found: post an augmentation comment via `gh issue comment <N> --body-file <path>` (unless `--no-fix-issues`).
3. If no match: file a new issue via `/larch:issue` (dedup ON; the issue skill does its own dedup pass) (unless `--no-fix-issues`).
4. With `--no-fix-issues`: suppress both filing and augmentation; record in `proposed_issues_no_filing` frontmatter field instead.

### Augmentation Comment Shape

```markdown
**Additional data from <PR list>:**

| PR | Count |
|---|---|
| #N | M occurrences |

Previous cumulative: X → Now: X+M
```

## Audit Report

Always file an audit report after the scan, EXCEPT when `since last audit` yields zero new PRs (exit cleanly without filing).

### Title Format

- Contiguous range: `[Run Logs Audit Report <ISO-timestamp>] PRs #X-#Y`
- Non-contiguous (≤4 PRs): `[Run Logs Audit Report <ISO-timestamp>] PRs #X, #Y`
- ISO-timestamp: UTC with `Z` suffix, minute precision (e.g. `2026-05-20T19:30Z`)

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

### Frontmatter (YAML block between `---` markers at top of body)

```yaml
audit_schema_version: 1
audit_timestamp: <ISO-timestamp>
audited_repo: <owner/name>
audited_pr_range:
  first: N
  last: M
  count: K
audited_prs: [N, ..., M]   # explicit list when range has gaps
prior_report_issue: <N | null>
issues_filed_this_audit: [...]
issues_augmented_this_audit: [...]
proposed_issues_no_filing: [...]   # only present when --no-fix-issues was set
cumulative_counters:
  exon_misclassifications: N
  oos_categories_mangled: N
  oos_categories_clean: N
  ns_retries_cursor_specialist: N
  ns_retries_cursor_specialist_launches: N
```

### Report Sections (in this order, exact `##` headers with a trailing space before the title; use `####` for internal subheadings)

- `## Summary`
- `## Delta from prior audit` (omit when `prior_report_issue` is null)
- `## Per-PR findings` (one `####` subsection per PR)
- `## Open issues snapshot` (list every open audit-eligible issue: number, title, last-seen-symptom-count)
- `## Scan results` (table: scan-name → pass/fail/finding count, plus issue cross-references)

## Close Prior Reports

After the new audit report is filed:
1. Find all OPEN issues with label `audit-report` in the target repo (excluding the just-filed one): `gh issue list --state open --label audit-report --repo <repo> --json number`
2. For each: post `Superseded by #<new>` as a comment, then close via `gh issue close <N> --repo <repo>`
3. Order: file new first, then close priors (if close-priors fails, orphaned open prior is cosmetic)

## Output

Stdout summary at the end:
- Per-scan PASS/FAIL counts
- List of new issues filed
- List of augmented issues
- Audit report URL

## Preconditions

- Working tree must be a clone of `--repo`
- `audit-report` label must exist in the target repo (created by the bootstrap audit report — treat its existence as a precondition assertion, not something to create on each invocation)
- `docs/run-logs-required-files.tsv` must exist in the repo root (for the Required-file presence scan)
- `larch-logs/implement/` directory must exist in the repo root (for all scans)

## Scripts

- `.claude/skills/audit-runs/scripts/test-audit-runs.sh` (contract: `.claude/skills/audit-runs/scripts/test-audit-runs.md`) — offline unit test harness for verbal-description parsing, guard logic, frontmatter round-trip, and title exclusion regex.

## Anti-patterns

- Do NOT file an empty audit report (zero PRs audited)
- Do NOT recurse: the skill must not audit its own audit-report issues
- Do NOT close prior reports before the new one is confirmed filed (ISSUE_NUMBER from create-one.sh is non-empty)
- Do NOT `gh issue create` directly — use `create-one.sh` for audit reports and `/larch:issue` for bug issues
