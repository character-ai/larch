### FINDING_16: [OUT_OF_SCOPE] LARCH_EXTERNAL_SERIAL_LOCK_DELAY not validated
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `scripts/check-reviewers.sh` / `scripts/launch-codex-ci.sh:128` — `HOLD="${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}"` is not validated like the three new probe env knobs. An invalid value silently degrades mutex-delay behavior. Pre-existing pattern not introduced by this diff.
- **Suggested revision**: Validate `HOLD` for numeric format, consistent with the other probe env knobs — but treat as low-priority since this is pre-existing.

---


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_25: [OUT_OF_SCOPE] Pre-existing --probe doc/code mismatch now corrected
- **Reviewer(s)**: dyn-key-propagation-output.txt
- **Concern**: The old contract document stated `--probe exits 2`; the actual code exits 1. The new doc and new test both correctly target exit 1. This was a pre-existing doc/code mismatch fixed in this branch.
- **Suggested revision**: No action required; the fix is already in this diff.

Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

