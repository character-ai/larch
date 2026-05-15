## Goal
Fix stale refs/remotes/origin/main tracking ref in capture-session-transcript.sh and local-cleanup.sh

## Implementation Plan
Fix stale refs/remotes/origin/main tracking ref when git fetch origin main is called.


### Problem
`git fetch origin main` fetches to FETCH_HEAD but does NOT update `refs/remotes/origin/main`. The push/reset logic in Step 18 (capture-session-transcript.sh) and local-cleanup.sh compares against `origin/main`, so it may operate on a stale ref when remote main has advanced.

### Files to Modify
1. scripts/capture-session-transcript.sh — line 160
2. scripts/local-cleanup.sh — line 73

### Changes
In both files, replace:
  `git fetch origin main`
with:
  `git fetch origin refs/heads/main:refs/remotes/origin/main`

This refspec form explicitly maps the remote branch `refs/heads/main` to the local tracking ref `refs/remotes/origin/main`, ensuring the tracking ref is updated in addition to FETCH_HEAD.

The `--quiet` flag and output redirection in each file are preserved unchanged.

### Edge Cases
- The refspec form works on repos where origin/main exists already (standard case) and where it doesn't (first fetch, creates the ref).
- No behavior change in the success path: both scripts use `origin/main` immediately after the fetch; the tracking ref will now reflect actual remote state.


## Test plan
Run `/relevant-checks` after changes. The change is 2-line mechanical substitution with no logic impact.
