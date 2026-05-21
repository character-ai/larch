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

1. **Normalize empty or omitted positional**: If `<verbal-description>` is absent or whitespace-only after trimming, set **effective description** to the canonical phrase `since last audit` and set **implicit since-last-audit** to true. Otherwise set **effective description** to the trimmed operator text and **implicit since-last-audit** to false. Do **not** run generic pattern matching on an empty string.
2. **`since last audit` scope (explicit phrase or effective description from step 1)**: When **effective description** matches the `since last audit` form (including after empty/omitted normalization):
   - Read the most-recent issue matching label `audit-report` (sorted `createdAt DESC`, both states): `gh issue list --state all --label audit-report --json number,title,body,createdAt --jq 'sort_by(.createdAt) | reverse | .[0]'`
   - Parse its YAML frontmatter for `audited_pr_range.last` (an integer PR number — NOT `audit_timestamp`)
   - Query for PRs merged after that PR's `mergedAt` timestamp (UTC from the GitHub API — no timezone conversion needed; `audit_timestamp` is not used in this comparison)
   - Error if no prior report exists OR its frontmatter is malformed/unparseable
   - Error if the query yields zero new PRs (do NOT file an empty report; exit cleanly with a message)
3. **Other supported forms**: When **effective description** is not `since last audit`, parse it and resolve to a concrete PR list using `gh pr list --repo <repo> --state merged --base main` with appropriate filters (`last N PRs`, `since <ISO-timestamp>`, `#N` / `PR #N`, etc.).
4. **Echo before the audit**: If **implicit since-last-audit** is true: `Resolved since last audit (implicit default: empty/omitted positional) to: [#X, #Y, #Z]. Proceeding.` Otherwise: `Resolved <effective description> to: [#X, #Y, #Z]. Proceeding.`

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

- Contiguous range: `[Run Logs Audit Report <Pacific-ISO-timestamp>] PRs #X-#Y`
- Non-contiguous (≤4 PRs): `[Run Logs Audit Report <Pacific-ISO-timestamp>] PRs #X, #Y`
- `<Pacific-ISO-timestamp>`: Pacific wall time with UTC offset, minute precision (e.g. `2026-05-20T12:30-07:00` during PDT; e.g. `2026-01-15T12:30-08:00` during PST — US Pacific uses `-08:00` only in winter, not on a May date)

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

`audit_timestamp` matches **Title Format** `<Pacific-ISO-timestamp>`: Pacific wall time with explicit `-07:00` or `-08:00` and minute precision (not the `since <ISO8601-instant>` filter convention and not UTC `Z` by itself).

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

## Scripts

- `.claude/skills/audit-runs/scripts/test-audit-runs.sh` (contract: `.claude/skills/audit-runs/scripts/test-audit-runs.md`) — offline unit test harness for verbal-description parsing, guard logic, frontmatter round-trip, and title exclusion regex.

## Anti-patterns

- Do NOT file an empty audit report (zero PRs audited)
- Do NOT recurse: the skill must not audit its own audit-report issues
- Do NOT close prior reports before the new one is confirmed filed (ISSUE_NUMBER from create-one.sh is non-empty)
- Do NOT `gh issue create` directly — use `create-one.sh` for audit reports and `/larch:issue` for bug issues
- Do NOT auto-file or auto-augment bug issues — only file the audit report itself at scan/report time. Bug-issue actions require explicit user direction in chat.
- Do NOT ask the 3-way question when there are zero findings — state `No findings — no bug issues to file.` and exit.
