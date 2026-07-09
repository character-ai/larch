---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Registry update targets the wrong CLI path
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The plan points the UPDATED change at a nonexistent `python/larch/cli.py` path, so the new shared-convention-regex command would not be registered in the real dispatcher.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Change the UPDATED path to `python/cli.py` and keep the registry edit there.


### [Plan Review] FINDING_2

### FINDING_2: Shared-convention lint skips too much by excluding both owners
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The proposed allowlist is too broad because it globally skips both owner modules, which would let future convention regexes drift inside one owner file without being checked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Do not exclude both owner modules globally. Scan owner files and suppress only the convention owned by that specific file; keep only the lint implementation self-exclusion global.


---LARCH-REJECTED-END---
