## Proposed Design Outline

### Goals
- Make `--skill=<name>` a required argument on both `/audit-runs` (`/larch:audit-runs`) and `/report-tokens` with a closed enum `{design, implement}`.
- Generalize both skills end-to-end so they operate on `larch-logs/<skill>/` for the selected skill: paths, scan logic, PR mapping, report titles, and report bodies.
- Preserve a backward-compat path so prior implement audit reports (legacy `[Run Logs Audit ... Report]` titles) are still discovered as prior reports when `--skill=implement` is in use.

### Non-goals
- Adding non-`{design, implement}` skill values (e.g., `research`). Allow-list is closed for this change.
- Auto-detecting the skill from cwd or recent activity. Operator must pass `--skill` explicitly.
- Rewriting either skill's overall workflow (preflight, scanning, reporting, etc.). The change is parameterization, not redesign.
- Migrating or rewriting existing audit-report issue bodies/frontmatter.

### Approach sketch
- Add `--skill=<name>` argv to both SKILL.md surfaces; reject missing-flag and out-of-enum values before any side effects.
- Parameterize `LOG_BASE` and similar `larch-logs/implement` literals via a single `LOG_ROOT="larch-logs/$SKILL"` derivation. Touched scripts: `run-analysis.sh`, `audit-resolve-prs.sh`, `audit-map-runs.sh`, `audit-scan-run.sh`, plus the SKILL.md prose for both skills.
- Split `scans.tsv` into `scans-implement.tsv` (renamed current file, content unchanged) + `scans-design.tsv` (new, only design-applicable scans). Scan dispatcher reads the path based on `--skill`.
- Skill-prefix all newly filed titles: `[Implement Run Logs Audit ...]` / `[Design Run Logs Audit ...]` for audit-runs; `[Implement Analysis Report]` / `[Design Analysis Report]` for report-tokens. Prior-report search regex is `^\[<Skill> Run Logs Audit .* Report\]$` for design; for implement also accept the legacy `^\[Run Logs Audit .* Report\]$` shape.
- For `--skill=design` audit-runs PR mapping, parse `<RUN_ID>` from chore PR titles matching `chore(larch-logs): flush design run <RUN_ID>` produced by `design-log-publish.sh`, then resolve `larch-logs/design/<RUN_ID>/`. Verbal-description grammar (`last N PRs`, `since last audit`, `since <ts>`, `#N`) is unchanged.

### Surfaces in scope
- `.claude/skills/audit-runs/SKILL.md` + scripts (`audit-resolve-prs.sh`, `audit-map-runs.sh`, `audit-scan-run.sh`, `audit-title.sh`, `audit-preflight.sh`, `test-audit-runs.sh`); `scans.tsv` → `scans-implement.tsv` + new `scans-design.tsv`.
- `skills/report-tokens/SKILL.md` + scripts (`run-analysis.sh`, fixtures, `test-rate-assertions.sh`, `test-report-tokens-recompute.sh`).
- Title-eligibility filter in `/design` (`scripts/lib-title-eligibility.sh`) if its archival-report regex must distinguish new skill-prefixed titles.

### Open questions
- Whether the audit concurrency guard scope should be per-skill or shared — defer to plan (implementation detail).
- Whether report-tokens should read `design_classification` from `run-params.json` for design runs (vs. inferring SIMPLE/HARD from `workflow_path` like implement) — defer to plan after inspecting `larch-logs/design/<RUN_ID>/timing-report.json` and `run-params.json` fields.
- Whether existing prose docs (`docs/run-logs.md`, README skill catalog) need wording updates beyond the SKILL.md edits — defer to plan.
