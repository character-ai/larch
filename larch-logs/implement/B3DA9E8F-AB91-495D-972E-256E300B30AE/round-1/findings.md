### FINDING_1: code-quality: scripts/launch-claude-review.sh:126-128
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Colon-delimited canonical dedup can false-match when one path is a prefix of another before the next colon boundary After /tmp/a:b is registered, a distinct /tmp/a can be skipped as a duplicate because :/tmp/a: appears inside :/tmp/a:b: Use indexed arrays with exact string equality for seen canonical paths (and consider the same for allow-roots)
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: scripts/launch-claude-review.sh:116-123
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Implicit context files are silently dropped when canonicalization cd fails after -f succeeds. A phase passes a valid DIFF_FILE path; parent directory permissions change before cd; launcher exits 0 without forwarding diff context and without stderr, producing an under-grounded voter/reviewer run. For strict=0, forward when -f passes if canonicalization is optional, or surface larch_err when path was non-empty but cd failed.
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: scripts/test-launch-claude-review.sh:230-242
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan edge case for repeated identical explicit --context-files is untested. Dedup logic for explicit-only duplicates could regress while implicit+explicit dedup still passes. Add --context-files PATH --context-files PATH and assert single rendered occurrence.
- **Suggested revision**: Address the concern above.

### FINDING_4: risk-integration: scripts/test-launch-claude-review.sh:1-23
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Global LARCH_TEST_CLAUDE_STDIN_LOG changes stub behavior for all legacy cases. Platform-specific tee/stdin issues could break unrelated harness assertions. Limit stdin logging to new test blocks only.
- **Suggested revision**: Address the concern above.

### FINDING_5: risk-integration: branch vs main (ca99c8f4 + f29aa43d)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Full branch bundles lint-fix-loop harness expansion unrelated to partition 1. PR could fail CI on test-lint-fix-loop/test-ship-pr despite launcher tests passing. Run full make lint / relevant harness buckets on PR head.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: skills/design/scripts/validate-plan-commands.sh:74
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] PERL_BADLANG=0 lacks a dedicated regression test. Locale-related --help capture flake could return without launcher changes. Add locale-focused probe test if this has flaked in CI.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/launch-claude-subprocess.sh:147-155` — Context file bytes are still fed to `claude` without `redact-secrets.sh`; that predates this branch and applies equally to implicit `--diff-file` / `--plan-file` context. **Suggested fix:** No change required for this PR; treat as operator-trusted path selection and rely on publication-boundary redaction already described in `SECURITY.md`.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `scripts/lint-fix-loop.sh` (ca99c8f4, #2909) — The accepted-coder-commit path allows merge commits when `HEAD` is an ancestor of post-dispatch `HEAD`, which can widen the diff range a fixer may commit if forbidden-path checks miss edge cases. **Suggested fix:** Out of scope for the context-files partition; track under #2909 / existing review FINDING_20 if tightening is desired.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **risk-integration** Branch composition — This diff vs `main` also ships unrelated `lint-fix-loop` / `ship-pr` harness changes and implement run logs; they do not weaken the context-files launcher boundary but increase review surface. **Suggested fix:** None for security of the launcher itself; split or call out in the PR description for reviewer focus.
- **Suggested revision**: Address the concern above.

### FINDING_10: architecture: scripts/launch-claude-review.sh:116-123
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Implicit context files that pass -f but fail dirname canonicalization are silently dropped. A TOCTOU or rare permission edge on an implicit --diff-file/--plan-file path can yield exit 0 while the review/vote runs without that context; previously the subprocess would fail loudly. On strict=0 canonicalization failure, forward the original path or fail with larch_err instead of return 0.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/launch-claude-review.sh:126-128
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Colon-delimited canonical dedup can false-positive when paths contain literal colons. Two distinct files whose canonical paths share a colon-delimited prefix segment could be incorrectly deduplicated on macOS/Linux rare filenames. Replace substring-in-string dedup with newline-separated records or explicit per-path equality checks.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/launch-claude-review.sh:101-153
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Launcher does not pre-check the 20-file context cap before calling the subprocess. Operators passing many --context-files plus implicit flags get a subprocess error instead of an early launcher exit 2 with a stable message. Count ctx_args before launch and exit 2 when >20, or document subprocess-only enforcement.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] correctness: scripts/launch-claude-review.sh:114
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Implicit context still does not require readability (-r). Unreadable implicit diff/plan files may still be forwarded under strict=0; failure mode depends on subprocess read behavior. Align implicit checks with -r or document intentional passthrough (pre-existing).
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] architecture: scripts/launch-claude-review.sh:33-52
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Non-context flags use ${2:?...} (exit 1) while --context-files uses exit 2. Mixed exit codes for similar missing-value mistakes on the same launcher. Out of scope unless unifying exit contracts across all flags.
- **Suggested revision**: Address the concern above.

