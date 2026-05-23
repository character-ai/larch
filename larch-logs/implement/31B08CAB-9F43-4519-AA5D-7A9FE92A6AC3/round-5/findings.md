### FINDING_1: architecture: merge-base..HEAD (e.g. skills/implement/scripts/oos-disposition-gate.sh; skills/design/scripts/file-design-oos.sh; CHANGELOG.md; larch-logs/**)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Unrelated semantic workflow and log artifacts are merged with the foreground-marker documentation/lint work, violating the stated markers-only semantics constraint for the Family B feature. Reviewers cannot isolate breadcrumb/turn-boundary doc changes from OOS disposition and cross-session filing behavior; a regression in either area blocks the unrelated feature’s merge train. Split into separate PRs or rewrite the feature contract so semantic changes are explicitly in-scope.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/implement/scripts/oos-disposition-gate.md:24-25
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Exit-code table mixes filed_urls wording with filed == 0 for the same aggregate. Operators debugging exit 1 may think filed_urls semantics diverged from the failure predicate. Use one consistent metric name in both rows (optionally note the shell variable name once).
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/implement/SKILL.md:1563-1568
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Redundant repeated canonical foreground banners and long bespoke text stack before a single ship-pr fence. Future edits can drop one duplicate and fail lint, or desynchronize NEVER #16 prose from the canonical marker. Keep a single canonical banner plus one consolidated prose block without repeating the identical banner line.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: AGENTS.md:56
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] AGENTS cites only make lint-foreground-markers, omitting the documented lint-foreground alias. Operators following the shorter documented target may miss the AGENTS cross-link. Mention both Makefile aliases in the same bullet.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: BASH_AUTHORING.md:232
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Section title diverges from the plan’s Foreground Default for Blocking Script Calls wording. Cross-issue grep and plan-to-doc audits do not line up verbatim. Align the heading text with the plan phrase or add it as an alternate title in parentheses.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: scripts/test-lint-foreground-markers.sh:498-515
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Family A regression uses grep count floors for run_in_background true across large markdown files. Harmless doc reflow that removes duplicate YAML examples could shrink counts and fail CI despite unchanged parallel semantics. Replace raw counts with structural anchors inside the known Family A fences.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/test-lint-foreground-markers.sh:357-400
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness case numbering skips index 16 between 15 and 17. Slightly harder traceability when mapping failures to documented case lists. Renumber cases sequentially.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: larch-logs/**
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Massive committed run-log diffs inflate branch review surface. Review latency increases when searching for functional changes. Accept as repo policy; optionally split log flush commits from code commits for reviewer ergonomics (process guidance only).
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/lint-foreground-markers.sh:248-281;scripts/test-lint-foreground-markers.sh:482-496
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Backslash-split basename yields no line containing full denylisted token; *.sh fast-path skips lines so no anchor; Case 24 still expects pass A fenced example can split ship-pr.sh / collect-agent-results.sh across lines so CI passes without banner/comment despite a human-readable invocation Join continuations before matching; or change Case 24 to assert failure/remove; or forbid split basenames in authoring + add a true positive continuation fixture
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/implement/scripts/oos-disposition-gate.sh:173-184;scripts/oos-disposition-shared.inc.bash:40-61;CHANGELOG.md;.claude-plugin/plugin.json;skills/design/scripts/file-design-oos.sh;larch-logs/**
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Bundle disposes strict URL counting design OOS persistence changelog version and run logs with foreground-marker work Operators reviewing a foreground-marker PR also absorb behavior and release-surface changes unrelated to Bash tool foregrounding Split branches or re-scope the issue acceptance to include disposition/version/log work explicitly
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/lint-foreground-markers.sh:97-106
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Banner check is substring-anywhere in 20-line window not leading paragraph line per plan A stray prose line containing the banner sentence mid-paragraph could satisfy the window without the intended standalone warning line Tighten match to leading paragraph line or relax the plan and sibling MD contract to substring matching
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/oos-disposition-shared.inc.bash:47-50
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Strict Filed URL grep anchors URL as end-of-line only Valid line `- **Filed URL**: https://github.com/o/i/1 note` counts as zero strict URLs and can fail disposition incorrectly Allow trailing commentary after URL or document EOL-only URL as required
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: BASH_AUTHORING.md:232-250
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Section heading text diverges from plan literal for section 4 Grep-based doc audits keyed to exact plan title may miss the shipped heading Align heading string with plan or update plan wording
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: AGENTS.md:184
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] References make lint-foreground-markers instead of acceptance alias make lint-foreground Minor operator confusion only; both targets exist Point AGENTS at make lint-foreground
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] code-quality: scripts/test-lint-foreground-markers.sh:498-515
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Family A floor check is count-only Cannot detect token swaps that preserve grep counts Optionally add structural anchors later; not required for this review
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/lint-foreground-markers.sh:62-69
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] git ls-files omits untracked markdown so the linter can skip new skills until git add Untracked skills/*/SKILL.md can pass pre-commit/make lint while still violating marker rules once later added Match lint-bash32 enumeration flags or document the intentional gap in lint-foreground-markers.md
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/test-lint-foreground-markers.sh:498-515
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Hard-coded minimum grep counts for Family A docs Legitimate doc edits that reduce run_in_background mentions break CI until harness floors are manually bumped Add rationale comments or stabilize on non-count assertions
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/test-lint-foreground-markers.sh vs scripts/lint-foreground-markers.sh:18-28
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness case for step2-implement.sh (and thin coverage for some denylist shapes) Regex regression for rare basename spellings could slip past CI Add minimal positive fixtures per denylist basename used in real skills
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/test-lint-foreground-markers.sh:400-420
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Multi-anchor failure tested without a dual-anchor success case Low risk gap in regression signal for per-anchor comment requirements Add a two-anchor clean fixture in one fence
- **Suggested revision**: Address the concern above.

### FINDING_20: security: skills/design/scripts/file-design-oos.sh:118-135,372-390
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] URLs from parsed issue stdout / OOS_FILE_MAP are written into markdown without strict URL validation A tampered or malformed stdout file could inject extra markdown lines or break OOS blocks while still looking like a URL field Validate each URL against a strict https GitHub issues pattern (or parse+allowlist) before appending to the accepted md
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/oos-disposition-shared.inc.bash:9-17
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] GH_HOST is only dot-escaped before embedding in grep -E host alternation Synthetic GH_HOST with ERE metacharacters could distort URL counting Validate hostname charset or fully escape ERE metacharacters in GH_HOST
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] risk-integration: skills/implement/scripts/oos-disposition-gate.sh:55-64
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] COMMIT_RANGE passed to git without extra hardening unchanged by this branch Unchanged git rev parsing trust model vs prior revision No change required for this feature branch; harden separately if untrusted input is ever wired here
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: scripts/lint-foreground-markers.sh:139-140
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Long-line bail-out skips anchor detection for denylisted invocations on one >12000-char line Linter exits 0 while a fenced one-line Family B example still documents a blocking script call without markers enforced Treat overlong anchor lines as errors or warn+fail; or document explicit false-negative
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: scripts/lint-foreground-markers.sh:174-179,254-264
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Comment-prefixed heredoc openers are ignored so heredoc state can desync versus real shell Heredoc bodies or faux-heredoc doc regions can false-require markers or miss real heredoc skipping Document edge case or parse commented << openers
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/lint-foreground-markers.sh:287
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Symlink SKILL.md paths are skipped entirely Forks using symlinked skill files bypass Family B marker enforcement Resolve symlink to regular file and lint or document unsupported layout
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/lint-foreground-markers.sh:62-69,scripts/lint-foreground-markers.md:3
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Tracked-only git enumeration plus always_run hook Untracked new skill markdown never fails foreground lint until git add; surprises first-time authors Document tracked-only expectation in docs/linting.md or add optional unstaged scan mode
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: scripts/oos-disposition-shared.inc.bash:47-50
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Strict Filed URL grep anchors URL to end of line Extra text on the same Filed URL list line drops the URL from strict_part and can fail the gate despite filed issues Allow trailing prose after URL or document URL-only line contract
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: AGENTS.md:56
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] lint-foreground-markers vs test-lint-foreground-markers naming Typo runs harness instead of lint or vice versa, slowing feedback or missing violations Prefer make lint-foreground in AGENTS and separate harness naming
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] architecture: CHANGELOG.md:22-30,larch-logs/**
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Multiple independent features under one PATCH version Release bisect narratives bundle unrelated behavioral changes Pre-existing release bundling practice
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: BASH_AUTHORING.md:50
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Section §4 heading text does not match the plan acceptance title "Foreground Default for Blocking Script Calls". Operators or tooling that quote the acceptance title will point at a non-existent heading; cross-doc "§4" references become ambiguous if multiple generations of prose assume the old title. Rename §4 to the acceptance title or update acceptance and all cross-references to the shipped title consistently.
- **Suggested revision**: Address the concern above.

