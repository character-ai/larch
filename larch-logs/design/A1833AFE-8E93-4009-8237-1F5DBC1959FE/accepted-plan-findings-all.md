### FINDING_10: Self-disarm metadata discovery must resolve the defining dataclass
- **Reviewer(s)**: Codex-dyn-Ast Lint Precision
- **Severity**: major
- **Concern**: `OptionalMetadata` is defined in `_plan_quality_commands.py` and re-exported by `plan_quality.py`. A scanner that only inspects dataclass declarations in the scanned gate module could miss `diff_added` and `mechanical_churn`, allowing new suppression paths to evade the lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Ast Lint Precision: Resolve the imported and re-exported `OptionalMetadata` definition, or explicitly bind the required field set to that dataclass while keeping the scan limited to the design gate surface.


### FINDING_11: Unreachable-branch analysis must track path conditions
- **Reviewer(s)**: Codex-dyn-Ast Lint Precision
- **Severity**: major
- **Concern**: An earlier branch with `if flag: return` does not make a later `if flag` unreachable; the later branch remains reachable when `flag` is false. The lint must prove that the earlier control flow makes the later condition impossible on every path reaching it, rather than treating repeated conditions or any earlier return as sufficient.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Ast Lint Precision: Track the path condition. Only flag a later branch when an earlier unconditional return, or an earlier branch proven to execute on every path reaching it, makes the later condition impossible. Reset facts when control-flow implication is uncertain


