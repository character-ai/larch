## Goal
Implement issue #7277: [IMPLEMENTING] [BUG] when /design or /implement splits a feature into components, it should give them common prefix.

## Implementation Plan
If original issue already had a square-bracket prefix, e.g., [BUG], [FEATURE], etc., it should be preserved.  The new prefix should follow the old one, and be of the format:
split-<original-issue-number>-N
when N is is the number of of split piece.
Further, dependencies between them, if any, should be expressed using /block-issue.
Finally, all dependencies of the original issue must be reconstructed to involve the new issues.

I believe this functionality is already implemented in larch.  Make sure to unify/reuse, and not to create yet another copy.

## Test plan
(no test plan section in plan-file)
