### OOS_1: [OUT_OF_SCOPE] gitleaks allowlist for python test paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: gitleaks allowlist for `python/test_redact.py` and python caches (`SECURITY.md` 242–246, `.gitleaks.toml` 100–103) is an intentional blind spot; real credentials under allowlisted python paths would not be caught by gitleaks layers 1–2 (TruffleHog may still catch live secrets). Pre-existing policy; keep fixtures synthetic; do not expand allowlist without review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_2: [OUT_OF_SCOPE] Bash streaming PEM mode not ported to Python
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Bash redact supports `--streaming` PEM mode (`scripts/test-redact-secrets.sh` 98–115); Python has no streaming API. Not on this branch’s live path; track for a later phase or document intentional non-port in Phase 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] Refusal regex on `output_file` only matches bash parity
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: nit
- **Concern**: `classify_launch_failure` applies `_REFUSAL_RE` only to `sidecar` and `_PARSE_RE` to both `sidecar` and `output_file`, matching `external_classify_launch_failure` in bash. The parity vector with refusal only in `output_file` encodes `other`/`unknown`, not `refusal`—not a regression.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] Rotation / `idx == 0` aligns with bash when `first_tier` in list
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: nit
- **Concern**: When `first_tier` is in `tier_list`, rotation makes `tier_list[0] == first_tier`, so `idx == 0` aligns with bash `waterfall_iter == 0`; `wrapper_rc == 2` fall-through matches bash because short-circuit requires `wrapper_rc == 0`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] Branch commit inventory (informational)
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: nit
- **Concern**: Branch commits since merge-base with main: `a6fb8beac`, `929f244bf`, `a8a657d8e` / `eca4b21ec`, `0ed5744ec` / `202f93e28` (review rounds).
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (brief):** 41 raw slots consolidated to 25 in-scope findings and 5 out-of-scope blocks. Largest merges: ship-pr plan drift (3→1), waterfall failure-class source (4→1), launcher cwd/argv/security (3→1), operator-path redact + test gaps (4→1), PEM line/anchor issues (2→1). FINDING_3 (extract shared classifier) kept separate from OOS_3 (bash-intentional refusal-on-output_file behavior). OOS_3–OOS_5 are attestations, not action items.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

