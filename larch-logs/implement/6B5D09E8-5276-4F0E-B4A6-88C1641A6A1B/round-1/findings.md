### FINDING_1: correctness: docs/issue-anchored-plan.md:3-6
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Opening uses present tense ("specifies the wire format that /design and /implement use") while no skills or scripts implement larch:plan:start/end or clarify markers in-tree. Readers treat issue-body markers and label automation as live behavior; debugging or automation fails because parsers and SKILL steps are absent. Qualify as target or planned spec; state implementation status; link to issue or PR that lands behavior.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: docs/issue-anchored-plan.md (Plan Block Format)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] New body markers share the larch:plan prefix with existing <!-- larch:plan v1 runid=... --> tracking-issue comment markers documented in docs/run-logs.md. Operators conflate issue-body embedded plans with slim larch:plan summary comments and misconfigure or parse the wrong surface. Add a subsection distinguishing body larch:plan:start/end from comment <!-- larch:plan v1 runid=... -->; cross-link docs/run-logs.md.
- **Suggested revision**: Address the concern above.

### FINDING_3: correctness: docs/issue-anchored-plan.md:74-75
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] clarify-state.sh is cited but only as "from the helpers PR" with no path or URL in-repo. Repo search finds no script; STATE table cannot be validated against code. Link a PR or issue, or mark provisional until clarify-state.sh exists at a named path.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: docs/issue-anchored-plan.md:94-95
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] "id counter starts at 0" next to id=1 examples invites misreading the first clarify id as 0. Misaligned implementations might emit id=0 requests. Clarify that 0 means no rounds yet and first request uses id=1.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: docs/issue-anchored-plan.md:140
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] References SKILL.md without repository-relative paths. Inconsistent with AGENTS.md canonical path style. Use skills/design/SKILL.md and skills/implement/SKILL.md.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: AGENTS.md:26; README.md:68
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Canonical bullets mirror the doc tagline without spec-vs-shipped nuance. Index entries overstate shipped capability alongside other live canonical docs. Align one-line summaries with qualified wording from the doc fix.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: docs/issue-anchored-plan.md:74
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] References clarify-state.sh and an unspecified helpers PR Script is absent from the repo; readers cannot validate STATE semantics or find implementation Remove or replace with a concrete in-repo path and merge status; avoid PR-only references
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: docs/issue-anchored-plan.md:3-9
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Present-tense claim that /design and /implement use this format No code in skills/ or scripts/ references these markers on this branch; operators may assume behavior already exists Add a clear spec-vs-implementation status note or conditional wording until code lands
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: docs/issue-anchored-plan.md:10-30
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New larch:plan:start/end vs existing larch:plan tracking comment name collision risk Confusion with docs/run-logs.md larch:plan tracking-issue comment Add explicit disambiguation and a cross-link to docs/run-logs.md
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: docs/issue-anchored-plan.md:94-95
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] "id counter starts at 0" vs first id=1 in examples Readers may think id=0 is valid or that the text contradicts the rules Clarify that no ids are consumed until the first request uses id=1
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: docs/issue-anchored-plan.md:38-54
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Clarification marker envelope not spelled out Unclear whether a closing marker exists or how parsers bound the comment Add one sentence: marker in issue comment body; no paired end marker like the plan block
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] code-quality: docs/workflow-lifecycle.md (not in diff)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No link from orchestration doc to issue-anchored plan wire format Higher-level doc does not point at the new canonical spec Consider a follow-up doc edit linking design/implement handoff to docs/issue-anchored-plan.md
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: docs/issue-anchored-plan.md:2-6
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Doc states /design and /implement already use this issue-body wire format No shipped skill/script implements these markers; readers assume live contract Reword as target/proposed spec until code exists; link implementation issue/PR
- **Suggested revision**: Address the concern above.

### FINDING_14: architecture: docs/issue-anchored-plan.md:12-30
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] New larch:plan:start/end issue-body format collides conceptually with shipped <!-- larch:plan v1 runid=... --> summary-comment marker Operators conflate two different mechanisms named larch:plan Add explicit contrast plus links to docs/run-logs.md and summary-comment-template.md
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: docs/issue-anchored-plan.md:74-81
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] References clarify-state.sh (helpers PR) and label not present elsewhere in repo Broken or unverifiable cross-reference to tooling Replace with stable PR/issue pointer or mark non-normative until script ships
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: docs/issue-anchored-plan.md:1-140
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Wire spec omits cross-link to SECURITY.md / implement outbound redaction for GitHub bodies Implementers might treat format-only spec as exempt from existing sanitization rules Add Safety bullet linking SECURITY.md and implement SKILL issue-body sanitization guidance
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: docs/issue-anchored-plan.md:94-95
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Clarify id narrative says counter starts at 0 while examples use id=1 first Minor confusion about initial id Clarify that first request uses id=1 when no prior clarify markers exist
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: docs/issue-anchored-plan.md:2-6
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] States /design and /implement already use this GitHub issue wire format No larch:plan/clarify markers or needs-design-clarification appear under skills/ or scripts/ in this tree; readers assume shipped behavior and cannot find enforcing code Qualify as target spec or cite implementing paths/PR; align wording with what is actually in the repo
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: docs/issue-anchored-plan.md:74-81
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] References clarify-state.sh from an unnamed helpers PR Script absent from repo; stable-name search fails; state table cannot be validated against code Replace with stable issue/PR link or repo path once merged; or mark subsection pending until script exists
- **Suggested revision**: Address the concern above.

### FINDING_20: architecture: docs/issue-anchored-plan.md:58-61
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] At-most-one clarify-response per id with no duplicate-response semantics Two responses with same id from retries or races leaves recovery undefined Specify reject vs deterministic winner and label transitions
- **Suggested revision**: Address the concern above.

### FINDING_21: code-quality: docs/issue-anchored-plan.md:94-95
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] id counter starts at 0 vs examples using id=1 Misread leads to wrong first marker id Reword to clarify first request uses id=1 or define id=0 reserved
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: README.md:68 and AGENTS.md:26
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Index blurbs repeat unqualified handoff claim Same misleading confidence as opening sentence via trusted TOC Mirror the corrected implemented-vs-spec wording from the doc lede
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] risk-integration: docs/workflow-lifecycle.md (not in diff)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Lifecycle doc does not link the new issue-anchored plan spec Discoverability gap for readers tracing design to implement File not touched by this branch; optional follow-up cross-link elsewhere
- **Suggested revision**: Address the concern above.

### FINDING_24: architecture: review input bundle (plan artifact absent)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan Fidelity review blocked: no design/implementation plan or requirements context was supplied with the diff. Requirement-by-requirement completeness and intent checks would be invented from the diff or new doc prose alone. Rerun with the authoritative plan (issue body, design-export/plan.txt, or ticket plan) attached to the review bundle.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: docs/issue-anchored-plan.md:3-4
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Opening presents issue-body markers and clarification flow as the wire format /design and /implement already use. No skills/scripts in-tree parse or emit larch:plan:start/end or clarify markers; readers assume runtime enforcement. Mark as proposed/target until implementation exists, or add explicit not-yet-implemented scope plus issue/PR link.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: docs/issue-anchored-plan.md vs docs/run-logs.md:243; skills/implement/references/summary-comment-template.md:7-11
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] New issue-body markers reuse the larch:plan name family alongside shipped <!-- larch:plan v1 runid=... --> summary comment contract. Operators conflate issue-body delimiters with tracking-issue summary markers and mis-apply both contracts. Rename body markers or add a prominent contrast section cross-linking summary-comment-template.md and run-logs.md.
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: docs/issue-anchored-plan.md:~74-75
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] References clarify-state.sh (helpers PR) for STATE values; script not in repository. STATE machine cannot be validated or operated from this repo; vague PR reference ages out. Link concrete PR/issue, gate the table until merge, or move to future-dependencies appendix.
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: docs/issue-anchored-plan.md:~66-72
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Documented needs-design-clarification label transitions are not evidenced in scripts/skills. Runbooks may assume label automation that is not wired. Clarify manual vs automated status or implement label hooks before claiming behavior.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: docs/issue-anchored-plan.md:~93-98
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] "id counter starts at 0" adjacent to examples using id=1. Mild reader confusion about initial id. Clarify that the first issued clarify id is 1 (or define counter vs next-id).
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: docs/issue-anchored-plan.md:~234-235
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Vague paths "/design and /implement SKILL.md". Harder to jump to canonical sources. Use skills/design/SKILL.md and skills/implement/SKILL.md.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] risk-integration: docs/workflow-lifecycle.md (unchanged)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] No cross-link from main workflow doc to docs/issue-anchored-plan.md. Slightly harder discovery of the new wire-format doc. Consider a Reference bullet in a follow-up PR touching workflow-lifecycle.md.
- **Suggested revision**: Address the concern above.

