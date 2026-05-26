### FINDING_3: code-quality: skills/implement/scripts/step-7a.sh:350-354
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] upsert skip uses STATUS=skipped only, not plan-specified SKIP_REASON matching on failed. A generator emitting STATUS=failed with a sanitizer SKIP_REASON would still upsert larch:diagrams. Add SKIP_REASON / sanitizer-log detection for failed status and a harness regression case.
- **Suggested revision**: Address the concern above.



