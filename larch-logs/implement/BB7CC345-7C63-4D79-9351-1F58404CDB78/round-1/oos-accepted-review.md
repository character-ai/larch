### OOS_1: [OUT_OF_SCOPE] Related permanent sandbox bails still retry as dispatch failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-architecture-output.txt
- **Severity**: latent
- **Concern**: `submodule-edit-required-out-of-scope` remains classified as `dispatch-failure` with retry semantics, although it represents a permanent external-implementer edit restriction similar to the protected-path bail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-architecture-output.txt: Either extend the early bail-token case to cover other permanent out-of-scope edit tokens, or narrow the public class name/docs so `protected-path` is documented as specific to `protected-path-edit-required-out-of-scope` until broader mapping exists.


