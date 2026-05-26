### FINDING_1: risk-integration: scripts/upsert-diagrams-comment.sh:114-129
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] assert_tmp_scoped_input excludes larch session cache paths used by DESIGN_TMPDIR/IMPLEMENT_TMPDIR Normal /design or /implement run fails before gh upsert with architecture/code-flow file must be under a temporary directory Add session_cache_root (~/.cache/larch/sessions) to allowed prefixes; add harness case for cache-path inputs
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: scripts/test-upsert-diagrams-comment.sh:195-213
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Fence regression test uses heading text inside a node label, not a real H2 line inside an open mermaid fence. A future parser regression that splits on ## lines inside fences would not be caught by CI. Add a fixture with a standalone ## Code Flow Diagram line inside ```mermaid and assert byte-faithful Code Flow preservation.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: scripts/test-tracking-issue-read-sentinel.sh:418-427
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Legacy runid-bearing larch:diagrams comments are not covered by the issue-read regression harness. After a filter regression, orphan <!-- larch:diagrams v1 runid=... --> bodies could re-enter TASK_FILE and pollute /implement context while stable comments remain filtered. Add a stubbed issue-read case with a legacy runid diagrams comment and assert it is skipped from TASK_FILE like the stable-marker case.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: scripts/test-upsert-diagrams-comment.sh:331-338
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No empty --code-flow-file preserve regression despite FINDING_3 symmetry for both sections. A bug that treats empty code-flow file as clear would pass CI while architecture empty-file preserve still works. Add an empty-code-file-preserve case mirroring empty-file-preserve with CODE_FLOW_SOURCE=preserved and unchanged Code Flow body.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/test-upsert-diagrams-comment.sh:395-401
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Dry-run harness does not assert the marker appears in the first preview block. A dry-run formatting regression could omit the marker from the operator-visible preview while sections-only output still looks correct. Assert <!-- larch:diagrams v1 --> appears before --- content-file --- and is absent from the second preview block.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/design/SKILL.md:972-976
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] /design Step 5c.5 sentinel to --clear-architecture path lacks offline call-chain coverage. Wiring mistakes in the 5c.5 branch (skip vs clear vs upsert) would pass structural SKILL pins but fail on non-architectural re-runs leaving stale Architecture sections. Add a minimal offline test or extend test-design-structure.sh to assert --clear-architecture is invoked when architecture-diagram.skipped exists and architecture-diagram.md is absent.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: scripts/test-upsert-diagrams-comment.sh:357-366
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] unclosed-fence test encodes loss of preserved Code Flow when Architecture fence is malformed. Issues with broken mermaid fences in stored Architecture sections can lose Code Flow content on the next /implement upsert without a hard failure. Document the limitation or implement fence-depth section parsing per plan and require byte-faithful preservation in the harness.
- **Suggested revision**: Address the concern above.


### FINDING_19: security: scripts/upsert-diagrams-comment.sh:242,276-278
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] --repo is not validated as OWNER/REPO before gh api interpolation. Tampered or mistyped REPO in session env can cause wrong-target or confusing gh calls instead of argv-boundary failure. Apply the get-issue-context.sh OWNER/REPO regex (or shared helper) before any gh call; mirror in tracking-issue-summary.sh.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: scripts/upsert-diagrams-comment.sh:318-319
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Preserved Architecture sections are re-sanitized and can abort the whole upsert /implement cannot publish Code Flow when an existing issue Architecture section fails sanitize-mermaid-fragment.sh Sanitize only new --*-file inputs, or degrade per-section with Warnings instead of failing the joint upsert
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: scripts/upsert-diagrams-comment.sh:145-191
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Section parser lacks mermaid fence-depth tracking; unclosed fences can truncate preserved content. Next upsert can publish a partial or mis-split comment without failing closed (harness unclosed-fence case). Implement fence-depth parsing per plan or fail closed on ambiguous fence structure and extend regression coverage.
- **Suggested revision**: Address the concern above.


### FINDING_21: security: scripts/upsert-diagrams-comment.sh:118-129
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] ERROR= KV lines can include raw filesystem paths from validation failures. Machine parsers or logs may capture operator tmpdir layout outside the redacted stderr path. Use a fixed token in ERROR= and keep detailed paths on stderr only.
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: scripts/upsert-diagrams-comment.sh:132-142,318-319
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Preserved GitHub sections are re-run through current sanitize-mermaid-fragment.sh; rejection fails entire upsert. /design published a valid Architecture section; sanitizer rules later reject preserved bytes; /implement Step 7a cannot add Code Flow (UPSERT_STATUS=failed, warning only) even though generation succeeded. Skip re-validation for unchanged preserved sections, or fail only the changing section, or add documented operator recovery flag.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: scripts/upsert-diagrams-comment.sh:145-191
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Section splitter uses heading+adjacent-fence heuristic, not fence depth; unclosed mermaid fences truncate trailing content. Prior comment has unclosed ```mermaid; next upsert drops tail after mistaken H2 boundary (harness unclosed-fence case). Track generic fence depth; or fail closed on non-zero depth at EOF instead of silent truncation.
- **Suggested revision**: Address the concern above.


### FINDING_25: architecture: scripts/upsert-diagrams-comment.sh:145-191
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Non-conforming section shapes (heading without nearby fence, extra blank lines) are not extracted and may be replaced on next upsert. Operator hand-edits issue comment or old format lacks fence; /implement upsert reports preserved but overwrites unseen content. Document strict format; widen is_section_start or warn on heading-only blocks.
- **Suggested revision**: Address the concern above.


### FINDING_28: architecture: scripts/upsert-diagrams-comment.md:1-37
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Contract omits tmpdir scoping, preserved sanitize, delete-on-empty, and no-op semantics. Operators read .md contract and misdiagnose failed or deleted diagram comments. Align contract with script and SECURITY.md failure modes.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: scripts/upsert-diagrams-comment.sh:145-191
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Section parser uses ad-hoc is_section_start heuristic instead of plan-specified fence-depth machine Malformed or edge-case comment bodies may lose sections silently (unclosed-fence test documents one such path) Reuse/adapt fence-toggle extract_section from skills/research/scripts/render-findings-batch.sh:101-145
- **Suggested revision**: Address the concern above.


### FINDING_31: correctness: scripts/upsert-diagrams-comment.sh:145-191
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan requires mermaid-fence-depth awk; implementation uses H2-plus-3-line fence lookahead instead. Comment with >3 blank lines between ## … Diagram and opening ``` can mis-split sections; next upsert may drop Architecture or Code Flow despite passing fence-label harness. Implement fence-depth tracking per plan or document/limit the heuristic and add a >3-blank-line regression case.
- **Suggested revision**: Address the concern above.


### FINDING_32: architecture: scripts/upsert-diagrams-comment.md:1-36
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Contract omits script behaviors required by post-plan security hardening. Readers of .md only miss tmp path policy preserved-section sanitization and empty-comment DELETE semantics documented elsewhere. Expand contract to match scripts/upsert-diagrams-comment.sh and SECURITY.md.
- **Suggested revision**: Address the concern above.


### FINDING_33: correctness: skills/implement/scripts/test-step-7a.md:5-14
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] test-step-7a.md omits preserve-architecture-production-helper case. Production-helper regressions at Step 7a call site would not be visible from the harness contract checklist. Add numbered case for preserve-architecture-production-helper aligned with test-step-7a.sh.
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: scripts/upsert-diagrams-comment.md:1-36
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract doc missing tmpdir scoping sanitize and delete semantics documented elsewhere Callers/docs drift from SECURITY.md and script behavior; review rounds re-discover the same rules Update upsert-diagrams-comment.md to document tmpdir policy sanitize pass and empty-comment delete
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: scripts/upsert-diagrams-comment.sh:132-143,318-319
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Preserved Architecture/Code Flow sections are re-sanitized on every upsert; sanitizer rejection fails the entire call. /design posted Architecture earlier; later /implement generates valid Code Flow but upsert exits 1 when preserved Architecture contains disallowed mermaid (e.g. unquoted pipe), so Code Flow is not published. Sanitize only newly supplied sections, or on preserve-time sanitizer failure warn and omit that section instead of aborting the whole upsert.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/upsert-diagrams-comment.sh:145-192
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Parser uses heading-plus-fence-within-3-lines heuristic, not the planned fence-depth state machine. Existing comment with unclosed Architecture mermaid fence: code-flow upsert mis-bounds sections and drops prior Code Flow content (unclosed-fence harness). Implement fence open/close depth tracking in extract_section, or fail closed on malformed fences instead of silent truncation.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/upsert-diagrams-comment.sh:159-167
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Section headings without a nearby fence opener are ignored and their body is lost on merge. Comment has ## Architecture Diagram plus prose only; /implement code-flow upsert drops Architecture prose with no error. Treat H2 diagram headings as section starts without requiring an immediate fence, or error when extracted content is missing expected fences.
- **Suggested revision**: Address the concern above.


