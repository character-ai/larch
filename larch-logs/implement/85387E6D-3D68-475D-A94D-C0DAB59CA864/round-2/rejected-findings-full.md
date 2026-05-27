### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: scripts/upsert-diagrams-comment.sh:205-228,278-282
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Helper lists issue comments then tracking-issue-summary.sh lists again before write Every diagrams upsert on busy issues pays for two paginated comment scans and a slightly wider stale-read window Teach tracking-issue-summary.sh to accept an existing comment id or fold PATCH into the helper after merge
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: risk-integration: skills/implement/scripts/test-step-7a.sh:548-558
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] diagram-generation-failure documents upsert skip but does not assert helper is uncalled If step-7a.sh regresses to call upsert-diagrams-comment.sh on STATUS=failed, CI stays green and a failed run could clobber a prior Code Flow section on the issue Add assert_not_contains upsert-diagrams-comment.sh to diagram-generation-failure (plan FINDING_3)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_11: security: scripts/upsert-diagrams-comment.sh:157-164,231-247
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Preserved diagram sections from fetched GitHub comments are republished after redaction only, without sanitize-mermaid-fragment.sh, and the stable marker is not bound to author or run identity On a public tracking issue, anyone who can post comments can plant <!-- larch:diagrams v1 --> with a malicious Architecture section; the next /implement Step 7a upsert that only passes --code-flow-file preserves that section and PATCHes it back publicly under the operator token Run sanitize-mermaid-fragment.sh on every section before compose (drop/fail on reject), or match only trusted comment ids/authors and document public-issue comment locking
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: security: scripts/upsert-diagrams-comment.sh:148-154,173-181
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] --architecture-file and --code-flow-file accept arbitrary readable paths with no tmpdir containment A mis-invoked CLI or orchestrator bug could pass --architecture-file pointing at .env or other secrets; redact-secrets may miss non-token secrets and publish them to the issue Require realpath under caller tmpdir or an explicit operator-only --allow-external-paths flag
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: security: SECURITY.md:131
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] SECURITY.md documents earlier Architecture exposure but not preserve-without-resanitize / public commenter trust Operators on public repos may assume diagrams are larch-generated only; foreign marker comments can persist until /design replaces or clears Document the joint-comment trust model and recommend comment restrictions or mandatory re-sanitize at upsert
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: architecture: scripts/upsert-diagrams-comment.sh:215
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Stable-marker list matching is exact with no BOM/CRLF normalization unlike tracking-issue-read.sh. A comment whose first line is BOM-prefixed or ends with \\r is not matched; a second stable larch:diagrams comment is created and Architecture/Code Flow split across comments. Strip BOM and trailing \\r from listed first lines before marker compare; add harness cases.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: risk-integration: skills/design/SKILL.md:974
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --clear-architecture only updates the stable marker; legacy runid comments are untouched. Non-architectural /design re-run after legacy /implement leaves stale Architecture on orphan runid comments while 5c.5 reports cleared. Document migration limit in Step 5c.5/3b or add optional legacy cleanup.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: architecture: scripts/upsert-diagrams-comment.sh:266-272
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] clear-architecture with no stable comment returns ARCHITECTURE_SOURCE=cleared on UPSERT_STATUS=no-op. Operators/logs imply GitHub architecture was removed when no stable comment was updated. Use absent/no-op-specific ARCHITECTURE_SOURCE when comment_id is empty.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: correctness: skills/implement/scripts/test-step-7a.sh:548-559
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] diagram-failure harness omits upsert-skip assertion documented in test-step-7a.md case 13 A future regression could re-invoke upsert-diagrams-comment.sh on STATUS=failed without failing CI because only diagram-failure-sanitizer and skip/rejected cases assert the skip Add assert_not_contains for upsert-diagrams-comment.sh in the diagram-failure case to match diagram-rejected and FINDING_3 acceptance
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/implement/scripts/step-7a.sh:103-110
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] compose_summary_diagrams name no longer matches behavior Readers expect full summary composition including architecture after the /design move Rename to prepare_code_flow_section and update step-7a.md
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/implement/scripts/test-step-7a.sh:141-180
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 7a harness stubs upsert-diagrams-comment.sh instead of calling production helper Real helper regressions could pass test-step-7a while failing only in the separate harness Add one preserve-architecture case using REPO_ROOT/scripts/upsert-diagrams-comment.sh with the gh stub
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: correctness: skills/implement/scripts/test-step-7a.sh:520-533
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Plan-required FINDING_3 regression case for skip/fail preserving prior Code Flow on the issue is not covered; tests only assert upsert is skipped locally. A prior stable comment with Code Flow exists, generator returns skipped/failed, and no test asserts remote preservation via upsert omission with seeded existing body. Add diagram-rejected/failed cases with STEP7A_UPSERT_EXISTING_BODY_FILE containing Code Flow; assert upsert-diagrams-comment.sh is not called and body capture stays unchanged.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

