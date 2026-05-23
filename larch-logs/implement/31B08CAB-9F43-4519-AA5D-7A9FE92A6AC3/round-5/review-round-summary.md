# Review Round 5

- Mode: `diff`
- 9 accepted, 14 rejected (13 exonerated)

## Accepted Findings

### FINDING_1: architecture: merge-base..HEAD (e.g. skills/implement/scripts/oos-disposition-gate.sh; skills/design/scripts/file-design-oos.sh; CHANGELOG.md; larch-logs/**)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Unrelated semantic workflow and log artifacts are merged with the foreground-marker documentation/lint work, violating the stated markers-only semantics constraint for the Family B feature. Reviewers cannot isolate breadcrumb/turn-boundary doc changes from OOS disposition and cross-session filing behavior; a regression in either area blocks the unrelated feature’s merge train. Split into separate PRs or rewrite the feature contract so semantic changes are explicitly in-scope.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: skills/implement/scripts/oos-disposition-gate.sh:173-184;scripts/oos-disposition-shared.inc.bash:40-61;CHANGELOG.md;.claude-plugin/plugin.json;skills/design/scripts/file-design-oos.sh;larch-logs/**
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Bundle disposes strict URL counting design OOS persistence changelog version and run logs with foreground-marker work Operators reviewing a foreground-marker PR also absorb behavior and release-surface changes unrelated to Bash tool foregrounding Split branches or re-scope the issue acceptance to include disposition/version/log work explicitly
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: scripts/oos-disposition-shared.inc.bash:47-50
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Strict Filed URL grep anchors URL as end-of-line only Valid line `- **Filed URL**: https://github.com/o/i/1 note` counts as zero strict URLs and can fail disposition incorrectly Allow trailing commentary after URL or document EOL-only URL as required
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: scripts/test-lint-foreground-markers.sh vs scripts/lint-foreground-markers.sh:18-28
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness case for step2-implement.sh (and thin coverage for some denylist shapes) Regex regression for rare basename spellings could slip past CI Add minimal positive fixtures per denylist basename used in real skills
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/implement/scripts/oos-disposition-gate.md:24-25
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Exit-code table mixes filed_urls wording with filed == 0 for the same aggregate. Operators debugging exit 1 may think filed_urls semantics diverged from the failure predicate. Use one consistent metric name in both rows (optionally note the shell variable name once).
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: scripts/lint-foreground-markers.sh:139-140
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Long-line bail-out skips anchor detection for denylisted invocations on one >12000-char line Linter exits 0 while a fenced one-line Family B example still documents a blocking script call without markers enforced Treat overlong anchor lines as errors or warn+fail; or document explicit false-negative
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: scripts/lint-foreground-markers.sh:287
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Symlink SKILL.md paths are skipped entirely Forks using symlinked skill files bypass Family B marker enforcement Resolve symlink to regular file and lint or document unsupported layout
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: AGENTS.md:56
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] AGENTS cites only make lint-foreground-markers, omitting the documented lint-foreground alias. Operators following the shorter documented target may miss the AGENTS cross-link. Mention both Makefile aliases in the same bullet.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/lint-foreground-markers.sh:248-281;scripts/test-lint-foreground-markers.sh:482-496
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Backslash-split basename yields no line containing full denylisted token; *.sh fast-path skips lines so no anchor; Case 24 still expects pass A fenced example can split ship-pr.sh / collect-agent-results.sh across lines so CI passes without banner/comment despite a human-readable invocation Join continuations before matching; or change Case 24 to assert failure/remove; or forbid split basenames in authoring + add a true positive continuation fixture
- **Suggested revision**: Address the concern above.


