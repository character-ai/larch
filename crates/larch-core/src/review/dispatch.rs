//! Typed, side-effect-free contracts shared by review dispatchers.

use std::{
    collections::{BTreeMap, BTreeSet},
    path::Path,
};

use serde_json::{Map, Value};

use crate::{CodexModelRole, ModelTool, resolve_model_args};

/// Review and plan-review dispatchers both carry exactly three voter slots.
pub const VOTER_SLOT_COUNT: usize = 3;

/// Stable ordering of voter status rows.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum VoterRowLayout {
    /// Code-review rows keep each voter's fields together.
    CodeReviewSequential,
    /// Plan-review rows interleave the second and third voters after voter one.
    PlanReviewInterleaved,
}

/// When a `VOTER_PATHS_FILE` row belongs in the wire output.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum VoterPathsFilePolicy {
    /// Always emit the path row.
    Always,
    /// Emit it only for a nonempty materialized file.
    Nonempty,
}

/// One resolved voter output slot.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VoterSlotState {
    /// Output path, or an empty string for absent output.
    pub path: String,
    /// Semantic tool label.
    pub tool: String,
    /// `launched`, `failed`, or `skipped`.
    pub status: String,
    /// `OK`, `NOT_SUBSTANTIVE`, or `SKIPPED`.
    pub parse_rate_status: String,
}

/// One policy required to resolve a voter slot from a waterfall binding.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VoterSlotPolicy {
    /// Stable slot name.
    pub slot_name: String,
    /// Vendor selected before a waterfall fallback.
    pub primary_tool: String,
    /// Semantic label used by failed and skipped slots.
    pub default_label: String,
    /// Semantic labels keyed by the actual dispatched vendor.
    pub semantic_labels: BTreeMap<String, String>,
}

/// One resolved waterfall output binding.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct VoterOutputBinding {
    /// Bound output path.
    pub path: String,
    /// Vendor that produced the output.
    pub tool: String,
    /// Whether the waterfall dropped the slot.
    pub dropped: bool,
}

/// Dispatch-helper validation failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DispatchError {
    /// A fixed three-voter policy contract received fewer than three policies.
    VoterCount,
    /// A voter-status wire contract received the wrong number of records.
    VoterRecordCount,
    /// A positive duration or timeout was invalid.
    InvalidPositiveFloat(String),
}

impl std::fmt::Display for DispatchError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::VoterCount => write!(
                formatter,
                "voter dispatch requires exactly three slot policies"
            ),
            Self::VoterRecordCount => write!(formatter, "exactly three voter records are required"),
            Self::InvalidPositiveFloat(label) => write!(formatter, "{label} must be positive"),
        }
    }
}

impl std::error::Error for DispatchError {}

/// Serialize an optional path at a wire boundary.
#[must_use]
pub fn path_for_wire(path: Option<&Path>) -> String {
    path.map_or_else(String::new, |value| value.display().to_string())
}

/// Parse an optional strictly positive float.
///
/// # Errors
/// Returns [`DispatchError::InvalidPositiveFloat`] for an invalid nonempty value.
pub fn optional_positive_float(value: &str, label: &str) -> Result<Option<f64>, DispatchError> {
    if value.is_empty() {
        return Ok(None);
    }
    let parsed = value
        .parse::<f64>()
        .map_err(|_| DispatchError::InvalidPositiveFloat(label.to_owned()))?;
    if parsed <= 0.0 {
        return Err(DispatchError::InvalidPositiveFloat(label.to_owned()));
    }
    Ok(Some(parsed))
}

/// Resolve exactly three voter states from the common waterfall binding shape.
///
/// # Errors
/// Returns [`DispatchError::VoterCount`] unless at least three policies are supplied.
pub fn voter_states_from_bindings(
    policies: &[VoterSlotPolicy],
    bindings: &BTreeMap<String, VoterOutputBinding>,
    launched_slots: &BTreeSet<String>,
    fallback_paths: &BTreeMap<String, String>,
) -> Result<Vec<VoterSlotState>, DispatchError> {
    if policies.len() < VOTER_SLOT_COUNT {
        return Err(DispatchError::VoterCount);
    }
    Ok(policies
        .iter()
        .take(VOTER_SLOT_COUNT)
        .map(|policy| {
            let fallback = fallback_paths
                .get(&policy.slot_name)
                .cloned()
                .unwrap_or_default();
            if !launched_slots.contains(&policy.slot_name) {
                return VoterSlotState {
                    path: fallback,
                    tool: policy.default_label.clone(),
                    status: "skipped".to_owned(),
                    parse_rate_status: "SKIPPED".to_owned(),
                };
            }
            let Some(binding) = bindings.get(&policy.slot_name) else {
                return failed_voter_state(policy, fallback);
            };
            if binding.dropped || binding.path.is_empty() {
                return failed_voter_state(policy, fallback);
            }
            let tool = if binding.tool.is_empty() {
                &policy.primary_tool
            } else {
                &binding.tool
            };
            VoterSlotState {
                path: binding.path.clone(),
                tool: policy
                    .semantic_labels
                    .get(tool)
                    .cloned()
                    .unwrap_or_else(|| policy.default_label.clone()),
                status: "launched".to_owned(),
                parse_rate_status: "SKIPPED".to_owned(),
            }
        })
        .collect())
}

fn failed_voter_state(policy: &VoterSlotPolicy, path: String) -> VoterSlotState {
    VoterSlotState {
        path,
        tool: policy.default_label.clone(),
        status: "failed".to_owned(),
        parse_rate_status: "SKIPPED".to_owned(),
    }
}

/// Render stable voter status rows, leaving filesystem inspection to the caller.
///
/// # Errors
/// Returns [`DispatchError::VoterRecordCount`] unless exactly three states are supplied.
pub fn voter_status_rows(
    voters: &[VoterSlotState],
    voter_paths_file: &str,
    row_layout: VoterRowLayout,
    paths_file_policy: VoterPathsFilePolicy,
    paths_file_nonempty: bool,
) -> Result<Vec<(String, String)>, DispatchError> {
    if voters.len() != VOTER_SLOT_COUNT {
        return Err(DispatchError::VoterRecordCount);
    }
    let order: &[(usize, usize)] = match row_layout {
        VoterRowLayout::CodeReviewSequential => &[
            (0, 0),
            (0, 1),
            (0, 2),
            (0, 3),
            (1, 0),
            (1, 1),
            (1, 2),
            (1, 3),
            (2, 0),
            (2, 1),
            (2, 2),
            (2, 3),
        ],
        VoterRowLayout::PlanReviewInterleaved => &[
            (0, 0),
            (0, 1),
            (0, 2),
            (0, 3),
            (1, 0),
            (2, 0),
            (1, 1),
            (2, 1),
            (1, 2),
            (2, 2),
            (1, 3),
            (2, 3),
        ],
    };
    let suffixes = ["PATH", "TOOL", "STATUS", "PARSE_RATE_STATUS"];
    let mut rows = order
        .iter()
        .map(|(voter, field)| {
            let state = &voters[*voter];
            let value = match field {
                0 => &state.path,
                1 => &state.tool,
                2 => &state.status,
                3 => &state.parse_rate_status,
                _ => unreachable!("fixed field order"),
            };
            (
                format!("VOTER_{}_{}", voter + 1, suffixes[*field]),
                value.clone(),
            )
        })
        .collect::<Vec<_>>();
    let paths_file_present = matches!(paths_file_policy, VoterPathsFilePolicy::Always)
        || (!voter_paths_file.is_empty() && paths_file_nonempty);
    if paths_file_present {
        let index = match row_layout {
            VoterRowLayout::CodeReviewSequential => rows.len(),
            VoterRowLayout::PlanReviewInterleaved => 6,
        };
        rows.insert(
            index,
            ("VOTER_PATHS_FILE".to_owned(), voter_paths_file.to_owned()),
        );
    }
    Ok(rows)
}

/// Interpret a delegated parse-rate command result with the Python fail-closed policy.
#[must_use]
pub fn parse_rate_status(returncode: i32, stdout: &str) -> String {
    if returncode != 0 {
        return "NOT_SUBSTANTIVE".to_owned();
    }
    let last = stdout.lines().map(str::trim).rfind(|line| !line.is_empty());
    match last {
        Some("OK") => "OK".to_owned(),
        _ => "NOT_SUBSTANTIVE".to_owned(),
    }
}

/// Resolve the model string recorded in a panel manifest through the canonical
/// vendor-model owner. Unknown tools and invalid settings fail closed to the
/// stable `unknown` wire value.
#[must_use]
pub fn resolved_manifest_model(
    tool: &str,
    model_role: &str,
    default_model: &str,
    environment: &BTreeMap<String, String>,
) -> String {
    let Ok(tool) = ModelTool::parse(tool) else {
        return "unknown".to_owned();
    };
    let role = CodexModelRole::parse(model_role).unwrap_or(CodexModelRole::Default);
    let Ok(result) = resolve_model_args(
        tool,
        matches!(tool, ModelTool::Codex),
        default_model,
        role,
        environment,
    ) else {
        return "unknown".to_owned();
    };
    let flag = match tool {
        ModelTool::Cursor => "--model",
        ModelTool::Codex => "-m",
    };
    result
        .argv()
        .windows(2)
        .find_map(|window| (window[0] == flag).then(|| window[1].clone()))
        .unwrap_or_else(|| "unknown".to_owned())
}

/// Add manifest attribution fields without overwriting producer-provided values.
#[must_use]
pub fn with_manifest_attribution(
    mut row: Map<String, Value>,
    model_role: Option<&str>,
    default_model: &str,
    environment: &BTreeMap<String, String>,
) -> Map<String, Value> {
    let tool = row
        .get("tool")
        .and_then(Value::as_str)
        .filter(|value| !value.is_empty())
        .unwrap_or("unknown")
        .to_owned();
    let role = model_role.map_or_else(
        || {
            row.get("model_role")
                .and_then(Value::as_str)
                .filter(|value| !value.is_empty())
                .unwrap_or("default")
                .to_owned()
        },
        ToOwned::to_owned,
    );
    row.entry("vendor".to_owned())
        .or_insert_with(|| Value::String(tool.clone()));
    if let Some(model_role) = model_role {
        row.entry("model_role".to_owned())
            .or_insert_with(|| Value::String(model_role.to_owned()));
    }
    row.entry("resolved_model".to_owned()).or_insert_with(|| {
        Value::String(resolved_manifest_model(
            &tool,
            &role,
            default_model,
            environment,
        ))
    });
    row
}
