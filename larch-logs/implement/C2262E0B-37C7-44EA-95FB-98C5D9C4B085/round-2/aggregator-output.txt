Here is the normalized structured finding list. Reviewer prose is treated as evidence only; no voting or fix application.

### FINDING_1: Judge wording vs Claude second-retry exception (SKILL.md)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The judge paragraph still reads like a blanket “no Claude substitution” rule for adversarial debate, which conflicts with the documented NEVER #2 carve-out for a lawful Claude second retry. Readers may think externals-only applies to the final retry or skip the exception when interpreting orchestration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Ballot/defense vendor anonymity after Claude retry (tests, protocol, smoke)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Plan-level intent calls for exercising the Claude-retry path and proving assembled ballot/defense text stays clean of banned vendor/model markers. Current CI mostly greps static fixtures or otherwise may not fail if orchestrator drops stripping on retry-sourced content. Separately, the attribution strip list may be incomplete relative to tokens that can appear in real transcripts, leaving residual re-identification risk unless list or explicit residual-risk documentation is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Waterfall step numbering (plan “8b” vs doc internal step 5) and auditability
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Execution docs describe the waterfall as an internal step 5 while plan/acceptance language still pins “8b,” so greps, runbooks, and checklist comparisons to the issue can miss the real section or report false gaps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Large committed design run tree mixed with functional diff
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: A very large committed design run directory alongside functional changes increases review noise and makes bisect/history harder to interpret.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Dense SKILL↔execution numbering bridge maintenance risk
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The cross-reference bridge between SKILL numbering and execution-doc numbering is dense and easy to desync on future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Quorum/collector transport vs Claude retry2 Write-authored files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The documented quorum gate ties “side passes” to collector `REVIEWER_FILE` rows with `STATUS=OK`, but a Claude second retry may bypass the collector while still producing a valid six-tag file. If the orchestrator follows the doc literally, a side might never clear the gate despite a good retry artifact, skewing fallback vs judge paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Waterfall choreography documented without driver-level harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The launch/collect/render waterfall is specified in markdown without a driver-level or stubbed integration harness, so regressions in retry/collection pairing might not fail CI until a live `/design` run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Stale “byte-identical” binding claim (dialectic-execution.md)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The binding convention still implies a byte-identical pre-extraction copy relationship to `SKILL.md` even after a SKILL vs execution split, which misleads maintainers about the real maintenance contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Semicolon-separated `--failure-reason` path untested in retry-prompt harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The semicolon-separated failure-reason formatting branch may lack harness coverage, so regressions in the `tr` handling path could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: SECURITY.md not updated for dialectic waterfall / retry prompt trust boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: New dialectic waterfall behavior and `render-debate-retry-prompt.sh` embedding prior outputs plus a Claude final retry expand trust-boundary and prompt-injection/attribution surfaces, but `SECURITY.md` was not updated to describe them despite repo norms calling out security-relevant documentation updates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: Unconstrained read/write paths in `render-debate-retry-prompt.sh`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: CLI paths for reads/writes may be validated only for existence, not containment; mistaken or hostile invocation could pull unintended files into the retry prompt or write rendered output outside the intended design session directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: Verbatim failure-reason tails embedded into prompts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Failure-reason detail tails are copied verbatim after allowlisted heads; if future wiring ever places model-generated text in those tails, it becomes an indirect prompt-injection channel for retry debaters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Large committed run logs in branch diff (policy-aligned)
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Very large committed design run logs increase accidental secret surface area and dilute review signal; sources note this is largely governed by existing committed run-log policy rather than being introduced solely by dialectic code edits, so no mandatory product change is asserted beyond normal secret hygiene when authoring logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: None for this review per repo run-log policy

### FINDING_14: `dialectic-debate.md` OUTPUT FORMAT vs trailing meta sections
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: OUTPUT FORMAT forbids extra top-level prose after the exemplar, but the template still includes SELF-CHECK and content rules afterward, inviting model echoes that break standalone `RECOMMEND` and quorum parsing rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Prior-output excerpt placement and instruction-like steering in retry renderer
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Prior output excerpts are embedded before the original prompt in the retry renderer; malicious or accidental instruction-like prior text could steer retry behavior despite disclaimers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: Duplicate routing narrative across waterfall steps 5 and 6
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Steps 5 and 6 both describe routing `STATUS` failures into the waterfall, which can confuse implementors or read as duplicated normative guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Structural OUTPUT FORMAT guard uses line count vs character window
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: An early OUTPUT FORMAT test relies on line counting rather than a tighter character-window assertion, weakening the guard relative to the intended structural invariant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: Judge composition wording vs per-side skip semantics
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Judge composition contrast text still reads like debater skips are a single “assigned tool unavailable” event, which mismatches per-side launchability / bucket-skipped mental models.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge notes (diagnostic, optional):**  
`FINDING_13` retains `[OUT_OF_SCOPE]` because both merged sources carried that tag. `FINDING_4` was kept separate from `FINDING_13` because it asserts an in-scope workflow/reviewability concern (split/minimize functional PR coupling) rather than the policy-aligned “no change required” posture of the out-of-scope log observations.

Because one or more `### FINDING_N:` blocks are present, `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` is **not** included.
