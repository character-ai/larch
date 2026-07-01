### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/finalize-step5.md:9-11
- **Concern**: Ordering-contract compression omits the byte-exact readability-load harness needle. Scenario: The plan tells implementers to shorten the intro/ordering contract while keeping a single `readability-style.md` reference. Edge cases only require `grep -Fc 'readability-style.md' -eq 1`. `scripts/test-design-structure.sh:508` also requires the full substring `read `skills/design/references/readability-style.md` once at Step 5 entry before diagram or final plan prose composition`. A paraphrase such as "read readability-style.md once before diagram work" can satisfy the once-count yet fail the contains check after the targeted ordering-contract shrink.
- **Proposed resolution**: Under Step 5c guidance, enumerate the ordering-contract needle byte-exactly (same treatment as the three `_publish_rc` pins). State that shortening the ordering contract must preserve that substring verbatim, not merely one filename mention.



