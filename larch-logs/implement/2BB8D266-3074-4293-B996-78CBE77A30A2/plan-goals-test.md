## Goal
Implement issue #4570: [IMPLEMENTING] /release should ignore for the purpose of PR count the PRs of chore run logs flush.

## Implementation Plan
/release prints:, e.g.
```
⏺ 5 PRs since baseline v51.0.1. Reading PR list for release notes.
```
but this is misleading.  It should instead say something like:
```
⏺ 2 PRs since baseline v51.0.1. Reading PR list for release notes. (larch run logs flush PRs are ignored)
```

## Test plan
(no test plan section in plan-file)
