### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Extract §3.8 collector stderr logic into shared lib
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Section 3.8 adds nested helpers and KV parsing inside a 1500+ line collector instead of the shared stderr lib. Harder to unit-test dedup/resolve logic and increases merge/conflict risk on the hottest collector script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract batch emit/dedup into lib-failed-agent-stderr-tail.sh; leave one call site after section 3.7.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Non-numeric LARCH_FAILED_AGENT_STDERR_TAIL_LINES fallback untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Non-numeric `LARCH_FAILED_AGENT_STDERR_TAIL_LINES` fallback to 30 is untested. Typo env could cause surprising behavior if fallback regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Set env to abc; assert 30-line tail from 40-line fixture.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Default review sidecar-first failure path not integration-tested in run-external-agent
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Default review sidecar-first failure path not integration-tested. `run-external-agent` could prefer `.diag` over `.sidecar`; review lanes lose real agent stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Failed run with populated .sidecar; assert .stderr-tail matches sidecar not diag.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: No ordering assertion for stderr-tail before .done
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No ordering assertion stderr-tail before .done. Race could theoretically surface .done before tail to collector.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert mtime ordering or document-only if deemed sufficient.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Collector emits .stderr-tail contents without read-time re-redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Collector §3.8 emits `.stderr-tail` contents directly without re-redaction at read time. A stale or forged `.stderr-tail` in the session tmpdir would be surfaced verbatim to FD 2 and tee'd collector logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Re-render or re-redact sidecar contents in `_emit_collector_stderr_tail_from_file` before larch_err.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Redactor failures swallowed; partial coverage on publish path
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Redactor failures are swallowed; partial redact-secrets coverage; stderr-tail may be published under gitleaks-exempt `larch-logs/`. A redaction miss or opaque bearer token in agent stderr can be committed and not caught by gitleaks Layers 1-2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Fail closed on redactor non-zero exit; tighten publish policy or add post-publish secret assertions for *.stderr-tail.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Non-zero exit with empty stderr produces no .stderr-tail
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Non-zero exit with empty stderr still produces no `.stderr-tail`. Codex/cursor exit 1 with 0-byte sidecar: verdict line only, same blind spot as before for empty-stream failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document limitation or synthesize tail from .diag / exit metadata when stderr is empty but status is failed.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Panel timeout 1860 clamped to 1800 without extending subprocess cap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Panel timeout 1860 is clamped to 1800 without extending the subprocess cap. Claude fallback runs 60s shorter than the panel budget; marginal timeouts on long reviews.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Align launch-claude-subprocess.sh cap with panel timeout or document effective 1800s ceiling.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Waterfall overwrites single launch-stderr path per output slot
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Single launch-stderr path per output is overwritten each waterfall phase. Phase-1 launcher validation stderr is lost if phase-3 runs on the same slot path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use per-phase launch-stderr filenames or append with phase labels; extend collector resolution.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

