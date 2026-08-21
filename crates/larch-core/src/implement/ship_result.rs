//! Typed ship-result JSON and the durable Step 8 result-env contract.

use std::{fmt, path::Path};

use serde::{Deserialize, Serialize};

use crate::{
    KeyPolicy, KvDocument, KvRow, RenderOptions, private_atomic_write, validate_merge_result_env,
};

/// Shared workflow outcome under the ship-result API name.
pub use crate::WorkflowOutcome as ShipOutcome;

/// JSON result emitted by the still-Python driver and reused by the Rust driver.
#[derive(Clone, Debug, Default, Deserialize, Eq, PartialEq, Serialize)]
#[serde(default)]
pub struct ShipResult {
    pub outcome: ShipOutcome,
    pub needs_user_reason: String,
    pub failed_run_id: String,
    pub pr_number: Option<i64>,
    pub pr_url: String,
    pub merge_result: String,
    pub detail: String,
    pub ledger_ready: bool,
    pub ledger_site: String,
    pub ledger_trigger: String,
    pub ledger_step: String,
    pub ledger_phase: String,
    pub ledger_dispatcher: String,
    pub ledger_exit_code: Option<i64>,
    pub ledger_failure_detail_log: String,
    pub main_health_head_sha: String,
    pub main_health_repair_committed: String,
    pub main_health_repair_failed_run_id: String,
    pub main_health_repair_base_sha: String,
    pub main_health_repair_head: String,
    pub emergency_repair_branch: String,
    pub original_branch_forbidden: String,
    pub main_repair_run_id: String,
    pub main_repair_head: String,
    pub emergency_repair_pr_number: String,
    pub ci_errors_file: String,
    pub ci_errors_distill_class: String,
    pub failed_jobs_count: i64,
}

/// Stable result parsing, validation, or publication failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ShipResultError(String);

impl ShipResultError {
    fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

impl fmt::Display for ShipResultError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::error::Error for ShipResultError {}

impl ShipResult {
    /// Parse the driver's one JSON result from its captured contract stream.
    ///
    /// # Errors
    /// Returns an error when the stream is not a typed result with an explicit outcome.
    pub fn from_json(text: &str) -> Result<Self, ShipResultError> {
        let value: serde_json::Value = serde_json::from_str(text.trim())
            .map_err(|error| ShipResultError::new(format!("invalid ship result JSON: {error}")))?;
        if !value
            .as_object()
            .is_some_and(|document| document.contains_key("outcome"))
        {
            return Err(ShipResultError::new(
                "invalid ship result JSON: missing outcome",
            ));
        }
        serde_json::from_value(value)
            .map_err(|error| ShipResultError::new(format!("invalid ship result JSON: {error}")))
    }

    /// Render the exact ordered Step 8 result-env rows.
    ///
    /// # Errors
    /// Returns an error when a result value cannot be represented in the KV wire grammar.
    pub fn render_result_env(&self) -> Result<String, ShipResultError> {
        let scalar = |value: &str| value.replace(['\r', '\n'], " ");
        let mut rows: Vec<(&str, String)> = vec![
            ("outcome", self.outcome.as_str().to_owned()),
            ("NEEDS_USER_REASON", scalar(&self.needs_user_reason)),
            ("FAILED_RUN_ID", scalar(&self.failed_run_id)),
            (
                "PR_NUMBER",
                self.pr_number
                    .map(|value| value.to_string())
                    .unwrap_or_default(),
            ),
            ("PR_URL", scalar(&self.pr_url)),
            ("MERGE_RESULT", scalar(&self.merge_result)),
            ("DETAIL", scalar(&self.detail)),
            ("ledger_ready", self.ledger_ready.to_string()),
            ("ledger_site", scalar(&self.ledger_site)),
            ("ledger_trigger", scalar(&self.ledger_trigger)),
            ("ledger_step", scalar(&self.ledger_step)),
            ("ledger_phase", scalar(&self.ledger_phase)),
            ("ledger_dispatcher", scalar(&self.ledger_dispatcher)),
            (
                "ledger_exit_code",
                self.ledger_exit_code
                    .map(|value| value.to_string())
                    .unwrap_or_default(),
            ),
            (
                "ledger_failure_detail_log",
                scalar(&self.ledger_failure_detail_log),
            ),
            ("MAIN_HEALTH_HEAD_SHA", scalar(&self.main_health_head_sha)),
            (
                "MAIN_HEALTH_REPAIR_COMMITTED",
                scalar(&self.main_health_repair_committed),
            ),
            (
                "MAIN_HEALTH_REPAIR_FAILED_RUN_ID",
                scalar(&self.main_health_repair_failed_run_id),
            ),
            (
                "MAIN_HEALTH_REPAIR_BASE_SHA",
                scalar(&self.main_health_repair_base_sha),
            ),
            (
                "MAIN_HEALTH_REPAIR_HEAD",
                scalar(&self.main_health_repair_head),
            ),
            (
                "EMERGENCY_REPAIR_BRANCH",
                scalar(&self.emergency_repair_branch),
            ),
            (
                "ORIGINAL_BRANCH_FORBIDDEN",
                scalar(&self.original_branch_forbidden),
            ),
            ("MAIN_REPAIR_RUN_ID", scalar(&self.main_repair_run_id)),
            ("MAIN_REPAIR_HEAD", scalar(&self.main_repair_head)),
            (
                "EMERGENCY_REPAIR_PR_NUMBER",
                scalar(&self.emergency_repair_pr_number),
            ),
            ("CI_ERRORS_FILE", scalar(&self.ci_errors_file)),
            (
                "FAILED_JOBS_COUNT",
                self.failed_jobs_count.max(0).to_string(),
            ),
        ];
        if self.ci_errors_file.is_empty() {
            rows.push((
                "CI_ERRORS_DISTILL_CLASS",
                scalar(&self.ci_errors_distill_class),
            ));
        }
        let rows = rows
            .into_iter()
            .map(|(key, value)| KvRow::new(key, value, KeyPolicy::Wire))
            .collect::<Result<Vec<_>, _>>()
            .map_err(|error| ShipResultError::new(error.to_string()))?;
        KvDocument::from_rows(rows)
            .render(RenderOptions::wire())
            .map_err(|error| ShipResultError::new(error.to_string()))
    }

    /// Validate then atomically publish the result env under `tmpdir`.
    ///
    /// # Errors
    /// Returns an error when the path is unsafe or the private atomic write fails.
    pub fn write_result_env(&self, path: &Path, tmpdir: &Path) -> Result<(), ShipResultError> {
        let path = validate_merge_result_env(path, tmpdir)
            .map_err(|error| ShipResultError::new(error.to_string()))?;
        private_atomic_write(&path, &self.render_result_env()?, tmpdir)
            .map_err(|error| ShipResultError::new(error.to_string()))
    }
}

/// Prevalidate a required result-env sink before the ship driver mutates state.
///
/// # Errors
/// Returns an error when the sink is not a safe regular-file path under `tmpdir`.
pub fn validate_ship_result_env(path: &Path, tmpdir: &Path) -> Result<(), ShipResultError> {
    validate_merge_result_env(path, tmpdir)
        .map(|_path| ())
        .map_err(|error| ShipResultError::new(error.to_string()))
}

#[cfg(test)]
mod tests {
    use super::{ShipOutcome, ShipResult, validate_ship_result_env};
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn result_env_preserves_wire_order_scalars_and_ci_pairing() {
        let result = ShipResult {
            outcome: ShipOutcome::NeedsUserInput,
            needs_user_reason: "first\nfixer".to_owned(),
            pr_number: Some(12),
            ledger_ready: true,
            ledger_exit_code: Some(3),
            ci_errors_distill_class: "distill-failed".to_owned(),
            failed_jobs_count: -2,
            ..ShipResult::default()
        };
        let text = result.render_result_env().expect("render");
        assert!(text.starts_with("outcome=NEEDS_USER_INPUT\nNEEDS_USER_REASON=first fixer\n"));
        assert!(text.contains("PR_NUMBER=12\n"));
        assert!(text.contains("ledger_ready=true\n"));
        assert!(text.contains("ledger_exit_code=3\n"));
        assert!(text.ends_with(
            "CI_ERRORS_FILE=\nFAILED_JOBS_COUNT=0\nCI_ERRORS_DISTILL_CLASS=distill-failed\n"
        ));
    }

    #[test]
    fn nonempty_ci_file_suppresses_distill_class() {
        let result = ShipResult {
            ci_errors_file: "/tmp/ci-errors.md".to_owned(),
            ci_errors_distill_class: "ignored".to_owned(),
            failed_jobs_count: 4,
            ..ShipResult::default()
        };
        let text = result.render_result_env().expect("render");
        assert!(text.ends_with("CI_ERRORS_FILE=/tmp/ci-errors.md\nFAILED_JOBS_COUNT=4\n"));
        assert!(!text.contains("CI_ERRORS_DISTILL_CLASS"));
    }

    #[test]
    fn result_env_write_is_confined_and_private() {
        let root = TempDir::new().expect("tmpdir");
        let path = root.path().join("bgjob/ship.result.env");
        fs::create_dir(path.parent().expect("parent")).expect("parent");
        validate_ship_result_env(&path, root.path()).expect("prevalidate");
        ShipResult::default()
            .write_result_env(&path, root.path())
            .expect("write");
        assert!(
            fs::read_to_string(&path)
                .expect("read")
                .starts_with("outcome=OK\n")
        );
        assert!(validate_ship_result_env(&root.path().join("../escape"), root.path()).is_err());
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt as _;
            assert_eq!(
                fs::metadata(&path).expect("metadata").permissions().mode() & 0o777,
                0o600
            );
        }
    }

    #[test]
    fn parser_rejects_malformed_or_unknown_outcomes() {
        assert!(ShipResult::from_json("not-json").is_err());
        assert!(ShipResult::from_json("{}").is_err());
        assert!(ShipResult::from_json(r#"{"outcome":"UNKNOWN"}"#).is_err());
        assert_eq!(
            ShipResult::from_json(r#"{"outcome":"STALLED","pr_number":null}"#)
                .expect("result")
                .outcome,
            ShipOutcome::Stalled
        );
    }
}
