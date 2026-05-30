### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Signature digit normalization collapses distinct failures
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `failed_agent_stderr_signature` normalizes all digit runs to `#`, so distinct failures differing only by exit codes or line numbers can hash equal. Multiple codex slots with the same message but different exits may suppress tails after the first. Tighten normalization, document the heuristic, or accept first-tail-wins per plan contract explicitly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: test-dispatch-with-waterfall launch-stderr assertion is existence-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The launch-stderr harness assertion is existence-only; the Claude fail stub emits no stderr. Empty `.launch-stderr` sidecars pass CI while on-demand collector render from launcher stderr stays unverified end-to-end.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_13: No test that .stderr-tail is written before .done on failure
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-launch-claude-subprocess.sh` does not assert ordering of `.stderr-tail` before `.done` on agent failure. A race could let the collector emit results before the tail sidecar exists, reproducing #3119-style lost diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Non-numeric LARCH_FAILED_AGENT_STDERR_TAIL_LINES fallback untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Invalid env values under `set -u`/`-e` are not harness-tested; `failed_agent_stderr_tail_lines` should fall back to 30 when env is non-numeric (e.g. `abc`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Collector stdout byte-stability with .stderr-tail not asserted
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Plan acceptance requires stdout unchanged by tail logic. Accidental stdout leakage from §3.8 would corrupt `KEY=value` parsing while dedup `STATUS` greps still pass. Golden-compare collector stdout with and without pre-seeded tails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Partial redact-secrets pattern coverage for expanded stderr surfacing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Expanded stderr surfacing relies on partial `redact-secrets.sh` regex coverage. Auth/config errors with opaque bearer tokens or DB URLs not matching covered families can leak into chat transcripts and optional `.stderr-tail` sidecars.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document limitation in SECURITY.md; extend redact-secrets patterns or stderr-specific scrubbing; retain byte/line caps.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: test-launch-claude-review missing stderr-tail and re-emit cases
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Timeout clamp tests landed but planned non-zero stderr-tail and full subprocess stderr re-emit preservation tests did not. Parent-level validation failures may stop writing `${OUTPUT}.stderr-tail` or stop re-emitting full stderr to voters without regression signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Mode-aware source selection plan/test location drift
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Mode-aware source selection moved to `select_failed_agent_stderr_source` in the lib vs inline in `run-external-agent.sh` as planned. Functionally OK but `test-run-external-agent.sh` mode integration assertions were not added as specified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Duplicate fence formats for stderr-tail emission
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Collector `larch_err` emit and `emit_failed_agent_stderr_tail_raw` use different delimiter/fence schemes for the same feature. Logs and replay parsers must handle two formats; unifying via one shared emit helper would reduce parser drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Large inline §3.8 dedup block in collector
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The inline dedup/emit block increases `collect-agent-results.sh` complexity, is harder to unit-test, and conflicts with otherwise good lib extraction. Extracting `emit_collector_failed_stderr_tails` to a sourced helper would improve reuse and testability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: No .stderr-tail when agent stderr file is empty
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `launch-claude-subprocess.sh` writes `.stderr-tail` only when agent stderr is non-empty. Some non-zero exits leave no sidecar; the collector has nothing unless the launcher path fills in. Document the exception or add a fallback source when stderr is empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

