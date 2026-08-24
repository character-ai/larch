//! External role-default readers for the `external-defaults` commands.

use std::collections::BTreeMap;

/// Role kinds emitted by `external-defaults role`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RoleKind {
    /// Ordered waterfall of tools.
    Waterfall,
    /// First present vendor wins.
    FirstAvailable,
    /// Multi-slot review or debate panel.
    SlotPanel,
    /// Single aggregator slot.
    SingleSlot,
    /// Voter policy table.
    VoterPolicies,
}

impl RoleKind {
    /// Return the wire token emitted on stdout.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Waterfall => "waterfall",
            Self::FirstAvailable => "first_available",
            Self::SlotPanel => "slot_panel",
            Self::SingleSlot => "single_slot",
            Self::VoterPolicies => "voter_policies",
        }
    }
}

/// One role row from the shared external-defaults table.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RoleDefault {
    /// Stable role identifier.
    pub role_id: &'static str,
    /// Role shape.
    pub kind: RoleKind,
    /// Ordered tool names for waterfall / `first_available` roles.
    pub order: &'static [&'static str],
    /// Optional env override name for `first_available` roles.
    pub env_override: &'static str,
    /// Slot count for slot-shaped roles.
    pub slot_count: usize,
    /// Voter count for `voter_policies` roles.
    pub voter_count: usize,
    /// Documentation phase column.
    pub doc_phase: &'static str,
    /// Documentation role column.
    pub doc_role: &'static str,
    /// Documentation skills column.
    pub doc_skills: &'static str,
    /// Documentation fallback column.
    pub doc_fallback: &'static str,
}

/// Resolver contract error mapped to CLI exit 2.
pub type ExternalDefaultError = crate::message_error::MessageError;
/// Vendor selection result for `external-defaults resolve-vendor`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ResolveResult {
    /// Selected vendor tool name, or empty when skipped.
    pub vendor: String,
    /// Skip reason when no vendor was selected.
    pub skip_reason: String,
}

const ROLE_DEFAULTS: &[RoleDefault] = &[
    RoleDefault {
        role_id: "implement.step2_coder",
        kind: RoleKind::Waterfall,
        order: &["codex", "cursor", "claude"],
        env_override: "",
        slot_count: 0,
        voter_count: 0,
        doc_phase: "Implement Step 2",
        doc_role: "Write the implementation",
        doc_skills: "/implement",
        doc_fallback: "Pick Cursor first for TRIVIAL or MODERATE and Codex first for HARD; --coder reorders the two external tools, then Claude.",
    },
    RoleDefault {
        role_id: "implement.lint_fix_coder",
        kind: RoleKind::Waterfall,
        order: &["claude", "codex", "cursor"],
        env_override: "",
        slot_count: 0,
        voter_count: 0,
        doc_phase: "Lint/checks",
        doc_role: "Repair local lint/check failures",
        doc_skills: "/implement, /review",
        doc_fallback: "Claude, then Codex, then Cursor; main agent required after external tiers fail.",
    },
    RoleDefault {
        role_id: "implement.ci_recovery_fixer",
        kind: RoleKind::Waterfall,
        order: &["codex", "cursor", "claude"],
        env_override: "",
        slot_count: 0,
        voter_count: 0,
        doc_phase: "CI recovery",
        doc_role: "Fix failing CI/checks",
        doc_skills: "/implement",
        doc_fallback: "Distinct registry role using Codex fix, then Cursor Composer 2.5 by default, then Claude Sonnet 4.6 1M.",
    },
    RoleDefault {
        role_id: "implement.rebase_conflict_fixer",
        kind: RoleKind::Waterfall,
        order: &["claude", "codex", "cursor"],
        env_override: "",
        slot_count: 0,
        voter_count: 0,
        doc_phase: "Rebase conflicts",
        doc_role: "Resolve rebase conflicts",
        doc_skills: "/implement",
        doc_fallback: "Distinct registry role using Claude, then Codex, then Cursor.",
    },
    RoleDefault {
        role_id: "review.fix_coder",
        kind: RoleKind::Waterfall,
        order: &["codex", "cursor", "claude"],
        env_override: "",
        slot_count: 0,
        voter_count: 0,
        doc_phase: "Review fixes",
        doc_role: "Apply accepted review findings",
        doc_skills: "/implement, /review",
        doc_fallback: "Codex fix, then Cursor Composer 2.5 by default, then Claude Sonnet 4.6 1M; main agent required after automated tiers fail.",
    },
    RoleDefault {
        role_id: "review.dynamic_archetype_scout",
        kind: RoleKind::Waterfall,
        order: &["cursor", "claude"],
        env_override: "",
        slot_count: 0,
        voter_count: 0,
        doc_phase: "Code-review scout",
        doc_role: "Propose dynamic reviewer archetypes",
        doc_skills: "/review",
        doc_fallback: "Cursor, then Claude. Codex is deliberately excluded.",
    },
    RoleDefault {
        role_id: "design.plan_archetype_scout",
        kind: RoleKind::Waterfall,
        order: &["cursor", "claude"],
        env_override: "",
        slot_count: 0,
        voter_count: 0,
        doc_phase: "Plan-review scout",
        doc_role: "Propose dynamic plan-review archetypes",
        doc_skills: "/design",
        doc_fallback: "Cursor, then Claude. Codex is deliberately excluded.",
    },
    RoleDefault {
        role_id: "design.plan_revision",
        kind: RoleKind::Waterfall,
        order: &["codex", "cursor", "claude"],
        env_override: "",
        slot_count: 0,
        voter_count: 0,
        doc_phase: "Plan revision",
        doc_role: "Apply accepted plan findings",
        doc_skills: "/design",
        doc_fallback: "Codex fix, then Cursor composer-2.5, then Claude Sonnet 4.6 1M.",
    },
    RoleDefault {
        role_id: "design.brainstorm_framing",
        kind: RoleKind::Waterfall,
        order: &["cursor", "codex", "claude"],
        env_override: "",
        slot_count: 0,
        voter_count: 0,
        doc_phase: "Brainstorm framing",
        doc_role: "Generate framing ideas",
        doc_skills: "/design",
        doc_fallback: "Step 1d.5 reads this role before launch and picks the first eligible external, then Claude text fallback.",
    },
    RoleDefault {
        role_id: "design.brainstorm_scope",
        kind: RoleKind::Waterfall,
        order: &["codex", "cursor", "claude"],
        env_override: "",
        slot_count: 0,
        voter_count: 0,
        doc_phase: "Brainstorm scope",
        doc_role: "Generate scope ideas",
        doc_skills: "/design",
        doc_fallback: "Step 1d.5 reads this role before launch and picks the first eligible external, then Claude text fallback.",
    },
    RoleDefault {
        role_id: "design.plan_drafter",
        kind: RoleKind::FirstAvailable,
        order: &["codex", "claude"],
        env_override: "LARCH_DESIGN_DRAFTER",
        slot_count: 0,
        voter_count: 0,
        doc_phase: "Plan drafting",
        doc_role: "Draft the implementation plan",
        doc_skills: "/design",
        doc_fallback: "Codex when present, else Claude; LARCH_DESIGN_DRAFTER is the only env override and invalid values soft-skip to inline drafting.",
    },
    RoleDefault {
        role_id: "review.panel",
        kind: RoleKind::SlotPanel,
        order: &[],
        env_override: "",
        slot_count: 6,
        voter_count: 0,
        doc_phase: "Code review panel",
        doc_role: "Review code changes",
        doc_skills: "/review, /implement Step 5",
        doc_fallback: "TRIVIAL emits Cursor Composer 2.5 singles when Cursor is available, else Codex review singles. MODERATE emits Cursor Composer 2.5 plus Codex gpt-5.6-terra pairs. HARD emits Cursor Composer 2.5 plus Codex gpt-5.6-terra pairs. Reviewer panels always dispatch with --no-fallback so missing vendors drop rows instead of backfilling.",
    },
    RoleDefault {
        role_id: "design.plan_review_panel",
        kind: RoleKind::SlotPanel,
        order: &[],
        env_override: "",
        slot_count: 9,
        voter_count: 0,
        doc_phase: "Plan review panel",
        doc_role: "Review implementation plans",
        doc_skills: "/design",
        doc_fallback: "Static archetypes are arch, innovation, pragmatic, requirements. Cursor reviewer rows resolve to Composer 2.5 by default when Cursor is available; Codex rows emit when Codex is available with the review role and a tier-resolved --default-model; no generic Codex reviewer is emitted; panel dispatch always uses --no-fallback.",
    },
    RoleDefault {
        role_id: "design.decompose_panel",
        kind: RoleKind::SlotPanel,
        order: &[],
        env_override: "",
        slot_count: 8,
        voter_count: 0,
        doc_phase: "Decompose panel",
        doc_role: "Propose issue partitions",
        doc_skills: "/design",
        doc_fallback: "Allowed parallel tools are Cursor and Codex; emit only present vendors per archetype with --no-fallback. Claude generic remains an explicit both-absent branch.",
    },
    RoleDefault {
        role_id: "review.voters",
        kind: RoleKind::VoterPolicies,
        order: &[],
        env_override: "",
        slot_count: 0,
        voter_count: 3,
        doc_phase: "Code-review voters",
        doc_role: "Vote on code-review findings",
        doc_skills: "/review",
        doc_fallback: "All voters dispatch through one shared waterfall manifest and re-dispatch on runtime failure: all three voters waterfall Codex, then Cursor, then Claude and voters 2/3 join the manifest whenever either external is present, so a both-external-down panel shrinks to the single Claude voter-1 anchor.",
    },
    RoleDefault {
        role_id: "design.plan_voters",
        kind: RoleKind::VoterPolicies,
        order: &[],
        env_override: "",
        slot_count: 0,
        voter_count: 3,
        doc_phase: "Plan voters",
        doc_role: "Vote on plan-review findings",
        doc_skills: "/design",
        doc_fallback: "All three plan voters share the code-review voter shape: Codex primary, then Cursor, then Claude in one shared waterfall manifest. When both external tools are down, the panel shrinks to one dedicated Claude voter-1 floor.",
    },
    RoleDefault {
        role_id: "review.findings_aggregator",
        kind: RoleKind::SingleSlot,
        order: &[],
        env_override: "",
        slot_count: 1,
        voter_count: 0,
        doc_phase: "Code findings aggregation",
        doc_role: "Merge code-review findings",
        doc_skills: "/review, /implement Step 5",
        doc_fallback: "Codex-primary single slot through dispatch-waterfall, using the review model role before Cursor or Claude fallback.",
    },
    RoleDefault {
        role_id: "design.plan_findings_aggregator",
        kind: RoleKind::SingleSlot,
        order: &[],
        env_override: "",
        slot_count: 1,
        voter_count: 0,
        doc_phase: "Plan findings aggregation",
        doc_role: "Merge plan-review findings",
        doc_skills: "/design",
        doc_fallback: "Codex-primary single slot through dispatch-waterfall, using the review model role before Cursor or Claude fallback.",
    },
    RoleDefault {
        role_id: "design.decompose_aggregator",
        kind: RoleKind::SingleSlot,
        order: &[],
        env_override: "",
        slot_count: 1,
        voter_count: 0,
        doc_phase: "Decompose aggregator",
        doc_role: "Merge partition proposals",
        doc_skills: "/design",
        doc_fallback: "Codex-primary single slot through dispatch-waterfall.",
    },
    RoleDefault {
        role_id: "debate.panel",
        kind: RoleKind::SlotPanel,
        order: &[],
        env_override: "",
        slot_count: 3,
        voter_count: 0,
        doc_phase: "Debate panel",
        doc_role: "Argue a proposal in persistent vendor sessions",
        doc_skills: "/debate",
        doc_fallback: "Fixed Cursor, Codex, and Claude slots with no silent substitution. Piece 2 activates launch and degraded-vendor accounting. The Claude slot is an in-session Agent-tool subagent; Cursor and Codex use subprocess transport.",
    },
    RoleDefault {
        role_id: "debate.synthesizer",
        kind: RoleKind::Waterfall,
        order: &["codex", "cursor", "claude"],
        env_override: "",
        slot_count: 0,
        voter_count: 0,
        doc_phase: "Debate synthesizer",
        doc_role: "Synthesize a converged debate into a proposal",
        doc_skills: "/debate",
        doc_fallback: "Codex-primary with fixed Codex, then Cursor, then Claude fallback order. Piece 2 activates this role.",
    },
];

/// Look up one role by id.
///
/// # Errors
///
/// Returns [`ExternalDefaultError`] when the role id is unknown.
pub fn role_default(role_id: &str) -> Result<&'static RoleDefault, ExternalDefaultError> {
    ROLE_DEFAULTS
        .iter()
        .find(|role| role.role_id == role_id)
        .ok_or_else(|| ExternalDefaultError::new(format!("unknown role: {role_id}")))
}

/// One fixed debate panel seat: slot, vendor tool, transport, and model pin.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DebateSeat {
    /// Slot name in `SLOT_ORDER`.
    pub slot: &'static str,
    /// Vendor tool.
    pub tool: &'static str,
    /// Launch transport.
    pub transport: &'static str,
    /// Model pin.
    pub model: &'static str,
}

/// Fixed `debate.panel` seating in protocol slot order.
///
/// Canonical Rust-owned `debate.panel` seats: Cursor and Codex subprocesses,
/// followed by the Claude agent-tool participant.
#[must_use]
pub const fn debate_panel_seating() -> [DebateSeat; 3] {
    [
        DebateSeat {
            slot: "cursor",
            tool: "cursor",
            transport: "subprocess",
            model: crate::DEBATE_CURSOR_MODEL,
        },
        DebateSeat {
            slot: "codex",
            tool: "codex",
            transport: "subprocess",
            model: crate::DEBATE_CODEX_MODEL,
        },
        DebateSeat {
            slot: "claude",
            tool: "claude",
            transport: "agent-tool",
            model: crate::DEBATE_CLAUDE_MODEL,
        },
    ]
}

/// Return every role that has a documentation phase.
#[must_use]
pub fn doc_rows() -> Vec<&'static RoleDefault> {
    ROLE_DEFAULTS
        .iter()
        .filter(|role| !role.doc_phase.is_empty())
        .collect()
}

fn available(
    tool: &str,
    codex_present: bool,
    cursor_present: bool,
) -> Result<bool, ExternalDefaultError> {
    match tool {
        "codex" => Ok(codex_present),
        "cursor" => Ok(cursor_present),
        "claude" => Ok(true),
        other => Err(ExternalDefaultError::new(format!("invalid tool {other:?}"))),
    }
}

fn override_result(raw: &str) -> Option<ResolveResult> {
    if raw.is_empty() {
        return None;
    }
    if raw.chars().any(char::is_whitespace) {
        return Some(ResolveResult {
            vendor: String::new(),
            skip_reason: "invalid-vendor".to_owned(),
        });
    }
    if raw != "codex" && raw != "claude" {
        return Some(ResolveResult {
            vendor: String::new(),
            skip_reason: "unknown-vendor".to_owned(),
        });
    }
    Some(ResolveResult {
        vendor: raw.to_owned(),
        skip_reason: String::new(),
    })
}

/// Resolve the first available vendor for a `first_available` role.
///
/// # Errors
///
/// Returns [`ExternalDefaultError`] when the role is unknown, not
/// `first_available`, or lists an invalid tool.
pub fn resolve_vendor(
    role_id: &str,
    env_map: &BTreeMap<String, String>,
    codex_present: bool,
    cursor_present: bool,
) -> Result<ResolveResult, ExternalDefaultError> {
    let role = role_default(role_id)?;
    if role.kind != RoleKind::FirstAvailable {
        return Err(ExternalDefaultError::new(format!(
            "{role_id}: resolve_vendor requires kind=first_available"
        )));
    }
    if !role.env_override.is_empty()
        && let Some(override_value) =
            override_result(env_map.get(role.env_override).map_or("", String::as_str))
    {
        return Ok(override_value);
    }
    for tool in role.order {
        if available(tool, codex_present, cursor_present)? {
            return Ok(ResolveResult {
                vendor: (*tool).to_owned(),
                skip_reason: String::new(),
            });
        }
    }
    Ok(ResolveResult {
        vendor: String::new(),
        skip_reason: "no-vendor".to_owned(),
    })
}

/// Parse a `true`/`false` CLI flag for resolve-vendor.
///
/// # Errors
///
/// Returns [`ExternalDefaultError`] when the value is not exactly `true` or
/// `false`.
pub fn parse_bool_flag(value: &str, flag: &str) -> Result<bool, ExternalDefaultError> {
    match value {
        "true" => Ok(true),
        "false" => Ok(false),
        _ => Err(ExternalDefaultError::new(format!(
            "{flag} must be true or false"
        ))),
    }
}

#[cfg(test)]
mod tests {
    use super::{doc_rows, resolve_vendor, role_default};
    use std::collections::BTreeMap;

    #[test]
    fn role_lookup_and_docs_cover_every_python_row() {
        assert_eq!(doc_rows().len(), 21);
        let role = role_default("design.plan_drafter").expect("role");
        assert_eq!(role.env_override, "LARCH_DESIGN_DRAFTER");
        assert_eq!(role.order, &["codex", "claude"]);
    }

    #[test]
    fn resolve_vendor_honors_override_and_presence() {
        let empty = BTreeMap::new();
        let selected = resolve_vendor("design.plan_drafter", &empty, true, false).expect("ok");
        assert_eq!(selected.vendor, "codex");

        let mut env = BTreeMap::new();
        env.insert("LARCH_DESIGN_DRAFTER".to_owned(), "claude".to_owned());
        let overridden = resolve_vendor("design.plan_drafter", &env, true, false).expect("ok");
        assert_eq!(overridden.vendor, "claude");

        env.insert("LARCH_DESIGN_DRAFTER".to_owned(), "nope".to_owned());
        let unknown = resolve_vendor("design.plan_drafter", &env, true, false).expect("ok");
        assert_eq!(unknown.skip_reason, "unknown-vendor");
    }
}
