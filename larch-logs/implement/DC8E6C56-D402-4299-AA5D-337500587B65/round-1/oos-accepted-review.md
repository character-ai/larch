### OOS_1: [OUT_OF_SCOPE] no regression harness for SessionStart sweep hook
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: No regression test harness pins the new SessionStart hook's always-exit-0 or spawn contract. Regressions in hook registration or launch behavior can ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] SECURITY.md omits SessionStart admin-merge hook
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No `SECURITY.md` entry documents the new SessionStart background admin-merge behavior. Operators auditing hook security surface from `SECURITY.md` would not see this shipped hook.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


