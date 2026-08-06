//! Degraded external-tool gate classification and operator-facing phrases.
//!
//! Pure decision logic for `agent degraded-tools-gate`. Inputs are already
//! resolved presence and binary-found strings; this module never probes.

/// External tools the degraded-tools gate reports on.
pub const EXTERNAL_TOOL_NAMES: [&str; 2] = ["codex", "cursor"];

/// Normalize a boolean presence token: only the literal `true` stays true.
#[must_use]
pub fn norm_bool(value: &str) -> &'static str {
    if value == "true" { "true" } else { "false" }
}

/// Normalize a tri-state binary-found token.
#[must_use]
pub fn norm_tristate(value: &str) -> &'static str {
    if value == "true" || value == "false" {
        if value == "true" { "true" } else { "false" }
    } else {
        "unknown"
    }
}

/// Derive one tool's availability state from binary and present tokens.
#[must_use]
pub fn tool_state(binary_found: &str, present: &str) -> &'static str {
    if binary_found == "false" {
        return "binary-missing";
    }
    if present == "true" {
        return "ok";
    }
    if binary_found == "true" {
        return "probe-failed";
    }
    "unavailable"
}

/// Operator-facing phrase for one tool state.
#[must_use]
pub fn state_phrase(state: &str) -> &'static str {
    match state {
        "ok" => "available",
        "binary-missing" => "UNAVAILABLE: CLI binary not found on PATH",
        "probe-failed" => {
            "UNAVAILABLE: runtime health probe failed (binary present but the auth/quota check did not pass)"
        }
        "unavailable" => "UNAVAILABLE: session health probe did not pass",
        _ => "unknown",
    }
}

/// Optional Codex gate-detail message used when Codex is `probe-failed`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CodexGateMessage {
    message: String,
}

impl CodexGateMessage {
    /// Wrap an already-rendered gate-detail message.
    #[must_use]
    pub fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }

    /// Return the operator-facing message.
    #[must_use]
    pub fn message(&self) -> &str {
        &self.message
    }
}

/// Result of the degraded-tools gate for one skill invocation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DegradedToolsResult {
    degraded: bool,
    codex_state: String,
    cursor_state: String,
    both_down: bool,
    presence_input_empty: bool,
    explanation: Vec<String>,
}

impl DegradedToolsResult {
    /// Classify tool availability from already-resolved presence strings.
    #[must_use]
    pub fn classify(
        codex_binary_found: &str,
        codex_present: &str,
        cursor_binary_found: &str,
        cursor_present: &str,
        skill: &str,
        codex_gate_message: Option<&CodexGateMessage>,
    ) -> Self {
        let presence_input_empty = codex_present.is_empty() || cursor_present.is_empty();
        let c_b = norm_tristate(codex_binary_found);
        let c_p = norm_bool(codex_present);
        let u_b = norm_tristate(cursor_binary_found);
        let u_p = norm_bool(cursor_present);
        let codex_state = tool_state(c_b, c_p);
        let cursor_state = tool_state(u_b, u_p);
        let degraded = codex_state != "ok" || cursor_state != "ok";
        let both_down = codex_state != "ok" && cursor_state != "ok";
        let mut explanation = Vec::new();
        if degraded {
            let codex_phrase = if codex_state == "probe-failed" {
                codex_gate_message.map_or_else(
                    || state_phrase(codex_state).to_owned(),
                    |detail| detail.message().to_owned(),
                )
            } else {
                state_phrase(codex_state).to_owned()
            };
            explanation.extend([
                format!("⚠ Degraded external-tool availability for this /{skill} run:"),
                String::new(),
                format!("  • Codex:  {codex_phrase}"),
                format!("  • Cursor: {}", state_phrase(cursor_state)),
                String::new(),
                "Step 0 uses this health probe only as an operator-safety gate.".to_owned(),
                "Later vendor calls do not route from this probe result; they use binary"
                    .to_owned(),
                "presence, launcher-owned retries, and existing fallback/degradation paths."
                    .to_owned(),
                String::new(),
            ]);
            if both_down {
                explanation.extend([
                    "Both external vendors are unavailable. This run cannot continue.".to_owned(),
                    "Fix at least one vendor or retry after the outage clears.".to_owned(),
                ]);
            } else {
                explanation.extend([
                    "Exactly one external vendor is unavailable. Explicit operator confirmation"
                        .to_owned(),
                    "is required before continuing with reduced model-family diversity.".to_owned(),
                ]);
            }
        }
        Self {
            degraded,
            codex_state: codex_state.to_owned(),
            cursor_state: cursor_state.to_owned(),
            both_down,
            presence_input_empty,
            explanation,
        }
    }

    /// Whether either vendor is not fully available.
    #[must_use]
    pub const fn degraded(&self) -> bool {
        self.degraded
    }

    /// Codex tool state token.
    #[must_use]
    pub fn codex_state(&self) -> &str {
        &self.codex_state
    }

    /// Cursor tool state token.
    #[must_use]
    pub fn cursor_state(&self) -> &str {
        &self.cursor_state
    }

    /// Whether both vendors are unavailable.
    #[must_use]
    pub const fn both_down(&self) -> bool {
        self.both_down
    }

    /// Whether either presence input resolved empty (caller rehydration bug).
    #[must_use]
    pub const fn presence_input_empty(&self) -> bool {
        self.presence_input_empty
    }

    /// Operator-facing explanation lines between BEGIN/END markers.
    #[must_use]
    pub fn explanation(&self) -> &[String] {
        &self.explanation
    }

    /// Emit the gate's KEY=value envelope lines (without explanation block).
    #[must_use]
    pub fn kv_lines(&self) -> Vec<String> {
        let mut lines = vec![
            format!("DEGRADED={}", if self.degraded { "true" } else { "false" }),
            format!("CODEX_STATE={}", self.codex_state),
            format!("CURSOR_STATE={}", self.cursor_state),
            format!(
                "BOTH_DOWN={}",
                if self.both_down { "true" } else { "false" }
            ),
        ];
        if self.both_down {
            lines.push("DEGRADED_HARD_FAIL=true".to_owned());
        }
        if self.presence_input_empty {
            lines.push("PRESENCE_INPUT_EMPTY=true".to_owned());
        }
        lines
    }
}

#[cfg(test)]
mod tests {
    use super::{DegradedToolsResult, norm_bool, norm_tristate, state_phrase, tool_state};

    #[test]
    fn normalizers_and_tool_states_match_python() {
        assert_eq!(norm_bool("true"), "true");
        assert_eq!(norm_bool(""), "false");
        assert_eq!(norm_bool("yes"), "false");
        assert_eq!(norm_tristate("true"), "true");
        assert_eq!(norm_tristate("false"), "false");
        assert_eq!(norm_tristate(""), "unknown");
        assert_eq!(tool_state("false", "false"), "binary-missing");
        assert_eq!(tool_state("true", "true"), "ok");
        assert_eq!(tool_state("true", "false"), "probe-failed");
        assert_eq!(tool_state("unknown", "false"), "unavailable");
        assert_eq!(state_phrase("ok"), "available");
        assert_eq!(
            state_phrase("unavailable"),
            "UNAVAILABLE: session health probe did not pass"
        );
        assert_eq!(state_phrase("not-a-real-state"), "unknown");
    }

    #[test]
    fn codex_gate_message_overrides_probe_failed_phrase() {
        use super::CodexGateMessage;
        let gate = CodexGateMessage::new("cached gate detail");
        assert_eq!(gate.message(), "cached gate detail");
        let result = DegradedToolsResult::classify(
            "true",
            "false",
            "true",
            "true",
            "implement",
            Some(&gate),
        );
        assert!(result.degraded());
        assert!(!result.both_down());
        assert_eq!(result.codex_state(), "probe-failed");
        assert_eq!(result.cursor_state(), "ok");
        assert!(
            result
                .explanation()
                .iter()
                .any(|line| line.contains("cached gate detail"))
        );
        let healthy = DegradedToolsResult::classify("true", "true", "true", "true", "design", None);
        assert!(!healthy.degraded());
        assert_eq!(
            healthy.kv_lines(),
            vec![
                "DEGRADED=false".to_owned(),
                "CODEX_STATE=ok".to_owned(),
                "CURSOR_STATE=ok".to_owned(),
                "BOTH_DOWN=false".to_owned(),
            ]
        );
    }

    #[test]
    fn empty_presence_is_a_distinct_bug_signal() {
        let result = DegradedToolsResult::classify("true", "", "true", "true", "implement", None);
        assert!(result.presence_input_empty());
        assert!(result.degraded());
        assert_eq!(result.codex_state(), "probe-failed");
        assert!(
            result
                .kv_lines()
                .iter()
                .any(|line| line == "PRESENCE_INPUT_EMPTY=true")
        );
    }

    #[test]
    fn both_down_emits_hard_fail() {
        let result =
            DegradedToolsResult::classify("false", "false", "false", "false", "design", None);
        assert!(result.both_down());
        assert!(result.degraded());
        let kv = result.kv_lines();
        assert!(kv.iter().any(|line| line == "DEGRADED_HARD_FAIL=true"));
        assert!(
            result
                .explanation()
                .iter()
                .any(|line| { line.contains("Both external vendors are unavailable") })
        );
    }

    #[test]
    fn one_down_requires_operator_confirmation() {
        let result =
            DegradedToolsResult::classify("true", "true", "false", "false", "review", None);
        assert!(result.degraded());
        assert!(!result.both_down());
        assert!(
            result
                .explanation()
                .iter()
                .any(|line| { line.contains("Exactly one external vendor is unavailable") })
        );
    }
}
