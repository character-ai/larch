# Review Round 2

- Mode: `diff`
- 3 accepted, 12 rejected (4 exonerated)

## Accepted Findings

### FINDING_15: correctness: scripts/upsert-diagrams-comment.sh:94-125
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Awk splitter only tracks mermaid fences; unclosed mermaid or plain code fences can mis-detect H2 section boundaries. Next upsert can drop Architecture or Code Flow when a fence contains or precedes a literal ## … Diagram line. Harden fence tracking or validate at generation; add unclosed/non-mermaid fence regression.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: scripts/upsert-diagrams-comment.sh:103-110
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Section splitter ignores ## only inside mermaid fences not generic code fences A non-mermaid fenced block containing ## Code Flow Diagram could be parsed as a new section boundary and drop content on the next merge Track any open ``` fence or add a regression body with a plain code fence plus heading-like line
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/upsert-diagrams-comment.sh:103-124
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Section parser fence tracking only recognizes mermaid fence openers, not generic code fences. A comment section containing a plain ``` block with a top-level ## heading line causes extract_section to end capture early and drop trailing content on the next upsert. Toggle in_fence on any ``` line, or restrict/document diagram sections as mermaid-only.
- **Suggested revision**: Address the concern above.


