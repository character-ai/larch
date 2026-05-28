## Decision 1: Scope depth — full generalization vs argv-only

- **Question**: Should `--skill=<name>` generalize directory paths, scan logic, and PR-mapping end-to-end, or just plumb the flag at the entry point?
- **Resolution**: **Full generalization**. Both `/audit-runs` and `/report-tokens` operate end-to-end on `larch-logs/<skill>/` for the selected skill. For audit-runs this includes PR mapping, scan registry contents, and title regex. For report-tokens this includes `LOG_BASE`, workflow-path reading, and plot labels.
- **Source**: user

## Decision 2: Validation — closed enum vs open string

- **Question**: Should `--skill=<x>` validate against a closed `{design, implement}` allow-list, or accept any string and fall back to directory-existence?
- **Resolution**: **Closed enum allow-list**. Reject `--skill=<x>` when `x ∉ {design, implement}` with a clear usage error. New values must be added to the allow-list explicitly. Loudest failure for typos; easiest deliberate extension.
- **Source**: user

## Decision 3: Scan filtering for audit-runs --skill=design

- **Question**: The implement scan registry (`scans.tsv`) is implement-specific (EXON misclassification, OOS mangle, NS-retry sidecars, etc.). How should design audits handle scan selection?
- **Resolution**: **Per-skill scan registries**. Rename current `scans.tsv` to `scans-implement.tsv`. Add `scans-design.tsv` listing only scans applicable to design runs. Skill flag selects the registry path. One-time refactor cost; explicit visibility into each scan's scope.
- **Source**: user

## Decision 4: Audit-report and analysis-report title format

- **Question**: Should reports use skill-prefix, shared titlespace + body field, or skill-suffix?
- **Resolution**: **Skill-prefix titles**.
  - audit-runs: `[Implement Run Logs Audit <ts> Report]` and `[Design Run Logs Audit <ts> Report]`.
  - report-tokens: `[Implement Analysis Report]` and `[Design Analysis Report]`.
  - Prior-report search regex becomes `^\[<Skill> Run Logs Audit .* Report\]$` (skill-scoped).
  - Existing implement audits stay under the legacy `[Run Logs Audit` pattern; prior-report lookup for `--skill=implement` includes BOTH the legacy `[Run Logs Audit ` and the new `[Implement Run Logs Audit ` shapes. Design starts clean with only the new prefix.
- **Source**: user

## Decision 5: PR mapping for design run logs

- **Question**: How should `/audit-runs --skill=design` map operator input to run-log directories?
- **Resolution**: **Map via design chore PRs**. Mirror the implement flow. Walk recent chore PRs (titled `chore(larch-logs): flush design run <RUN_ID>` per `design-log-publish.sh`), extract `<RUN_ID>` from the title literal, and resolve to `larch-logs/design/<RUN_ID>/`. Same operator UX (`last N PRs`, `since last audit`, `since <ts>`, `#N`) — no separate verbal-description grammar.
- **Source**: user

## Deferred to implementation / Round 2

- **Concurrency guard scope**: whether `--skill=design` and `--skill=implement` share the existing 5-minute lock or get separate locks.
- **Backward-compat for existing audit-report issue bodies**: implement audits before this change have no skill prefix on titles; the legacy-and-prefixed dual-pattern prior-report regex in Decision 4 covers titles, but if audit-report bodies/frontmatter need a `skill: implement` backfill, that's an implementation choice.
- **Exact field semantics in report-tokens for design runs**: where to read `workflow_path` / `design_classification` from in design runs (`timing-report.json`, `run-params.json`, or plan-review tally fallback) — design and implement may have different field names.
- **CI workflow callers**: none found in `.github/`; no immediate breakage risk from making the flag required.
