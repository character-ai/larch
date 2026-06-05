### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Codex-dyn-publish-surface, Codex-dyn-round-semantics
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:59
- **Concern**: Design OOS grep counts every voting-tally OOS row, not accepted-only. Scenario: Architecture §18 and binding goal require per-round accepted OOS, but `_emit_round_timing_row` uses `grep -cE '^\| OOS_[0-9]+ \|'` on `voting-tally.md`, which also matches exonerated/rejected OOS (e.g. `| OOS_1 | ... | exonerated |`). `rounds[].oos` is inflated vs accepted OOS and vs Step 5b filing.
- **Proposed resolution**: Count only accepted tally rows, e.g. `grep -cE '^\| OOS_[0-9]+ \|.*\| accepted \|' "$DESIGN_TMPDIR/voting-tally.md"` (keep `[[ -f ... ]]` guard). Mirror the filter in `scripts/test-timing-report.sh` design fixtures and `timing-report.md` if it describes OOS semantics.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:470-504
- **Concern**: Design round oos count plan counts every OOS tally row instead of accepted OOS only. Scenario: The proposed grep ^\| OOS_[0-9]+ \| counts rejected or exonerated OOS rows too, so timing-report.json reports inflated oos counts for /design rounds with non-accepted OOS items
- **Proposed resolution**: Filter voting-tally.md by both OOS item id and Result accepted, for example with awk over the Findings table result column, while still reading voting-tally.md so security-accepted OOS rows are included

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:180-388
- **Concern**: Step 5 round timing would stop immediately after _implement_round_body. Scenario: The same fix-applied round then runs relevant checks, optional lint-fix retries, and continuation/terminal gates, so duration_seconds can miss minutes of round work
- **Proposed resolution**: Delay round_end and record-round for fix-applied paths until immediately before each later continue or exit; use a small helper to avoid duplicating the ledger call

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:59 (plan _emit_round_timing_row)
- **Concern**: Rejected-count grep uses a trailing colon on FINDING_N headings. Scenario: Plan/_emit uses `^### \[Plan Review\] FINDING_[0-9]+:` but tally writes `### [Plan Review] FINDING_N` (no colon); per-round `rejected` stays 0 in JSON/run logs while tally shows rejections
- **Proposed resolution**: larch-logs/design/*/rejected-findings.md:1; skills/design/scripts/tally-plan-review.sh:499 Use `grep -cE '^### \[Plan Review\] FINDING_[0-9]+'` (no colon); align test-timing-report fixtures and docs with the same pattern

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:470-479
- **Concern**: Plan's proposed OOS grep counts every OOS row, not accepted OOS only. Scenario: The tally table includes the Result column; a rejected or exonerated OOS row still matches ^\| OOS_[0-9]+ \|, so timing-report.json would overstate rounds[].oos despite the plan requiring accepted-OOS counts
- **Proposed resolution**: Count only OOS rows whose Result column is accepted in _emit_round_timing_row, and add a fixture with rejected/exonerated OOS rows to prove they are excluded

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:59
- **Concern**: Proposed OOS tally uses grep -cE '^\| OOS_[0-9]+ \|' which counts every Findings-table OOS row. Scenario: Plan and architecture require per-round accepted OOS (incl. security-accepted rows only in voting-tally.md). Tally emits one row per OOS id with a Result column (e.g. exonerated/rejected/accepted). Exonerated or rejected OOS rows are counted toward rounds[].oos, inflating telemetry vs accepted OOS and vs oos-accepted-design.md semantics
- **Proposed resolution**: Count only Findings rows whose Result is accepted (e.g. grep -cE '^\| OOS_[0-9]+ \|[^|]*\| accepted \|$' with [[ -f ]] guard, or awk on the pipe table); update test-timing-report.sh design fixture and plan-review-loop.md to assert accepted-only OOS

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/run-step5-review.sh:236-239; scripts/step-telemetry-mark.sh:41-42
- **Concern**: Plan reuses step-telemetry-mark.sh for a timing-only Step 5 resume mark, but that helper also writes token-ledger marks. Scenario: This violates the stated no /report-tokens or other analysis-tool change constraint; a --starting-round > 1 resume would add an extra token Step 5 mark and change token-report bucketing
- **Proposed resolution**: Use a timing-only mark in run-step5-review.sh, e.g. call timing-ledger.sh mark with LARCH_TIMING_LEDGER and IMPLEMENT_TMPDIR exported, instead of step-telemetry-mark.sh

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-ledger-contract, Cursor-dyn-ledger-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:59
- **Concern**: skills/design/scripts/tally-plan-review.sh:499. Scenario: Design rejected-count grep requires a trailing colon after FINDING_N but tally writes headings without one
- **Proposed resolution**: `grep -cE '^### \[Plan Review\] FINDING_[0-9]+:'` on `rejected-findings.md` never matches; committed `rounds[].rejected` stays 0 while accepted counts look correct Use `grep -cE '^### \[Plan Review\] FINDING_[0-9]+'` (no trailing colon), matching `printf '### [Plan Review] %s\n\n' "$id"` in tally-plan-review.sh

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-ledger-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:474-515
- **Concern**: Proposed design OOS count uses grep on every OOS row, but the tally table emits accepted and rejected OOS rows; only the Result column distinguishes them. Scenario: A round with one accepted OOS and one rejected or exonerated OOS reports "oos":2 instead of the accepted-OOS count 1
- **Proposed resolution**: Count voting-tally.md rows where Item matches OOS_N and Result is accepted, using awk field parsing/trimming; keep avoiding oos.md so security-accepted OOS still count

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-ledger-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/timing-report.sh:392-409
- **Concern**: The mis-attachment fixture described in the plan conflicts with the current per-mark interval model; a Step 5 round after a Step 7 mark cannot attach to the prior Step 5 entry under the proposed [s,e) rule. Scenario: Tests may force aggregation to ignore intervals or collapse duplicate Step 5 marks, reintroducing wrong-step attachment, or the tests will fail despite correct interval logic
- **Proposed resolution**: Revise the fixture: without a Step 5 re-mark, assert the later round is omitted and not attached to Step 7; with a Step 5 re-mark, assert it attaches to the second Step 5 per_step entry

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-publish-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:59; skills/design/scripts/tally-plan-review.sh:499
- **Concern**: Rejected-count grep requires a colon the tally writer never emits. Scenario: Every design plan-review round records rejected=0 in ledger/committed timing JSON while accepted/OOS look correct
- **Proposed resolution**: Use `grep -cE '^### \[Plan Review\] FINDING_[0-9]+$'` (or `^### FINDING_[0-9]+:` on `rejected-findings.md` only); add a fixture/assert in `scripts/test-timing-report.sh`

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-publish-surface
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-final-summary.sh:86-88; skills/design/scripts/design-publish.sh:257-264; scripts/design-log-publish.sh:348-365
- **Concern**: Pre-publish timing render lacks the existing rm-f freshness guard, so an old timing-report-final.json can survive a failed or unavailable render and then be copied. Scenario: render-final-summary deletes old token/timing JSON before rendering; design-log-publish copies every top-level tmpdir file, so a retry after a prior post-publish summary can publish stale timing-report-final.json if timing-report.sh exits before replacing it
- **Proposed resolution**: In design-publish.sh remove timing-report-final.json/stderr/failure immediately before the pre-publish render or render to a fresh temp and only move on success; warn on missing or empty fresh output before design-log-publish.sh

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-round-semantics
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:470-479 (proposed _emit_round_timing_row in plan.txt:56-59)
- **Concern**: Design `oos` uses `grep -cE '^\| OOS_[0-9]+ \|'` on the whole Findings table, but tally-plan-review.sh prints every ballot id there with its Result (accepted/rejected/exonerated). Scenario: Rejected or exonerated OOS rows still match the grep, so `rounds[].oos` overstates accepted OOS and disagrees with tally semantics / `oos-accepted-design.md`
- **Proposed resolution**: Count only accepted OOS rows (e.g. awk on `voting-tally.md` Findings lines where the Result field is `accepted`, including security-accepted rows absent from `oos-accepted-design.md`); align `scripts/test-timing-report.sh` fixture expectations

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-round-semantics
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:53,61; skills/review/scripts/review-core.sh:694-718; skills/implement/SKILL.md:782-784; skills/design/scripts/plan-review-loop.sh:1414-1420; skills/design/SKILL.md:1122-1124
- **Concern**: Main-agent-vote-required rounds would record pre-adjudication counts. Scenario: The plan emits implement/design round rows before the inline main-agent re-tally paths. review-core emits ACCEPTED_COUNT=0 and REJECTED_COUNT=0 for main-agent-vote-required, and design exits plan-review-loop before SKILL.md re-runs tally. The append-only ledger then keeps stale accepted/rejected/oos values.
- **Proposed resolution**: Do not emit a preliminary round row for main-agent-vote-required. Defer record-round until after the synthetic vote re-tally, using the re-tally artifacts/env for final counts; persist round_start if needed so duration can still include the whole round.

