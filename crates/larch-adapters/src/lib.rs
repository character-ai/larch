//! Concrete adapters for filesystem, process, Git, time, and service boundaries.

pub mod clock;
pub mod git;
pub mod github;
mod github_actions;
mod github_rest;
pub mod google_auth;
pub mod logging;
pub mod process;
pub mod retry;
pub mod runtime;
pub mod upgrade_larch;

use larch_core::BuildMetadata;

mod file_io;
mod filesystem;

pub use file_io::{
    FileIoError, FileIoErrorKind, atomic_write_bytes, atomic_write_utf8, guarded_update_env,
    read_utf8, rename_same_directory,
};
pub use filesystem::{
    ConfinedPath, PathIntent, PathSafetyError, PathSafetyErrorKind, PluginRoot, RepositoryRoot,
    SecureTempDir, SecureTempFile, TemporaryRoot, normalize_path,
};
pub use git::{
    AddRequest, ApplyRequest, BranchMutationRequest, CheckoutRequest, CleanRequest, CloneRequest,
    CommitMessage, CommitRequest, ConfigMutationRequest, ExactDiffRequest, FetchRequest,
    ForceWithLease, GitCli, GitCliError, GitCliInputError, GitCliInputErrorKind, GitCliPolicy,
    GitCliResult, GitConfigKey, GitFilePath, GitPath, GitRef, GitRefspec, GitRemote, GitToken,
    GitUrl, GixRepository, InitRequest, InterpretTrailersRequest, LsRemoteRequest, MergeRequest,
    PullRequest, PushRequest, RebaseRequest, RemoteMutationRequest, ResetMode, ResetRequest,
    RestoreRequest, RmRequest, SparseCheckoutRequest, StashRequest, SubmoduleRequest,
    TagMutationRequest, VersionRequest, WorktreeRequest, classify_process_error,
};
pub use process::{
    NoopProcessObserver, OpenFileHolderStatus, TokioProcessRunner, probe_open_file_holder,
};

/// Return metadata compiled into the adapter layer.
#[must_use]
pub const fn build_metadata() -> BuildMetadata {
    BuildMetadata::new(env!("CARGO_PKG_VERSION"), env!("LARCH_BUILD_TARGET"))
}

#[cfg(test)]
mod tests {
    use super::build_metadata;

    #[test]
    fn build_metadata_uses_the_workspace_version() {
        assert_eq!(build_metadata().version(), env!("CARGO_PKG_VERSION"));
        assert_eq!(build_metadata().target(), env!("LARCH_BUILD_TARGET"));
    }
}
