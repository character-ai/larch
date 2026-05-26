# Review Round 1

- Mode: `diff`
- 21 accepted, 5 rejected (3 exonerated)

## Accepted Findings

### FINDING_1: code-quality: skills/implement/scripts/step-7a.sh:103-108
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] compose_summary_diagrams keys off diagram file presence instead of STATUS=ok A reused IMPLEMENT_TMPDIR with a leftover code-flow-diagram.md after STATUS=failed/skipped would still upsert and overwrite a valid prior Code Flow section on the issue Only write code-flow-section.md when generation STATUS is ok; always remove the section file on skip/fail/small-non-runtime paths
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: skills/implement/scripts/test-step-7a.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Plan-required Step 7a harness cases (stable marker body, Architecture preserve, no-prior code-flow-only, legacy orphan) are absent; helper harness covers merge logic only. Regression at call site (wrong helper args or skip logic) would not be caught by test-step-7a.sh. Extend test-step-7a.sh with stubbed or real-helper integration cases listed in plan acceptance.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: scripts/test-tracking-issue-summary.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Plan testing strategy stable-marker smoke through tracking-issue-summary.sh not implemented. Marker prepend/upsert regressions in delegated path could ship without offline detection. Add one test-upsert-summary case with <!-- larch:diagrams v1 --> marker.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: skills/implement/scripts/step-7a.md:50-51
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc says code-flow-section.md only on STATUS=ok but step-7a.sh uses file existence. Misleading operator/debug guidance on preserve vs replace. Fix step-7a.sh to match doc (STATUS=ok gate).
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/implement/scripts/test-step-7a.sh:141-161,377-403
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Step 7a harness stubs upsert-diagrams-comment.sh so plan-required merge cases are untested at the call site. A /design-posted Architecture section could be dropped on the next /implement run without CI failure because test-step-7a never validates preserve/legacy/no-prior-comment bodies. Extend the harness with gh-stubbed integration cases for Architecture preservation, code-flow-only create, and legacy orphan non-collision per plan acceptance.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: scripts/test-tracking-issue-summary.sh:1-94
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required stable-marker smoke test for larch:diagrams through upsert-summary is missing. Stable marker validation/regression in tracking-issue-summary.sh could break helper delegation while make lint stays green. Add create/update cases using <!-- larch:diagrams v1 --> and sections-only content-file bodies.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: scripts/tracking-issue-read.sh:427-436
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Stable larch:diagrams marker filter has no automated regression test. Removing the new case arm would inject full diagram bodies into issue-context reads used downstream. Add a tracking-issue-read harness case asserting stable-marker comments are skipped.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: scripts/test-ship-pr.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] PR prep no longer pins removal of Architecture Diagram from pr-body.md after compose-architecture-sketch deletion. A future edit could reintroduce Architecture blocks in PR bodies without CI signal. Assert pr-body.md contains Code Flow details and lacks Architecture Diagram summary block.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/implement/scripts/step-7a.sh:376-378
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 7a omits --repo on upsert-diagrams-comment.sh despite plan threading Forked /implement can post larch:diagrams to the fork origin while the tracking issue is on upstream, yielding a missing or duplicate diagrams comment on the design issue Rehydrate REPO or UPSTREAM_REPO from session-env and pass --repo on the upsert call
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: skills/design/SKILL.md:972-976
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] /design Step 5c.5 --clear-architecture and failure logging paths lack runtime harness coverage. FINDING_8 stale-section clearing or best-effort failure logging could regress with only SKILL structural pins passing. Add offline harness for sentinel + clear-architecture and UPSERT_STATUS=failed warning append.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: skills/implement/scripts/test-step-7a.md:5-28
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness sibling doc drift: new regression cases documented in step-7a.md are absent from test-step-7a.md. Contributors may omit planned cases because the harness contract understates required coverage. Sync test-step-7a.md Cases list with step-7a.md regression checklist.
- **Suggested revision**: Address the concern above.


### FINDING_22: security: scripts/upsert-diagrams-comment.sh:191-207,265-267
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] gh API and delegate stderr are embedded in failure messages without redact-secrets.sh or redact_gh_error. A failed upsert after gh returns a token-shaped stderr string can leak that value via ERROR= machine output and downstream logs. Run all captured gh/delegate stderr through redact_gh_error (or equivalent) before emit_failure; add a harness case with a planted token in stub stderr.
- **Suggested revision**: Address the concern above.


### FINDING_25: security: SECURITY.md:131
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] New larch:diagrams security prose omits gh stderr redaction requirements documented for sibling writers. Operators may assume fail-closed stderr handling that upsert-diagrams-comment.sh does not yet implement. Add explicit gh stderr redact_gh_error requirements matching tracking-issue-summary.sh / plan-block-write.sh.
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: skills/implement/scripts/step-7a.sh:103-107
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] compose_summary_diagrams keys off file existence not DIAGRAM_STATUS=ok After STATUS=skipped/failed a prior code-flow-diagram.md can remain; compose_summary_diagrams still writes code-flow-section.md and upsert-diagrams-comment runs clobbering a valid issue Code Flow section on retry in the same IMPLEMENT_TMPDIR Gate section write on DIAGRAM_STATUS=ok; rm -f code-flow-diagram.md and code-flow-section.md on skip/fail before upsert
- **Suggested revision**: Address the concern above.


### FINDING_27: correctness: skills/implement/scripts/test-step-7a.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan-required Step 7a harness cases for Architecture preserve no-prior comment legacy orphan and skip/fail preserve are not implemented. Regression at the Step 7a orchestration layer (wrong upsert gating or argv) would not fail CI because only test-upsert-diagrams-comment.sh exercises merge semantics. Extend test-step-7a.sh stub or add cases that assert preserve/no-prior/orphan/skip-fail behavior at the call site; update test-step-7a.md in lockstep.
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: skills/implement/scripts/test-step-7a.md:5-28
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Sibling harness contract omits plan-enumerated diagram regression cases documented in step-7a.md. Contributors and reviewers assume listed behaviors are tested; CI green does not guarantee checklist coverage. Add numbered cases matching step-7a.md regression checklist and wire them in test-step-7a.sh.
- **Suggested revision**: Address the concern above.


### FINDING_29: correctness: scripts/test-tracking-issue-summary.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan testing strategy stable-marker smoke test through upsert-summary is missing. Marker-prepending or content-file handling bugs in tracking-issue-summary.sh could ship despite green upsert-diagrams tests. Add a stable-marker round-trip case with sections-only content-file and single-marker assertion.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/implement/scripts/test-step-7a.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Plan-listed regression cases for preserve-architecture, code-flow-only create, and legacy orphan collision are not implemented in the step-7a harness Acceptance criteria and step-7a.md checklist claim coverage that only exists in the separate upsert harness; wiring regressions at the call site could slip through Add the missing cases to test-step-7a.sh or explicitly delegate them in test-step-7a.md and trim acceptance bullets
- **Suggested revision**: Address the concern above.


### FINDING_30: correctness: CHANGELOG.md:3669
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] FINDING_10 verification grep still hits ARCHITECTURE_DIAGRAM_FILE in changelog. Pre-merge grep fails acceptance; stale doc claims manifest still hydrates a removed variable. Remove or correct the changelog reference; re-run the broadened grep excluding allowed legacy-doc lines.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: skills/implement/scripts/step-7a.md:50-51
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Documented STATUS=ok gate does not match step-7a.sh implementation Operators debugging FINDING_3 will trust the contract and miss file-presence coupling bugs Align code and doc after fixing compose_summary_diagrams gating
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/implement/scripts/step-7a.sh:103-107
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] compose_summary_diagrams gates on code-flow-diagram.md existence instead of DIAGRAM_STATUS=ok; generator leaves stale diagram on skip (plan FINDING_3). Second Step 7a run in same IMPLEMENT_TMPDIR after sanitizer rejection still upserts because stale code-flow-diagram.md exists despite DIAGRAM_STATUS=skipped, overwriting issue Code Flow instead of preserving. Gate section write on DIAGRAM_STATUS=ok; rm -f code-flow-diagram.md on non-ok generator exits; add harness with pre-seeded diagram + rejected generator.
- **Suggested revision**: Address the concern above.


