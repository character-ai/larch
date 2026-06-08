## Goal
Implement issue #3719: [IMPLEMENTING] logs-size-reduction: Phase 5: /gc-run-logs skill for age-based run-log slimming\n\n## Context.

## Implementation Plan
## Context

Phase 5 of the logs-size-reduction series — the only phase that **caps growth permanently**. Phases 1–4 are one-time cuts plus slimmer per-run output, but the corpus still grows ~10–20 runs/week. This issue adds a new **exported plugin skill `/gc-run-logs`** implementing an age-based retention policy.

Blocked on #3706 and #3709 (the one-time retroactive PRs must land first so GC never races them on the same dirs).

## Skill spec

`skills/gc-run-logs/SKILL.md` (exported by the plugin, like `/cleanup`):

- **`--older-than DAYS`** (optional, default **90**): run dirs whose run date is older than the threshold get **slimmed to the consumer core**; newer dirs untouched.
- **`--delete`** (optional, off by default): instead of slimming, fully delete qualifying run dirs (git history remains the archive; recovery documented as `git show <sha>:<path>`).
- **`--dry-run`** (optional): print the per-dir plan (slim/delete/skip + reclaimed bytes) without changing anything.
- Scope: `larch-logs/design/`, `larch-logs/implement/`, `larch-logs/review/` when present.

**Slim-to-core keep set** (everything else in the run dir is deleted):
- both skills: `manifest.json`, `final-summary.md` (when present)
- implement: `token-report.json`, `timing-report.json`, `review-findings-full.jsonl`, `execution-issues.ndjson`, `run-statistics.md`
- design: `token-report-final.json`, `timing-report-final.json`, `run-params.json`, `plan.txt`

This preserves `/report-tokens` cost-trend history **indefinitely** (it reads exactly these reports + manifest/run-params) and keeps the machine-canonical findings record, while shedding round-level forensic detail for aged runs.

## Mechanics

1. Run-date resolution: `manifest.json::started_at` when parseable, else the dir's first-commit date (`git log --diff-filter=A`); unparseable → skip with a warning (never guess).
2. Guards: skip dirs containing `pause-state.txt` (resumable design runs); skip dirs whose manifest status suggests an in-flight run **newer than the threshold window**; idempotent — already-slimmed dirs are no-ops.
3. Output: a dedicated **log-only PR** (bulk-edit disclosure per `docs/run-logs.md`), branch + `gh pr create` through the skill; operator merges. Single-runner caution: refuse to start when an `/implement` or `/design` session is live in the repo (same dirty-tree ethos as the existing launchers).
4. Audit interplay: `required-file-presence` is step-conditional per `docs/run-logs-required-files.tsv` — slimmed dirs keep every always-required row; the TSV gains a note that dirs older than the GC threshold may be slimmed (scan emits `informational` rather than `fail` for files removed by GC; gate on a `gc-slimmed` marker file written into each slimmed dir).
5. `docs/run-logs.md` gains a Retention section: full fidelity ≤ `--older-than` days; consumer core beyond; `--delete` as explicit operator escalation.

## Consumer safety

- `/report-tokens` (both skills): full history preserved by the keep set.
- `audit-runs`: audits target recent batches (within the window); aged dirs carry the `gc-slimmed` marker for honest scan reporting.
- No automation runs GC implicitly — operator-invoked only.

## Expected effect

Steady-state working tree converges to: last-90-days full fidelity (~10–25 MB at current run rates) + consumer core for everything older (~1–2 KB/dir/report set) instead of unbounded ~20–35 MB/month growth.

## Test plan
(no test plan section in plan-file)
