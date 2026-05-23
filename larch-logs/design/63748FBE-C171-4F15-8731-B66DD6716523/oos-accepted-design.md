### OOS_1: LARCH_RENDER_CACHE_DIR propagation parity for /design
- **Description**: `scripts/launch-review.sh:220-222` exports `LARCH_RENDER_CACHE_DIR` only when `IMPLEMENT_TMPDIR` is set. Standalone /design may miss shared render-cache wiring during external reviewer launches. Separate follow-up issue.
- **Reviewer**: Cursor-Arch
- **Phase**: design


### OOS_2: capture-session-transcript.sh IMPLEMENT_TMPDIR-only
- **Description**: `scripts/capture-session-transcript.sh:131-135` derives session-id only from IMPLEMENT_TMPDIR — same parity gap as launch-review.sh; not in scope of this issue but worth a follow-up.
- **Reviewer**: Cursor-Innovation
- **Phase**: design


