### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-dyn-schema-evidence, Codex-dyn-schema-evidence
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:600-602
- **Concern**: 1. Proposed design PR title regex does not match the actual design-log publish PR title. Scenario: The plan filters and maps design PRs with ^chore\(larch-logs\): flush design run ...$, but design-log-publish creates PRs titled chore(larch-logs): design run <RUN_ID>; --skill=design last/since queries and PR-to-run mapping would skip real design log PRs
- **Proposed resolution**: Update audit-resolve-prs.sh and audit-map-runs.sh to match the existing PR title shape, or explicitly include a minimal design-log-publish.sh title migration in the plan and tests

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:118-119
- **Concern**: 2. Proposed report-tokens design path still reads implement-only artifact names. Scenario: Committed design logs use token-report-final.json and timing-report-final.json, while the plan only changes LOG_BASE and keeps token-report.json/timing-report.json scanning; --skill=design would skip parseable design runs and report no token data
- **Proposed resolution**: For --skill=design, read token-report-final.json and timing-report-final.json with run-params.json fallback; keep current token-report.json/timing-report.json behavior for --skill=implement

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/skills/audit-runs/SKILL.md:107
- **Concern**: 3. New skill-prefixed audit report titles are not added to the audit-report noise exclusion. Scenario: The plan changes audit titles to [Implement Run Logs Audit ...] and [Design Run Logs Audit ...] but leaves the finding dedupe search exclusion documented as only ^\[Run Logs Audit .* Report\]; future searches can match prior audit reports and route findings to proposed_augmentations or suppress new issues incorrectly
- **Proposed resolution**: Update the exclusion contract wherever the search is implemented to exclude legacy and new audit-report title shapes, ideally with the same shared title-matcher used by prior-report discovery/closing

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:597-602
- **Concern**: Plan keys design audit PR discovery to the wrong PR title shape. Scenario: `design-log-publish.sh` creates PRs titled `chore(larch-logs): design run <RUN_ID>`, but the plan filters and maps `--skill=design` with `^chore\(larch-logs\): flush design run ...$`; design audits will find zero PRs or emit empty run mappings.
- **Proposed resolution**: Use the existing PR title regex `^chore\(larch-logs\): design run ([A-Za-z0-9._-]+)$`, or explicitly change the publisher title in the same PR if that is intended.

### FINDING_5:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:117-122
- **Concern**: Design token scans would look for implement-style filenames. Scenario: Committed design logs use `token-report-final.json` and `timing-report-final.json`, while the plan only swaps `LOG_BASE` and keeps `token-report.json` / `timing-report.json`; `--skill=design` would silently skip all current design runs.
- **Proposed resolution**: For `--skill=design`, read `token-report-final.json` and `timing-report-final.json`, or probe the final names first and fall back to legacy names; make the design fixtures use the real final filenames.

### FINDING_6:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:1134-1138
- **Concern**: `--plot-from` cannot enforce skill-specific report titles if it only fetches the body. Scenario: The plan promises `--skill=design --plot-from <legacy implement report>` is rejected, but the current fetch path writes only `.body` to the analyzer; a body parser cannot tell `[Analysis Report]` from `[Design Analysis Report]`.
- **Proposed resolution**: Fetch `title,body` for `--plot-from`, validate the title against the selected skill before parsing the raw data block, then pass only the body to the existing loader.

### FINDING_7:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: .claude/skills/audit-runs/SKILL.md:107-115
- **Concern**: New prefixed audit reports are not excluded from bug-issue dedupe searches. Scenario: The plan changes audit report titles to `[Implement Run Logs Audit ...]` and `[Design Run Logs Audit ...]`, but the proposed bug-issue action rules still exclude only `^\[Run Logs Audit .* Report\]`; future audit-report issues can match finding keyword searches and be mistaken for open/closed bug issues.
- **Proposed resolution**: Update the audit-report noise exclusion to cover legacy, implement-prefixed, and design-prefixed audit titles wherever finding dedupe filters issue search results.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:600-602
- **Concern**: Design audit regex targets the wrong PR-title shape. Scenario: The plan filters and maps design runs using ^chore(larch-logs): flush design run..., but design-log-publish creates PRs titled chore(larch-logs): design run <RUN_ID>; --skill=design audits can resolve zero PRs or fail to map them
- **Proposed resolution**: Use the existing PR title shape for audit-resolve-prs.sh and audit-map-runs.sh, or explicitly change design-log-publish.sh title generation and cover both old and new title shapes

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:117-120
- **Concern**: Design token reports use final-suffixed filenames. Scenario: The plan only changes LOG_BASE to larch-logs/$SKILL, but committed design logs contain token-report-final.json and timing-report-final.json, so --skill=design will skip real runs while tests using token-report.json give false confidence
- **Proposed resolution**: For --skill=design read token-report-final.json and timing-report-final.json, with run-params.json fallback as planned; update design fixtures to mirror the committed final-suffixed file names

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/report-tokens/scripts/run-analysis.sh:1134-1138
- **Concern**: --plot-from cannot enforce skill-specific report titles. Scenario: The plan says design rejects legacy [Analysis Report] issues, but the current fetch path reads only .body; without fetching .title the analyzer cannot distinguish legacy implement reports from [Design Analysis Report] bodies
- **Proposed resolution**: Fetch title alongside body in --plot-from mode and validate title prefix before plotting, allowing legacy [Analysis Report] only for --skill=implement

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:601
- **Concern**: Plan design chore-PR regex uses commit-subject prefix flush design run but gh pr create title is chore(larch-logs): design run <RUN_ID>. Scenario: audit-resolve-prs.sh filters and audit-map-runs.sh title parse never match real merged design log PRs so design audits get empty PR lists or unmapped run dirs
- **Proposed resolution**: Align regexes with PR title chore(larch-logs): design run plus capture group; anchor tests to design-log-publish.sh not flush commit subject

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:600-601
- **Concern**: Plan matches design PR titles as flush design run, but design-log-publish creates PR titles as chore(larch-logs): design run <RUN_ID>. Scenario: /audit-runs --skill=design last/since filters and mapping skip or fail to map real design log PRs
- **Proposed resolution**: Match the existing PR title regex ^chore\(larch-logs\): design run ([0-9A-Fa-f-]+)$, or explicitly change the publisher and tests together

### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:117-122
- **Concern**: Plan only switches LOG_BASE while keeping token-report.json and timing-report.json filenames. Scenario: /report-tokens --skill=design skips committed design runs because real design logs use token-report-final.json and timing-report-final.json
- **Proposed resolution**: Use per-skill filenames or fallbacks: design reads token-report-final.json and timing-report-final.json; implement keeps the existing names

### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/skills/audit-runs/scripts/audit-scan-run.sh:311-316
- **Concern**: Design oos-category-mangle row relies on implement-only review-findings-full.jsonl, while design plan-review data is TSV under plan-review/round-N. Scenario: The proposed no-code-change scan always skips for design, giving false coverage
- **Proposed resolution**: For minimum scope, remove oos-category-mangle from scans-design.tsv until a design parser exists, or add a small design branch that reads the plan-review TSV

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:118-122
- **Concern**: Plan only switches LOG_BASE but keeps the token report filename as token-report.json while real design logs use token-report-final.json. Scenario: /report-tokens --skill=design scans larch-logs/design and skips every committed design run because the required token-report.json file is absent
- **Proposed resolution**: Add skill-specific token report selection so design reads token-report-final.json and implement reads token-report.json; update the design fixture to mirror that real filename

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:1088-1096,1134-1138
- **Concern**: Plan says --plot-from skill-scopes by report title through the issue-body parser, but the script only fetches body and the parser has no title. Scenario: /report-tokens --skill=design --plot-from N can accept a legacy [Analysis Report] issue body and plot implement-era data instead of rejecting the skill mismatch
- **Proposed resolution**: Fetch title and body for --plot-from and validate the title before plotting, or add an explicit skill marker to report bodies and validate it; add the legacy-design rejection test

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-callsite-audit, Codex-dyn-callsite-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:18 and .claude/skills/audit-runs/SKILL.md:82-83
- **Concern**: The plan permits audit-map-runs.sh to receive --log-root instead of --skill even though the proposed design mapping branch depends on --skill.. Scenario: A /audit-runs --skill design implementation could call audit-map-runs.sh with only --log-root larch-logs/design; the script would not enter the design title-parsing branch and would keep implement-style closes/body mapping.
- **Proposed resolution**: Require every SKILL.md audit-map-runs.sh call to pass --skill "$SKILL"; keep --log-root as an optional test/manual override and validate it does not conflict with the selected skill.

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-callsite-audit, Codex-dyn-callsite-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:18-60 and .claude/skills/audit-runs/scripts/audit-scan-run.sh:43-55
- **Concern**: The plan says SKILL.md should pass --skill to audit-scan-run.sh but also says audit-scan-run.sh needs no code change.. Scenario: Following the SKILL.md wiring makes audit-scan-run.sh exit with unknown argument --skill; following the no-code-change note leaves the orchestrating call without the required --skill flag.
- **Proposed resolution**: Add a minimal --skill parser/enum check to audit-scan-run.sh and its contract/tests, then pass --skill "$SKILL" alongside the centrally derived --scans-tsv "$SCANS_TSV".

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-callsite-audit, Codex-dyn-callsite-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:1134-1139 and <TMPDIR>/plan.txt:85-91
- **Concern**: The plan does not state how --skill reaches the --plot-from early-exit analyzer path or how title scoping is enforced when only the issue body is fetched.. Scenario: /report-tokens --skill design --plot-from <legacy implement analysis issue> cannot reject the legacy [Analysis Report] title if the branch still fetches only .body or calls the embedded analyzer without skill context.
- **Proposed resolution**: In run-analysis.sh, parse SKILL before the early exit, fetch title and body for --plot-from, validate title against SKILL, and pass/export SKILL into the analyzer path used for plot regeneration.

### FINDING_20:
- **Reviewer(s)**: Cursor-dyn-schema-evidence, Codex-dyn-schema-evidence
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:116-123
- **Concern**: Report-tokens design path keeps the implement token-report.json contract that design logs do not satisfy. Scenario: Current larch-logs/design has larch-tokens-*.jsonl and timing-ledger.tsv files, but zero token-report.json and zero timing-report.json files; changing only LOG_BASE to larch-logs/design makes --skill=design scan no parseable runs
- **Proposed resolution**: For a minimum-change PR, defer report-tokens --skill=design, or add an explicit reader for the current design artifacts instead of assuming token-report.json and timing-report.json exist

### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-schema-evidence, Codex-dyn-schema-evidence
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: .claude/skills/audit-runs/scripts/audit-scan-run.sh:313-315 .claude/skills/audit-runs/scripts/audit-scan-run.sh:483-488
- **Concern**: scans-design includes rows whose current scanners are hardwired to absent design artifacts. Scenario: Design logs have accepted-plan-findings.md and some execution-issues.md files, but no review-findings-full.jsonl and no execution-issues.ndjson; oos-category-mangle and execution-issues-categories would consistently skip rather than audit design data
- **Proposed resolution**: Keep scans-design.tsv to scans that work on existing design artifacts, such as cache-freshness and oos-silent-drop, unless this PR also adapts those scanners to the design artifact names

### FINDING_22:
- **Reviewer(s)**: Cursor-dyn-regex-anchor, Codex-dyn-regex-anchor
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:1134-1138
- **Concern**: --plot-from cannot enforce the planned skill title boundary because the current path fetches only .body, while the plan only says to update the issue-body parser.. Scenario: Passing --skill=design --plot-from for a legacy [Analysis Report] issue, or --skill=implement for a [Design Analysis Report] issue, can still load raw records because no title is available to validate.
- **Proposed resolution**: Fetch title with the body and validate it before parsing: implement accepts ^\[(Analysis Report|Implement Analysis Report)\] and design accepts ^\[Design Analysis Report\] only.

### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-regex-anchor, Codex-dyn-regex-anchor
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:600-602
- **Concern**: The plan anchors design PR matching on ^chore\(larch-logs\): flush design run ..., but the current publisher creates PRs titled chore(larch-logs): design run <RUN_ID>.. Scenario: --skill=design last/since filtering and PR-to-run mapping would skip real design-log PRs or fail to resolve run dirs.
- **Proposed resolution**: Use the existing PR title anchor ^chore\(larch-logs\): design run ([0-9A-F-]+)$ for PR title matching, unless the plan intentionally changes design-log-publish.sh too.
