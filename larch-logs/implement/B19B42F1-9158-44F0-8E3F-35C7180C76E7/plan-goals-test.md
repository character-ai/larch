## Goal
Implement issue #4218: [IMPLEMENTING] [BUG] /combine-issues should create temporary files in a unique temp directory and not in /tmp directly.

## Implementation Plan
Failure example:
```
All groups are under the size cap (≤6 items each). No source contributes to multiple groups.

⏺ User answered Claude's questions:
· Apply this combination scheme? It merges 19 OOS issues into 5 (closing the 19 sources via deferred closure + dependency inheritance), and leaves stale #4205/#4123/#4130 untouched. You can also pick a subset of groups via Other (e.g. "1,3,4"). → Apply all 5 groups

Approved — applying all 5 groups. Let me write the combined bodies, then create the combined issues with deferred closure (oos-5).

⏺ Write(/tmp/oos-group1.md)
Error writing file

⏺ Write(/tmp/oos-group2.md)
Error writing file

⏺ Write(/tmp/oos-group3.md)
Error writing file

⏺ Write(/tmp/oos-group4.md)
Error writing file

⏺ Write(/tmp/oos-group5.md)
Error writing file

The /tmp/oos-group*.md paths already exist from a prior run. Let me use a fresh unique directory for body files and state.
```

## Test plan
(no test plan section in plan-file)
