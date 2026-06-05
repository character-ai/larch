### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: architecture: scripts/lib-vote-tally.sh:76-80
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] is_scope_reduction_block passes its argument to --file but callers may supply inline block text Future tally integration passes heredoc content; detection always false Use stdin or a temp file inside the helper so block content is always evaluated
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: correctness: skills/design/scripts/plan-review-loop.sh:171-173
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] CR/LF guard checks the anchor path string not emit safety Path check never triggers; false sense of emission hardening Remove dead check or enforce at emit_kv/result-env write (already done in run-step3-review.sh)
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: Branch: `sergey-zhupanov/implementing-design-review-anchor-scout-3511` (tracking `origin/main`, **ahead 6 commits**)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - Branch: `sergey-zhupanov/implementing-design-review-anchor-scout-3511` (tracking `origin/main`, **ahead 6 commits**)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_24: Planned scope (from your plan): ~1,353 diff lines across new helpers (`plan-block-strip-body.sh`, `check-scope-reduction-marker.sh`), `plan-review-loop.sh` scope-anchor/dedup/parity/renumber wiring, prompt/dispatch updates, `aggregate-findings.sh` plan-mode preservation, `run-step3-review.sh` / `SKILL.md` `SCOPE_ANCHOR_FILE` handoff, and expanded harnesses
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - Planned scope (from your plan): ~1,353 diff lines across new helpers (`plan-block-strip-body.sh`, `check-scope-reduction-marker.sh`), `plan-review-loop.sh` scope-anchor/dedup/parity/renumber wiring, prompt/dispatch updates, `aggregate-findings.sh` plan-mode preservation, `run-step3-review.sh` / `SKILL.md` `SCOPE_ANCHOR_FILE` handoff, and expanded harnesses I **cannot** honestly report commit messages, file-level diffs, missing plan items, or line-specific findings without reading the diff and source. **To get the full review**, please either:
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_25: **Switch to Agent mode** and re-send this request (so `git log`, `git diff`, and file reads can run), or  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Switch to Agent mode** and re-send this request (so `git log`, `git diff`, and file reads can run), or
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_26: **Retry in Ask mode** once file reads are working again.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Retry in Ask mode** once file reads are working again. When tools are available, the review will walk your plan checklist explicitly: | Planned surface | Verification | |---|---| | `scripts/plan-block-strip-body.sh` + tests | Marker regex parity with `plan-block-read.sh`, malformed fail-closed, pass-through | | `scripts/check-scope-reduction-marker.sh` + tests | Leading-marker detection, severity-prefix strip, false-positive guards | | `plan-review-loop.sh` | Staged `plan-review-scope-anchor.txt`, brainstorm non-binding, dedup parity, ballot renumber | | `render-plan-review-prompt.sh`, `render-voter-prompt.sh` | Untrusted framing, `[SCOPE-REDUCTION]` instruction, voter inline anchor | | `dispatch-plan-voters.sh`, `dispatch-plan-review-panel.sh` | `--scope-anchor-file` / `--feature-file` forwarding on all paths | | `aggregate-findings.sh` | Plan-mode tagged-block exclusion, validation fallback, renumber | | `run-step3-review.sh`, `SKILL.md` | Design `feature-description.txt` binding, `SCOPE_ANCHOR_FILE` env handoff, MainAgent rubric | | Harnesses / `Makefile` | New targets registered, acceptance scenarios covered | Sorry I can’t deliver line-referenced findings yet — re-run when reads (or Agent mode) are available and I’ll produce the structured `### In-Scope Findings` / TSV output you requested.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: correctness: skills/review/scripts/aggregate-findings.sh:192-195
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Plan-mode insufficient-input exit skips tagged append/renumber path One untagged plus multiple tagged findings: aggregation skipped; ballot renumber may still fail if dedup left duplicate FINDING_1 headings On insufficient-input in plan mode, append withheld tagged blocks and run sequential renumber before emit_result
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_54

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_54: **code-quality** `skills/design/scripts/plan-review-loop.sh:1383-1396` — The post-dedup in-scope/OOS split is a bare `python3` heredoc under `set -euo pipefail` with no `set +e` and no fallback, unlike the nearby parity gate (`1398-1444`) and ballot renumber (`1493-1530`) paths that degrade gracefully. On macOS, a transient Python failure (missing interpreter, OOM, syntax error in the inline script) aborts the whole plan-review round instead of retaining the already-written `findings-in-scope.pre-dedup.md` snapshot. **Suggested fix:** Mirror the ballot/parity pattern: `set +e`, capture `$?`, and on non-zero fall back to copying `findings-in-scope.pre-dedup.md` (or skip the split and keep the pre-dedup stream) with a `WARN` breadcrumb.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **code-quality** `skills/design/scripts/plan-review-loop.sh:1383-1396` — The post-dedup in-scope/OOS split is a bare `python3` heredoc under `set -euo pipefail` with no `set +e` and no fallback, unlike the nearby parity gate (`1398-1444`) and ballot renumber (`1493-1530`) paths that degrade gracefully. On macOS, a transient Python failure (missing interpreter, OOM, syntax error in the inline script) aborts the whole plan-review round instead of retaining the already-written `findings-in-scope.pre-dedup.md` snapshot. **Suggested fix:** Mirror the ballot/parity pattern: `set +e`, capture `$?`, and on non-zero fall back to copying `findings-in-scope.pre-dedup.md` (or skip the split and keep the pre-dedup stream) with a `WARN` breadcrumb.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_58

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_58: **risk-integration** `scripts/compute-pr-line-counts.sh:59-66` — `gh api` stderr is redirected to `/dev/null`, and `write-final-report.sh` never records a `Warnings` / `execution-issues.md` entry when `LINES_STATUS` is `unavailable` or `skipped` for reasons other than `REPO_UNAVAILABLE=true`. Operators only see `- **Lines (PR diff)**: N/A` with no signal whether the failure was auth, rate limit, bad repo, or simply no PR. That is weaker observability than the corrupt-token path, which appends a warning and surfaces it in the summary. **Suggested fix:** Capture `gh` stderr to a tmp file on non-zero exit, append a one-line `Warnings` entry via `append-execution-issue.sh` (or `append-tool-failure.sh`) with redacted stderr, and optionally include `REASON=<token>` from the helper KV in the warning text while keeping the summary non-fatal.
- **Reviewer**: dyn-reporting-metrics-output.txt
- **Concern**: - **risk-integration** `scripts/compute-pr-line-counts.sh:59-66` — `gh api` stderr is redirected to `/dev/null`, and `write-final-report.sh` never records a `Warnings` / `execution-issues.md` entry when `LINES_STATUS` is `unavailable` or `skipped` for reasons other than `REPO_UNAVAILABLE=true`. Operators only see `- **Lines (PR diff)**: N/A` with no signal whether the failure was auth, rate limit, bad repo, or simply no PR. That is weaker observability than the corrupt-token path, which appends a warning and surfaces it in the summary. **Suggested fix:** Capture `gh` stderr to a tmp file on non-zero exit, append a one-line `Warnings` entry via `append-execution-issue.sh` (or `append-tool-failure.sh`) with redacted stderr, and optionally include `REASON=<token>` from the helper KV in the warning text while keeping the summary non-fatal.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: correctness: scripts/lib-vote-tally.sh:76-80
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] is_scope_reduction_block documents block input but requires a filesystem path Caller passes inline markdown; helper treats it as path; marker detection always false Use temp file or dual stdin/file API consistently
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_60

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_60: **risk-integration** `skills/implement/scripts/test-write-final-report.sh:852-900` — The outcome matrix exercises merged / `pr-created` / `forked-dry-run` fixtures that set a non-zero `PR_NUMBER` and rely on the shared `gh` shim, but it never asserts the new `- **Lines (PR diff)**:` bullet in those paths (unlike the dedicated `impl-lines`, `impl_runav`, and `impl_ghfail` fixtures at lines 758–850). A regression that dropped line-count forwarding for happy-path outcomes would not be caught by the matrix loop. **Suggested fix:** For outcomes with `expect_pr=present`, add `assert_contains '- **Lines (PR diff)**: code +17/-3, larch-logs +5/-1'` (or `N/A` when the fixture intentionally omits PR) to the matrix assertions.
- **Reviewer**: dyn-reporting-metrics-output.txt
- **Concern**: - **risk-integration** `skills/implement/scripts/test-write-final-report.sh:852-900` — The outcome matrix exercises merged / `pr-created` / `forked-dry-run` fixtures that set a non-zero `PR_NUMBER` and rely on the shared `gh` shim, but it never asserts the new `- **Lines (PR diff)**:` bullet in those paths (unlike the dedicated `impl-lines`, `impl_runav`, and `impl_ghfail` fixtures at lines 758–850). A regression that dropped line-count forwarding for happy-path outcomes would not be caught by the matrix loop. **Suggested fix:** For outcomes with `expect_pr=present`, add `assert_contains '- **Lines (PR diff)**: code +17/-3, larch-logs +5/-1'` (or `N/A` when the fixture intentionally omits PR) to the matrix assertions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

