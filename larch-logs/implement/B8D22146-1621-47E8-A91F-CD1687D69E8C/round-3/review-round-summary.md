# Review Round 3

- Mode: `diff`
- Accepted findings: 4
- Rejected findings: 13
- Exonerated findings: 2
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Important** (`correctness`) — `scripts/dispatch-code-voters.sh:101` / `skills/review/scripts/tally-code-votes.sh:202`: fallback voters that run on Claude write parse-rate diagnostics as `claude-parse-rate-diag.txt`, but the tally later maps voter files by output basename, so `codex-vote-output-phase3.txt` maps to `codex-parse-rate-diag.txt`. Concrete scenario: Codex is unavailable, voter 2 falls back to Claude, both original and retry emit narrative output, and voter 1 Claude is valid; dispatch marks voter 2 `NOT_SUBSTANTIVE`, but tally removes voter 1 because `claude-parse-rate-diag.txt` exists and still includes voter 2’s narrative file in the effective quorum. Use a slot/output-specific diagnostic identity, or pass parse-rate status/path metadata from dispatch to tally, and add a fallback-Claude parse-rate regression.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** (`correctness`) — `scripts/dispatch-code-voters.sh:101` / `skills/review/scripts/tally-code-votes.sh:202`: fallback voters that run on Claude write parse-rate diagnostics as `claude-parse-rate-diag.txt`, but the tally later maps voter files by output basename, so `codex-vote-output-phase3.txt` maps to `codex-parse-rate-diag.txt`. Concrete scenario: Codex is unavailable, voter 2 falls back to Claude, both original and retry emit narrative output, and voter 1 Claude is valid; dispatch marks voter 2 `NOT_SUBSTANTIVE`, but tally removes voter 1 because `claude-parse-rate-diag.txt` exists and still includes voter 2’s narrative file in the effective quorum. Use a slot/output-specific diagnostic identity, or pass parse-rate status/path metadata from dispatch to tally, and add a fallback-Claude parse-rate regression.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/review/scripts/tally-code-votes.sh:235-257
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Zero effective voters early exit omits voter parse-rate banner block that only runs when EFFECTIVE_VOTERS>=1. All voter files present but parse-degraded yields main-agent path with generic zero-judge warning only; no explicit parse-rate narrative in voting-tally.md; tests do not assert that banner. Emit parse-rate-aware warnings on early exit when VOTER_PARSE_FAILED_COUNT>0 and ELIGIBLE_VOTERS>0 or share banner helper before return.
- **Suggested revision**: Address the concern above.


### FINDING_7: code-quality: scripts/dispatch-code-voters.sh:99-113 skills/review/scripts/tally-code-votes.sh:198-208
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicate voter_parse_rate_diag_path helpers with divergent capabilities (optional voter_tool vs basename-only). Future change updates only one copy; tally may not see a diag file dispatch wrote (or the reverse), skewing EFFECTIVE_VOTERS and banners. Share one sourced helper or designate a single authoritative path and delete the duplicate.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/review/scripts/tally-code-votes.sh:198-232
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Tally excludes any voter whose canonical parse-rate diag file exists in REVIEW_TMPDIR, with no binding to the current voter output. A prior NOT_SUBSTANTIVE run leaves skills/review/scripts/tally-code-votes.sh-style diag paths under REVIEW_TMPDIR; later the operator drops in fresh structured claude-vote-output.txt (or re-runs tally only) without deleting claude-parse-rate-diag.txt. EFFECTIVE_VOTER_FILES omits Claude, EFFECTIVE_VOTERS and per-finding outcomes shift incorrectly. Bind diag validity to the voter file (metadata or colocated diag), or clear canonical diags at the start of a voter dispatch/tally run for that tmpdir.
- **Suggested revision**: Address the concern above.


