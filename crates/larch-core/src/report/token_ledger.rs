//! Token-ledger record grammar and research-lane tally helpers.
//!
//! Owns the byte-stable JSONL mark/vendor rows and the research lane sidecar
//! contract used by the Rust `token` recording and staging commands. Filesystem
//! locking and path confinement stay in the CLI owner.

use crate::normalize_claude_ledger_model;
use serde_json::Value;
use sha2::{Digest as _, Sha256};
use std::{
    collections::BTreeMap,
    path::{Component, Path, PathBuf},
};

/// One parsed vendor-usage sidecar payload ready for ledger or NDJSON append.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TokenSidecarPayload {
    /// Normalized tool name (`codex`, `cursor`, `claude`, `claude_sub`, or `unknown`).
    pub tool: String,
    /// Stable raw label recorded beside the usage counts.
    pub raw: String,
    /// Uncached input tokens.
    pub input: u64,
    /// Output tokens.
    pub output: u64,
    /// Cache-read tokens.
    pub cache_read: u64,
    /// Cache-create tokens.
    pub cache_create: u64,
    /// Combined total tokens.
    pub total: u64,
    /// Optional model id already normalized for Claude ledger vendors.
    pub model: String,
}

/// Build one mark ledger line with stable key order and compact separators.
#[must_use]
pub fn mark_line(step: &str, timestamp: &str) -> String {
    format!(
        "{{\"type\":\"mark\",\"step\":{},\"ts\":{}}}\n",
        Value::String(step.to_owned()),
        Value::String(timestamp.to_owned()),
    )
}

/// Build one vendor ledger line, rejecting the reserved `claude` vendor.
///
/// # Errors
/// Returns the operator diagnostic when `vendor` is the reserved main-agent id.
pub fn vendor_line(
    vendor: &str,
    input: u64,
    output: u64,
    cache_read: u64,
    cache_create: u64,
    total: u64,
    raw: &str,
    model: &str,
    timestamp: &str,
) -> Result<String, String> {
    if vendor == "claude" {
        return Err(
            "vendor 'claude' is reserved; use 'claude_sub' for spawned-process Claude".to_owned(),
        );
    }
    // Emit keys in Python `json.dumps` insertion order so ledger bytes stay
    // stable without relying on serde_json preserve_order.
    let keys = [
        ("type", Value::String("vendor".to_owned())),
        ("vendor", Value::String(vendor.to_owned())),
        ("input", Value::Number(input.into())),
        ("output", Value::Number(output.into())),
        ("cache_read", Value::Number(cache_read.into())),
        ("cache_create", Value::Number(cache_create.into())),
        ("total", Value::Number(total.into())),
        ("raw", Value::String(raw.to_owned())),
        ("ts", Value::String(timestamp.to_owned())),
    ];
    let mut parts = Vec::with_capacity(10);
    for (key, value) in keys {
        parts.push(format!("\"{key}\":{value}"));
    }
    if !model.is_empty() {
        let recorded = if vendor == "claude_sub" {
            normalize_claude_ledger_model(model).to_owned()
        } else {
            model.to_owned()
        };
        parts.push(format!("\"model\":{}", Value::String(recorded)));
    }
    Ok(format!("{{{}}}\n", parts.join(",")))
}

/// Encode one staging NDJSON row from a parsed sidecar payload.
#[must_use]
pub fn sidecar_ndjson_line(payload: &TokenSidecarPayload) -> String {
    let mut parts = vec![
        format!("\"tool\":{}", Value::String(payload.tool.clone())),
        format!("\"raw\":{}", Value::String(payload.raw.clone())),
        format!("\"input\":{}", Value::Number(payload.input.into())),
        format!("\"output\":{}", Value::Number(payload.output.into())),
        format!(
            "\"cache_read\":{}",
            Value::Number(payload.cache_read.into())
        ),
        format!(
            "\"cache_create\":{}",
            Value::Number(payload.cache_create.into())
        ),
        format!("\"total\":{}", Value::Number(payload.total.into())),
    ];
    if !payload.model.is_empty() {
        parts.push(format!(
            "\"model\":{}",
            Value::String(payload.model.clone())
        ));
    }
    format!("{{{}}}\n", parts.join(","))
}

/// Parse a KEY=value token-record sidecar into a usage payload.
#[must_use]
pub fn parse_token_record_sidecar(kv: &BTreeMap<String, String>) -> Option<TokenSidecarPayload> {
    let mut tool = kv.get("TOOL").map_or("unknown", String::as_str).to_owned();
    if !matches!(tool.as_str(), "codex" | "cursor" | "claude" | "claude_sub") {
        tool = "unknown".to_owned();
    }
    let uint_key = |key: &str| -> u64 {
        kv.get(key)
            .filter(|raw| raw.bytes().all(|byte| byte.is_ascii_digit()))
            .and_then(|raw| raw.parse().ok())
            .unwrap_or(0)
    };
    let input = uint_key("INPUT");
    let output = uint_key("OUTPUT");
    let cache_read = uint_key("CACHE_READ");
    let cache_create = uint_key("CACHE_CREATE");
    let mut total = uint_key("TOTAL");
    if total == 0 {
        total = input + output + cache_read + cache_create;
    }
    if total == 0 {
        return None;
    }
    let raw = kv
        .get("RAW")
        .filter(|value| !value.is_empty())
        .cloned()
        .unwrap_or_else(|| format!("{tool}_ci_fix"));
    let model_raw = kv.get("MODEL").map_or("", String::as_str);
    let model = if model_raw.is_empty() {
        String::new()
    } else if matches!(tool.as_str(), "claude" | "claude_sub") {
        normalize_claude_ledger_model(model_raw).to_owned()
    } else {
        model_raw.to_owned()
    };
    Some(TokenSidecarPayload {
        tool,
        raw,
        input,
        output,
        cache_read,
        cache_create,
        total,
        model,
    })
}

/// Map a sidecar tool onto the active-ledger vendor namespace.
#[must_use]
pub fn active_ledger_vendor(tool: &str) -> Option<&'static str> {
    match tool {
        "codex" => Some("codex"),
        "cursor" => Some("cursor"),
        "claude" | "claude_sub" => Some("claude_sub"),
        _ => None,
    }
}

/// Hex SHA-256 of one UTF-8 value, matching Python's `_sha256_hex`.
#[must_use]
pub fn sha256_hex(value: &str) -> String {
    let digest = Sha256::digest(value.as_bytes());
    hex_encode(&digest)
}

/// Sanitize a lane name the same way Python does for sidecar filenames.
#[must_use]
pub fn safe_lane_slug(lane: &str) -> String {
    lane.to_ascii_lowercase()
        .chars()
        .map(|ch| {
            if ch.is_ascii_lowercase() || ch.is_ascii_digit() {
                ch
            } else {
                '-'
            }
        })
        .collect()
}

/// Basename for one research/validation lane sidecar.
#[must_use]
pub fn lane_sidecar_name(phase: &str, lane: &str) -> String {
    format!("lane-tokens-{phase}-{}.txt", safe_lane_slug(lane))
}

/// KEY=value body written by `token lane-write`.
#[must_use]
pub fn lane_sidecar_body(phase: &str, lane: &str, tool: &str, total_tokens: &str) -> String {
    format!("PHASE={phase}\nLANE={lane}\nTOOL={tool}\nTOTAL_TOKENS={total_tokens}\n")
}

/// Validate `--phase` for lane telemetry.
///
/// # Errors
/// Returns the operator diagnostic when the phase is not allowed.
pub fn validate_lane_phase(phase: &str) -> Result<(), String> {
    if matches!(phase, "research" | "validation") {
        Ok(())
    } else {
        Err("--phase must be research or validation".to_owned())
    }
}

/// Validate `--total-tokens` for lane telemetry.
///
/// # Errors
/// Returns the operator diagnostic when the value is neither `unknown` nor a
/// non-negative integer.
pub fn validate_total_tokens(total_tokens: &str) -> Result<(), String> {
    if total_tokens == "unknown" || total_tokens.bytes().all(|byte| byte.is_ascii_digit()) {
        Ok(())
    } else {
        Err("--total-tokens must be a non-negative integer or 'unknown'".to_owned())
    }
}

/// Report whether `raw` contains a `..` path component.
#[must_use]
pub fn contains_dotdot(raw: &str) -> bool {
    Path::new(raw)
        .components()
        .any(|component| matches!(component, Component::ParentDir))
}

/// Default ledger basename for a resolved session slug.
#[must_use]
pub fn default_ledger_basename(session_slug: &str) -> String {
    format!("larch-tokens-{session_slug}.jsonl")
}

/// Render the research `token lane-report` Markdown body.
#[must_use]
pub fn render_lane_report(
    lanes: &BTreeMap<&'static str, Vec<String>>,
    totals: &BTreeMap<&'static str, u64>,
    measured: &BTreeMap<&'static str, u64>,
    unknown: &BTreeMap<&'static str, u64>,
    rate_per_million: f64,
    root_missing: bool,
) -> String {
    let mut lines = vec![
        "## Token Spend (Claude tokens only; external lanes excluded)".to_owned(),
        String::new(),
    ];
    if root_missing {
        lines.push(
            "_(token telemetry unavailable: $RESEARCH_TMPDIR was already removed)_".to_owned(),
        );
        return lines.join("\n");
    }
    let research_empty = lanes.get("research").is_none_or(Vec::is_empty);
    let validation_empty = lanes.get("validation").is_none_or(Vec::is_empty);
    if research_empty && validation_empty {
        lines.push(
            "_(no measurements available: Claude inline only, no measurable subagent invocations)_"
                .to_owned(),
        );
        return lines.join("\n");
    }
    lines.push(phase_row(
        "Research phase",
        "research",
        lanes,
        totals,
        measured,
        unknown,
        rate_per_million,
    ));
    lines.push(phase_row(
        "Validation phase",
        "validation",
        lanes,
        totals,
        measured,
        unknown,
        rate_per_million,
    ));
    let grand = totals.get("research").copied().unwrap_or(0)
        + totals.get("validation").copied().unwrap_or(0);
    let total_measured = measured.get("research").copied().unwrap_or(0)
        + measured.get("validation").copied().unwrap_or(0);
    let total_unknown = unknown.get("research").copied().unwrap_or(0)
        + unknown.get("validation").copied().unwrap_or(0);
    let total_lanes = total_measured + total_unknown;
    let mut cov = format!("({total_lanes} lanes, {total_measured} measured");
    if total_unknown > 0 {
        cov.push_str(&format!(", {total_unknown} unmeasurable)"));
    } else {
        cov.push(')');
    }
    let cost = if rate_per_million > 0.0 && grand > 0 {
        format!("  ${:.4}", (grand as f64 * rate_per_million) / 1_000_000.0)
    } else {
        String::new()
    };
    lines.push(format!("  {:<22} {cov}: total={grand}{cost}", "Total"));
    lines.push(String::new());
    lines.push(
        "_Note: only Claude subagent (Agent-tool) invocations report token counts. Claude inline (orchestrator) and external lanes (Cursor/Codex) are excluded from the totals above._"
            .to_owned(),
    );
    lines.join("\n")
}

/// Resolve a candidate ledger path under one of the allowed roots.
///
/// # Errors
/// Returns the operator diagnostic when the candidate escapes every allowed root
/// or contains a forbidden `..` segment.
pub fn resolve_under_roots(
    raw: &str,
    tmp_root: &Path,
    allowed: &[PathBuf],
) -> Result<PathBuf, String> {
    if raw.is_empty() || contains_dotdot(raw) {
        return Err(format!("ledger must not be empty or contain '..': {raw}"));
    }
    let candidate = {
        let path = PathBuf::from(raw);
        if path.is_absolute() {
            path
        } else {
            tmp_root.join(path)
        }
    };
    let parent = candidate.parent().unwrap_or_else(|| Path::new("."));
    let parent = parent
        .canonicalize()
        .map_err(|_error| format!("ledger must resolve under TMPDIR: {raw}"))?;
    let resolved = parent.join(candidate.file_name().unwrap_or_default());
    if !allowed.iter().any(|base| path_under(&resolved, base)) {
        return Err(format!("ledger must resolve under TMPDIR: {raw}"));
    }
    Ok(resolved)
}

fn path_under(child: &Path, parent: &Path) -> bool {
    child == parent || child.starts_with(parent)
}

fn phase_row(
    label: &str,
    phase: &'static str,
    lanes: &BTreeMap<&'static str, Vec<String>>,
    totals: &BTreeMap<&'static str, u64>,
    measured: &BTreeMap<&'static str, u64>,
    unknown: &BTreeMap<&'static str, u64>,
    rate_per_million: f64,
) -> String {
    let empty = lanes.get(phase).is_none_or(Vec::is_empty);
    if empty {
        let suffix = if phase == "research" {
            "(4 lanes, Codex-first with per-lane Claude fallback): not measured"
        } else {
            "(3 reviewers, Code|Cursor|Codex): not measured"
        };
        return format!("  {label:<22} {suffix}");
    }
    let measured_count = measured.get(phase).copied().unwrap_or(0);
    let unknown_count = unknown.get(phase).copied().unwrap_or(0);
    let count = measured_count + unknown_count;
    let mut cov = format!("({count} lanes, {measured_count} measured");
    if unknown_count > 0 {
        cov.push_str(&format!(", {unknown_count} unmeasurable)"));
    } else {
        cov.push(')');
    }
    let total = totals.get(phase).copied().unwrap_or(0);
    let cost = if rate_per_million > 0.0 && total > 0 {
        format!("  ${:.4}", (total as f64 * rate_per_million) / 1_000_000.0)
    } else {
        String::new()
    };
    format!("  {label:<22}{cov}: total={total}{cost}")
}

fn hex_encode(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::{
        active_ledger_vendor, mark_line, parse_token_record_sidecar, safe_lane_slug,
        sidecar_ndjson_line, vendor_line,
    };
    use std::collections::BTreeMap;

    #[test]
    fn mark_line_preserves_key_order() {
        assert_eq!(
            mark_line("Step 1", "2026-01-02T03:04:05Z"),
            "{\"type\":\"mark\",\"step\":\"Step 1\",\"ts\":\"2026-01-02T03:04:05Z\"}\n"
        );
    }

    #[test]
    fn vendor_line_rejects_reserved_claude() {
        assert!(vendor_line("claude", 1, 0, 0, 0, 1, "x", "", "t").is_err());
    }

    #[test]
    fn vendor_line_normalizes_claude_sub_model() {
        let line = vendor_line(
            "claude_sub",
            1,
            2,
            3,
            4,
            10,
            "claude_review",
            "claude-sonnet-4-6[1m]",
            "2026-01-02T03:04:05Z",
        )
        .expect("vendor line");
        assert!(line.contains("\"model\":\"claude-sonnet-4-6\""));
        assert!(line.ends_with('\n'));
    }

    #[test]
    fn sidecar_parser_sums_when_total_missing() {
        let mut kv = BTreeMap::new();
        kv.insert("TOOL".to_owned(), "codex".to_owned());
        kv.insert("INPUT".to_owned(), "3".to_owned());
        kv.insert("OUTPUT".to_owned(), "4".to_owned());
        let payload = parse_token_record_sidecar(&kv).expect("payload");
        assert_eq!(payload.total, 7);
        assert_eq!(payload.raw, "codex_ci_fix");
        assert_eq!(active_ledger_vendor(&payload.tool), Some("codex"));
        assert!(sidecar_ndjson_line(&payload).contains("\"total\":7"));
    }

    #[test]
    fn lane_slug_matches_python() {
        assert_eq!(safe_lane_slug("edge-cases"), "edge-cases");
        assert_eq!(safe_lane_slug("Code Review"), "code-review");
    }
}
