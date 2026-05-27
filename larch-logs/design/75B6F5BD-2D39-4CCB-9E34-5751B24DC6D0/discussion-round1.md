## Decision 1: Scope — mirror fix to write-final-report.sh
- **Question**: Apply the same fallback-distinguishability fix to skills/implement/scripts/write-final-report.sh, or design-side only?
- **Resolution**: Both. Apply to both render-final-summary.sh (Step 1c question 1).
- **Source**: user

## Decision 2: Failure signal contract
- **Question**: Should the script exit non-zero on fallback, or only mark the output file?
- **Resolution**: Mark output only; keep exit 0. Preserves caller contract at every callsite (SKILL.md Step 0b, 5c items 8/10, Final-summary-block fences).
- **Source**: user

## Decision 3: Marker visibility surface
- **Question**: Where must the fallback marker be visible — HTML comment only, banner + comment, or sidecar file?
- **Resolution**: Visible banner inside the body AND HTML comment. Banner surfaces at top chat via the shared post-publish full-body emit rule.
- **Source**: user

## Decision 4: Banner placement vs audit-parser invariant
- **Question**: Where does the banner go inside final-summary.md without breaking downstream parsers?
- **Resolution**: Banner must NOT be the first non-empty line. scripts/verify-run-log-completeness.sh and .claude/skills/audit-runs/scripts/audit-scan-run.sh anchor on the first non-empty line matching the terminal-outcome suffix regex (scripts/run-log-terminal-outcomes.inc.bash). Place the banner AFTER the `## ... run <RUN_ID> — <OUTCOME>` heading, before the bullet list.
- **Source**: codebase

## Decision 5: Intermediate `--cost-unavailable` retry stage in write-final-report.sh
- **Question**: Does the "degraded fallback" marker apply to the intermediate `--cost-unavailable` render-run-summary retry, or only to the terminal compose_self_fallback?
- **Resolution**: Only the terminal compose_self_fallback. The intermediate stage still produces a full render-run-summary body and already exposes its degradation via `- **Cost**: N/A`. The OOS issue is specifically about the printf-based compose_self_fallback path.
- **Source**: codebase

## Decision 6: Test coverage scope
- **Question**: Must both regression harnesses (test-render-final-summary.sh, test-write-final-report.sh) gain assertions for the new marker?
- **Resolution**: Yes — same-PR test updates per `.claude/rules/script-md-siblings.md`. Add a single fallback-marker test case per harness (force invoke_render / run_body_render to fail and assert the banner + HTML comment appear in the generated final-summary.md).
- **Source**: codebase (rule)
