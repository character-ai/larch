### FINDING_3: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:2270-2276
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] retry-sees-prewritten-prior uses background sleep/cp race against sync stub On overloaded CI the copy may occur after both probe attempts causing intermittent harness failure Use create-prior sync stub or synchronize copy with stub invocation instead of timing-based background job
- **Suggested revision**: Address the concern above.



