### OOS_1: [OUT_OF_SCOPE] G-Py-9 lacks cross-reference to G-Py-2 layering
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: nit
- **Concern**: G-Py-2 governs when locals need annotations (with carve-outs for obvious RHS); G-Py-9 governs annotation quality for locals that are annotated. Without a cross-reference, reviewers may treat when-to-annotate and how-to-annotate as independent rules and get conflicting signals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add cross-reference in G-Py-9 to G-Py-2
  - From cursor-specialist-testing: Add a one-line cross-reference in G-Py-9's Why or Deviate when pointing readers to G-Py-2 for the annotate-vs-skip judgment.

### OOS_2: [OUT_OF_SCOPE] Subprocess ratchet baseline reasons still cite pre-G-Py-9 ratchet
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: Hundreds of baseline rows use reason strings such as `grandfathered direct subprocess usage pre-G-Py-9 ratchet`, which implied G-Py-9 would cover subprocess-via-runner enforcement. This PR assigns G-Py-9 to local-variable typing instead, so operators auditing baseline reasons may misread ratchet intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Rename ratchet reason strings to G-Py-7 or a dedicated subprocess guideline ID in a follow-up PR.
  - From cursor-specialist-testing: In a follow-up, rename those reason strings to reference G-Py-7 (or a future dedicated subprocess guideline ID) and regenerate only if the linter requires reason updates.

### OOS_3: [OUT_OF_SCOPE] Issue title and feature description overshoot G-Py-9 scope
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The issue title and feature description promise strongly typed every local declaration, but G-Py-9 only constrains annotation quality and allows G-Py-2 omission carve-outs. Reviewers or implementers may treat all locals as mandatory-annotate when the guideline set does not require that.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a G-Py-2 cross-reference in G-Py-9 or align the tracking issue title with the narrower rule.
  - From cursor-specialist-testing: Either tighten G-Py-9 wording to match the feature intent or adjust the issue title/body so plan and guideline align.

