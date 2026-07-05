# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: cap-1 rollup parser misses bare duplicate URL shape
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: The cap-1 rollup parser still ignores the bare `ISSUE_DUPLICATE_OF_URL` form, so deduped cap-1 filings can fail to recover a slot URL and never write Filed URL/OOS_FILE_MAP rows for the originals. That can let reruns refire the same bundle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_2: cap-1 partial failure leaves successful originals unstamped
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Blanket failure gating disables the cap-1 rollup stamping path when one success exists alongside failed siblings, leaving some successful originals without Filed URL and allowing reruns. Derive the rollup URL from the single success and stamp every non-failed original.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_7: malformed TSV input can abort report rendering
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: Strict TSV parsing only catches `OSError` and `csv.Error`, so malformed `findings-classification.tsv` files can raise `UnicodeDecodeError` and stop report rendering instead of falling back.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add a malformed-TSV fallback test


