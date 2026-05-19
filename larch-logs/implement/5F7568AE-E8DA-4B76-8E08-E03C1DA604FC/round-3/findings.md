### FINDING_1: **Important** `architecture` `skills/review/references/heavy-worker.md:69` still defines `review-summary.json` as `schema_version: 1` and has no `panel` object. Standalone `/review --diff --subagent --dynamic-archetypes 2` follows this heavy-worker contract rather than `emit-tally.sh`, so it can produce a v1 summary with no `panel.scout_status`, `dynamic_slot_count`, `static_slot_count`, or `total_slot_count`, defeating the new observability contract for subagent review. Update the heavy-worker schema and instructions to emit schema v2 with the same panel fields, or route the heavy worker through the same `emit-tally.sh` contract.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `architecture` `skills/review/references/heavy-worker.md:69` still defines `review-summary.json` as `schema_version: 1` and has no `panel` object. Standalone `/review --diff --subagent --dynamic-archetypes 2` follows this heavy-worker contract rather than `emit-tally.sh`, so it can produce a v1 summary with no `panel.scout_status`, `dynamic_slot_count`, `static_slot_count`, or `total_slot_count`, defeating the new observability contract for subagent review. Update the heavy-worker schema and instructions to emit schema v2 with the same panel fields, or route the heavy worker through the same `emit-tally.sh` contract.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `risk-integration` `scripts/refresh-run-logs.sh:71` writes `final-summary.md` before the common path has a PR URL. On a clean no-retry run, Trigger C runs before PR creation, so `write-final-report.sh` records `PR: N/A`; after `scripts/ship-pr.sh:969` sets `PR_URL`, the post-PR-create larch-log commit at `scripts/ship-pr.sh:992-1000` only updates the manifest and never regenerates `final-summary.md`. After merge, the post-merge sentinel still suppresses committing the Step 17/18 regenerated file, so the committed run-log keeps stale `PR: N/A`. Fix by calling `write-final-report.sh` after `state_set_many PR_NUMBER ... PR_URL ...` and before the post-PR-create `larch-log.sh commit`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/refresh-run-logs.sh:71` writes `final-summary.md` before the common path has a PR URL. On a clean no-retry run, Trigger C runs before PR creation, so `write-final-report.sh` records `PR: N/A`; after `scripts/ship-pr.sh:969` sets `PR_URL`, the post-PR-create larch-log commit at `scripts/ship-pr.sh:992-1000` only updates the manifest and never regenerates `final-summary.md`. After merge, the post-merge sentinel still suppresses committing the Step 17/18 regenerated file, so the committed run-log keeps stale `PR: N/A`. Fix by calling `write-final-report.sh` after `state_set_many PR_NUMBER ... PR_URL ...` and before the post-PR-create `larch-log.sh commit`.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: larch-logs/implement/5F7568AE-E8DA-4B76-8E08-E03C1DA604FC/
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Committed implement run-log directory with embedded plan text is ancillary to the three observability code changes. PR noise / run-log hygiene only. None for plan fidelity; treat as normal chore(larch-logs) unless policy changes.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: larch-logs/implement/5F7568AE-E8DA-4B76-8E08-E03C1DA604FC/plan-goals-test.md:42-101
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Embedded plan text predates SKILL Part B wording drift Historical committed run-log not runtime contract None for code; optional log hygiene only
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/test-write-final-report.sh:433-434
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Added stall-status assertion not listed in the observability plan. No plan traceability impact. None unless tests are considered part of formal acceptance scope.
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: scripts/refresh-run-logs.sh:30-33 skills/implement/SKILL.md:1659-1690
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] final-summary refresh tied to pre-merge refresh; MERGE_RESULT merged skips helper Workflows that never hit refresh before merge may differ from Step-7a spec Document or add deterministic pre-merge write if required
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: skills/implement/SKILL.md:387-389 vs scripts/refresh-run-logs.sh:171-172
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Part B implemented via refresh-run-logs + SKILL prohibition, not Step 7a write-final-report before larch-log commit as written in plan/feature text. Plan reviewers mark Part B incomplete; behavior depends on refresh triggers vs explicit Step 7a contract. Reconcile SKILL/plan text with chosen mechanism, or implement the plan’s Step 7a placement.
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: skills/implement/scripts/write-final-report.md:79-90 (diff hunk)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan Part B asked to document pre-bump timing; docs describe deferred post-ship-pr / Step 17-18 usage instead. Readers following the written plan look for Step 7a guidance that the doc explicitly steers away from. Align documentation with the authoritative timing contract (refresh-only vs Step 7a).
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:684-703
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Aggregate body_start logic can point past EOF when # Rejected Findings has no following blank line. A two-line compact ledger `# Rejected Findings` immediately followed by `### FINDING_…` yields `## Round N` plus an empty body in the run-root aggregate and loses all rejected prose for that round. After detecting the title line set body_start to the first following non-empty non-title line or clamp sed start to in-range line numbers.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: feature_description Part A vs branch diff
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Feature text cites dispatch-panel.sh as the pass-through surface; diff does not modify dispatch-panel.sh. Strict traceability to that file name is weakened even though review-core.sh already ingests dispatch KV output into emit_args. Optional narrative fix or a discoverability comment; no code change required if behavior is already correct.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/implement/SKILL.md:1659-1689;scripts/refresh-run-logs.sh:30-90
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Part B diverges from the implementation plan: SKILL forbids Step 7a write-final-report; behavior moved into refresh-run-logs before larch-log commit instead of the plan’s Step 7a insertion. refresh-run-logs.sh exits at MERGE_RESULT merged|admin_merged|already_merged before write-final-report runs; post-merge sentinel still blocks larch-log commit, so committed final-summary.md depends on a pre-merge refresh hitting write-final-report rather than the plan’s pre-bump Step 7a commit bundle. Either implement the plan’s Step 7a call (accepting provisional PR_URL) or revise the plan and prove ship-pr always triggers a qualifying pre-merge refresh.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/review-and-fix/scripts/review-and-fix.sh:442-453
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] render_rejected_findings_for_tally title strip is strict line 1 BOM/trailing space leaves duplicate title in tally body Strip BOM / trim or use looser pattern
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/review-and-fix/scripts/review-and-fix.sh:552-564
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] render_rejected_findings_for_tally only strips '# Rejected Findings' on NR==1. BOM or leading whitespace prevents skip; duplicate heading in code-review-tally body. Skip leading empty lines / strip BOM before the NR==1 heading test.
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

### FINDING_18: risk-integration: scripts/refresh-run-logs.sh:171-172
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] write-final-report.sh is stderr-discarded and errors ignored via '2>/dev/null || true'. Upsert/render fails silently; refresh commit can omit final-summary.md with no breadcrumb. Capture rc/stderr like other refresh steps or handle failures explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/refresh-run-logs.sh:171-172
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] write-final-report.sh added with stderr discarded and || true write-final-report can fail (gh auth template I/O) while refresh still commits other artifacts; CI happy-path test does not detect regression vs missing final-summary. Surface failures via append-tool-failure or fail refresh when final-summary write fails; extend test-refresh-run-logs with a forced-failure stub case.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/refresh-run-logs.sh:71-72
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] write-final-report errors swallowed by 2>/dev/null || true Silent stale final-summary in committed run-log Capture rc/stderr like other ship-pr failure paths
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/implement/SKILL.md:387-388 vs scripts/refresh-run-logs.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Part B implemented via refresh-run-logs instead of Step 7a per plan text If a future merge path skips refresh-run-logs before sentinel final-summary may still be omitted (unproven in diff). Map all merge paths to refresh or add a targeted ship-pr integration assertion.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: skills/review/scripts/emit-tally.sh:1105-1106
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] New integer validation for slot flags has no negative harness test Invalid CLI values could regress without CI signal. Add one test expecting non-zero exit for bad --dynamic-slots/--static-slot-count.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: skills/review/scripts/emit-tally.sh:131 skills/review/scripts/emit-tally.md:1-5
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] schema_version bumped to 2 with new panel Strict external consumers on schema_version 1 break Document migration or widen consumer version checks
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: skills/review/scripts/review-core.sh:356-394
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] zero-findings path now hard-calls emit-tally under set -e emit-tally failure aborts entire review round before zero-findings status Wrap emit with controlled failure handling or preflight tally file
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: skills/review/scripts/review-core.sh:381-394
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Zero-findings path now hard-depends on emit-tally succeeding under set -e. emit-tally or jq failure turns a previously successful zero-findings exit into hard failure / Step 5 stall. Wrap emit as best-effort with explicit fallback review-summary.json, or preflight tally paths.
- **Suggested revision**: Address the concern above.

