### FINDING_1: P3119 helper `fail()` text trips breadcrumb-monitor grep gate
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The new regression helper’s `fail()` message embeds the literal substring `breadcrumb-monitor.sh`. Plan close-time grep requires zero `breadcrumb-monitor` hits outside `larch-logs`, `CHANGELOG`, and forensics breadcrumbs. This harness can fail that gate and block PR merge even when skill fences are clean.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: `assert_p3119` does not cover all plan grep-gate tokens
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `assert_p3119` omits `LARCH_*` sentinels and `monitor_rc`. Partial fence regression (sentinel exports only) can pass structure tests and mis-route stalls per plan failure mode 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_8: No structural pin for foreground `writer_rc` routing in implement SKILL
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-implement-structure.sh` does not pin FINDING_1-style foreground `writer_rc` routing. Re-added `monitor_rc` or `LARCH_STATUS_FILE` prose in `skills/implement/SKILL.md` would not fail CI until runtime mis-routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: `skills/research/SKILL.md` omitted from Family-B P3119 fence checks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/research/SKILL.md` is not in the `assert_p3119` set used by structure tests. Collector Family-B shape could return to research `SKILL.md` without failing structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


