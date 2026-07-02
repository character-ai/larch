### OOS_1: [OUT_OF_SCOPE] Review registry path harvesting intentionally scoped to design/implement
- **Reviewer(s)**: dyn-dyn-closure-classifier
- **Severity**: latent
- **Concern**: `skills/review/SKILL.md:18` pins `read step-name-registry.tsv` without a `skills/*/scripts/` path. `REGISTRY_PATH_RE` only harvests full registry paths, so review's registry file is not in the `review` closure. The issue scoped session-start TSV harvesting to design/implement; this looks like an intentional gap, not a branch regression.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Design narrow-matcher asymmetry predates intentional plan scope
- **Reviewer(s)**: dyn-dyn-closure-classifier
- **Severity**: latent
- **Concern**: `skills/design/SKILL.md:97,110` uses the same `use ... session-setup-output.md for` and `procedure in ... external-reviewers.md` shapes as review Step 0, but narrow matchers are review-only by design. Design closure still omits those shared files. That asymmetry predates the intentional narrow-scope choice in the plan; widening it would be a separate baseline change.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes**

- **FINDING_1** subsumes input FINDING_1, 4, 5, 7, and 8 (same `index=0` root cause; severity max = latent).
- **FINDING_6** and **FINDING_4** share the review-registry topic but stay separate: in-scope fix vs. `[OUT_OF_SCOPE]` intentional-gap disposition; merging would either drop the in-scope fix or wrongly tag the in-scope block `[OUT_OF_SCOPE]`.
- **FINDING_6** and **FINDING_7** carry no `- From <slot>:` bullets because the source entries only had generic "Address the concern above" placeholders.
- All six validator inventory slots appear in at least one `- **Reviewer(s)**:` line.
