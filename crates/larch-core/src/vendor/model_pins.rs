//! Resolve config-pinned vendor model ids against live vendor model lists.
//!
//! Used by `/status` when a vendor probe reports `ok`. Cursor pins are checked
//! via `cursor agent models`; Codex has no model-list surface and is reported
//! as unverifiable rather than silently skipped.

use crate::vendor_model::{
    CODEX_DEFAULT_MODEL, CODEX_REVIEW_MODEL_DEFAULT, CODEX_VOTE_MODEL_DEFAULT,
    CURSOR_DEFAULT_MODEL, CURSOR_GROK_4_5_HIGH_MODEL, DEBATE_CODEX_MODEL, DEBATE_CURSOR_MODEL,
};
use regex::Regex;
use std::sync::OnceLock;

/// Status when every pinned id appears in the live list.
pub const MODEL_PINS_STATUS_OK: &str = "ok";
/// Status when at least one pinned id is absent from the live list.
pub const MODEL_PINS_STATUS_UNKNOWN_ID: &str = "unknown-id";
/// Status when `cursor agent models` exits non-zero.
pub const MODEL_PINS_STATUS_LIST_FAILED: &str = "list-failed";
/// Status when the live list cannot be parsed.
pub const MODEL_PINS_STATUS_UNPARSEABLE: &str = "unparseable";
/// Status when the vendor has no list surface (Codex).
pub const MODEL_PINS_STATUS_UNVERIFIABLE: &str = "unverifiable";
/// Status when the vendor probe is not ok, so pins are not resolved.
pub const MODEL_PINS_STATUS_SKIPPED: &str = "skipped";

/// Header line emitted by `cursor agent models`.
pub const CURSOR_MODEL_LIST_HEADER: &str = "Available models";

/// Argv for the Cursor model-list command (executable omitted).
pub const CURSOR_MODEL_LIST_ARGV: [&str; 2] = ["agent", "models"];

/// Default timeout for the model-list child, in seconds.
pub const EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC: u64 = 30;

/// One named pin declaration.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PinnedModel {
    /// Config constant that owns this pin.
    pub constant_name: &'static str,
    /// Model id string.
    pub model_id: &'static str,
}

/// Per-vendor pin resolution outcome.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VendorModelPinResult {
    vendor: String,
    status: String,
    detail: String,
}

impl VendorModelPinResult {
    /// Build a pin result.
    #[must_use]
    pub fn new(
        vendor: impl Into<String>,
        status: impl Into<String>,
        detail: impl Into<String>,
    ) -> Self {
        Self {
            vendor: vendor.into(),
            status: status.into(),
            detail: detail.into(),
        }
    }

    /// Vendor name (`cursor` or `codex`).
    #[must_use]
    pub fn vendor(&self) -> &str {
        &self.vendor
    }

    /// Status token.
    #[must_use]
    pub fn status(&self) -> &str {
        &self.status
    }

    /// Optional operator-facing detail (single line).
    #[must_use]
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

/// Combined Cursor and Codex pin report.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ModelPinsReport {
    /// Cursor pin resolution.
    pub cursor: VendorModelPinResult,
    /// Codex pin resolution.
    pub codex: VendorModelPinResult,
}

/// All named Cursor pin declarations, retaining duplicate model IDs.
#[must_use]
pub fn cursor_pinned_model_declarations() -> Vec<PinnedModel> {
    let mut declarations = Vec::new();
    let mut seen_impl = std::collections::BTreeSet::new();
    for model_id in [
        CURSOR_GROK_4_5_HIGH_MODEL, // trivial
        CURSOR_GROK_4_5_HIGH_MODEL, // moderate
        CURSOR_DEFAULT_MODEL,       // hard
    ] {
        if seen_impl.insert(model_id) {
            declarations.push(PinnedModel {
                constant_name: "CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY",
                model_id,
            });
        }
    }
    declarations.push(PinnedModel {
        constant_name: "DEBATE_CURSOR_MODEL",
        model_id: DEBATE_CURSOR_MODEL,
    });
    declarations
}

/// Unique Cursor pins sorted by model id.
#[must_use]
pub fn cursor_pinned_models() -> Vec<PinnedModel> {
    let mut by_id = std::collections::BTreeMap::new();
    for pin in cursor_pinned_model_declarations() {
        by_id.entry(pin.model_id).or_insert(pin.constant_name);
    }
    by_id
        .into_iter()
        .map(|(model_id, constant_name)| PinnedModel {
            constant_name,
            model_id,
        })
        .collect()
}

/// All named Codex pin declarations.
#[must_use]
pub fn codex_pinned_model_declarations() -> Vec<PinnedModel> {
    vec![
        PinnedModel {
            constant_name: "CODEX_DEFAULT_MODEL",
            model_id: CODEX_DEFAULT_MODEL,
        },
        PinnedModel {
            constant_name: "CODEX_REVIEW_MODEL_DEFAULT",
            model_id: CODEX_REVIEW_MODEL_DEFAULT,
        },
        PinnedModel {
            constant_name: "CODEX_VOTE_MODEL_DEFAULT",
            model_id: CODEX_VOTE_MODEL_DEFAULT,
        },
        PinnedModel {
            constant_name: "DEBATE_CODEX_MODEL",
            model_id: DEBATE_CODEX_MODEL,
        },
    ]
}

/// Unique Codex pins sorted by model id.
#[must_use]
pub fn codex_pinned_models() -> Vec<PinnedModel> {
    let mut by_id = std::collections::BTreeMap::new();
    for pin in codex_pinned_model_declarations() {
        by_id.entry(pin.model_id).or_insert(pin.constant_name);
    }
    by_id
        .into_iter()
        .map(|(model_id, constant_name)| PinnedModel {
            constant_name,
            model_id,
        })
        .collect()
}

fn cursor_model_line_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"^([A-Za-z0-9][A-Za-z0-9._+-]*) - .+$").expect("cursor model line regex")
    })
}

/// Parse `cursor agent models` stdout with a pinned grammar.
///
/// Returns the set of model ids, or `None` when the output is unparseable
/// (fail closed: empty, header-only, or any non-matching non-blank line).
#[must_use]
pub fn parse_cursor_model_list(stdout: &str) -> Option<std::collections::BTreeSet<String>> {
    let mut ids = std::collections::BTreeSet::new();
    for raw_line in stdout.lines() {
        let line = raw_line.trim();
        if line.is_empty() {
            continue;
        }
        if line == CURSOR_MODEL_LIST_HEADER {
            continue;
        }
        let captures = cursor_model_line_re().captures(line)?;
        ids.insert(captures[1].to_owned());
    }
    if ids.is_empty() { None } else { Some(ids) }
}

fn sanitize_detail(value: &str) -> String {
    value.replace(['\r', '\n'], " ").trim().to_owned()
}

fn format_unknown_detail(unknown: &[PinnedModel]) -> String {
    unknown
        .iter()
        .map(|pin| format!("{}={}", pin.constant_name, pin.model_id))
        .collect::<Vec<_>>()
        .join("; ")
}

/// Classify a failed `cursor agent models` invocation.
#[must_use]
pub fn list_failed_detail(returncode: i32, stderr: &str, timed_out: bool) -> String {
    if timed_out {
        return "cursor agent models timed out".to_owned();
    }
    let stderr = sanitize_detail(stderr);
    if stderr.is_empty() {
        format!("cursor agent models exited {returncode}")
    } else {
        format!("cursor agent models exited {returncode}: {stderr}")
    }
}

/// Resolve Cursor pins against a live model-list outcome when the vendor is ok.
#[must_use]
pub fn resolve_cursor_model_pins_from_list(
    vendor_state: &str,
    list_outcome: Option<CursorModelListOutcome>,
) -> VendorModelPinResult {
    if vendor_state != "ok" {
        return VendorModelPinResult::new(
            "cursor",
            MODEL_PINS_STATUS_SKIPPED,
            "vendor probe not ok",
        );
    }
    let Some(outcome) = list_outcome else {
        return VendorModelPinResult::new(
            "cursor",
            MODEL_PINS_STATUS_LIST_FAILED,
            "cursor agent models exited without a result",
        );
    };
    if outcome.returncode != 0 {
        return VendorModelPinResult::new(
            "cursor",
            MODEL_PINS_STATUS_LIST_FAILED,
            list_failed_detail(outcome.returncode, &outcome.stderr, outcome.timed_out),
        );
    }
    let Some(live_ids) = parse_cursor_model_list(&outcome.stdout) else {
        return VendorModelPinResult::new(
            "cursor",
            MODEL_PINS_STATUS_UNPARSEABLE,
            "cursor agent models output unparseable",
        );
    };
    let unknown_ids: std::collections::BTreeSet<&str> = cursor_pinned_models()
        .into_iter()
        .filter(|pin| !live_ids.contains(pin.model_id))
        .map(|pin| pin.model_id)
        .collect();
    if !unknown_ids.is_empty() {
        let unknown: Vec<PinnedModel> = cursor_pinned_model_declarations()
            .into_iter()
            .filter(|pin| unknown_ids.contains(pin.model_id))
            .collect();
        return VendorModelPinResult::new(
            "cursor",
            MODEL_PINS_STATUS_UNKNOWN_ID,
            format_unknown_detail(&unknown),
        );
    }
    VendorModelPinResult::new("cursor", MODEL_PINS_STATUS_OK, "")
}

/// Report Codex pins as unverifiable when the vendor probe is ok.
#[must_use]
pub fn resolve_codex_model_pins(vendor_state: &str) -> VendorModelPinResult {
    if vendor_state != "ok" {
        return VendorModelPinResult::new(
            "codex",
            MODEL_PINS_STATUS_SKIPPED,
            "vendor probe not ok",
        );
    }
    let pin_summary = codex_pinned_model_declarations()
        .into_iter()
        .map(|pin| format!("{}={}", pin.constant_name, pin.model_id))
        .collect::<Vec<_>>()
        .join(", ");
    VendorModelPinResult::new(
        "codex",
        MODEL_PINS_STATUS_UNVERIFIABLE,
        format!("codex has no model-list surface ({pin_summary})"),
    )
}

/// Outcome of one `cursor agent models` child.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CursorModelListOutcome {
    /// Process exit code (or 124 when timed out at the Python boundary).
    pub returncode: i32,
    /// Captured stdout.
    pub stdout: String,
    /// Captured stderr.
    pub stderr: String,
    /// Whether the child timed out.
    pub timed_out: bool,
}

/// Resolve both vendors' pins.
#[must_use]
pub fn resolve_model_pins(
    codex_state: &str,
    cursor_state: &str,
    cursor_list: Option<CursorModelListOutcome>,
) -> ModelPinsReport {
    ModelPinsReport {
        cursor: resolve_cursor_model_pins_from_list(cursor_state, cursor_list),
        codex: resolve_codex_model_pins(codex_state),
    }
}

/// Resolve the model-list timeout from an optional env value.
#[must_use]
pub fn model_list_timeout_seconds(raw: Option<&str>) -> u64 {
    let Some(raw) = raw.map(str::trim).filter(|value| !value.is_empty()) else {
        return EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC;
    };
    match raw.parse::<f64>() {
        #[allow(
            clippy::cast_possible_truncation,
            clippy::cast_sign_loss,
            clippy::cast_precision_loss
        )] // positive finite seconds; ceil then narrow to u64
        Ok(value) if value > 0.0 => value.ceil() as u64,
        _ => EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC,
    }
}

#[cfg(test)]
mod tests {
    use super::{
        CURSOR_MODEL_LIST_HEADER, CursorModelListOutcome,
        EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC, MODEL_PINS_STATUS_LIST_FAILED,
        MODEL_PINS_STATUS_OK, MODEL_PINS_STATUS_SKIPPED, MODEL_PINS_STATUS_UNKNOWN_ID,
        MODEL_PINS_STATUS_UNPARSEABLE, MODEL_PINS_STATUS_UNVERIFIABLE, VendorModelPinResult,
        codex_pinned_models, cursor_pinned_models, list_failed_detail, model_list_timeout_seconds,
        parse_cursor_model_list, resolve_codex_model_pins, resolve_cursor_model_pins_from_list,
        resolve_model_pins,
    };
    use crate::vendor_model::{CURSOR_DEFAULT_MODEL, CURSOR_GROK_4_5_HIGH_MODEL};
    use std::fmt::Write as _;

    #[test]
    fn parse_cursor_model_list_accepts_known_grammar() {
        let parsed = parse_cursor_model_list(&format!(
            "{CURSOR_MODEL_LIST_HEADER}\n{CURSOR_DEFAULT_MODEL} - default\n{CURSOR_GROK_4_5_HIGH_MODEL} - grok\n"
        ))
        .expect("parse");
        assert!(parsed.contains(CURSOR_DEFAULT_MODEL));
        assert!(parsed.contains(CURSOR_GROK_4_5_HIGH_MODEL));
        assert!(parse_cursor_model_list("Available models\nnot a model line\n").is_none());
        assert!(parse_cursor_model_list("Available models\n\n").is_none());
        assert!(parse_cursor_model_list("").is_none());
    }

    #[test]
    fn resolve_cursor_unknown_and_ok() {
        let pins = cursor_pinned_models();
        let mut stdout = format!("{CURSOR_MODEL_LIST_HEADER}\n");
        for pin in &pins {
            let _ = writeln!(stdout, "{} - label", pin.model_id);
        }
        let ok = resolve_cursor_model_pins_from_list(
            "ok",
            Some(CursorModelListOutcome {
                returncode: 0,
                stdout,
                stderr: String::new(),
                timed_out: false,
            }),
        );
        assert_eq!(ok.status(), MODEL_PINS_STATUS_OK);

        let unknown = resolve_cursor_model_pins_from_list(
            "ok",
            Some(CursorModelListOutcome {
                returncode: 0,
                stdout: format!("{CURSOR_MODEL_LIST_HEADER}\nother-model - x\n"),
                stderr: String::new(),
                timed_out: false,
            }),
        );
        assert_eq!(unknown.status(), MODEL_PINS_STATUS_UNKNOWN_ID);

        let skipped = resolve_cursor_model_pins_from_list("binary-missing", None);
        assert_eq!(skipped.status(), MODEL_PINS_STATUS_SKIPPED);
    }

    #[test]
    fn resolve_codex_unverifiable_and_combined_report() {
        let codex = resolve_codex_model_pins("ok");
        assert_eq!(codex.status(), MODEL_PINS_STATUS_UNVERIFIABLE);
        assert!(codex.detail().contains("no model-list surface"));

        let pins = cursor_pinned_models();
        let mut stdout = format!("{CURSOR_MODEL_LIST_HEADER}\n");
        for pin in &pins {
            let _ = writeln!(stdout, "{} - label", pin.model_id);
        }
        let report = resolve_model_pins(
            "ok",
            "ok",
            Some(CursorModelListOutcome {
                returncode: 0,
                stdout,
                stderr: String::new(),
                timed_out: false,
            }),
        );
        assert_eq!(report.cursor.status(), MODEL_PINS_STATUS_OK);
        assert_eq!(report.codex.status(), MODEL_PINS_STATUS_UNVERIFIABLE);

        let unparseable = resolve_cursor_model_pins_from_list(
            "ok",
            Some(CursorModelListOutcome {
                returncode: 0,
                stdout: "garbage\n".to_owned(),
                stderr: String::new(),
                timed_out: false,
            }),
        );
        assert_eq!(unparseable.status(), MODEL_PINS_STATUS_UNPARSEABLE);
    }

    #[test]
    fn pin_accessors_timeout_and_list_failure_edges() {
        let pin = VendorModelPinResult::new("cursor", MODEL_PINS_STATUS_OK, "detail\nline");
        assert_eq!(pin.vendor(), "cursor");
        assert_eq!(pin.status(), MODEL_PINS_STATUS_OK);
        assert_eq!(pin.detail(), "detail\nline");

        let codex_pins = codex_pinned_models();
        assert!(!codex_pins.is_empty());
        assert!(
            codex_pins
                .windows(2)
                .all(|pair| pair[0].model_id <= pair[1].model_id)
        );

        assert_eq!(
            list_failed_detail(124, "ignored", true),
            "cursor agent models timed out"
        );
        assert_eq!(
            list_failed_detail(2, "", false),
            "cursor agent models exited 2"
        );
        assert_eq!(
            list_failed_detail(3, "boom\r\nline", false),
            "cursor agent models exited 3: boom  line"
        );

        let missing_list = resolve_cursor_model_pins_from_list("ok", None);
        assert_eq!(missing_list.status(), MODEL_PINS_STATUS_LIST_FAILED);
        assert!(missing_list.detail().contains("without a result"));

        let failed_list = resolve_cursor_model_pins_from_list(
            "ok",
            Some(CursorModelListOutcome {
                returncode: 9,
                stdout: String::new(),
                stderr: String::new(),
                timed_out: false,
            }),
        );
        assert_eq!(failed_list.status(), MODEL_PINS_STATUS_LIST_FAILED);
        assert!(failed_list.detail().contains("exited 9"));

        let skipped_codex = resolve_codex_model_pins("probe-failed");
        assert_eq!(skipped_codex.status(), MODEL_PINS_STATUS_SKIPPED);
        assert_eq!(skipped_codex.vendor(), "codex");

        assert_eq!(
            model_list_timeout_seconds(None),
            EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC
        );
        assert_eq!(
            model_list_timeout_seconds(Some("")),
            EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC
        );
        assert_eq!(model_list_timeout_seconds(Some("1.2")), 2);
        assert_eq!(
            model_list_timeout_seconds(Some("0")),
            EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC
        );
        assert_eq!(
            model_list_timeout_seconds(Some("nope")),
            EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC
        );
    }
}
