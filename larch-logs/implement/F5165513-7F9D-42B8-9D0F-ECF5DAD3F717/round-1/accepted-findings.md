### FINDING_3: Empty `category` when no canonical `##` — tests, contracts, and consumers
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-test-coverage-output.txt
- **Concern**: Coverage only exercises plan-review `accepted` when a canonical `## <focus-area>:` appears after the synthetic prose `##` title; the strict-scan path that exhausts lines and yields an empty `category`, multi-skip ordering, and “wrong order” regressions are not asserted. Accepted rows can legitimately have `category=""` while `prose_body` still carries the finding; tooling or analytics that assumed non-empty `category` may mis-bucket, miscount, or drop rows.
- **Suggested revision**: Add a plan-review `accepted` fixture with only non-canonical `##` lines (and optionally multiple junk `##` lines before a canonical tag) asserting `category` is empty; document the producer contract and/or validate downstream handling; optionally document an authoring expectation when consumers require a non-empty category.


