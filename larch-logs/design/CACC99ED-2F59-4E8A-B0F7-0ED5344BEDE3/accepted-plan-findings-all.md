### FINDING_1: Disarm the EXIT trap before nested exit
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `_step3_review_guarantee_post_loop_exit` ends with `exit "$_rc"` while the replacement EXIT handler does not first disarm the active trap. That can re-enter the handler on nested `exit`, risking recursive trap execution or an incorrect terminal status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `trap - EXIT` (or mirror cleanup's `trap - EXIT TERM HUP INT`) as the first step after `local _rc=$?` in the post-loop helper, before marker removal and sentinel guarantee.
  - From Cursor-Pragmatic: Add `trap - EXIT TERM HUP INT` immediately after `local _rc=$?` in `_step3_review_guarantee_post_loop_exit`, mirroring `_step3_review_cleanup`, then clear `.bg-wait-active`, call `_step3_review_guarantee_completed_sentinels`, and `exit "$_rc"`.


