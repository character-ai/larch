# Review Round 1

- Mode: `diff`
- 6 accepted, 3 rejected (3 exonerated)

## Accepted Findings

### FINDING_1: code-quality: scripts/launch-claude-review.sh:126-128
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Colon-delimited canonical dedup can false-match when one path is a prefix of another before the next colon boundary After /tmp/a:b is registered, a distinct /tmp/a can be skipped as a duplicate because :/tmp/a: appears inside :/tmp/a:b: Use indexed arrays with exact string equality for seen canonical paths (and consider the same for allow-roots)
- **Suggested revision**: Address the concern above.


### FINDING_10: architecture: scripts/launch-claude-review.sh:116-123
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Implicit context files that pass -f but fail dirname canonicalization are silently dropped. A TOCTOU or rare permission edge on an implicit --diff-file/--plan-file path can yield exit 0 while the review/vote runs without that context; previously the subprocess would fail loudly. On strict=0 canonicalization failure, forward the original path or fail with larch_err instead of return 0.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: scripts/launch-claude-review.sh:126-128
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Colon-delimited canonical dedup can false-positive when paths contain literal colons. Two distinct files whose canonical paths share a colon-delimited prefix segment could be incorrectly deduplicated on macOS/Linux rare filenames. Replace substring-in-string dedup with newline-separated records or explicit per-path equality checks.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: scripts/launch-claude-review.sh:116-123
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Implicit context files are silently dropped when canonicalization cd fails after -f succeeds. A phase passes a valid DIFF_FILE path; parent directory permissions change before cd; launcher exits 0 without forwarding diff context and without stderr, producing an under-grounded voter/reviewer run. For strict=0, forward when -f passes if canonicalization is optional, or surface larch_err when path was non-empty but cd failed.
- **Suggested revision**: Address the concern above.


### FINDING_3: risk-integration: scripts/test-launch-claude-review.sh:230-242
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan edge case for repeated identical explicit --context-files is untested. Dedup logic for explicit-only duplicates could regress while implicit+explicit dedup still passes. Add --context-files PATH --context-files PATH and assert single rendered occurrence.
- **Suggested revision**: Address the concern above.


### FINDING_5: risk-integration: branch vs main (ca99c8f4 + f29aa43d)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Full branch bundles lint-fix-loop harness expansion unrelated to partition 1. PR could fail CI on test-lint-fix-loop/test-ship-pr despite launcher tests passing. Run full make lint / relevant harness buckets on PR head.
- **Suggested revision**: Address the concern above.


