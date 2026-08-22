//! Typed Git command runtime shared by bounded CLI operations.

use larch_adapters::{
    ExactDiffRequest, GitCli, GitCliPolicy, GitRef, TokioProcessRunner,
    runtime::{Cancellation, LarchRuntime},
};
use std::path::Path;

/// Runtime-bound typed Git client components for one trusted repository root.
pub struct GitCommandRuntime {
    pub runtime: LarchRuntime,
    pub cancellation: Cancellation,
    pub policy: GitCliPolicy,
    pub runner: TokioProcessRunner,
}

/// Build the canonical exact, name-only diff request shared by CLI readers.
#[must_use]
pub const fn exact_name_only_request(
    base: Option<GitRef>,
    head: Option<GitRef>,
) -> ExactDiffRequest {
    ExactDiffRequest {
        cached: false,
        binary: false,
        no_ext_diff: false,
        numstat_z_rename_50: false,
        unified_context: None,
        name_only: true,
        name_status: false,
        quiet: false,
        exit_code: false,
        base,
        head,
        paths: Vec::new(),
    }
}

impl GitCommandRuntime {
    /// Build typed Git command components for `repository_root`.
    ///
    /// # Errors
    ///
    /// Returns an error when the Git policy or Tokio runtime cannot be created.
    pub fn for_repository(repository_root: &Path) -> Result<Self, String> {
        let policy =
            GitCliPolicy::new(repository_root.to_path_buf()).map_err(|error| error.to_string())?;
        let runtime = LarchRuntime::new().map_err(|error| error.to_string())?;
        Ok(Self {
            runtime,
            cancellation: Cancellation::new(),
            policy,
            runner: TokioProcessRunner::default(),
        })
    }

    /// Return a typed Git CLI client bound to this runtime's repository policy.
    #[must_use]
    pub fn git_cli(&self) -> GitCli<'_, TokioProcessRunner> {
        GitCli::new(&self.runner, self.policy.clone())
    }
}
