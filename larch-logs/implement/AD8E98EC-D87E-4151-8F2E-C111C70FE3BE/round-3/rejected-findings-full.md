### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Default launch jitter adds happy-path latency without CI coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Default 250ms pre-loop jitter adds up to 250ms wall-clock per cursor slot on the happy path; large parallel panels pay cumulative delay with no harness coverage of the delay path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document CI/autonomous opt-out (JITTER_MS=0) or add a harness timing assertion if jitter must stay default-on.

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_11: New SL-cursor-* cases not listed in harness sibling doc
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-launch-review.md` Coverage section does not name new mixed/quota cursor cases; contributors may miss them when extending the launcher.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: List all new SL-cursor-* case IDs explicitly in the Coverage section.

---


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Committed larch-logs may retain sensitive envelope fields
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: New empty-result diagnostics and `*-output.txt.json` sidecars copy full Cursor JSON envelopes minus top-level `.result`; sensitive text in `.error` or other keys may ship in merged PRs after best-effort `redact-secrets` only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Redact or allowlist envelope fields before cp to .json; avoid (.error | tostring) dumps in .diag without nested redaction.

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Diagnostic write fail-opens to unredacted copy when redaction fails
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: When `redact-secrets.sh` fails, the launcher may still `cp` raw `_diag_tmp` into `.diag`, leaving API/error prose in artifacts consumed by failure logs and execution-issue composers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Omit .diag or write a fixed placeholder when redaction fails; do not cp raw _diag_tmp.

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Retry backoff does not stagger empty-result or exit-code retries
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: One-time pre-loop jitter does not desynchronize retries; after aligned initial failures, parallel slots can re-hit Cursor on similar `1<<attempt` backoff and re-synchronize bursts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add per-retry random delay (or slot-derived offset) inside each continue path, not only before the loop.

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Empty-result diagnostic block inline in `_launch_cursor`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: ~50 lines of sanitize/jq/redact logic inline in `_launch_cursor` reduce readability of the auth loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Optional local helper `_cursor_write_empty_result_diag` to keep the auth loop readable; only worth doing if this file grows again.

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Codex and Cursor transient backoff logic can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_cursor_transient_backoff` was extracted for the cursor path, but `_launch_codex` still inlines equivalent delay logic, so retry timing can diverge on future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Hoist a single file-level helper (e.g. `_review_transient_backoff`) used by both `_launch_codex` and `_launch_cursor`, or document in `launch-review.md` that codex must be updated in lockstep.

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: No JSON-envelope quota classification before empty-result retry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Empty-result retry guards rely on grep substrings in sidecar/diag/stdout; exit 0 with empty `.result` and rate-limit metadata only in JSON envelope fields that do not match patterns can still consume empty-result retries (up to three per slot), re-sending full reviewer prompts and worsening outage load. Codex mirrors quota from JSON events; cursor has no equivalent before empty-result retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror quota from envelope to sidecar or classify rate-limit type/subtype as non-retryable before empty-result retry.
  - From cursor-specialist-security-output.txt: Classify JSON envelope quota/rate-limit fields as non-retryable; cap total cursor invocations per slot across retry types.
  - From cursor-specialist-edge-cases-output.txt: Extend guard with jq-based envelope quota classification or mirror quota markers into the sidecar before retry.

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_5: Terminal `.diag` omits planned pointer to full envelope file
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `${OUTPUT}.diag` `FAILURE_REASON` does not include the planned in-diag reference to `${OUTPUT}.json`; operators must discover the full envelope artifact separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add a redacted `(full envelope: ${OUTPUT}.json)` suffix to FAILURE_REASON.
  - From cursor-specialist-plan-fidelity-output.txt: Append a redacted envelope path or stable artifact reference to FAILURE_REASON while keeping field sanitization.

---


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Whitespace-only `.result` not treated as empty for retry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Backend returning whitespace-only `.result` (e.g. `" "`) does not trigger empty-result retry; the slot may still fail later at the first-line content gate as empty-looking output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Trim or treat whitespace-only `.result` like empty for retry/diagnostic if observed in the wild.

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: No harness for jq-missing or malformed JSON on empty-result path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No CI case covers jq absent or corrupt envelope on the empty-result branch; production could regress to undocumented behavior without signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add minimal stubs or PATH/jq-off cases asserting no empty-result retry and expected output promotion.

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Launch jitter env var not behaviorally tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `LARCH_CURSOR_LAUNCH_JITTER_MS` is documented but harness runs use `JITTER_MS=0`; sleep/ms parsing regressions could ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a small timing/counting case or state in test-launch-review.md that jitter is intentionally production-only.

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

