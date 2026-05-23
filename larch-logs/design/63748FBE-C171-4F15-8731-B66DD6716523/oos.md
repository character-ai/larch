### OOS_1: LARCH_RENDER_CACHE_DIR propagation parity for /design
- **Description**: `scripts/launch-review.sh:220-222` exports `LARCH_RENDER_CACHE_DIR` only when `IMPLEMENT_TMPDIR` is set. Standalone /design may miss shared render-cache wiring during external reviewer launches. Separate follow-up issue.
- **Reviewer**: Cursor-Arch
- **Phase**: design


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: capture-session-transcript.sh IMPLEMENT_TMPDIR-only
- **Description**: `scripts/capture-session-transcript.sh:131-135` derives session-id only from IMPLEMENT_TMPDIR — same parity gap as launch-review.sh; not in scope of this issue but worth a follow-up.
- **Reviewer**: Cursor-Innovation
- **Phase**: design


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: implement launchers IMPLEMENT_TMPDIR-only session-id export (NESTED-/design REMOVAL — do not file)
- **Description**: `scripts/launch-codex-implement.sh:125-126`, `scripts/launch-cursor-implement.sh:108-109` export LARCH_TOKEN_SESSION_ID from IMPLEMENT_TMPDIR only. Per user direction, the nested-/design path is being cleaned up in a separate in-flight session — do NOT file this as a follow-up OOS issue.
- **Reviewer**: Cursor-Innovation
- **Phase**: design

---

## Voting reminder

Vote YES, NO, or EXONERATE for each FINDING_N and OOS_N. For each OOS_N, YES means "file as GitHub issue", NO/EXONERATE means "do not file". OOS_3 should be voted NO/EXONERATE explicitly per user direction (no nested-/design follow-up).

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

