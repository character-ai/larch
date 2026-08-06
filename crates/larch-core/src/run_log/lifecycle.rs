//! Shared run-lifecycle identity and terminal outcome policy.

use std::{error::Error, fmt, path::PathBuf};

use serde::{Deserialize, Serialize};

use crate::{
    RunLogStorageMode, RunLogStorageReason, RunLogStorageResolution, ToolRepositoryStorage,
};

/// Schema version for the lifecycle fields embedded in a v2 run manifest.
pub const LIFECYCLE_SCHEMA_VERSION: u64 = 3;
/// Schema version for the durable subprocess-rehydration context.
pub const LIFECYCLE_CONTEXT_SCHEMA_VERSION: u64 = 3;
/// Durable context basename.
pub const LIFECYCLE_CONTEXT_BASENAME: &str = "context.json";
/// Universal terminal report basename.
pub const UNIVERSAL_FINAL_REPORT: &str = "final-report.md";
/// Universal structured execution-issues basename.
pub const UNIVERSAL_EXECUTION_ISSUES: &str = "execution-issues.ndjson";
/// Universal session transcript basename.
pub const UNIVERSAL_SESSION_TRANSCRIPT: &str = "session-transcript.jsonl";

/// One of the four terminal states exposed by the lifecycle command family.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LifecycleOutcome {
    Success,
    Failure,
    Cancelled,
    EarlyReturn,
}

impl LifecycleOutcome {
    /// Stable manifest and stdout value.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Success => "success",
            Self::Failure => "failure",
            Self::Cancelled => "cancelled",
            Self::EarlyReturn => "early-return",
        }
    }
}

/// Persisted identity that lets a later subprocess finish a run without shell state.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct LifecycleContext {
    pub schema_version: u64,
    pub repo_root: PathBuf,
    pub publication_mode: String,
    pub storage_resolution_reason: String,
    pub storage_base_uri: Option<String>,
    pub client_repo: String,
    pub tool_repo_uri: Option<String>,
    pub storage_origin_id: Option<String>,
    pub local_namespace_id: Option<String>,
    pub skill: String,
    pub run_id: String,
    pub log_root: PathBuf,
    pub run_dir: PathBuf,
}

impl LifecycleContext {
    /// Create a context from one already-validated storage resolution.
    #[must_use]
    pub fn new(
        repo_root: PathBuf,
        resolution: &RunLogStorageResolution,
        skill: String,
        run_id: String,
        log_root: PathBuf,
    ) -> Self {
        let storage = resolution.storage();
        let run_dir = log_root.join(&skill).join(&run_id);
        Self {
            schema_version: LIFECYCLE_CONTEXT_SCHEMA_VERSION,
            repo_root,
            publication_mode: resolution.mode().to_string(),
            storage_resolution_reason: resolution.reason().to_string(),
            storage_base_uri: storage.map(|value| value.base.uri()),
            client_repo: resolution.client_repo().to_owned(),
            tool_repo_uri: storage.map(ToolRepositoryStorage::uri),
            storage_origin_id: storage.map(ToolRepositoryStorage::storage_origin_id),
            local_namespace_id: resolution.local_namespace_id().map(str::to_owned),
            skill,
            run_id,
            log_root,
            run_dir,
        }
    }

    /// Validate immutable context identity and select its pinned resolution.
    ///
    /// Disabled context intentionally wins over a newly enabled configuration.
    ///
    /// # Errors
    /// Returns a closed lifecycle error when identity, paths, or storage drifted.
    pub fn validate(
        &self,
        repo_root: &std::path::Path,
        skill: &str,
        run_id: &str,
        active: &RunLogStorageResolution,
        local: &RunLogStorageResolution,
    ) -> Result<RunLogStorageResolution, LifecycleError> {
        if self.schema_version != LIFECYCLE_CONTEXT_SCHEMA_VERSION
            || self.repo_root != repo_root
            || self.skill != skill
            || self.run_id != run_id
        {
            return Err(LifecycleError::new("lifecycle context identity mismatch"));
        }
        if !self.log_root.is_absolute() || self.run_dir != self.log_root.join(skill).join(run_id) {
            return Err(LifecycleError::new(
                "lifecycle context staging path mismatch",
            ));
        }
        let pinned = if self.publication_mode == RunLogStorageMode::Disabled.as_str() {
            if self.client_repo != local.client_repo()
                || self.local_namespace_id != local.local_namespace_id().map(str::to_owned)
                || self.storage_base_uri.is_some()
                || self.tool_repo_uri.is_some()
                || self.storage_origin_id.is_some()
            {
                return Err(LifecycleError::new(
                    "disabled lifecycle context identity mismatch",
                ));
            }
            let reason = match self.storage_resolution_reason.as_str() {
                "config-file-missing" => RunLogStorageReason::ConfigFileMissing,
                "larch-table-missing" => RunLogStorageReason::LarchTableMissing,
                "storage-base-uri-omitted" => RunLogStorageReason::StorageBaseUriOmitted,
                _ => {
                    return Err(LifecycleError::new(
                        "disabled lifecycle context identity mismatch",
                    ));
                }
            };
            return RunLogStorageResolution::new(
                RunLogStorageMode::Disabled,
                reason,
                None,
                self.client_repo.clone(),
                self.local_namespace_id.clone(),
            )
            .map_err(|_| LifecycleError::new("disabled lifecycle context identity mismatch"));
        } else if self.publication_mode == RunLogStorageMode::Enabled.as_str() {
            active
        } else {
            return Err(LifecycleError::new(
                "lifecycle context paths or publication identity are missing",
            ));
        };
        if !self.matches_resolution(pinned) {
            return Err(LifecycleError::new(
                if pinned.mode() == RunLogStorageMode::Disabled {
                    "disabled lifecycle context identity mismatch"
                } else {
                    "configured storage or Git origin changed after lifecycle start"
                },
            ));
        }
        Ok(pinned.clone())
    }

    /// Compare all persisted storage fields with one resolution.
    #[must_use]
    pub fn matches_resolution(&self, resolution: &RunLogStorageResolution) -> bool {
        let storage = resolution.storage();
        self.publication_mode == resolution.mode().as_str()
            && self.storage_resolution_reason == resolution.reason().as_str()
            && self.client_repo == resolution.client_repo()
            && self.storage_base_uri == storage.map(|value| value.base.uri())
            && self.tool_repo_uri == storage.map(ToolRepositoryStorage::uri)
            && self.storage_origin_id == storage.map(ToolRepositoryStorage::storage_origin_id)
            && self.local_namespace_id == resolution.local_namespace_id().map(str::to_owned)
    }
}

/// A run-lifecycle state transition or persisted identity is invalid.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LifecycleError(Box<str>);

impl LifecycleError {
    #[must_use]
    pub fn new(message: impl Into<String>) -> Self {
        Self(message.into().into_boxed_str())
    }
}

impl fmt::Display for LifecycleError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl Error for LifecycleError {}
