### FINDING_14: [OUT_OF_SCOPE] risk-integration: docs/workflow-lifecycle.md:40-70
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Topology docs and mermaid still document --auto forwarding for /imaq, /alias, and /create-skill after skills removed --auto. Readers or external automation authors following canonical docs may pass unknown flags or misunderstand delegation edges; fails at invocation rather than a silent security bypass. Update docs/skills.md and docs/workflow-lifecycle.md (and any dependent diagrams) to match current SKILL.md forwarding in a separate doc-sync pass.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_9: [OUT_OF_SCOPE] code-quality: scripts/check-mid-run-dirty-tree.md:24
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc still mentions --auto carve-out though skills no longer expose --auto. File not modified in branch diff; adjacent stale doc only. Update carve-out prose when touching dirty-tree docs for a future change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


