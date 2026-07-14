---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Module-preamble detection misses docstring-first skip-file directives
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Module-preamble detection may miss `skip-file` directives appearing after a module docstring, causing grandfathered modules to evade the gate or produce incorrect line identities.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit module-preamble contract (all unindented `#` comments before the first `import`/`from`/statement, regardless of docstring position) and a test fixture mirroring `_rendering_generators.py` docstring-then-skip-file ordering.


### [Plan Review] FINDING_4

### FINDING_4: Space-separated pylint disable syntax is not detected
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: A detector keyed only to `disable=<codes>` forms misses Pylint’s valid `disable <codes>` syntax, leaving whole-file duplicate-code bypasses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify and test both `disable=<codes>` and `disable <codes>` module-preamble grammars for R0801 and duplicate-code, including comma-separated tails in each form.


---LARCH-REJECTED-END---
