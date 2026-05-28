### FINDING_1: Design audit PR matching uses the wrong title shape
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-dyn-schema-evidence, Codex-dyn-schema-evidence, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-regex-anchor, Codex-dyn-regex-anchor
- **Severity**: important
- **Concern**: The plan filters or maps design log PRs using a `flush design run` title pattern, but `design-log-publish.sh` creates PRs titled `chore(larch-logs): design run <RUN_ID>`. As a result, `/audit-runs --skill=design` last/since discovery and PR-to-run mapping can skip real design log PRs or produce empty/unmapped run data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch, Cursor-dyn-schema-evidence, Codex-dyn-schema-evidence: Update audit-resolve-prs.sh and audit-map-runs.sh to match the existing PR title shape, or explicitly include a minimal design-log-publish.sh title migration in the plan and tests
  - From Cursor-Edge, Codex-Edge: Use the existing PR title regex `^chore\(larch-logs\): design run ([A-Za-z0-9._-]+)$`, or explicitly change the publisher title in the same PR if that is intended.
  - From Cursor-Innovation, Codex-Innovation: Use the existing PR title shape for audit-resolve-prs.sh and audit-map-runs.sh, or explicitly change design-log-publish.sh title generation and cover both old and new title shapes
  - From Cursor-Pragmatic: Align regexes with PR title chore(larch-logs): design run plus capture group; anchor tests to design-log-publish.sh not flush commit subject
  - From Codex-Pragmatic: Match the existing PR title regex ^chore\(larch-logs\): design run ([0-9A-Fa-f-]+)$, or explicitly change the publisher and tests together
  - From Cursor-dyn-regex-anchor, Codex-dyn-regex-anchor: Use the existing PR title anchor ^chore\(larch-logs\): design run ([0-9A-F-]+)$ for PR title matching, unless the plan intentionally changes design-log-publish.sh too.


### FINDING_2: Design token analysis uses implement-only artifact filenames
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-schema-evidence, Codex-dyn-schema-evidence
- **Severity**: important
- **Concern**: The planned `/report-tokens --skill=design` path changes the log base to `larch-logs/design` but continues looking for implement-style `token-report.json` and `timing-report.json`. Current design logs use final-suffixed files or other design-specific artifacts, so design token scans would silently skip parseable runs or report no token data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: For --skill=design, read token-report-final.json and timing-report-final.json with run-params.json fallback; keep current token-report.json/timing-report.json behavior for --skill=implement
  - From Cursor-Edge, Codex-Edge: For `--skill=design`, read `token-report-final.json` and `timing-report-final.json`, or probe the final names first and fall back to legacy names; make the design fixtures use the real final filenames.
  - From Cursor-Innovation, Codex-Innovation: For --skill=design read token-report-final.json and timing-report-final.json, with run-params.json fallback as planned; update design fixtures to mirror the committed final-suffixed file names
  - From Codex-Pragmatic: Use per-skill filenames or fallbacks: design reads token-report-final.json and timing-report-final.json; implement keeps the existing names
  - From Cursor-Requirements, Codex-Requirements: Add skill-specific token report selection so design reads token-report-final.json and implement reads token-report.json; update the design fixture to mirror that real filename
  - From Cursor-dyn-schema-evidence, Codex-dyn-schema-evidence: For a minimum-change PR, defer report-tokens --skill=design, or add an explicit reader for the current design artifacts instead of assuming token-report.json and timing-report.json exist


### FINDING_3: New audit report titles are not excluded from issue dedupe searches
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge
- **Severity**: important
- **Concern**: The plan changes audit report titles to skill-prefixed forms such as `[Implement Run Logs Audit ...]` and `[Design Run Logs Audit ...]`, but the documented or proposed issue-search noise exclusion only excludes the legacy `^[Run Logs Audit .* Report]` shape. Future finding dedupe searches may match prior audit report issues and misclassify or suppress findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Update the exclusion contract wherever the search is implemented to exclude legacy and new audit-report title shapes, ideally with the same shared title-matcher used by prior-report discovery/closing
  - From Cursor-Edge, Codex-Edge: Update the audit-report noise exclusion to cover legacy, implement-prefixed, and design-prefixed audit titles wherever finding dedupe filters issue search results.


### FINDING_4: `--plot-from` cannot enforce skill-specific title boundaries from body-only fetches
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-dyn-callsite-audit, Codex-dyn-callsite-audit, Cursor-dyn-regex-anchor, Codex-dyn-regex-anchor
- **Severity**: important
- **Concern**: The plan expects `/report-tokens --skill=design --plot-from` to reject legacy implement analysis reports, but the current fetch path only passes issue body content to the analyzer. Without fetching and validating the issue title, the analyzer cannot distinguish `[Analysis Report]`, `[Implement Analysis Report]`, and `[Design Analysis Report]` sources before loading raw records.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Fetch `title,body` for `--plot-from`, validate the title against the selected skill before parsing the raw data block, then pass only the body to the existing loader.
  - From Cursor-Innovation, Codex-Innovation: Fetch title alongside body in --plot-from mode and validate title prefix before plotting, allowing legacy [Analysis Report] only for --skill=implement
  - From Cursor-Requirements, Codex-Requirements: Fetch title and body for --plot-from and validate the title before plotting, or add an explicit skill marker to report bodies and validate it; add the legacy-design rejection test
  - From Cursor-dyn-callsite-audit, Codex-dyn-callsite-audit: In run-analysis.sh, parse SKILL before the early exit, fetch title and body for --plot-from, validate title against SKILL, and pass/export SKILL into the analyzer path used for plot regeneration.
  - From Cursor-dyn-regex-anchor, Codex-dyn-regex-anchor: Fetch title with the body and validate it before parsing: implement accepts ^\[(Analysis Report|Implement Analysis Report)\] and design accepts ^\[Design Analysis Report\] only.


### FINDING_5: Design scan rows rely on artifacts that design logs do not contain
- **Reviewer(s)**: Codex-Pragmatic, Cursor-dyn-schema-evidence, Codex-dyn-schema-evidence
- **Severity**: important
- **Concern**: Proposed design scan coverage includes scanners that are hardwired to implement-only artifact names such as `review-findings-full.jsonl` or `execution-issues.ndjson`, while design logs use different files such as plan-review TSVs or markdown artifacts. Those rows would consistently skip design data and create false confidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: For minimum scope, remove oos-category-mangle from scans-design.tsv until a design parser exists, or add a small design branch that reads the plan-review TSV
  - From Cursor-dyn-schema-evidence, Codex-dyn-schema-evidence: Keep scans-design.tsv to scans that work on existing design artifacts, such as cache-freshness and oos-silent-drop, unless this PR also adapts those scanners to the design artifact names


### FINDING_6: `audit-map-runs.sh` may not receive the skill needed for design mapping
- **Reviewer(s)**: Cursor-dyn-callsite-audit, Codex-dyn-callsite-audit
- **Severity**: important
- **Concern**: The plan permits `audit-map-runs.sh` to be called with `--log-root` instead of `--skill`, but the proposed design title parsing branch depends on the selected skill. A design audit could pass only `--log-root larch-logs/design`, causing the script to stay on implement-style mapping behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-callsite-audit, Codex-dyn-callsite-audit: Require every SKILL.md audit-map-runs.sh call to pass --skill "$SKILL"; keep --log-root as an optional test/manual override and validate it does not conflict with the selected skill.


### FINDING_7: `audit-scan-run.sh` call contract conflicts with its argument parser
- **Reviewer(s)**: Cursor-dyn-callsite-audit, Codex-dyn-callsite-audit
- **Severity**: important
- **Concern**: The plan says `SKILL.md` should pass `--skill` to `audit-scan-run.sh`, but also says `audit-scan-run.sh` needs no code change. The current parser would reject `--skill` as an unknown argument, while omitting it leaves the orchestration without the required skill flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-callsite-audit, Codex-dyn-callsite-audit: Add a minimal --skill parser/enum check to audit-scan-run.sh and its contract/tests, then pass --skill "$SKILL" alongside the centrally derived --scans-tsv "$SCANS_TSV".

