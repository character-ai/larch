### FINDING_11: correctness: skills/implement/SKILL.md:1659-1689;scripts/refresh-run-logs.sh:30-90
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Part B diverges from the implementation plan: SKILL forbids Step 7a write-final-report; behavior moved into refresh-run-logs before larch-log commit instead of the plan’s Step 7a insertion. refresh-run-logs.sh exits at MERGE_RESULT merged|admin_merged|already_merged before write-final-report runs; post-merge sentinel still blocks larch-log commit, so committed final-summary.md depends on a pre-merge refresh hitting write-final-report rather than the plan’s pre-bump Step 7a commit bundle. Either implement the plan’s Step 7a call (accepting provisional PR_URL) or revise the plan and prove ship-pr always triggers a qualifying pre-merge refresh.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: skills/review-and-fix/scripts/review-and-fix.sh:684-702
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] body_start awk uses END {print NR+1} when no blank line follows # Rejected Findings Aggregate uses sed from line 3 on a 2-line H1+prose file and drops all rejected prose for that round (empty ## Round N section; tally body loses content). Default body_start to 2 when H1 matches and no blank delimiter is found or require a blank line after H1 in producers.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: skills/review-and-fix/scripts/review-and-fix.sh:684-703
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] write_rejected_findings_aggregate body_start awk uses first blank line of entire file after matching first non-empty line as heading; does not anchor after the title. (a) # Rejected Findings then immediate body with no blank line: END prints past EOF, sed drops all prose for that round. (b) Leading blank before title: body_start points into title block, duplicate # Rejected Findings inside ## Round N. After detecting top-level heading, compute body_start only on lines after it, or strip that heading block explicitly before appending.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: skills/review-and-fix/scripts/review-and-fix.sh:684-703
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] body_start awk uses END print NR+1 when no blank line after title sed body_start can be past EOF so a round's prose is omitted from rejected-findings aggregate Use body_start=2 after title or awk that skips only the title line
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: skills/review-and-fix/scripts/review-and-fix.sh:684-703
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] body_start awk plus sed slice can skip all body lines when the file starts with # Rejected Findings but has no blank line before the next content A round file like line1 # Rejected Findings and line2 ### prose yields body_start past EOF and sed prints nothing so rejected prose is missing from the run-root aggregate and downstream tally excerpts while other rounds still trigger the full-detail path Compute body_start relative to the heading without requiring a blank separator or validate and fall back to body_start=2 after heading line validate body_start is integer in range 1..line_count before sed
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** `risk-integration` `scripts/refresh-run-logs.sh:71` writes `final-summary.md` before the common path has a PR URL. On a clean no-retry run, Trigger C runs before PR creation, so `write-final-report.sh` records `PR: N/A`; after `scripts/ship-pr.sh:969` sets `PR_URL`, the post-PR-create larch-log commit at `scripts/ship-pr.sh:992-1000` only updates the manifest and never regenerates `final-summary.md`. After merge, the post-merge sentinel still suppresses committing the Step 17/18 regenerated file, so the committed run-log keeps stale `PR: N/A`. Fix by calling `write-final-report.sh` after `state_set_many PR_NUMBER ... PR_URL ...` and before the post-PR-create `larch-log.sh commit`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/refresh-run-logs.sh:71` writes `final-summary.md` before the common path has a PR URL. On a clean no-retry run, Trigger C runs before PR creation, so `write-final-report.sh` records `PR: N/A`; after `scripts/ship-pr.sh:969` sets `PR_URL`, the post-PR-create larch-log commit at `scripts/ship-pr.sh:992-1000` only updates the manifest and never regenerates `final-summary.md`. After merge, the post-merge sentinel still suppresses committing the Step 17/18 regenerated file, so the committed run-log keeps stale `PR: N/A`. Fix by calling `write-final-report.sh` after `state_set_many PR_NUMBER ... PR_URL ...` and before the post-PR-create `larch-log.sh commit`.
- **Suggested revision**: Address the concern above.


### FINDING_6: architecture: scripts/refresh-run-logs.sh:30-33 skills/implement/SKILL.md:1659-1690
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] final-summary refresh tied to pre-merge refresh; MERGE_RESULT merged skips helper Workflows that never hit refresh before merge may differ from Step-7a spec Document or add deterministic pre-merge write if required
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:684-703
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Aggregate body_start logic can point past EOF when # Rejected Findings has no following blank line. A two-line compact ledger `# Rejected Findings` immediately followed by `### FINDING_…` yields `## Round N` plus an empty body in the run-root aggregate and loses all rejected prose for that round. After detecting the title line set body_start to the first following non-empty non-title line or clamp sed start to in-range line numbers.
- **Suggested revision**: Address the concern above.


