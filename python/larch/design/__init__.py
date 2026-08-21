"""larch.design: design, planning, and clarification subsystem.

Home for the design phases: the workflow phase modules
through ``design_step6`` (workflow phases), ``design_core`` (shared
lifecycle helpers and small entry points, plus the surviving result-env and
final-summary library helpers relocated from the retired ``design_terminal``
and ``design_summary`` — ``resolve_summary_mode``, ``FinalSummaryRenderRequest``,
``render_final_summary_for_request``, ``upsert_final_summary_from_disk``; the
terminal-state, failure-report, and gate/final-summary render verbs are
Rust-owned in ``crates/larch-cli/src/design_terminal_commands.rs`` and
``crates/larch-cli/src/design_gate_summary_commands.rs``), ``design_oos``
(out-of-scope annotation), ``decompose`` (issue decomposition), ``plan_quality``
(plan validation and quality gates), and ``clarify`` (clarification
round-trip helpers).
"""
