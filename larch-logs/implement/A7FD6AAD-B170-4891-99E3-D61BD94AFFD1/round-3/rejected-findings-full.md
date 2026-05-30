### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Collector stdout golden coverage gap for §3.8
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-collect-agent-results.sh` checks tails do not leak and `STATUS=FAILED` remain but does not golden-compare full collector stdout; §3.8 regression could change `FAILURE_REASON=` or KV field order without failing dedup assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Golden-compare full collector stdout lines (especially FAILURE_REASON=) for failed slots with and without stderr-tail sidecars.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Missing run-external-agent integration test for sidecar-first stderr source
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Mode-aware default review (sidecar before diag) is unit-tested in lib harness but not integration-tested through `run-external-agent` on failure; `select_failed_agent_stderr_source` could regress for codex panel default launches while lib-only tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add failed default-mode run with distinct .sidecar and .diag content; assert .stderr-tail matches sidecar.
  - From cursor-specialist-plan-fidelity-output.txt: Add a wrapper harness case with .sidecar populated or document lib harness as the canonical mode-order test


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: collect-findings collector hard-fail may double-print diagnostics
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Collector stderr is teed to FD 2 then replayed from log on `collector_rc != 0` (`collect-findings.sh` ~208–222) with no test coverage; hard-fail paths may double-print and mix live tee with redacted replay.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Skip replay when tee was used or add a harness asserting single emission on collector_rc != 0.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: launch-claude-subprocess harness lacks `.stderr-tail` / `.done` ordering assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-launch-claude-subprocess.sh` does not assert `.stderr-tail` is written before `.done` on agent failure; collector could observe `.done` before `.stderr-tail` under timing pressure without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add ordering assertion (poll for tail before done or compare mtimes) on the failure stub path.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Collector §3.8 dedup/tail logic inlined (~110 lines)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Large blocks of dedup and tail resolution are inlined in `scripts/collect-agent-results.sh` (~1426–1537) despite plan intent for tiny call sites; harder to test and evolve stderr surfacing separately from collection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract §3.8 helpers to a sourced lib; leave collect-agent-results.sh with a single emit call


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Committed publishable `.stderr-tail` artifacts lack gitleaks backstop
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Publishable stderr-tail artifacts rely on partial `redact-secrets` inside gitleaks-excluded `larch-logs/`; opaque bearer or connection-string stderr can be committed in `*.stderr-tail` without gitleaks backstop (`SECURITY.md` ~256).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Extend redaction patterns for stderr tails and/or gate publish on scan; keep operator guidance in SECURITY.md prominent.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Implement/non-review lanes still lack stderr-tail surfacing (in-scope documentation)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Implement/lint-fix lanes still lack stderr-tail surfacing; non-review codex/cursor failures in `/implement` remain verdict-only in chat (distinct from planned OOS launcher hook work but affects operator expectations).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Follow-up hook at implement launchers; document limitation in configuration doc until done.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: Bash hook `lines=()` array pollutes global namespace
- **Reviewer(s)**: dyn-hook-parser-fidelity-output.txt
- **Severity**: latent
- **Concern**: `extract_bash_task_output_poll_token` uses a global `lines=()` array; fragile if hook is sourced or nested (low impact today when executed as script).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-parser-fidelity-output.txt: Declare `local lines=()` inside `extract_bash_task_output_poll_token` (Bash 3.2 supports `local` arrays in functions).


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicate fenced-block formatting in stderr-tail lib
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-failed-agent-stderr-tail.sh` duplicates fence string formatting between `larch_err` line loop and raw FD2 `cat`; fence strings can drift between foreground and batch paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate fence emission in the lib (quiet + raw variants)


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_34

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_34: Residual orchestrator-transcript influence via stderr-shaped content
- **Reviewer(s)**: dyn-stderr-redaction-chain-output.txt
- **Severity**: latent
- **Concern**: §3.8 places bounded redacted stderr on FD 2 without neutralizing content shaped like larch `KEY=value|…` RESULTS lines, hook JSON, or `<!-- … -->` markers; compromised CLI stderr could influence orchestrator transcript (stdout KV parsing stays safe).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stderr-redaction-chain-output.txt: Document this as accepted residual risk in `SECURITY.md` §Failed-agent stderr tails; optionally add a fixed “untrusted subprocess stderr” banner and strip or escape lines matching `^[A-Z_]+=` / `^<!--` before `larch_err`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Anti-read-poll hook expansion increases PR blast radius
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Large `scripts/hook-anti-read-poll.sh` / `hooks/hooks.json` / `AGENTS.md` expansion is not in #3202 plan scope; harder to bisect stderr surfacing vs polling-hook regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider splitting hook work to a separate PR or cross-link in CHANGELOG


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

