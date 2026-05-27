### FINDING_1: design-outline scope omits Q&A-only exclusion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `design-outline.md` does not state that ad-hoc Q&A-only `/design` exits are excluded from the outline approval path, so operators loading only that reference may apply the outline gate too broadly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_2: Step 1e can run Gate A on pre-plan control flow
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-cross-doc-sync-output.txt
- **Severity**: important
- **Concern**: Step 1e’s banner/body can still execute on first-time or missing-outline pre-plan paths where Gate A should be skipped or control should return to Step 1d.7, risking Shape 2 execution without `plan.txt` and violating the outline-first flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-cross-doc-sync-output.txt: Address the concern above.

### FINDING_3: Step 1e re-entry provenance is not machine-detectable
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The Step 1e guard depends on conversational provenance from Gate B(c)/C(b) rather than a sentinel or env flag, so resumed or misrouted runs can incorrectly skip or fire Gate A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Approve outline lacks required acknowledgment breadcrumb
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Approve outline path writes `.outline-approved` and proceeds to sketches without the brief operator-visible acknowledgment required by acceptance criteria.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: cancelled-outline is missing from post-publish outcome matrix
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-shell-interface-output.txt
- **Severity**: important
- **Concern**: The exhaustive post-publish summary outcome matrix omits `cancelled-outline`, leaving title/outcome/stdout parity and cancel-site note behavior undercovered compared with other legal cancel outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-shell-interface-output.txt: Address the concern above.

### FINDING_6: Structure tests do not pin Step 2a/2b outline propagation
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Check 2974 does not pin the SKILL.md Step 2a/2b prose that prepends or reads `design-outline.md`, so future edits could silently remove load-bearing outline propagation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] workflow lifecycle docs are stale for outline gate
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `docs/workflow-lifecycle.md` still describes `/design` without brainstorm or Step 1d.7 outline gate wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: design-outline publish contract is false
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `design-outline.md` claims it is excluded from design-log publish bundles, but `design-log-publish.sh` publishes top-level session artifacts through redaction, creating a misleading security expectation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: Outline content is injected into external agents without untrusted delimiters
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Merged outline text derived from issue/user content is passed to external sketch/debate agents as binding approved direction without untrusted boundaries or digesting, increasing prompt-injection risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] session artifacts retain existing publish/redaction risk
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Top-level session artifacts already publish to `larch-logs` with redaction only, and the same risk existed for `brainstorm.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: Approve outline can write sentinel without non-empty outline
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Approve outline path can create `.outline-approved` without first requiring a successful non-empty `design-outline.md`, allowing downstream outline injection to be skipped silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Plan review loop omits approved outline from reviewer feature context
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `plan-review-loop.sh` merges `brainstorm.md` but not `design-outline.md`, so approved outline constraints may be invisible to plan reviewers if Step 2b drifts from the outline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Dialectic Step 2a.5 only optionally injects outline
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 2a requires outline injection, but Step 2a.5 only says the dialectic may inject it, allowing architecture resolution without binding approved outline direction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: render-final-summary caller count is stale
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `render-final-summary.md` still says eleven callers after adding the `cancelled-outline` caller, leaving contributor-facing summary outcome documentation miscounted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] CHANGELOG brainstorm/Gate A wording is stale
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-cross-doc-sync-output.txt
- **Severity**: nit
- **Concern**: `CHANGELOG.md` still describes old `--brainstorm` / Gate A sequencing and does not mention the Step 1d.7 outline gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-cross-doc-sync-output.txt: Address the concern above.

### FINDING_16: Step 1d sprawl return still routes to Gate A
- **Reviewer(s)**: dyn-cross-doc-sync-output.txt, dyn-sentinel-lifecycle-output.txt
- **Severity**: important
- **Concern**: The Split-path “Refine plan myself” return table still routes Step 1d sprawl to Step 1e Gate A, which is now post-plan re-entry-only and can bypass outline approval on a pre-plan path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-doc-sync-output.txt: Address the concern above.
  - From dyn-sentinel-lifecycle-output.txt: Address the concern above.

### FINDING_17: approval-gates header contradicts re-entry-only Gate A
- **Reviewer(s)**: dyn-cross-doc-sync-output.txt
- **Severity**: important
- **Concern**: `approval-gates.md` still says Gate A always prompts, conflicting with the new first-time Step 1d.7 outline gate and Gate A’s re-entry-only role.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-doc-sync-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] plan-review-loop outline omission is intentional L1 deferral
- **Reviewer(s)**: dyn-cross-doc-sync-output.txt
- **Severity**: nit
- **Concern**: `plan-review-loop.sh` does not merge `design-outline.md`, but the reviewer marked this as matching the plan’s L1 scope and relying on Steps 2a/2b to reflect outline-bound scope in the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-doc-sync-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] implement run-log artifacts are non-normative
- **Reviewer(s)**: dyn-cross-doc-sync-output.txt
- **Severity**: nit
- **Concern**: Implement run-log artifacts under `larch-logs/implement/F9A07665-.../` are bundled in the branch diff but are operational logs, not normative orchestration sources.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-doc-sync-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] retargeting audit found no additional stale handoffs
- **Reviewer(s)**: dyn-cross-doc-sync-output.txt
- **Severity**: nit
- **Concern**: The scout audit found several changed skill/doc surfaces already correctly retargeted away from stale `proceed to Step 1e` / `before Gate A` language.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-doc-sync-output.txt: Address the concern above.

### FINDING_21: cancelled-outline fallback summary orders notes before sentinel
- **Reviewer(s)**: dyn-shell-interface-output.txt
- **Severity**: important
- **Concern**: `compose_self_fallback` emits the `cancelled-outline` cancel-site note before the run-summary sentinel, unlike the primary renderer contract where note lines are appended after the sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-interface-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] note-lines-file handling is valid and harmless when absent
- **Reviewer(s)**: dyn-shell-interface-output.txt
- **Severity**: nit
- **Concern**: `--note-lines-file` is supported and only consumed when the path exists; cleanup ordering makes missing files harmless for non-`cancelled-outline` outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-interface-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] primary cancelled-outline summary path is partially covered
- **Reviewer(s)**: dyn-shell-interface-output.txt
- **Severity**: nit
- **Concern**: The dedicated primary-path test checks `cancelled-outline` outcome, cancel-site text, and stdout/file parity, but not note placement after sentinel or fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-interface-output.txt: Address the concern above.

### FINDING_24: Step 1d.7 approved sentinel can re-enter sketches after plan exists
- **Reviewer(s)**: dyn-sentinel-lifecycle-output.txt
- **Severity**: important
- **Concern**: The Step 1d.7 guard routes any `.outline-approved` session to Step 2a, even when `plan.txt` already exists, so resumed or replayed post-plan flows can incorrectly re-enter sketches instead of staying in the post-plan gate path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-lifecycle-output.txt: Address the concern above.

### FINDING_25: Step 2a/2b treat draft outline as approved without sentinel
- **Reviewer(s)**: dyn-sentinel-lifecycle-output.txt
- **Severity**: important
- **Concern**: Step 2a and Step 2b use any non-empty `design-outline.md` as approved binding context without checking `.outline-approved`, so canceled or draft outline content can be injected if control reaches those steps incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-lifecycle-output.txt: Address the concern above.

### FINDING_26: Sentinel lifecycle is underspecified
- **Reviewer(s)**: dyn-sentinel-lifecycle-output.txt
- **Severity**: important
- **Concern**: `design-outline.md` does not explicitly state that `.outline-approved` is written only on Approve, never on Refine/Cancel, nor does it document recovery from stale sentinel/session state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-lifecycle-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Step 1e sentinel would improve tractability
- **Reviewer(s)**: dyn-sentinel-lifecycle-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that Step 1e’s Gate B/C re-entry condition is not representable in `$DESIGN_TMPDIR` alone, though `plan.txt` presence currently makes legitimate post-plan re-entry behave correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-lifecycle-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] outline cancel summary failure behavior is unspecified
- **Reviewer(s)**: dyn-sentinel-lifecycle-output.txt
- **Severity**: nit
- **Concern**: Outline cancel runs the Final summary block and exits; if `render-final-summary.sh` fails non-zero, behavior is unspecified, matching other cancel paths, but no partial sentinel risk exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-lifecycle-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] cancelled-outline handling does not touch sentinel
- **Reviewer(s)**: dyn-sentinel-lifecycle-output.txt
- **Severity**: nit
- **Concern**: `cancelled-outline` handling in `render-final-summary.sh` is consistent and failure paths do not touch `.outline-approved`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-lifecycle-output.txt: Address the concern above.
