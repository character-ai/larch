Here is the normalized structured finding list (read-only aggregation; no voting or raw transcripts).

```text
### FINDING_1: LARCH_VERIFY_MANIFEST “repo-relative” vs actual cwd resolution
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-allowlist-coverage-output.txt, dyn-env-override-scope-output.txt, dyn-test-isolation-output.txt
- **Concern**: Documentation describes `LARCH_VERIFY_MANIFEST` as absolute or repo-relative, but the verifier opens the path as given (`[ -f "$MANIFEST" ]` / input redirection), so non-absolute values resolve against the process current working directory, not `REPO_ROOT`. Callers or harnesses that set a repo-looking path while `cwd` is not the repository root can hit “missing manifest,” open the wrong file, or get misleading behavior versus the docs.
- **Suggested revision**: Either align docs to “absolute or cwd-relative (recommend absolute for harnesses)” or resolve non-absolute `LARCH_VERIFY_MANIFEST` under `REPO_ROOT` (with sensible `//` normalization if implemented); if fixing in code, add a small harness case for the chosen semantics.

### FINDING_2: Locale-stable grep inconsistency next to new allowlist check
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: New or adjacent checks use `LC_ALL=C grep` while the nearby `*` segment probe uses default-locale `grep`, creating a minor inconsistency; practical mis-parse risk for the fixed `*` probe is low.
- **Suggested revision**: Use `LC_ALL=C` on the `*` probe as well, fold both into one locale-stable pattern test, or replace the probe with a bash string test for byte-stable behavior.

### FINDING_3: [OUT_OF_SCOPE] Allowlist still permits multi-segment `*` paths vs “single asterisk segment” contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Contract text implies a single `*` segment, but the allowlist/glob behavior can still admit rows with multiple `*` segments (e.g. `a*b*c.txt`), with broader glob expansion than a strict single-`*` grammar; treated as latent / pre-existing, not introduced by the hardening alone.
- **Suggested revision**: Optional follow-up only: enforce single-`*` shape or stricter path grammar if product intent requires it.

### FINDING_4: Ambient exported `LARCH_VERIFY_MANIFEST` can skew canonical verification and the offline harness
- **Reviewer(s)**: dyn-env-override-scope-output.txt, dyn-test-isolation-output.txt
- **Concern**: The verifier honors `LARCH_VERIFY_MANIFEST` from the environment whenever set; the harness does not clear a pre-exported value before default-case runs, and the Makefile target is not wrapped with `env -u LARCH_VERIFY_MANIFEST`. A globally exported override (profile, shared CI env, image defaults) can silently point verification at a non-canonical manifest without dirtying the tree; the same ambient export can make tests 1–13 use the wrong manifest (false failures or false passes), while per-command overrides only isolate when the variable is not already exported from outside.
- **Suggested revision**: `unset LARCH_VERIFY_MANIFEST` near the top of `scripts/test-verify-run-log-completeness.sh` (after `set -euo pipefail`), use `env -u LARCH_VERIFY_MANIFEST` on Makefile targets meant to enforce the canonical manifest, keep intentional overrides as `VAR=value cmd` only where needed, and document explicitly against exporting the variable for “real” verification shells.

### FINDING_5: [OUT_OF_SCOPE] Reviewer clarifications (harness mechanics, fixtures, diff scope)
- **Reviewer(s)**: dyn-test-isolation-output.txt
- **Concern**: Out-of-scope notes from the same source: test 14’s `LARCH_VERIFY_MANIFEST=… cmd` form does not persist in the parent shell and is not the cross-case leakage mechanism when the variable is not exported from outside; `bad_manifest` / `run_bad_chars` live under `mktemp` `$TMP` with the same `EXIT` cleanup pattern as other cases; synthetic manifest header/column order matches `docs/run-logs-required-files.tsv:1`; branch diff also carries orthogonal `larch-logs/implement/...` metadata noise relative to verifier-focused review.
- **Suggested revision**: No in-scope change required from these observations alone; optionally keep diff hygiene separate from verifier changes if maintaining review signal.
```
