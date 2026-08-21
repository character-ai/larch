"""larch.design: design, planning, and clarification subsystem.

Home for the design phases: the workflow phase modules
through ``design_step6`` (workflow phases), ``design_core`` (shared
lifecycle helpers and small entry points, plus the surviving result-env and
final-summary library helpers relocated from the retired ``design_terminal``;
the four terminal-state and failure-report verbs are Rust-owned in
``crates/larch-cli/src/design_terminal_commands.rs``), ``design_oos``
(out-of-scope annotation), ``decompose`` (issue decomposition), ``plan_quality``
(plan validation and quality gates), and ``clarify`` (clarification
round-trip helpers).
"""
