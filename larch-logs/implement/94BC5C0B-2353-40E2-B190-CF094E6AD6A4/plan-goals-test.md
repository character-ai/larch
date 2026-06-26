## Goal
Implement issue #5435: [IMPLEMENTING] [BUG] We still have the breadcrumb mentioning version bump, even though version bumps were eliminated from every-PR flow.

## Implementation Plan
...and moved to their own manually-executed /release.
E.G.:
```
▎ 🔶 /implement 8: version bump
```
Further, the name of the step that created diagram in /implement (and possibly /design) needs to be renamed, as it does a lot more than than just the diagram, and that's misleading.

## Test plan
(no test plan section in plan-file)
