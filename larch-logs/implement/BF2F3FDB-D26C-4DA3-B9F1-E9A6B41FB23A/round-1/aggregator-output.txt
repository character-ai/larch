### FINDING_1: Design prose misstates Bash stdout as the visibility channel
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` still describes `render-final-summary.sh` as printing the summary to chat, including anti-halt/end-step prose. That conflicts with the new contract that Bash may persist/stream but the orchestrator must emit `final-summary.md` verbatim to top chat when non-empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Test harness under-pins design full-body emit prose
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-render-cost-line-callsites.sh` pins only two of four design full-body emit sites. Anti-halt and end-of-Step-5 prose could regress to cost-line-only language while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Changelog omits shipped #2970 note under 42.6.1
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `CHANGELOG.md` lists the #2970 fix only under Unreleased while plugin version `42.6.1` is already present, so release notes for `42.6.1` omit that shipped change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Branch mixes unrelated #3007 and #2970 work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch combines #2970 summary-emission work with #3007 telemetry/parser/version/log changes, making review, release notes, and bisecting harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: Step 18 can skip top-chat emit when Step 17 body was never emitted
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `/implement` Step 18 relies on body comparison and `.step17-printed`, but that does not reliably prove the Step 17 full body reached top chat. If Step 17 skipped or halted before orchestrator emission and Step 18 renders identical bytes, the operator can still see no final summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: Step 17 sentinel is written by Bash, not verified orchestrator emission
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `.step17-printed` is touched by the Step 17 Bash fence on script success/non-empty summary, but prose also treats it as evidence of orchestrator full-body emission. That can mask a skipped top-chat emit and creates ambiguity about the sentinel’s owner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: Step 18 body-diff path lacks executable test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/test-write-final-report.sh` does not exercise the `.step18-prebody` plus `cmp -s` changed/unchanged body path, so a Bash fence bug in snapshot order or comparison behavior could ship despite string pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Design top-chat emit contract remains prose-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: CI can grep prose, but cannot verify that the live orchestrator actually reads and pastes the full summary body into top chat. A manual smoke or tighter mechanical mechanism is still needed to catch paraphrase, cost-line-only output, or halted emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Retired design gating prose can partially reappear undetected
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Negative greps in `scripts/test-render-cost-line-callsites.sh` omit close variants of retired cost/gating/mechanism text, so partial reintroduction could evade the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Wrapper log allowlist may still publish diagnostics
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `scripts/larch-log.sh` still allowlists `*.wrapper.log` committed round artifacts. This branch keeps Codex JSONL out, but stderr-shaped diagnostics can still be published in logs; the issue predates this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Full-block transcript emission increases summary prominence
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Verbatim orchestrator emission makes canonical summaries more prominent in the assistant transcript, although the same content was already written to GitHub and run logs. Prompt-injection risk depends on compromising existing upstream summary inputs, with unchanged mitigations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Negotiation harness lacks JSONL-free sidecar assertion
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-run-negotiation-round.sh` does not assert JSONL-free sidecars like related harnesses do. This is a test gap, not a demonstrated branch leak.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: Design emit gates do not consistently require helper success
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Design anti-halt and end-of-Step-5 emit gates omit the helper exit-0 requirement used elsewhere. If post-publish render fails or is skipped while an older `final-summary.md` remains, those sites could still require emitting stale content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: Design contains duplicate mandatory full-summary emit sites
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Multiple design instructions can all require full-body top-chat emission on the same happy path, causing duplicate or triplicate identical summary blocks instead of one canonical visible summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
