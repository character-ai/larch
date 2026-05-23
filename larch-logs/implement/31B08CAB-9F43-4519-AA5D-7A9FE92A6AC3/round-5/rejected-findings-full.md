### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: correctness: scripts/lint-foreground-markers.sh:97-106
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Banner check is substring-anywhere in 20-line window not leading paragraph line per plan A stray prose line containing the banner sentence mid-paragraph could satisfy the window without the intended standalone warning line Tighten match to leading paragraph line or relax the plan and sibling MD contract to substring matching
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: code-quality: AGENTS.md:184
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] References make lint-foreground-markers instead of acceptance alias make lint-foreground Minor operator confusion only; both targets exist Point AGENTS at make lint-foreground
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_16: risk-integration: scripts/lint-foreground-markers.sh:62-69
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] git ls-files omits untracked markdown so the linter can skip new skills until git add Untracked skills/*/SKILL.md can pass pre-commit/make lint while still violating marker rules once later added Match lint-bash32 enumeration flags or document the intentional gap in lint-foreground-markers.md
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: risk-integration: scripts/test-lint-foreground-markers.sh:498-515
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Hard-coded minimum grep counts for Family A docs Legitimate doc edits that reduce run_in_background mentions break CI until harness floors are manually bumped Add rationale comments or stabilize on non-count assertions
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: risk-integration: scripts/test-lint-foreground-markers.sh:400-420
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Multi-anchor failure tested without a dual-anchor success case Low risk gap in regression signal for per-anchor comment requirements Add a two-anchor clean fixture in one fence
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: security: skills/design/scripts/file-design-oos.sh:118-135,372-390
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] URLs from parsed issue stdout / OOS_FILE_MAP are written into markdown without strict URL validation A tampered or malformed stdout file could inject extra markdown lines or break OOS blocks while still looking like a URL field Validate each URL against a strict https GitHub issues pattern (or parse+allowlist) before appending to the accepted md
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: risk-integration: scripts/oos-disposition-shared.inc.bash:9-17
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] GH_HOST is only dot-escaped before embedding in grep -E host alternation Synthetic GH_HOST with ERE metacharacters could distort URL counting Validate hostname charset or fully escape ERE metacharacters in GH_HOST
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: correctness: scripts/lint-foreground-markers.sh:174-179,254-264
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Comment-prefixed heredoc openers are ignored so heredoc state can desync versus real shell Heredoc bodies or faux-heredoc doc regions can false-require markers or miss real heredoc skipping Document edge case or parse commented << openers
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: risk-integration: scripts/lint-foreground-markers.sh:62-69,scripts/lint-foreground-markers.md:3
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Tracked-only git enumeration plus always_run hook Untracked new skill markdown never fails foreground lint until git add; surprises first-time authors Document tracked-only expectation in docs/linting.md or add optional unstaged scan mode
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: correctness: scripts/oos-disposition-shared.inc.bash:47-50
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Strict Filed URL grep anchors URL to end of line Extra text on the same Filed URL list line drops the URL from strict_part and can fail the gate despite filed issues Allow trailing prose after URL or document URL-only line contract
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: risk-integration: AGENTS.md:56
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] lint-foreground-markers vs test-lint-foreground-markers naming Typo runs harness instead of lint or vice versa, slowing feedback or missing violations Prefer make lint-foreground in AGENTS and separate harness naming
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/implement/SKILL.md:1563-1568
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Redundant repeated canonical foreground banners and long bespoke text stack before a single ship-pr fence. Future edits can drop one duplicate and fail lint, or desynchronize NEVER #16 prose from the canonical marker. Keep a single canonical banner plus one consolidated prose block without repeating the identical banner line.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: risk-integration: scripts/test-lint-foreground-markers.sh:498-515
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Family A regression uses grep count floors for run_in_background true across large markdown files. Harmless doc reflow that removes duplicate YAML examples could shrink counts and fail CI despite unchanged parallel semantics. Replace raw counts with structural anchors inside the known Family A fences.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: code-quality: scripts/test-lint-foreground-markers.sh:357-400
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness case numbering skips index 16 between 15 and 17. Slightly harder traceability when mapping failures to documented case lists. Renumber cases sequentially.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

