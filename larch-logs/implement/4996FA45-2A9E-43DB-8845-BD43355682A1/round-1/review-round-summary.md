# Review Round 1

- Mode: `diff`
- Accepted findings: 2
- Rejected findings: 0
- Exonerated findings: 1
- Neutral findings: 0

## Accepted Findings

### FINDING_1: LARCH_VERIFY_MANIFEST “repo-relative” vs actual cwd resolution
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-allowlist-coverage-output.txt, dyn-env-override-scope-output.txt, dyn-test-isolation-output.txt
- **Concern**: Documentation describes `LARCH_VERIFY_MANIFEST` as absolute or repo-relative, but the verifier opens the path as given (`[ -f "$MANIFEST" ]` / input redirection), so non-absolute values resolve against the process current working directory, not `REPO_ROOT`. Callers or harnesses that set a repo-looking path while `cwd` is not the repository root can hit “missing manifest,” open the wrong file, or get misleading behavior versus the docs.
- **Suggested revision**: Either align docs to “absolute or cwd-relative (recommend absolute for harnesses)” or resolve non-absolute `LARCH_VERIFY_MANIFEST` under `REPO_ROOT` (with sensible `//` normalization if implemented); if fixing in code, add a small harness case for the chosen semantics.


### FINDING_4: Ambient exported `LARCH_VERIFY_MANIFEST` can skew canonical verification and the offline harness
- **Reviewer(s)**: dyn-env-override-scope-output.txt, dyn-test-isolation-output.txt
- **Concern**: The verifier honors `LARCH_VERIFY_MANIFEST` from the environment whenever set; the harness does not clear a pre-exported value before default-case runs, and the Makefile target is not wrapped with `env -u LARCH_VERIFY_MANIFEST`. A globally exported override (profile, shared CI env, image defaults) can silently point verification at a non-canonical manifest without dirtying the tree; the same ambient export can make tests 1–13 use the wrong manifest (false failures or false passes), while per-command overrides only isolate when the variable is not already exported from outside.
- **Suggested revision**: `unset LARCH_VERIFY_MANIFEST` near the top of `scripts/test-verify-run-log-completeness.sh` (after `set -euo pipefail`), use `env -u LARCH_VERIFY_MANIFEST` on Makefile targets meant to enforce the canonical manifest, keep intentional overrides as `VAR=value cmd` only where needed, and document explicitly against exporting the variable for “real” verification shells.


